"""Şekillendir (Liquify benzeri): fırçayla it/çek, şişir, küçült ve otomatik omuz hizalama.
Yer değiştirme alanı çalışma görüntüsünde hesaplanır; fotoğrafa ve saydamlık haritasına birlikte uygulanır.
Yüz bölgesi (cilt, göz, kaş, burun, ağız) kilitlidir: şekillendirme yüzün hatlarını değiştirmez."""
from __future__ import annotations

import cv2
import numpy as np

from . import face as F

FACE_LBL = (F.SKIN, F.LBROW, F.RBROW, F.LEYE, F.REYE, F.GLASSES, F.NOSE, F.MOUTH, F.ULIP, F.LLIP, F.LEAR, F.REAR)


def face_lock(labels, iod):
    m = np.isin(labels, FACE_LBL).astype(np.uint8)
    k = max(3, int(iod * 0.10)) | 1
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    return cv2.GaussianBlur(m.astype(np.float32), (0, 0), max(2.0, iod * 0.06))


def chin_y(labels):
    ys = np.nonzero(np.isin(labels, (F.SKIN, F.MOUTH, F.ULIP, F.LLIP)).any(1))[0]
    return float(ys.max()) if len(ys) else labels.shape[0] * 0.5


def measure_shoulders(A, labels, iod):
    """Omuz hattı yükseklik farkı (piksel). >0: sol omuz (görüntüde solda) daha aşağıda. None: ölçülemedi."""
    H, W = A.shape
    ys, xs = np.nonzero(np.isin(labels, FACE_LBL))
    if len(xs) < 50:
        return None
    cx = float(np.median(xs))
    cy0 = chin_y(labels)
    mask = A > 0.5
    tops = {}
    for side, (a, b) in (("L", (cx - 2.4 * iod, cx - 1.1 * iod)), ("R", (cx + 1.1 * iod, cx + 2.4 * iod))):
        a, b = int(max(0, a)), int(min(W - 1, b))
        if b - a < 8:
            return None
        vals = []
        for x in range(a, b, max(1, (b - a) // 24)):
            col = np.nonzero(mask[int(cy0 - 0.1 * iod):, x])[0]
            if len(col):
                vals.append(col[0] + int(cy0 - 0.1 * iod))
        if len(vals) < 4:
            return None
        tops[side] = float(np.median(vals))
    return tops["L"] - tops["R"]


def build_maps(shape, labels, iod, ops, omuz_fark=0.0, A=None, kilit=True):
    """(map_x, map_y) float32. ops: [{t:'it'|'sis'|'kuc', pts:[[x,y]..] (0..1), r (genişliğe oranla), guc (0..1)}]."""
    H, W = shape
    dx = np.zeros((H, W), np.float32)
    dy = np.zeros((H, W), np.float32)
    lock = (1 - face_lock(labels, iod)) if kilit else np.ones((H, W), np.float32)
    for op in ops:
        r = max(4.0, op["r"] * W)
        guc = float(op.get("guc", 0.6))
        pts = [(x * W, y * H) for x, y in op["pts"]]
        x0, y0 = int(max(0, min(p[0] for p in pts) - r)), int(max(0, min(p[1] for p in pts) - r))
        x1, y1 = int(min(W, max(p[0] for p in pts) + r + 1)), int(min(H, max(p[1] for p in pts) + r + 1))
        if x1 <= x0 or y1 <= y0:
            continue
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        if op["t"] == "it":
            for i in range(1, len(pts)):
                (ax, ay), (bx, by) = pts[i - 1], pts[i]
                vx, vy = bx - ax, by - ay
                d2 = ((gx - ax) ** 2 + (gy - ay) ** 2) / (r * r)
                w = np.clip(1 - d2, 0, 1) ** 2
                dx[y0:y1, x0:x1] -= vx * w * lock[y0:y1, x0:x1]   # içeriği hareket yönüne taşımak için ters örnekleme
                dy[y0:y1, x0:x1] -= vy * w * lock[y0:y1, x0:x1]
        else:
            sgn = -1.0 if op["t"] == "sis" else 1.0   # şişir: merkezden dışarı; küçült: merkeze doğru
            for (px, py) in pts[:: max(1, len(pts) // 12)]:
                d2 = ((gx - px) ** 2 + (gy - py) ** 2) / (r * r)
                w = np.clip(1 - d2, 0, 1) ** 2 * guc * 0.35
                dx[y0:y1, x0:x1] += sgn * (gx - px) * w * lock[y0:y1, x0:x1]
                dy[y0:y1, x0:x1] += sgn * (gy - py) * w * lock[y0:y1, x0:x1]
    if abs(omuz_fark) > 0.5:
        ys, xs = np.nonzero(np.isin(labels, FACE_LBL))
        cx = float(np.median(xs))
        cy0 = chin_y(labels)
        gx = np.arange(W, dtype=np.float32)[None, :]
        gy = np.arange(H, dtype=np.float32)[:, None]
        half = max(iod * 3.0, 1.0)
        ramp = np.clip(-(gx - cx) / half, -1, 1)               # sol +, sağ −
        zone = np.clip((gy - (cy0 + 0.05 * iod)) / (0.5 * iod), 0, 1)
        zone = zone * zone * (3 - 2 * zone)                      # çeneden aşağısı: yumuşak geçiş
        dy += (omuz_fark / 2.0) * ramp * zone
    X, Y = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    return X + dx, Y + dy


def apply(arr, maps):
    mx, my = maps
    return cv2.remap(arr, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
