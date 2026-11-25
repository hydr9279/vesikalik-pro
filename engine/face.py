"""Yüz bulma (YuNet + simetri ile eğim), yüz bölgeleme (BiSeNet) ve ölçüm noktaları."""
from __future__ import annotations

import math

import cv2
import numpy as np

from . import models
from .paths import model_path

# CelebAMask-HQ sınıfları
SKIN, LBROW, RBROW, LEYE, REYE, GLASSES, LEAR, REAR, EARRING, NOSE, MOUTH, ULIP, LLIP, NECK, NECKL, CLOTH, HAIR, HAT = range(1, 19)

_det = None


def _detector():
    global _det
    if _det is None:
        _det = cv2.FaceDetectorYN.create(model_path("yunet.onnx"), "", (320, 320), 0.7, 0.3, 5000)
    return _det


def detect(img: np.ndarray):
    """Tüm yüzler (güven ≥0,85). Döner: liste[dict(box, re, le, nose, mr, ml, score)] büyükten küçüğe."""
    h, w = img.shape[:2]
    s = min(1.0, 1280.0 / max(h, w))
    small = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else img
    d = _detector()
    d.setInputSize((small.shape[1], small.shape[0]))
    _, faces = d.detect(small)
    if faces is None:
        return []
    good = [f for f in faces if f[14] >= 0.85] or [f for f in faces if f[14] >= 0.7]
    out = []
    for f in good:
        f = f.copy()
        f[:14] /= s
        p = f[4:14].reshape(5, 2).astype(np.float64)
        out.append(dict(box=f[:4].astype(np.float64), re=p[0], le=p[1], nose=p[2], mr=p[3], ml=p[4], score=float(f[14])))
    out.sort(key=lambda d: d["box"][2] * d["box"][3] * d["score"] ** 4, reverse=True)
    return out


def symmetry_angle(img: np.ndarray, f: dict) -> float:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    iod = float(np.linalg.norm(f["le"] - f["re"]))
    c = (f["re"] + f["le"] + f["mr"] + f["ml"]) / 4
    sc, sz = 64.0 / max(iod, 1.0), 128

    def score(a):
        M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), float(a), sc)
        M[:, 2] += [sz / 2 - c[0], sz / 2 - c[1]]
        crop = cv2.warpAffine(g, M, (sz, sz), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        best = -2.0
        for dx in range(-8, 9, 2):
            cc = np.roll(crop, dx, 1)[:, 16:-16]
            a1 = cc - cc.mean()
            best = max(best, float((a1 * a1[:, ::-1]).sum() / max(1e-6, (a1 * a1).sum())))
        return best

    coarse = max(np.arange(-30, 30.1, 2.0), key=score)
    return float(max(np.arange(coarse - 2, coarse + 2.01, 0.5), key=score))


def parse(img: np.ndarray, center, side: float, angle: float):
    """Yüz bölgeleme. Döner: (etiket haritası img boyutunda uint8)."""
    sz = 512
    M = cv2.getRotationMatrix2D((float(center[0]), float(center[1])), angle, sz / side)
    M[:, 2] += [sz / 2 - center[0], sz / 2 - center[1]]
    crop = cv2.warpAffine(img, M, (sz, sz), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    x = models.norm_input(crop, sz, (0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
    out = models.run("parse", {models.session("parse").get_inputs()[0].name: x})[0][0]
    lab = out.argmax(0).astype(np.uint8)
    Minv = cv2.invertAffineTransform(M)
    full = cv2.warpAffine(lab, Minv, (img.shape[1], img.shape[0]), flags=cv2.INTER_NEAREST,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return full, lab, M


def centroid(mask: np.ndarray):
    ys, xs = np.nonzero(mask)
    if len(xs) < 5:
        return None
    return np.array([xs.mean(), ys.mean()], np.float64)


def rot(center, angle):
    return cv2.getRotationMatrix2D((float(center[0]), float(center[1])), angle, 1.0)


def apply(M, p):
    return M[:, :2] @ np.asarray(p, np.float64) + M[:, 2]
