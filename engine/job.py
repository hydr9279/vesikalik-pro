"""Bir fotoğrafın tüm işleme durumu: analiz → maske → rötuş → kadraj → çıktı."""
from __future__ import annotations

import hashlib
import json
import math
import os

import cv2
import numpy as np

from . import face as F
from . import models
from .formats import FORMATS, GRADIENTS, GRADIENT_DEFAULTS, SOLIDS, MM, photo_px
from . import shape as SH
from .finish import DEFAULT_PRO, DEFAULT_KESKIN, skin_sample_mask, portrait_smooth, clone_apply, unsharp
from .imgutil import (imread_any, guided_filter, estimate_foreground, hex2bgr, apply_lut)
from .log import log, log_exc

SS = 2            # çıktıyı 2 kat büyük işle, sonra küçült (kalite)
WORK_FACE_H = 950  # çalışma görüntüsünde yüz kutusu yüksekliği (px)

DEFAULT_MATTE = {"model": "auto", "fon_ayikla": 60, "sac_detay": 70, "yumusaklik": 30, "daraltma": 1, "tasma": 80, "sac_temizle": 0, "sac_renk": 0, "sac_modu": "otomatik", "vitmatte": False}
DEFAULT_RETOUCH = {"leke": 55, "yumusatma": 25, "doku": 70, "parlama": 40, "gozalti": 15, "goz_beyaz": 0,
                   "dis_beyaz": 0, "gozluk": 0, "pozlama": 0, "kontrast": 0, "sicaklik": 0, "oto_beyaz": True,
                   "stil": "", "stil_guc": 100, "spots": [], "geri_al": [],
                   "koruma": 85, "guvenli": True, "fircalar": [], "koruma_fircalar": [],
                   "pro": dict(DEFAULT_PRO), "klon": [], "keskin": dict(DEFAULT_KESKIN)}
DEFAULT_GEOM = {"zoom": 1.0, "dx": 0.0, "dy": 0.0, "rot": 0.0, "duzlestir": True}
DEFAULT_BG = {"tip": "auto", "renk": "#FFFFFF", "degrade": 1, "merkez_x": 0.5, "merkez_y": 0.38, "yayilma": 0.75,
              "sertlik": 1.3, "ic": None, "dis": None, "fon_aydinlat": 35, "fon_temizle": 60}


def _smooth_fill(img, w, rel_sigma):
    """Ağırlıklı (normalize) büyük bulanıklık — küçük ölçekte hesaplanır, hızlıdır."""
    H, W = w.shape
    f = 8
    sw, sh = max(8, W // f), max(8, H // f)
    imgs = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA)
    ws = cv2.resize(w.astype(np.float32), (sw, sh), interpolation=cv2.INTER_AREA)
    k = max(1.0, max(sw, sh) * rel_sigma)
    num = cv2.GaussianBlur(imgs * ws[..., None], (0, 0), k)
    den = cv2.GaussianBlur(ws, (0, 0), k)[..., None] + 1e-4
    return cv2.resize((num / den).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)


def _key(d) -> str:
    return hashlib.md5(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()


class Job:
    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(path)
        self.orig = imread_any(path)
        self.analyzed = False
        self.matted = False
        self.A = None
        self.Wr = None
        self.manuel_rgb = None       # Manuel rötuş yaması (H,W,3) ve değişen piksel maskesi
        self.manuel_m = None
        self.manuel_A = None         # Manuel dekupe/saç maskesi (H,W float) ve değişen piksel maskesi
        self.manuel_Am = None
        self.shape_ops = []          # Şekillendir fırça işlemleri
        self.omuz = 0.0              # uygulanan omuz düzeltmesi (0 = kapalı, 1 = tam düzeltme)
        self._shape_key = None
        self._shape_maps = None
        self._retouch_key = None
        self._fg_cache = None
        self.edits = []
        self.matte_params = dict(DEFAULT_MATTE)
        self.retouch_params = json.loads(json.dumps(DEFAULT_RETOUCH))
        self.geom = dict(DEFAULT_GEOM)
        self.bg = dict(DEFAULT_BG)
        self.warnings = []
        self.spots_found = []

    # ------------------------------------------------------------------ analiz
    def analyze(self, prog=lambda p, m: None):
        prog(0.05, "Yüz aranıyor")
        faces = F.detect(self.orig)
        if not faces:
            raise ValueError("Fotoğrafta yüz bulunamadı.")
        self.face_count = len(faces)
        f0 = faces[0]
        fx, fy, fw, fh = f0["box"]
        H, W = self.orig.shape[:2]
        # çalışma bölgesi: yüz etrafında geniş, aşağıda gövde
        x0 = int(max(0, fx - fw * 2.3)); x1 = int(min(W, fx + fw * 3.3))
        y0 = int(max(0, fy - fh * 1.9)); y1 = int(min(H, fy + fh * 3.8))
        s = min(1.0, WORK_FACE_H / fh)
        self.Wm = np.array([[s, 0, -x0 * s], [0, s, -y0 * s]], np.float64)
        region = self.orig[y0:y1, x0:x1]
        self.W = cv2.resize(region, (max(1, int((x1 - x0) * s)), max(1, int((y1 - y0) * s))),
                            interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
        self.region = (x0, y0, x1, y1)
        self.region_touches_top = y0 == 0 and (fy - fh * 1.9) < 0
        prog(0.2, "Baş eğimi ölçülüyor")
        fW = {k: (F.apply(self.Wm, v) if k not in ("box", "score") else v) for k, v in f0.items()}
        fW["box"] = np.array([fx * s - x0 * s, fy * s - y0 * s, fw * s, fh * s])
        ang = F.symmetry_angle(self.W, fW)
        if abs(ang) < 1.0:
            ang = math.degrees(math.atan2(fW["le"][1] - fW["re"][1], fW["le"][0] - fW["re"][0]))
        self.roll_measured = ang
        prog(0.35, "Yüz bölgeleri ayrıştırılıyor")
        eye_mid0 = (fW["re"] + fW["le"]) / 2
        side = max(fW["box"][2], fW["box"][3]) * 1.75
        center = eye_mid0 + np.array([0, fW["box"][3] * 0.12])
        self.labels, lab_crop, Mc = F.parse(self.W, center, side, ang)
        # Göz merkezleri: bölgeleme (sağ/sol yüz ortasına göre ayrılır), yoksa YuNet
        eyes_all = (self.labels == F.LEYE) | (self.labels == F.REYE)
        mid_x = (fW["re"][0] + fW["le"][0]) / 2
        xs_grid = np.arange(self.labels.shape[1])[None, :]
        iod0 = float(np.linalg.norm(fW["le"] - fW["re"]))
        self.eye_px = {}
        pts = {}
        for side_name, lm, cond in (("r", fW["re"], xs_grid < mid_x), ("l", fW["le"], xs_grid >= mid_x)):
            roi = np.zeros_like(eyes_all)
            cv2.circle(roi.view(np.uint8), (int(lm[0]), int(lm[1])), int(iod0 * 0.38), 1, -1)
            m = eyes_all & cond & roi.astype(bool)
            self.eye_px[side_name] = m
            c = F.centroid(m) if m.sum() > 15 else None
            pts[side_name] = c if c is not None else lm
        re, le = pts["r"], pts["l"]
        self.eye_r, self.eye_l = re, le
        self.iod = float(np.linalg.norm(le - re))
        lips = F.centroid((self.labels == F.ULIP) | (self.labels == F.LLIP) | (self.labels == F.MOUTH))
        self.mouth = lips if lips is not None else (fW["mr"] + fW["ml"]) / 2
        self.nose = F.centroid(self.labels == F.NOSE)
        if self.nose is None:
            self.nose = fW["nose"]
        # düzleştirme açısı: gözlerden (bölgeleme sonrası güvenilir)
        ang2 = math.degrees(math.atan2(le[1] - re[1], le[0] - re[0]))
        self.angle = ang2 if abs(ang2 - ang) < 6 else ang
        self.eye_mid = (le + re) / 2
        # Çene: dik çerçevede yüz sütunundaki en alt cilt pikseli
        self.R = F.rot(self.eye_mid, self.angle)
        Ru = self.R
        lab_u = cv2.warpAffine(self.labels, Ru, (self.W.shape[1], self.W.shape[0]), flags=cv2.INTER_NEAREST)
        e_u = F.apply(Ru, self.eye_mid)
        m_u = F.apply(Ru, self.mouth)
        cx = int(e_u[0])
        band = lab_u[:, max(0, cx - int(self.iod * 0.18)): cx + int(self.iod * 0.18)]
        skin_rows = np.where(((band == F.SKIN) | (band == F.NOSE) | (band == F.LLIP)).mean(1) > 0.5)[0]
        skin_rows = skin_rows[skin_rows > m_u[1]]
        est = m_u[1] + 0.78 * (m_u[1] - e_u[1])
        if len(skin_rows):
            # kesintisiz bloğun sonu (ağızdan aşağı)
            r = skin_rows[0]
            for v in skin_rows[1:]:
                if v - r > 3:
                    break
                r = v
            chin = float(r)
            if not (0.75 * (est - e_u[1]) < chin - e_u[1] < 1.35 * (est - e_u[1])):
                chin = est
        else:
            chin = est
        self.u_eye_y = float(e_u[1])
        self.u_cx = float(e_u[0])
        self.u_chin = chin
        self.u_mouth = float(m_u[1])
        self.lab_u = lab_u
        # tepe: maske hazır olana kadar bölgeleme (saç/örtü) ile tahmin
        hairtop = np.where(((lab_u == F.HAIR) | (lab_u == F.HAT) | (lab_u == F.SKIN))[:, max(0, cx - int(self.iod * 0.6)): cx + int(self.iod * 0.6)].any(1))[0]
        self.u_crown = float(hairtop[0]) if len(hairtop) else self.u_eye_y - (self.u_chin - self.u_eye_y) * 1.05
        self.crown_cut = False
        # göstergeler
        self.yaw = float((F.apply(Ru, self.nose)[0] - e_u[0]) / max(self.iod, 1))
        self.analyzed = True
        prog(0.45, "Analiz tamam")

    # ------------------------------------------------------------------ maske
    def matte(self, prog=lambda p, m: None, force=False):
        if self.matted and not force:
            return
        key = models.best_matte_model(self.matte_params.get("model", "auto"))
        info = models.MODELS[key]
        prog(0.5, f"Arka plan ayrıştırılıyor ({info.get('ad', key)})")
        x = models.norm_input(self.W, info["size"], info["mean"], info["std"])
        s = models.session(key)
        out = np.squeeze(models.run(key, {s.get_inputs()[0].name: x})[0]).astype(np.float32)
        if out.ndim == 3:   # çok kanallı çıktı: ilk kanal
            out = out[0]
        sg = info["sigmoid"]
        if sg is None:   # çıktı zaten 0-1 aralığında mı?
            sg = bool(out.min() < -0.05 or out.max() > 1.05)
        if sg:
            out = 1 / (1 + np.exp(-out))
        out = (out - out.min()) / max(1e-6, out.max() - out.min())
        self.matte_model = key
        self.A_model = cv2.resize(out.astype(np.float32), (self.W.shape[1], self.W.shape[0]), interpolation=cv2.INTER_CUBIC)
        self.A_model = np.clip(self.A_model, 0, 1)
        if self.matte_params.get("vitmatte") and models.has_model("vitmatte"):
            prog(0.6, "Kenar rafine ediliyor (ViTMatte)")
            try:
                self.A_model = self._vitmatte_refine(self.A_model)
            except Exception:
                log_exc("ViTMatte rafine başarısız (atlandı)")
        # en büyük bileşen (yanlış parçaları at)
        b = (self.A_model > 0.5).astype(np.uint8)
        n, lbl, st, _ = cv2.connectedComponentsWithStats(b, 8)
        if n > 2:
            big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
            keep = cv2.dilate((lbl == big).astype(np.uint8), np.ones((9, 9), np.uint8), iterations=3)
            self.A_model *= keep.astype(np.float32)
        prog(0.7, "Saç kenarları iyileştiriliyor")
        I = self.W.astype(np.float32) / 255
        r = max(2, int(max(self.W.shape[:2]) / 400))
        self.A_fine = np.clip(guided_filter(I, self.A_model, r, 1e-4), 0, 1).astype(np.float32)
        self.A_coarse = np.clip(guided_filter(I, self.A_model, r * 3, 1e-2), 0, 1).astype(np.float32)
        # Fon plakası: kişinin arkasındaki fon renginin tahmini (renk farkıyla kenar temizliği için)
        self.Bplate = _smooth_fill(I, np.clip(1 - self.A_model * 1.4, 0, 1) ** 2, 1 / 18)
        self.Idiff = np.linalg.norm(I - self.Bplate, axis=2).astype(np.float32)
        # Ön plan (saç) rengi plakası: kişinin kesin içindeki piksellerden yayılan renk
        self.Fplate = _smooth_fill(I, ((self.A_model > 0.97) & ((self.labels == F.HAIR) | (self.labels == F.HAT))).astype(np.float32), 1 / 30)
        self.A_color = self._color_alpha(I)
        self.matted = True
        self._find_suspicious()
        self.rebuild_alpha()
        prog(0.8, "Maske hazır")

    def _vitmatte_refine(self, A):
        """ViTMatte: mevcut maskeden trimap üretip belirsiz kenar bandını rafine eder (tek 4 kanallı girdi: RGB + trimap)."""
        H, W = A.shape
        k = max(5, int(max(H, W) / 80)) | 1
        fg = cv2.erode((A > 0.95).astype(np.uint8), np.ones((k, k), np.uint8))
        bg = 1 - cv2.dilate((A > 0.05).astype(np.uint8), np.ones((k, k), np.uint8))
        tri = np.full((H, W), 0.5, np.float32)
        tri[fg > 0] = 1.0
        tri[bg > 0] = 0.0
        s = min(1.0, 1024 / max(H, W))
        h2, w2 = int(round(H * s / 32)) * 32 or 32, int(round(W * s / 32)) * 32 or 32
        img = cv2.cvtColor(cv2.resize(self.W, (w2, h2), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        info = models.MODELS["vitmatte"]
        img = (img - np.array(info["mean"], np.float32)) / np.array(info["std"], np.float32)
        t2 = cv2.resize(tri, (w2, h2), interpolation=cv2.INTER_NEAREST)[..., None]
        x = np.concatenate([img, (t2 - 0.5) / 0.5], axis=2).transpose(2, 0, 1)[None].astype(np.float32)
        sess = models.session("vitmatte")
        out = np.squeeze(models.run("vitmatte", {sess.get_inputs()[0].name: x})[0]).astype(np.float32)
        out = np.clip(out, 0, 1)
        out = cv2.resize(out, (W, H), interpolation=cv2.INTER_CUBIC)
        unk = (tri == 0.5)
        return np.where(unk, out, A).astype(np.float32)

    def _find_suspicious(self):
        u = ((self.A_model > 0.12) & (self.A_model < 0.88)).astype(np.uint8)
        # yalnızca belirsizliğin yoğun olduğu yerler (ince saç kenarı değil, kararsız geniş alanlar)
        dens = cv2.blur(u.astype(np.float32), (41, 41))
        u = (dens > 0.45).astype(np.uint8)
        u = cv2.morphologyEx(u, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        n, lbl, st, _ = cv2.connectedComponentsWithStats(u, 8)
        H, W = u.shape
        boxes = []
        for i in np.argsort(-st[1:, cv2.CC_STAT_AREA])[:3] + 1:
            x, y, w, h, a = st[i]
            if a < (self.iod * 0.35) ** 2:
                continue
            region = "saç" if y < self.u_eye_y else "omuz/gövde"
            boxes.append({"x": x / W, "y": y / H, "w": w / W, "h": h / H, "ad": f"{'Saç uçları' if region == 'saç' else 'Omuz kenarı'}"})
        self.suspicious = boxes

    def _color_alpha(self, I):
        """Saç bandında renk-farkı tabanlı alfa: piksel, yerel saç rengi (F) ile fon rengi (B) arasında nerede duruyor."""
        B, Fc = self.Bplate, self.Fplate
        d = Fc - B
        den = np.maximum((d * d).sum(2), 1e-4)
        al = ((I - B) * d).sum(2) / den
        contrast = np.sqrt(den)
        al = np.clip((al - 0.30) / 0.55, 0, 1)
        # fon ile ön plan renkleri birbirine çok yakınsa renk tahmini güvenilmez
        conf = np.clip((contrast - 0.10) / 0.12, 0, 1)
        # artık (model dışı) renk sapması: pikselin rengi B-F doğrusuna yakın olmalı
        proj = B + al[..., None] * d
        res = np.linalg.norm(I - proj, axis=2)
        conf *= np.clip(1 - res / 0.07, 0, 1)
        return (al * conf + (1 - conf) * -1).astype(np.float32)  # -1: güvenilmez

    def _hair_band(self):
        m = self.A_model
        r = max(3, int(max(m.shape) / 160))
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        outer = cv2.dilate((m > 0.25).astype(np.uint8), k, iterations=2)
        inner = cv2.erode((m > 0.92).astype(np.uint8), k, iterations=1)
        band = (outer > 0) & (inner == 0)
        # yalnızca saç / şapka / başörtüsü çevresi ve başın üstü (omuz-gövde kenarı hariç)
        L = self.labels
        near = cv2.dilate(((L == F.HAIR) | (L == F.HAT)).astype(np.uint8), k, iterations=max(2, int(self.iod * 0.08 / r)))
        band &= near > 0
        return cv2.GaussianBlur(band.astype(np.float32), (0, 0), 2.0)

    def rebuild_alpha(self):
        """Ayarlar ve düzeltmelerle son maskeyi oluşturur."""
        p = self.matte_params
        d = p["sac_detay"] / 100.0
        A = self.A_fine * d + self.A_coarse * (1 - d)
        A = np.clip((A - 0.04) / 0.92, 0, 1)
        w = p.get("sac_renk", 0) / 100.0
        if w > 0 and getattr(self, "A_color", None) is not None:
            ac = self.A_color
            ok = ac >= 0
            band = self._hair_band() * ok.astype(np.float32) * w
            # renk tahmini modelin gördüğünden belirgin biçimde daha opaksa (kaçırılmış tel) alfayı yükselt,
            # daha şeffafsa (hale) alçalt
            A = A * (1 - band) + np.minimum(A, np.clip(ac * 1.25, 0, 1)) * band
        if p.get("fon_ayikla", 0) > 0:
            # yarı saydam bölgede rengi fona çok yakın pikselleri (gri hale) temizle
            thr = 0.02 + 0.10 * p["fon_ayikla"] / 100.0
            keep = np.clip((self.Idiff - thr * 0.4) / thr, 0, 1)
            soft = (A > 0.02) & (A < 0.9)
            prot = cv2.dilate(((self.labels > 0) & (self.labels != F.HAIR) & (self.labels != F.HAT)).astype(np.uint8),
                              np.ones((9, 9), np.uint8))
            A = np.where(soft & (prot == 0), A * keep, A)
        Hh, Ww = A.shape
        for e in self.edits:
            if e["t"] == "sam":
                m = e.get("_mask")
                if m is None:
                    m = self._sam_mask(e["x"] * Ww, e["y"] * Hh)
                    e["_mask"] = m
                ms = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.5)
                A = np.maximum(A, ms) if e["pos"] else np.minimum(A, 1 - ms)
            elif e["t"] == "brush":
                m = np.zeros_like(A)
                r = max(1, int(e["r"] * Ww))
                pts = [(int(x * Ww), int(y * Hh)) for x, y in e["pts"]]
                for i, pt in enumerate(pts):
                    cv2.circle(m, pt, r, 1.0, -1, cv2.LINE_AA)
                    if i:
                        cv2.line(m, pts[i - 1], pt, 1.0, 2 * r, cv2.LINE_AA)
                soft = max(0.5, (1 - e.get("hard", 0.6)) * r * 0.6)
                m = cv2.GaussianBlur(m, (0, 0), soft)
                A = np.maximum(A, m) if e["add"] else np.minimum(A, 1 - m)
        if p["sac_temizle"] > 0:
            k = max(3, int(self.iod * 0.02 + self.iod * 0.06 * p["sac_temizle"] / 100)) | 1
            opened = cv2.morphologyEx(A, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
            protect = cv2.dilate(((self.labels > 0) & (self.labels != F.HAIR)).astype(np.uint8), np.ones((15, 15), np.uint8))
            s = p["sac_temizle"] / 100.0
            A = np.where(protect > 0, A, A * (1 - s) + opened * s)
        if p["daraltma"] > 0:
            k = 2 * int(p["daraltma"]) + 1
            A = cv2.erode(A, np.ones((k, k), np.uint8))
        if p["yumusaklik"] > 0:
            A = cv2.GaussianBlur(A, (0, 0), 0.3 + p["yumusaklik"] / 100.0 * 2.0)
        A = np.clip(A, 0, 1).astype(np.float32)
        if self.manuel_A is not None and self.manuel_Am is not None and self.manuel_A.shape == A.shape:
            A = np.where(self.manuel_Am, self.manuel_A, A)   # manuel dekupe/saç düzeltmesi
        self.A = A
        self._fg_cache = None
        self._crown()

    def _sam_mask(self, px, py):
        H, W = self.W.shape[:2]
        side = int(max(H, W) * 0.55)
        x0 = int(np.clip(px - side / 2, 0, max(0, W - side))); y0 = int(np.clip(py - side / 2, 0, max(0, H - side)))
        crop = self.W[y0:y0 + side, x0:x0 + side]
        ch, cw = crop.shape[:2]
        img = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB), (640, 640)).astype(np.float32) / 255
        pts = np.array([[[[(px - x0) * 640 / cw, (py - y0) * 640 / ch]]]], np.float32)
        lbl = np.array([[[1]]], np.float32)
        out = models.run("sam", {"batched_images": img.transpose(2, 0, 1)[None], "batched_point_coords": pts,
                                 "batched_point_labels": lbl})[0]
        m = cv2.resize(out[0, 0, 0].astype(np.float32), (cw, ch)) >= 0
        full = np.zeros((H, W), np.uint8)
        full[y0:y0 + ch, x0:x0 + cw] = m
        return full

    def _crown(self):
        """Başın tepesi (saç/örtü dahil), dik çerçevede."""
        Au = cv2.warpAffine(self.A, self.R, (self.W.shape[1], self.W.shape[0]), flags=cv2.INTER_LINEAR)
        cx = int(self.u_cx)
        w = int(self.iod * 0.8)
        band = Au[:, max(0, cx - w): cx + w]
        frac = (band > 0.5).mean(1)
        r = int(self.u_eye_y)
        while r > 0 and frac[r - 1] > 0.08:
            r -= 1
        self.u_crown = float(r)
        self.crown_cut = r <= 2 and self.region_touches_top
        est = self.u_eye_y - (self.u_chin - self.u_eye_y) * 1.05
        if self.u_chin - r > 2.6 * (self.u_chin - self.u_eye_y):  # anormal: maske hatası
            self.u_crown = est

    def add_edit(self, e: dict):
        self.edits.append(e)
        self.rebuild_alpha()

    def undo_edit(self):
        if self.edits:
            self.edits.pop()
            self.rebuild_alpha()


    # ------------------------------------------------------------------ koruma / fırça haritaları
    def _stroke_mask(self, strokes, key="r"):
        H, W = self.labels.shape
        out = np.zeros((H, W), np.float32)
        for e in strokes:
            m = np.zeros((H, W), np.float32)
            r = max(1, int(e["r"] * W))
            pts = [(int(x * W), int(y * H)) for x, y in e["pts"]]
            for i, pt in enumerate(pts):
                cv2.circle(m, pt, r, 1.0, -1, cv2.LINE_AA)
                if i:
                    cv2.line(m, pts[i - 1], pt, 1.0, 2 * r, cv2.LINE_AA)
            soft = max(0.5, (1 - e.get("hard", 0.4)) * r * 0.6)
            m = cv2.GaussianBlur(m, (0, 0), soft) * float(e.get("val", 1.0))
            out = np.maximum(out, m)
        return out

    def _auto_skin_samples(self):
        """Ten örneği seçilmediyse yüz noktalarından otomatik örnek: yanaklar ve alın (piksel)."""
        L = self.labels
        out = []
        for lbl in (F.SKIN,):
            ys, xs = np.nonzero(L == lbl)
            if len(xs) > 50:
                for q in ((25, 50), (75, 50), (50, 20), (50, 70)):
                    cx, cy = np.percentile(xs, q[0]), np.percentile(ys, q[1])
                    d = (xs - cx) ** 2 + (ys - cy) ** 2
                    i = int(np.argmin(d))
                    out.append((float(xs[i]), float(ys[i])))
        return out

    def _protect(self, img):
        """Rötuşun dokunmaması gereken ince detaylar: kirpik, kaş, dudak, burun delikleri, bıyık/sakal (1=korunur)."""
        p = self.retouch_params
        L, iod = self.labels, max(self.iod, 1.0)
        H, W = L.shape
        el = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        prot = np.zeros((H, W), np.float32)
        eyes = ((L == F.LEYE) | (L == F.REYE)).astype(np.uint8)
        prot = np.maximum(prot, cv2.dilate(eyes, el(max(2, int(iod * 0.11)))).astype(np.float32))
        brows = ((L == F.LBROW) | (L == F.RBROW)).astype(np.uint8)
        prot = np.maximum(prot, cv2.dilate(brows, el(max(2, int(iod * 0.04)))).astype(np.float32))
        lips = ((L == F.MOUTH) | (L == F.ULIP) | (L == F.LLIP)).astype(np.uint8)
        prot = np.maximum(prot, cv2.dilate(lips, el(max(2, int(iod * 0.035)))).astype(np.float32))
        nose = (L == F.NOSE)
        if nose.sum() > 20:
            ys, xs = np.nonzero(nose)
            y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
            lowy = int(y0 + (y1 - y0) * 0.55)
            pad = int((x1 - x0) * 0.12)
            prot[lowy:y1 + int(iod * 0.05), max(0, x0 - pad):x1 + pad] = 1.0
        # bıyık / sakal / kirli sakal: alt yüzde cilde göre koyu veya dokulu bölgeler
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        Lc = lab[..., 0]
        k = (max(9, int(iod * 0.6)) | 1)
        med = cv2.medianBlur(Lc, min(k, 151))
        dark = (med.astype(np.int16) - Lc.astype(np.int16)) > 14
        f32 = Lc.astype(np.float32)
        mu = cv2.blur(f32, (7, 7))
        sd = np.sqrt(np.maximum(cv2.blur(f32 * f32, (7, 7)) - mu * mu, 0))
        low = np.zeros((H, W), np.uint8)
        low[int(self.u_eye_y + iod * 0.9):, :] = 1
        facearea = cv2.dilate(((L == F.SKIN) | (L == F.NOSE) | (L == F.MOUTH) | (L == F.ULIP) | (L == F.LLIP)).astype(np.uint8), el(int(iod * 0.05)))
        hair = ((dark | (sd > 9)) & (low > 0) & (facearea > 0)).astype(np.uint8)
        hair = cv2.morphologyEx(hair, cv2.MORPH_CLOSE, el(max(2, int(iod * 0.03))))
        n, lbl, st, _ = cv2.connectedComponentsWithStats(hair, 8)
        keep = np.zeros(n, bool)
        keep[1:] = st[1:, cv2.CC_STAT_AREA] > (iod * 0.04) ** 2
        hair = keep[lbl].astype(np.uint8)
        prot = np.maximum(prot, cv2.dilate(hair, el(max(2, int(iod * 0.03)))).astype(np.float32))
        prot = cv2.GaussianBlur(prot, (0, 0), max(1.0, iod * 0.012))
        prot = np.clip(prot * (p.get("koruma", 85) / 100.0), 0, 1)
        if p.get("koruma_fircalar"):
            prot = np.maximum(prot, self._stroke_mask(p["koruma_fircalar"]))
        return prot.astype(np.float32)

    def protect_overlay(self, img):
        pr = self._protect(self.W)
        a = (pr * 0.55)[..., None]
        col = np.array([80, 200, 90], np.float32)
        return np.clip(img.astype(np.float32) * (1 - a) + col * a, 0, 255).astype(np.uint8)

    # ------------------------------------------------------------------ rötuş
    def retouch(self, prog=lambda p, m: None):
        p = self.retouch_params
        key = _key(p)
        if self.Wr is not None and key == self._retouch_key:
            return
        img = self.W.copy()
        L = self.labels
        iod = self.iod
        skin = ((L == F.SKIN) | (L == F.NOSE)).astype(np.uint8)
        skin_core = cv2.erode(skin, np.ones((5, 5), np.uint8), iterations=max(1, int(iod * 0.02)))
        prot = self._protect(self.W)
        skin_core = (skin_core * (prot < 0.25)).astype(np.uint8)
        # yüz kutusu (işlemi hızlandırmak için)
        ys, xs = np.nonzero((L > 0) & (L != F.CLOTH))
        if len(xs) == 0:
            self.Wr = img
            self._retouch_key = key
            return
        bx0, bx1 = max(0, xs.min() - 20), min(img.shape[1], xs.max() + 20)
        by0, by1 = max(0, ys.min() - 20), min(img.shape[0], ys.max() + 20)

        # 1) Leke / sivilce
        spots = np.zeros(L.shape, np.uint8)
        if p["leke"] > 0:
            prog(0.55, "Lekeler aranıyor")
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            k = max(5, int(iod * 0.25)) | 1
            k = min(k, 99)
            Lc = lab[..., 0]
            med = cv2.medianBlur(Lc, k)
            dark = (med.astype(np.int16) - Lc.astype(np.int16)) > np.interp(p["leke"], [0, 100], [30, 8])
            A_ = lab[..., 1]
            amed = cv2.medianBlur(A_, k)
            red = (A_.astype(np.int16) - amed.astype(np.int16)) > np.interp(p["leke"], [0, 100], [16, 5])
            cand = ((dark | red) & (skin_core > 0)).astype(np.uint8)
            n, lbl, st, _ = cv2.connectedComponentsWithStats(cand, 8)
            max_area = math.pi * (iod * 0.07) ** 2
            min_area = max(2, (iod * 0.008) ** 2)
            ok = np.zeros(n, bool)
            ok[1:] = (st[1:, cv2.CC_STAT_AREA] < max_area) & (st[1:, cv2.CC_STAT_AREA] >= min_area)
            spots = ok[lbl].astype(np.uint8)
            spots = (spots * (prot < 0.25)).astype(np.uint8)
            # kullanıcının geri aldığı lekeler
            Hh, Ww = L.shape
            for ux, uy in p.get("geri_al", []):
                cv2.circle(spots, (int(ux * Ww), int(uy * Hh)), int(iod * 0.06), 0, -1)
            self.spots_found = []
            n2, lbl2, st2, cen2 = cv2.connectedComponentsWithStats(spots, 8)
            for i in range(1, n2):
                self.spots_found.append([float(cen2[i][0] / Ww), float(cen2[i][1] / Hh)])
        Hh, Ww = L.shape
        for sx, sy, sr in p.get("spots", []):
            cv2.circle(spots, (int(sx * Ww), int(sy * Hh)), max(2, int(sr * Ww)), 1, -1)
        # 2) Gözlük yansıması
        if p["gozluk"] > 0 and (L == F.GLASSES).sum() > iod * 2:
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            g = cv2.dilate((L == F.GLASSES).astype(np.uint8), np.ones((9, 9), np.uint8))
            lens = cv2.dilate(((L == F.LEYE) | (L == F.REYE)).astype(np.uint8), np.ones((3, 3), np.uint8),
                              iterations=int(iod * 0.12))
            region = (g | lens) & ~((L == F.LEYE) | (L == F.REYE)).astype(bool)
            hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]
            thr = np.interp(p["gozluk"], [0, 100], [0.35, 0.15])
            glare = (val > 235) & (sat < 40)
            tint = (hue > 35) & (hue < 105) & (sat > 255 * thr)
            gm = ((glare | tint) & region).astype(np.uint8)
            gm = cv2.dilate(gm, np.ones((5, 5), np.uint8), iterations=2)
            spots = np.maximum(spots, gm)
        if spots.any():
            skey = hashlib.md5(spots.tobytes()).hexdigest()
            if getattr(self, "_inpaint_key", None) == skey:
                img = self._inpainted
            else:
                prog(0.62, "Lekeler onarılıyor (LaMa)")
                sp = cv2.dilate(spots, np.ones((3, 3), np.uint8), iterations=max(1, int(iod * 0.012)))
                img = self._inpaint(img, sp, (bx0, by0, bx1, by1))
                self._inpaint_key, self._inpainted = skey, img

        f = img.astype(np.float32)
        skin_soft = cv2.GaussianBlur(skin.astype(np.float32), (0, 0), max(1.5, iod * 0.02)) * (1 - prot)
        yum = min(p["yumusatma"], 70) if p.get("guvenli", True) else p["yumusatma"]
        doku = max(p["doku"], 45) if p.get("guvenli", True) else p["doku"]
        # 3) Yumuşatma (doku korunarak)
        if yum > 0:
            prog(0.7, "Cilt yumuşatılıyor")
            sub = img[by0:by1, bx0:bx1]
            d = max(5, int(iod * 0.08))
            sm = cv2.bilateralFilter(sub, d, 14 + yum * 0.3, d * 1.6).astype(np.float32)
            fs = sub.astype(np.float32)
            fine = fs - cv2.GaussianBlur(fs, (0, 0), max(0.8, iod * 0.006))
            target = sm + fine * (doku / 100.0)
            a = (yum / 100.0) * 0.9 * skin_soft[by0:by1, bx0:bx1, None]
            f[by0:by1, bx0:bx1] = fs * (1 - a) + target * a
        # 4) Parlama
        if p["parlama"] > 0:
            u8 = np.clip(f, 0, 255).astype(np.uint8)
            hsv = cv2.cvtColor(u8, cv2.COLOR_BGR2HSV).astype(np.float32)
            V, S = hsv[..., 2], hsv[..., 1]
            base = cv2.GaussianBlur(f, (0, 0), max(3, iod * 0.15))
            sh = np.clip((V - 180) / 60.0, 0, 1) * np.clip((120 - S) / 80.0, 0, 1)
            sh = cv2.GaussianBlur(sh, (0, 0), max(1.5, iod * 0.03)) * skin_soft
            a = sh[..., None] * (p["parlama"] / 100.0) * 0.85
            f = f * (1 - a) + np.minimum(f, base * 0.98 + (f - base) * 0.25) * a
        # 5) Göz altı
        if p["gozalti"] > 0:
            eyes = ((L == F.LEYE) | (L == F.REYE)).astype(np.uint8)
            M = np.float32([[1, 0, 0], [0, 1, iod * 0.18]])
            under = cv2.warpAffine(cv2.dilate(eyes, np.ones((3, 3), np.uint8), iterations=int(iod * 0.06)), M, (Ww, Hh))
            under = (under & skin & ~eyes.astype(bool)).astype(np.float32)
            under = cv2.GaussianBlur(under, (0, 0), iod * 0.05)
            lab = cv2.cvtColor(np.clip(f, 0, 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
            lab[..., 0] += under * p["gozalti"] / 100.0 * 14
            f = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32)
        # 6) Göz ve diş beyazlatma
        for amount, mask_cls, smax, vmin in ((p["goz_beyaz"], (F.LEYE, F.REYE), 90, 90), (p["dis_beyaz"], (F.MOUTH,), 110, 80)):
            if amount <= 0:
                continue
            u8 = np.clip(f, 0, 255).astype(np.uint8)
            hsv = cv2.cvtColor(u8, cv2.COLOR_BGR2HSV).astype(np.float32)
            m = np.isin(L, mask_cls) & (hsv[..., 1] < smax) & (hsv[..., 2] > vmin)
            m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2)
            k = amount / 100.0
            hsv[..., 1] *= 1 - 0.5 * k * m
            hsv[..., 2] = np.minimum(255, hsv[..., 2] * (1 + 0.12 * k * m))
            f = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
        # 6b) Gelişmiş portre rötuşu (ten örneklerine göre; korunan ince detaylara dokunmaz)
        pro = {**DEFAULT_PRO, **(p.get("pro") or {})}
        if pro.get("acik") and pro.get("miktar", 0) > 0:
            prog(0.8, "Gelişmiş portre rötuşu")
            u8 = np.clip(f, 0, 255).astype(np.uint8)
            smp = [(x * Ww, y * Hh) for x, y in pro.get("ornekler", [])]
            if not smp:
                smp = self._auto_skin_samples()
            sm = skin_sample_mask(u8, smp, iod, tol=float(pro.get("tolerans", 24))) if smp else skin_soft
            wide = cv2.GaussianBlur(cv2.dilate(skin, np.ones((5, 5), np.uint8), iterations=max(1, int(iod * 0.03))).astype(np.float32), (0, 0), max(1.5, iod * 0.02))
            msk = np.minimum(sm, wide) * (1 - prot) * (float(pro.get("yayilma", 100)) / 100.0)
            f = portrait_smooth(u8, msk, iod, pro).astype(np.float32)
        # 6c) Klon damgası
        if p.get("klon"):
            f = clone_apply(f, p["klon"], iod)
        if p.get("fircalar"):
            rs = self._stroke_mask(p["fircalar"])[..., None]
            f = f * (1 - rs) + self.W.astype(np.float32) * rs
        out = np.clip(f, 0, 255).astype(np.uint8)
        # 7) Işık ve renk (tüm görüntü)
        out = self._tone(out, p)
        # 8) Keskinleştirme (Unsharp Mask)
        ks = {**DEFAULT_KESKIN, **(p.get("keskin") or {})}
        if ks.get("miktar", 0) > 0:
            out = unsharp(out, ks, iod, skin_soft)
        if self.manuel_rgb is not None and self.manuel_m is not None and self.manuel_rgb.shape == out.shape:
            out = np.where(self.manuel_m[..., None], self.manuel_rgb, out)   # manuel rötuş yaması (son katman)
        self.Wr = out
        self._retouch_key = key
        self._fg_cache = None

    def _inpaint(self, img, mask, bbox):
        x0, y0, x1, y1 = bbox
        side = max(x1 - x0, y1 - y0)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        H, W = img.shape[:2]
        sx0 = int(np.clip(cx - side // 2, 0, max(0, W - side))); sy0 = int(np.clip(cy - side // 2, 0, max(0, H - side)))
        crop = img[sy0:sy0 + side, sx0:sx0 + side]
        mcrop = mask[sy0:sy0 + side, sx0:sx0 + side]
        ch, cw = crop.shape[:2]
        if models.has_model("lama"):
            try:
                x = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB), (512, 512), interpolation=cv2.INTER_AREA)
                x = x.astype(np.float32).transpose(2, 0, 1)[None] / 255
                mm = (cv2.resize(mcrop, (512, 512), interpolation=cv2.INTER_NEAREST) > 0).astype(np.float32)[None, None]
                o = models.run("lama", {"image": x, "mask": mm})[0][0].transpose(1, 2, 0)
                o = cv2.cvtColor(np.clip(o, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
                o = cv2.resize(o, (cw, ch), interpolation=cv2.INTER_CUBIC)
                # LaMa düşük çözünürlüklü; dokuyu korumak için yüksek frekansı orijinalden komşu alandan taşı
                soft = cv2.GaussianBlur(mcrop.astype(np.float32), (0, 0), 1.5)[..., None]
                res = crop.astype(np.float32) * (1 - soft) + o.astype(np.float32) * soft
                out = img.copy()
                out[sy0:sy0 + ch, sx0:sx0 + cw] = np.clip(res, 0, 255).astype(np.uint8)
                return out
            except Exception as e:
                log(f"LaMa hatası: {e}", "WARN")
        return cv2.inpaint(img, mask, 5, cv2.INPAINT_TELEA)

    def _tone(self, img, p):
        f = img.astype(np.float32)
        if p.get("oto_beyaz") and self.A is not None:
            bgm = (self.A < 0.05)
            if bgm.sum() > 1000:
                mean = f[bgm].mean(0)
                gray = mean.mean()
                gains = np.clip(gray / np.maximum(mean, 1), 0.85, 1.15)
                f *= gains
        if p["sicaklik"]:
            t = p["sicaklik"] / 100.0
            f[..., 2] *= 1 + 0.08 * t
            f[..., 0] *= 1 - 0.08 * t
        if p["pozlama"]:
            f *= 2 ** (p["pozlama"] / 100.0)
        if p["kontrast"]:
            c = p["kontrast"] / 100.0
            x = np.clip(f / 255, 0, 1)
            s = x * x * (3 - 2 * x)
            f = (x + (s - x) * c * 1.5) * 255
        out = np.clip(f, 0, 255).astype(np.uint8)
        if p.get("stil"):
            lut = load_style(p["stil"])
            if lut is not None:
                out = apply_lut(out, lut, p.get("stil_guc", 100) / 100.0)
        return out

    # ------------------------------------------------------------------ kadraj
    def transform(self, fmt: dict, scale_mult: float = SS):
        """Çalışma görüntüsü → çıktı tuvali (2x3), tuval boyutu, mm başına piksel."""
        g = self.geom
        ppm = MM * scale_mult
        Wc, Hc = int(round(fmt["gen_mm"] * ppm)), int(round(fmt["yuk_mm"] * ppm))
        ang = self.angle if g.get("duzlestir", True) else 0.0
        R = F.rot(self.eye_mid, ang)
        e_u = np.array([self.u_cx, self.u_eye_y])
        if not g.get("duzlestir", True):
            e_u = self.eye_mid
        s = (fmt["chin_mm"] - fmt["eye_mm"]) * ppm / max(1.0, self.u_chin - self.u_eye_y) * g["zoom"]
        tx = Wc / 2 + g["dx"] * ppm
        ty = fmt["eye_mm"] * ppm + g["dy"] * ppm
        S = np.array([[s, 0, tx - s * e_u[0]], [0, s, ty - s * e_u[1]], [0, 0, 1]])
        M = S @ np.vstack([R, [0, 0, 1]])
        if g.get("rot"):
            Rm = cv2.getRotationMatrix2D((tx, ty), -g["rot"], 1.0)
            M = np.vstack([Rm, [0, 0, 1]]) @ M
        return M[:2], (Wc, Hc), ppm, s

    def measures(self, fmt: dict) -> dict:
        M, (Wc, Hc), ppm, s = self.transform(fmt, 1)
        Rinv = cv2.invertAffineTransform(self.R)
        crown = F.apply(Rinv, (self.u_cx, self.u_crown))
        chin = F.apply(Rinv, (self.u_cx, self.u_chin))
        eye = self.eye_mid
        c_mm = F.apply(M, crown)[1] / ppm
        ch_mm = F.apply(M, chin)[1] / ppm
        e_mm = F.apply(M, eye)[1] / ppm
        return {"tepe_mm": round(c_mm, 1), "cene_mm": round(ch_mm, 1), "goz_mm": round(e_mm, 1),
                "bas_mm": round(ch_mm - c_mm, 1), "merkez_mm": round(F.apply(M, eye)[0] / ppm, 1)}

    def omuz_fark(self):
        """Ölçülen omuz yükseklik farkı (piksel); yoksa None."""
        if self.A is None or self.labels is None:
            return None
        return SH.measure_shoulders(self.A, self.labels, self.iod)

    def _shaped(self, arr):
        """Şekillendir uygulanmışsa yer değiştirme alanını görüntüye uygular."""
        if not self.shape_ops and not self.omuz:
            return arr
        fark = (self.omuz_fark() or 0.0) * float(self.omuz) if self.omuz else 0.0
        key = _key([self.shape_ops, round(fark, 1)])
        if key != self._shape_key:
            self._shape_maps = SH.build_maps(self.labels.shape, self.labels, self.iod, self.shape_ops, fark)
            self._shape_key = key
        return SH.apply(arr, self._shape_maps)

    def _foreground(self):
        if self._fg_cache is None:
            I = self.Wr.astype(np.float32) / 255
            Fg = estimate_foreground(I, self.A)
            t = self.matte_params["tasma"] / 100.0
            Fg = Fg * t + I * (1 - t)
            self._fg_cache = np.clip(Fg * 255, 0, 255).astype(np.uint8)
        return self._fg_cache

    def render(self, fmt: dict, preview: bool = True, show_alpha: bool = False, stage: str = "final", mult=None):
        """Kadrajlanmış fotoğraf. preview=True: mult× tuval (varsayılan 1x), değilse 300 DPI son çıktı."""
        if mult is None:
            mult = 1 if preview else SS
        M, (Wc, Hc), ppm, s = self.transform(fmt, mult)
        src = self.Wr if (self.Wr is not None and stage != "raw") else self.W
        if stage != "raw":
            src = self._shaped(src)
        interp = cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC
        if s < 0.5:
            # kenar yumuşaması (aliasing) önlemi
            k = int(1 / s)
            src = cv2.GaussianBlur(src, (0, 0), 0.4 * k)
        canvas = cv2.warpAffine(src, M, (Wc, Hc), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        if self.A is None:
            return self._finish(canvas, fmt, preview)
        A = cv2.warpAffine(self._shaped(self.A) if stage != "raw" else self.A, M, (Wc, Hc), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        if show_alpha:
            return (A * 255).astype(np.uint8)
        bg = self.bg
        tip = bg["tip"]
        if tip == "auto":
            tip = "original" if fmt["fon"] == "original" else "solid"
        if tip == "original":
            out = canvas.astype(np.float32)
            inv = (1 - A)[..., None]
            if bg.get("fon_temizle", 0) > 0:
                smooth = _smooth_fill(out, 1 - A, 1 / 25)
                t = bg["fon_temizle"] / 100.0
                out = out * (1 - inv * t) + smooth * inv * t
            if bg.get("fon_aydinlat", 0) > 0:
                t = bg["fon_aydinlat"] / 100.0 * 0.6
                out = out + (255 - out) * t * inv
            out = np.clip(out, 0, 255).astype(np.uint8)
        else:
            Fg = cv2.warpAffine(self._shaped(self._foreground()), M, (Wc, Hc), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            back = self._background(fmt, bg, tip, Wc, Hc)
            a = A[..., None]
            out = np.clip(Fg.astype(np.float32) * a + back * (1 - a), 0, 255).astype(np.uint8)
        return self._finish(out, fmt, preview)

    def _background(self, fmt, bg, tip, Wc, Hc):
        if tip == "solid":
            col = bg.get("renk") or SOLIDS.get(fmt["fon"], "#FFFFFF")
            if bg["tip"] == "auto":
                col = SOLIDS.get(fmt["fon"], "#FFFFFF")
            return np.ones((Hc, Wc, 3), np.float32) * hex2bgr(col)
        g = next((x for x in GRADIENTS if x["no"] == int(bg.get("degrade", 1))), GRADIENTS[0])
        c1 = hex2bgr(bg.get("ic") or g["ic"])
        c2 = hex2bgr(bg.get("dis") or g["dis"])
        yy, xx = np.mgrid[0:Hc, 0:Wc].astype(np.float32)
        if g["tip"] == "kose":
            d = np.sqrt((xx / Wc - 1.0) ** 2 + (yy / Hc) ** 2) / 1.35
            t = np.clip(d, 0, 1) ** 1.1
        else:
            d = np.sqrt((xx / Wc - bg["merkez_x"]) ** 2 + ((yy / Hc - bg["merkez_y"]) * Hc / Wc * 0.75) ** 2)
            t = np.clip(d / max(0.05, bg["yayilma"]), 0, 1) ** bg["sertlik"]
        back = c1 * (1 - t[..., None]) + c2 * t[..., None]
        rng = np.random.default_rng(7)
        return back + rng.normal(0, 0.8, back.shape).astype(np.float32)

    def _finish(self, img, fmt, preview):
        if preview:
            return img
        Wf, Hf = photo_px(fmt)
        img = cv2.resize(img, (Wf, Hf), interpolation=cv2.INTER_AREA)
        bl = cv2.GaussianBlur(img, (0, 0), 1.0)
        return cv2.addWeighted(img, 1.3, bl, -0.3, 0)

    # ------------------------------------------------------------------ uygunluk
    def compliance(self, fmt: dict) -> list:
        L = self.labels
        iod = max(self.iod, 1)
        strict = fmt.get("strict", True)
        res = []

        def add(ad, durum, deger):
            res.append({"ad": ad, "durum": durum, "deger": deger})

        add("Tek yüz", "ok" if self.face_count == 1 else "warn",
            "Evet" if self.face_count == 1 else f"{self.face_count} yüz bulundu")
        heights = []
        for k in ("r", "l"):
            ys, xs = np.nonzero(self.eye_px[k])
            heights.append((ys.max() - ys.min() + 1) / iod if len(ys) > 15 else None)
        known = [h for h in heights if h is not None]
        glasses_amt = (L == F.GLASSES).sum() / iod ** 2
        if not known:
            add("Gözler açık", "warn", "Ölçülemedi — gözlük/yansıma, kontrol edin")
        elif min(known) < 0.07:
            add("Gözler açık", "bad", "Kapalı / kısık olabilir")
        else:
            add("Gözler açık", "ok", "Açık")
        mouth = (L == F.MOUTH).sum() / iod ** 2
        add("Ağız kapalı", "ok" if mouth < 0.03 else ("warn" if mouth < 0.07 else "bad"),
            "Kapalı" if mouth < 0.03 else "Dudaklar aralık / dişler görünüyor")
        yaw = abs(self.yaw)
        add("Baş dönüklüğü", "ok" if yaw < 0.06 else ("warn" if yaw < 0.12 else "bad"), f"{yaw * 60:.0f}° civarı")
        roll = abs(self.roll_measured)
        add("Baş eğikliği", "ok" if roll < 4 else "warn", f"{roll:.1f}° (otomatik düzeltildi)" if self.geom.get("duzlestir", True) else f"{roll:.1f}°")
        m = self.measures(fmt)
        hmin, hmax = fmt["head_min"], fmt["head_max"]
        add("Baş ölçüsü", "ok" if hmin <= m["bas_mm"] <= hmax else "warn", f"{m['bas_mm']} mm ({hmin}–{hmax})")
        add("Başın üstü", "ok" if (m["tepe_mm"] > 1.0 and not getattr(self, "crown_cut", False)) else "warn",
            f"{m['tepe_mm']} mm boşluk" if m["tepe_mm"] > 1 else "Kadraja çok yakın / kesik")
        # ışık dengesi: yüzün sol ve sağ yarısı
        skin = ((L == F.SKIN) | (L == F.NOSE))
        g = cv2.cvtColor(self.W, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32)
        xs = np.nonzero(skin)[1]
        if len(xs) > 100:
            cx = self.eye_mid[0]
            left = g[skin & (np.arange(g.shape[1])[None, :] < cx)]
            right = g[skin & (np.arange(g.shape[1])[None, :] >= cx)]
            if len(left) > 50 and len(right) > 50:
                diff = abs(left.mean() - right.mean()) / max(left.mean(), right.mean())
                add("Işık dengesi", "ok" if diff < 0.08 else ("warn" if diff < 0.15 else "bad"), f"Sol/sağ fark %{diff * 100:.0f}")
            mean = g[skin].mean()
            add("Pozlama", "ok" if 120 < mean < 225 else "warn", "Uygun" if 120 < mean < 225 else ("Koyu" if mean <= 120 else "Çok açık"))
        # netlik
        ys, xs2 = np.nonzero(skin)
        if len(xs2):
            crop = cv2.cvtColor(self.W[ys.min():ys.max(), xs2.min():xs2.max()], cv2.COLOR_BGR2GRAY)
            lv = cv2.Laplacian(crop, cv2.CV_64F).var() if crop.size else 0
            add("Netlik", "ok" if lv > 25 else "warn", "Keskin" if lv > 25 else "Hafif bulanık")
        # kırmızı göz
        eyes = (L == F.LEYE) | (L == F.REYE)
        if eyes.sum() > 20:
            b, gch, r = [self.W[..., i][eyes].astype(np.float32) for i in range(3)]
            red = ((r > 2.0 * gch) & (r > 2.0 * b) & (r > 120)).mean()
            add("Kırmızı göz", "ok" if red < 0.15 else "bad", "Yok" if red < 0.15 else "Var")
        if glasses_amt > 0.03:
            add("Gözlük", "bad" if strict else "warn", "Biyometrikte kabul edilmez" if strict else "Var — yansımayı kontrol edin")
        else:
            add("Gözlük", "ok", "Yok")
        if self.A is not None and self.bg.get("tip") == "original":
            add("Fon", "ok", "Orijinal fon")
        return res


# ---------------------------------------------------------------------- stil profilleri
_STYLE_CACHE = {}


def styles_dir():
    from .paths import data_dir
    d = os.path.join(data_dir(), "stiller")
    os.makedirs(d, exist_ok=True)
    return d


def load_style(name: str):
    if name in _STYLE_CACHE:
        return _STYLE_CACHE[name]
    p = os.path.join(styles_dir(), name + ".npy")
    if not os.path.exists(p):
        return None
    lut = np.load(p)
    _STYLE_CACHE[name] = lut
    return lut


def save_style(name: str, lut):
    np.save(os.path.join(styles_dir(), name + ".npy"), lut)
    _STYLE_CACHE[name] = lut


def list_styles():
    return sorted(f[:-4] for f in os.listdir(styles_dir()) if f.endswith(".npy"))
