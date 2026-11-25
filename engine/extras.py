"""Polaroid (Instax Square) ve Serbest Baskı modülleri — yüz tanıma yok, kırpmasız + bulanık dolgu varsayılanı."""
from __future__ import annotations

import os

import cv2
import numpy as np

LINE = (164, 164, 164)
DPI = 300


def mm(v: float) -> int:
    return int(round(v / 25.4 * DPI))


PAPERS = {  # serbest baskı kağıtları (mm, dikey)
    "10x15": (100, 150),
    "13x18": (130, 180),
    "15x21": (150, 210),
}


def adjust(img, p: dict):
    """Ortak renk ayarları: poz (EV), parlaklık, kontrast, doygunluk, sıcaklık."""
    if not p:
        return img
    f = img.astype(np.float32)
    ev = float(p.get("poz", 0))
    if ev:
        f = f * (2 ** ev)
    b = float(p.get("parlaklik", 0))
    if b:
        f = f + b * 1.2
    c = float(p.get("kontrast", 0)) / 100.0
    if c:
        x = np.clip(f / 255, 0, 1)
        s = x * x * (3 - 2 * x)
        f = (x + (s - x) * c * 1.5) * 255
    t = float(p.get("sicaklik", 0)) / 100.0
    if t:
        f[..., 2] *= 1 + 0.08 * t
        f[..., 0] *= 1 - 0.08 * t
    sat = float(p.get("doygunluk", 0)) / 100.0
    if sat:
        hsv = cv2.cvtColor(np.clip(f, 0, 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[..., 1] = np.clip(hsv[..., 1] * (1 + sat), 0, 255)
        f = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    return np.clip(f, 0, 255).astype(np.uint8)


def fit_blur(img, W: int, H: int, p: dict | None = None):
    """Fotoğrafı W×H alana kırpmadan yerleştirir; boşluklar aynı fotoğrafın bulanık hali.
    p: zoom (1=sığdır), dx, dy (alan genişliği/yüksekliği oranı), rot (derece), mod ('sigdir'|'doldur')."""
    p = p or {}
    ih, iw = img.shape[:2]
    rot = float(p.get("rot", 0))
    zoom = float(p.get("zoom", 1.0))
    mode = p.get("mod", "sigdir")
    # arka plan: kapsayan boyut + güçlü bulanıklık
    cover = max(W / iw, H / ih)
    bs = cv2.resize(img, (max(8, int(iw * cover / 8)), max(8, int(ih * cover / 8))), interpolation=cv2.INTER_AREA)
    bs = cv2.GaussianBlur(bs, (0, 0), 6)
    bg = cv2.resize(bs, (int(iw * cover) + 1, int(ih * cover) + 1), interpolation=cv2.INTER_CUBIC)
    y0, x0 = (bg.shape[0] - H) // 2, (bg.shape[1] - W) // 2
    bg = bg[y0:y0 + H, x0:x0 + W].astype(np.float32) * 0.92
    s = (max(W / iw, H / ih) if mode == "doldur" else min(W / iw, H / ih)) * zoom
    M = cv2.getRotationMatrix2D((iw / 2, ih / 2), -rot, s)
    M[:, 2] += [W / 2 - iw / 2 + float(p.get("dx", 0)) * W, H / 2 - ih / 2 + float(p.get("dy", 0)) * H]
    fg = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC if s >= 1 else cv2.INTER_AREA, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    mask = cv2.warpAffine(np.ones((ih, iw), np.float32), M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    mask = cv2.GaussianBlur(mask, (0, 0), 0.8)[..., None]
    out = fg.astype(np.float32) * mask + bg * (1 - mask)
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- Polaroid (Instax Square)
CARD_MM = (72, 86)
PHOTO_MM = 62
CARD_PX = (mm(CARD_MM[0]), mm(CARD_MM[1]))
PHOTO_PX = mm(PHOTO_MM)


def _font(size):
    from PIL import ImageFont
    for f in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def polaroid_card(img, p: dict | None = None):
    cw, ch = CARD_PX
    card = np.full((ch, cw, 3), 255, np.uint8)
    p = p or {}
    ph = fit_blur(adjust(img, p), PHOTO_PX, PHOTO_PX, p)
    x = (cw - PHOTO_PX) // 2
    y = x
    card[y:y + PHOTO_PX, x:x + PHOTO_PX] = ph
    return card


def polaroid_frame_card(metin: str = "HAYAL MEDYA", alt: str = "0312 264 0 888", stil: int = 1):
    """Tek kalan yarım sayfa için Hayal Medya özel çerçevesi (içi boş, süslü kart)."""
    from PIL import Image, ImageDraw
    cw, ch = CARD_PX
    im = Image.new("RGB", (cw, ch), (255, 255, 255))
    d = ImageDraw.Draw(im)
    x = (cw - PHOTO_PX) // 2
    # fotoğraf alanı: açık krem zemin + ince çift çizgi
    d.rectangle([x, x, x + PHOTO_PX, x + PHOTO_PX], fill=(244, 240, 232))
    d.rectangle([x + 18, x + 18, x + PHOTO_PX - 18, x + PHOTO_PX - 18], outline=(205, 196, 180), width=3)
    fb, fs = _font(46), _font(30)
    tw = d.textlength(metin, font=fb)
    d.text(((cw - tw) / 2, x + PHOTO_PX / 2 - 40), metin, fill=(120, 108, 90), font=fb)
    tw = d.textlength("Fotoğraf Stüdyosu", font=fs)
    d.text(((cw - tw) / 2, x + PHOTO_PX / 2 + 24), "Fotoğraf Stüdyosu", fill=(150, 140, 122), font=fs)
    tw = d.textlength(alt, font=fs)
    d.text(((cw - tw) / 2, x + PHOTO_PX + 40), alt, fill=(140, 130, 112), font=fs)
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def polaroid_sheets(cards: list):
    """İki kart yatay yan yana, 10x15 yatay sayfa; çıktı kağıda uygun (dikey 1181x1772) döndürülmüş."""
    pages = []
    PW, PH = mm(150), mm(100)  # yatay 10x15
    cw, ch = CARD_PX
    for i in range(0, len(cards), 2):
        pair = cards[i:i + 2]
        if len(pair) == 1:
            pair.append(polaroid_frame_card())
        sheet = np.full((PH, PW, 3), 255, np.uint8)
        x0 = (PW - 2 * cw) // 2
        y0 = (PH - ch) // 2
        for k, c in enumerate(pair):
            x = x0 + k * cw
            sheet[y0:y0 + ch, x:x + cw] = c
        # ince gri kesim çizgileri (kart kenarları)
        for k in range(3):
            x = x0 + k * cw
            sheet[y0 - 20:y0 + ch + 20, min(PW - 1, x)] = LINE
        for y in (y0, y0 + ch):
            sheet[y, x0 - 20:x0 + 2 * cw + 20] = LINE
        pages.append(cv2.rotate(sheet, cv2.ROTATE_90_CLOCKWISE))
    return pages


# ---------------------------------------------------------------- Serbest baskı
def free_print(img, paper: str, p: dict | None = None):
    """Tek bir baskı: kağıt boyutunda (fotoğrafın yönüne göre dik/yatay), kırpmasız + bulanık dolgu."""
    pw, ph = PAPERS.get(paper, PAPERS["10x15"])
    ih, iw = img.shape[:2]
    p = p or {}
    W, H = mm(pw), mm(ph)
    if iw > ih:
        W, H = H, W
    return fit_blur(adjust(img, p), W, H, p)


def free_name(orig: str, paper: str, adet: int) -> str:
    base = os.path.splitext(os.path.basename(orig))[0]
    return f"{paper}_{adet}adet_{base}.jpg"
