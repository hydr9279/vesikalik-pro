"""Görüntü yardımcıları: okuma/yazma, rehberli filtre, ön plan rengi tahmini, LUT."""
from __future__ import annotations

import base64
import io

import cv2
import numpy as np
from PIL import Image, ImageOps

from .formats import DPI


# Desteklenen girdi biçimleri (JPG, PNG, TIFF, WebP, JFIF, HEIC/HEIF, AVIF, BMP ve kamera RAW)
RAW_EXTS = (".nef", ".nrw", ".dng", ".cr2", ".cr3", ".arw", ".orf", ".rw2", ".raf", ".pef", ".srw")
IMG_EXTS = (".jpg", ".jpeg", ".jfif", ".jpe", ".png", ".tif", ".tiff", ".bmp", ".webp",
            ".heic", ".heif", ".avif") + RAW_EXTS
_HEIF_OK = None


def _heif():
    global _HEIF_OK
    if _HEIF_OK is None:
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
            try:
                pillow_heif.register_avif_opener()
            except Exception:
                pass
            _HEIF_OK = True
        except Exception:
            _HEIF_OK = False
    return _HEIF_OK


def is_image(name: str) -> bool:
    return str(name).lower().endswith(IMG_EXTS)


def _open_any(path: str) -> Image.Image:
    low = path.lower()
    if low.endswith(RAW_EXTS):
        import rawpy
        with rawpy.imread(path) as raw:
            rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=False, output_bps=8, half_size=False)
        return Image.fromarray(rgb)
    if low.endswith((".heic", ".heif", ".avif")):
        if not _heif():
            raise RuntimeError("HEIC/AVIF desteği yüklenemedi (pillow-heif).")
    else:
        _heif()
    return Image.open(path)


def imread_any(path: str) -> np.ndarray:
    """Türkçe karakterli yol + EXIF yönü + renk profili (sRGB'ye çevirir) + şeffaflık (beyaza). BGR uint8."""
    im = _open_any(path)
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        zemin = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        im = Image.alpha_composite(zemin, rgba).convert("RGB")
    elif im.mode in ("I;16", "I;16B", "I", "F"):
        a = np.asarray(im).astype(np.float32)
        a = a / (a.max() or 1) * 255
        im = Image.fromarray(a.astype(np.uint8)).convert("RGB")
    icc = im.info.get("icc_profile")
    if icc:
        try:
            from PIL import ImageCms
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            name = ImageCms.getProfileDescription(src) or ""
            if "sRGB" not in name:
                im = ImageCms.profileToProfile(im.convert("RGB"), src, ImageCms.createProfile("sRGB"))
        except Exception:
            pass
    im = im.convert("RGB")
    return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)


def save_jpeg(img_bgr: np.ndarray, path: str, quality: int = 100) -> None:
    im = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    try:
        from PIL import ImageCms
        icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    except Exception:
        icc = None
    kw = dict(quality=quality, dpi=(DPI, DPI), subsampling=0, optimize=True)
    if icc:
        kw["icc_profile"] = icc
    im.save(path, "JPEG", **kw)


def to_b64(img_bgr: np.ndarray, max_side: int = 1400, quality: int = 88) -> str:
    h, w = img_bgr.shape[:2]
    s = min(1.0, max_side / max(h, w))
    if s < 1:
        img_bgr = cv2.resize(img_bgr, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def png_b64(gray: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", gray)
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode()


def hex2bgr(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)], np.float32)


def box(x: np.ndarray, r: int) -> np.ndarray:
    k = 2 * max(1, int(r)) + 1
    return cv2.boxFilter(x, -1, (k, k), borderType=cv2.BORDER_REFLECT)


def guided_filter(I: np.ndarray, p: np.ndarray, r: int, eps: float) -> np.ndarray:
    """Renkli rehberli filtre. I: HxWx3 float32 0..1, p: HxW float32."""
    mean_I = box(I, r)
    mean_p = box(p, r)
    cov_Ip = box(I * p[..., None], r) - mean_I * mean_p[..., None]
    var = np.empty(I.shape[:2] + (3, 3), np.float32)
    for i in range(3):
        for j in range(i, 3):
            v = box(I[..., i] * I[..., j], r) - mean_I[..., i] * mean_I[..., j]
            var[..., i, j] = v
            var[..., j, i] = v
    var += np.eye(3, dtype=np.float32) * eps
    a = np.linalg.solve(var, cov_Ip[..., None])[..., 0]
    b = mean_p - np.einsum("hwc,hwc->hw", a, mean_I)
    return np.einsum("hwc,hwc->hw", box(a, r), I) + box(b, r)


def estimate_foreground(img: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Saç kenarlarındaki eski fon rengini temizler (blur-fusion). img 0..1 float."""
    a = alpha[..., None]
    eps = 1e-5
    big = max(30, int(max(img.shape[:2]) / 25))

    def fuse(F, B, r):
        ba = box(alpha, r)[..., None]
        bF = box(F * a, r) / (ba + eps)
        bB = box(B * (1 - a), r) / ((1 - ba) + eps)
        F2 = bF + a * (img - a * bF - (1 - a) * bB)
        return np.clip(F2, 0, 1), bB

    F, B = fuse(img, img, big)
    F, _ = fuse(F, B, 6)
    return F


def apply_lut(img_bgr: np.ndarray, lut: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """3B LUT (N×N×N×3, RGB 0..1) uygular — üç doğrusal ara değer."""
    n = lut.shape[0]
    x = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0 * (n - 1)
    i0 = np.clip(np.floor(x).astype(np.int32), 0, n - 2)
    f = x - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
    fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
    out = np.zeros_like(x)
    for dr in (0, 1):
        wr = fr if dr else 1 - fr
        for dg in (0, 1):
            wg = fg if dg else 1 - fg
            for db in (0, 1):
                wb = fb if db else 1 - fb
                out += wr * wg * wb * lut[r0 + dr, g0 + dg, b0 + db]
    res = cv2.cvtColor(np.clip(out * 255, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    if strength < 1:
        res = cv2.addWeighted(res, strength, img_bgr, 1 - strength, 0)
    return res


def learn_lut(pairs: list, n: int = 17) -> np.ndarray:
    """Öncesi/sonrası çiftlerinden renk stilini öğrenir (3B LUT)."""
    acc = np.zeros((n, n, n, 3), np.float64)
    cnt = np.zeros((n, n, n), np.float64)
    for before, after in pairs:
        h, w = before.shape[:2]
        s = 900 / max(h, w)
        b = cv2.resize(before, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        a = cv2.resize(after, (b.shape[1], b.shape[0]), interpolation=cv2.INTER_AREA)
        b = cv2.cvtColor(b, cv2.COLOR_BGR2RGB).reshape(-1, 3).astype(np.float64) / 255
        a = cv2.cvtColor(a, cv2.COLOR_BGR2RGB).reshape(-1, 3).astype(np.float64) / 255
        idx = np.clip(np.round(b * (n - 1)).astype(int), 0, n - 1)
        flat = idx[:, 0] * n * n + idx[:, 1] * n + idx[:, 2]
        for c in range(3):
            acc[..., c] += np.bincount(flat, a[:, c], n ** 3).reshape(n, n, n)
        cnt += np.bincount(flat, None, n ** 3).reshape(n, n, n)
    grid = np.stack(np.meshgrid(*[np.linspace(0, 1, n)] * 3, indexing="ij"), -1)
    lut = grid.copy()
    known = cnt > 3
    lut[known] = acc[known] / cnt[known][:, None]
    # boş hücreler: kimlik + bilinen komşuların ortalama farkı (yumuşak)
    diff = np.zeros_like(lut)
    diff[known] = lut[known] - grid[known]
    w = known.astype(np.float64)
    for _ in range(6):
        k = np.ones((3, 3, 3)) if False else None
        d2 = np.zeros_like(diff)
        w2 = np.zeros_like(w)
        for ax in range(3):
            for sh in (-1, 1):
                d2 += np.roll(diff * w[..., None], sh, axis=ax)
                w2 += np.roll(w, sh, axis=ax)
        fill = (~known) & (w2 > 0)
        diff[fill] = d2[fill] / w2[fill][:, None]
        w = np.maximum(w, (w2 > 0).astype(np.float64) * 0.5)
        known = known | fill
    return np.clip(grid + diff, 0, 1).astype(np.float32)
