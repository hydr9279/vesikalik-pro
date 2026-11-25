"""10x15 baskı sayfaları (Hayal Medya referans dizimleri) ve yazıcı test sayfası."""
from __future__ import annotations

import cv2
import numpy as np

from .formats import PAPER_10x15, mm2px, MM

LINE = (164, 164, 164)      # biyometrik / vize kesim çizgisi #A4A4A4
FRAME = (121, 121, 121)     # vesikalık çerçevesi #797979


def blank():
    W, H = PAPER_10x15["px"]
    return np.full((H, W, 3), 255, np.uint8)


def _joined(sheet, cells, x0, y0, cw, ch, cols, rows, line=LINE, outer_lr=True):
    """Bitişik ızgara: fotoğraflar arasında ve çevresinde tek 1 px çizgi."""
    H, W = sheet.shape[:2]
    i = 0
    for r in range(rows):
        for c in range(cols):
            if i >= len(cells):
                break
            x = x0 + c * (cw + 1) + 1
            y = y0 + r * (ch + 1) + 1
            ph = cells[i]
            ph = cv2.resize(ph, (cw, ch), interpolation=cv2.INTER_AREA) if ph.shape[:2] != (ch, cw) else ph
            xe, ye = min(W, x + cw), min(H, y + ch)
            sheet[y:ye, max(0, x):xe] = ph[: ye - y, max(0, -x): xe - x]
            i += 1
    used_rows = (len(cells) + cols - 1) // cols
    for r in range(used_rows + 1):
        y = y0 + r * (ch + 1)
        if 0 <= y < H:
            sheet[y, max(0, x0): min(W, x0 + cols * (cw + 1) + 1)] = line
    for c in range(cols + 1):
        x = x0 + c * (cw + 1)
        if (c in (0, cols)) and not outer_lr:
            continue
        if 0 <= x < W:
            sheet[max(0, y0): min(H, y0 + used_rows * (ch + 1) + 1), x] = line
    return sheet


def sheet_for(fmt_id: str, fmt: dict, photo: np.ndarray, adet: int) -> np.ndarray:
    W, H = PAPER_10x15["px"]
    sheet = blank()
    ph, pw = photo.shape[:2]
    if fmt["dizim"] == "bitisik":
        # Biyometrik: kağıdın sağ-sol kenarına yaslı, üstten 107 px
        cw = (W - 1) // 2
        _joined(sheet, [photo] * 4, -1, fmt.get("ust_px", 107), cw, ph, 2, 2, outer_lr=False)
        return sheet
    if fmt["dizim"] == "cerceveli":
        # Vesikalık: ayrı kutular, 2 px koyu gri çerçeve
        boxes = [(49, 99), (597, 99), (49, 889), (597, 889)]
        for (x, y) in boxes:
            sheet[y:y + ph + 4, x:x + pw + 4] = FRAME
            sheet[y + 2:y + 2 + ph, x + 2:x + 2 + pw] = photo
        return sheet
    # Vize: ortalı, bitişik; 8 adet sığmazsa fotoğraflar yan çevrilir
    n = 8 if adet >= 8 else 4
    cand = []
    for rotated in (False, True):
        p = np.ascontiguousarray(np.rot90(photo)) if rotated else photo
        h, w = p.shape[:2]
        for cols in (1, 2, 3, 4):
            rows = -(-n // cols)
            gw, gh = cols * (w + 1) + 1, rows * (h + 1) + 1
            if gw <= W and gh <= H:
                cand.append((rotated, cols, rows, p, abs(gw / W - gh / H)))
    if not cand:
        # ABD / Hindistan 5,08 cm: iki sütun kağıda tam sığmaz → hücre 1 px daraltılır
        cw = (W - 1) // 2 - 1
        p = photo[:, (pw - cw) // 2:(pw - cw) // 2 + cw]
        rows = -(-n // 2)
        gw, gh = 2 * (cw + 1) + 1, rows * (ph + 1) + 1
        return _joined(sheet, [p] * n, (W - gw) // 2, (H - gh) // 2, cw, ph, 2, rows)
    rotated, cols, rows, p, _ = sorted(cand, key=lambda c: (c[1] * c[2] != n, c[0], c[4]))[0]
    h, w = p.shape[:2]
    gw, gh = cols * (w + 1) + 1, rows * (h + 1) + 1
    return _joined(sheet, [p] * n, (W - gw) // 2, (H - gh) // 2, w, h, cols, rows)


def max_count(fmt: dict) -> list:
    return fmt.get("adetler", [4])


def test_page() -> np.ndarray:
    """Yazıcı ölçek testi: 10x15 kağıtta mm cetvelleri ve 50x60 kutu."""
    W, H = PAPER_10x15["px"]
    s = blank()
    ink = (40, 40, 40)
    # kenar işaretleri
    cv2.rectangle(s, (0, 0), (W - 1, H - 1), (180, 180, 180), 1)
    # yatay cetvel 0–80 mm
    x0, y0 = mm2px(10), mm2px(20)
    for mmv in range(0, 81):
        x = x0 + int(round(mmv * MM))
        L = 50 if mmv % 10 == 0 else (32 if mmv % 5 == 0 else 18)
        cv2.line(s, (x, y0), (x, y0 + L), ink, 2 if mmv % 10 == 0 else 1)
        if mmv % 10 == 0:
            cv2.putText(s, str(mmv), (x - 12, y0 + 85), cv2.FONT_HERSHEY_SIMPLEX, 0.9, ink, 2, cv2.LINE_AA)
    # dikey cetvel 0–120 mm
    x1, y1 = mm2px(10), mm2px(32)
    for mmv in range(0, 121):
        y = y1 + int(round(mmv * MM))
        L = 50 if mmv % 10 == 0 else (32 if mmv % 5 == 0 else 18)
        cv2.line(s, (x1, y), (x1 + L, y), ink, 2 if mmv % 10 == 0 else 1)
        if mmv % 10 == 0 and mmv:
            cv2.putText(s, str(mmv), (x1 + 60, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, ink, 2, cv2.LINE_AA)
    # 50x60 biyometrik kutu
    bx, by = mm2px(38), mm2px(45)
    cv2.rectangle(s, (bx, by), (bx + mm2px(50), by + mm2px(60)), (0, 0, 200), 2)
    cv2.putText(s, "50 x 60 mm", (bx + 120, by + mm2px(30)), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 200), 2, cv2.LINE_AA)
    cv2.putText(s, "HAYAL MEDYA - Yazici olcek testi", (mm2px(10), mm2px(130)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, ink, 2, cv2.LINE_AA)
    cv2.putText(s, "Cetvelleri gercek cetvelle olcun: 80 mm ve 120 mm", (mm2px(10), mm2px(137)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, ink, 2, cv2.LINE_AA)
    return s
