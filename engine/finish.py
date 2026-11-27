"""Son aşama rötuş araçları: gelişmiş portre yumuşatma (Imagenomic benzeri), klon damgası, keskinleştirme (Unsharp Mask)."""
from __future__ import annotations

import cv2
import numpy as np

DEFAULT_PRO = {"acik": False, "miktar": 60, "ince": 4, "orta": 5, "kaba": 3, "esik": 55, "tolerans": 24, "yayilma": 100,
               "ornekler": []}
DEFAULT_KESKIN = {"miktar": 0, "yaricap": 1.0, "esik": 0, "cilt_koru": True}


def skin_sample_mask(img_bgr, samples, iod, tol=24, feather=1.0):
    """Seçilen ten örneklerine renk bakımından benzeyen yerler (0..1). samples: [(x,y)] piksel."""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    H, W = lab.shape[:2]
    d = np.full((H, W), 1e9, np.float32)
    r = max(2, int(iod * 0.04))
    wts = np.array([0.6, 1.4, 1.4], np.float32)
    for (x, y) in samples:
        x, y = int(np.clip(x, r, W - r - 1)), int(np.clip(y, r, H - r - 1))
        p = lab[y - r:y + r, x - r:x + r].reshape(-1, 3).mean(0)
        d = np.minimum(d, np.sqrt((((lab - p) ** 2) * wts).sum(2)))
    m = np.clip(1 - (d - tol) / (tol * 0.8), 0, 1)
    return cv2.GaussianBlur(m, (0, 0), max(1.0, iod * 0.012 * feather))


def portrait_smooth(img_bgr, mask, iod, p):
    """3 ölçekli eşikli yumuşatma. mask: 0..1 uygulanacak yer. p: DEFAULT_PRO sözlüğü."""
    K = float(p.get("miktar", 60)) / 100.0
    if K <= 0:
        return img_bgr
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = lab[..., 0]
    scales = [(iod * 0.012, p.get("ince", 4)), (iod * 0.03, p.get("orta", 5)), (iod * 0.07, p.get("kaba", 3))]
    T = max(2.0, 20.0 * float(p.get("esik", 55)) / 55.0 * 0.9)
    cur, res = L, np.zeros_like(L)
    for sig, amt in scales:
        g = cv2.GaussianBlur(cur, (0, 0), max(0.8, sig))
        band = cur - g
        a = float(np.clip(amt / 10.0 * K * 1.6, 0, 1))
        keep = np.clip(np.abs(band) / T, 0, 1) ** 1.5
        res += band * (a * keep + (1 - a))
        cur = g
    new = cur + res
    m = np.clip(mask, 0, 1)
    out = lab.copy()
    out[..., 0] = L * (1 - m) + new * m
    for c in (1, 2):
        g = cv2.GaussianBlur(lab[..., c], (0, 0), iod * 0.03)
        out[..., c] = lab[..., c] * (1 - m * 0.5 * K) + g * m * 0.5 * K
    return cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def clone_apply(f, ops, iod):
    """Klon damgası. f: float32 BGR (yerinde değişir). ops: [{pts:[[x,y]..] (0..1), src:[x,y] (0..1, ilk noktanın kaynağı),
    r (genişliğe oranla), hard (0..1), val (opaklık 0..1)}]. Her vuruş için kapsama haritası tek seferde karıştırılır
    (üst üste bindirmede opaklık birikmez)."""
    H, W = f.shape[:2]
    for op in ops:
        pts = [(x * W, y * H) for x, y in op["pts"]]
        if not pts:
            continue
        ox, oy = op["src"][0] * W - pts[0][0], op["src"][1] * H - pts[0][1]
        r = max(2, int(op["r"] * W))
        hard = float(op.get("hard", 0.4))
        val = float(op.get("val", 1.0))
        m = np.zeros((H, W), np.float32)
        for i, pt in enumerate(pts):
            c = (int(round(pt[0])), int(round(pt[1])))
            cv2.circle(m, c, r, 1.0, -1, cv2.LINE_AA)
            if i:
                cv2.line(m, (int(round(pts[i - 1][0])), int(round(pts[i - 1][1]))), c, 1.0, 2 * r, cv2.LINE_AA)
        soft = max(0.5, (1 - hard) * r * 0.6)
        m = cv2.GaussianBlur(m, (0, 0), soft) * val
        M = np.float32([[1, 0, -ox], [0, 1, -oy]])
        shifted = cv2.warpAffine(f, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        f[:] = f * (1 - m[..., None]) + shifted * m[..., None]
    return f


def unsharp(img_bgr, p, iod, skin_w=None):
    """Unsharp Mask (yalnızca parlaklık kanalında). miktar %, yaricap piksel (çözünürlüğe göre ölçeklenir), esik seviye."""
    amt = float(p.get("miktar", 0)) / 100.0
    if amt <= 0:
        return img_bgr
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L = lab[..., 0]
    rad = max(0.4, float(p.get("yaricap", 1.0)) * max(1.0, iod / 80.0))
    blur = cv2.GaussianBlur(L, (0, 0), rad)
    d = L - blur
    thr = float(p.get("esik", 0))
    if thr > 0:
        d = np.where(np.abs(d) >= thr, d, 0)
    k = amt
    if p.get("cilt_koru", True) and skin_w is not None:
        k = amt * (1 - 0.6 * np.clip(skin_w, 0, 1))
    lab[..., 0] = np.clip(L + d * k * 1.5, 0, 255)
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
