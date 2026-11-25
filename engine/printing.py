"""Windows yazdırma (pywin32): yazıcı listesi, profil, ölçek düzeltme, kenarsız 10x15, test sayfası.

Görüntü yazıcıya fiziksel ölçüsüyle gönderilir (300 DPI → yazıcının kendi DPI'sı), 'sayfaya sığdır' yapılmaz.
Profil: {"kagit_gen_mm":100,"kagit_yuk_mm":150,"olcek_x":1.0,"olcek_y":1.0,"kaydir_x_mm":0,"kaydir_y_mm":0,"devmode":{...}}
"""
from __future__ import annotations

import sys

import numpy as np

from .log import log

WIN = sys.platform.startswith("win")

KNOWN = {
    "mitsubishi": {"ad": "Mitsubishi CP-D70W", "not": "Termal yazıcı. Sürücüde kağıt: 6x4 (152x102). Kenarsız varsayılan."},
    "l7180": {"ad": "Epson L7180", "not": "Sürücüde: Kağıt 10x15 cm, Kenarsız açık, Genişletme miktarı EN AZ (Min)."},
    "l850": {"ad": "Epson L850", "not": "Sürücüde: Kağıt 10x15 cm, Kenarsız açık, Genişletme miktarı EN AZ (Min)."},
}


def default_profile(name: str) -> dict:
    n = name.lower()
    hint = next((v["not"] for k, v in KNOWN.items() if k in n.replace(" ", "")), "")
    return {"kagit_gen_mm": 100.0, "kagit_yuk_mm": 150.0, "olcek_x": 1.0, "olcek_y": 1.0,
            "kaydir_x_mm": 0.0, "kaydir_y_mm": 0.0, "not": hint, "serbest": "mitsubishi" not in n.replace(" ", "").lower()}


def list_printers() -> list:
    if not WIN:
        return []
    import win32print
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    names = [p[2] for p in win32print.EnumPrinters(flags)]
    return names


def default_printer() -> str:
    if not WIN:
        return ""
    import win32print
    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        return ""


def _devmode_from(printer: str, saved: dict | None):
    import win32print
    h = win32print.OpenPrinter(printer)
    try:
        dm = win32print.GetPrinter(h, 2)["pDevMode"]
        if saved:
            for k, v in saved.items():
                if k == "DriverData":
                    try:
                        dm.DriverData = bytes.fromhex(v)
                    except Exception:
                        pass
                elif hasattr(dm, k):
                    try:
                        setattr(dm, k, v)
                    except Exception:
                        pass
        return dm
    finally:
        win32print.ClosePrinter(h)


_DM_FIELDS = ("Orientation", "PaperSize", "PaperLength", "PaperWidth", "Copies", "PrintQuality", "Color",
              "MediaType", "DitherType", "Fields")


def printer_dialog(printer: str, saved: dict | None, hwnd: int = 0) -> dict | None:
    """Sürücünün kendi ayar penceresi (kenarsız, kağıt türü vb.). Seçilen ayarları döndürür."""
    if not WIN:
        return None
    import win32con
    import win32print
    h = win32print.OpenPrinter(printer)
    try:
        dm = _devmode_from(printer, saved)
        res = win32print.DocumentProperties(hwnd, h, printer, dm, dm,
                                            win32con.DM_IN_PROMPT | win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER)
        if res != 1:  # İptal
            return None
        out = {k: getattr(dm, k) for k in _DM_FIELDS if hasattr(dm, k)}
        try:
            out["DriverData"] = bytes(dm.DriverData).hex()
        except Exception:
            pass
        return out
    finally:
        win32print.ClosePrinter(h)


def print_image(img_bgr: np.ndarray, printer: str, profile: dict, copies: int = 1, title: str = "Vesikalik Pro") -> None:
    """300 DPI görüntüyü gerçek ölçüsünde basar."""
    if not WIN:
        raise RuntimeError("Yazdırma yalnızca Windows'ta çalışır.")
    import win32con
    import win32gui
    import win32print
    import win32ui
    from PIL import Image, ImageWin
    import cv2

    dm = _devmode_from(printer, profile.get("devmode"))
    try:
        dm.Copies = max(1, int(copies))
        dm.Fields |= win32con.DM_COPIES
    except Exception:
        pass
    hdc_raw = win32gui.CreateDC("WINSPOOL", printer, dm)
    hdc = win32ui.CreateDCFromHandle(hdc_raw)
    try:
        dpi_x = hdc.GetDeviceCaps(win32con.LOGPIXELSX)
        dpi_y = hdc.GetDeviceCaps(win32con.LOGPIXELSY)
        off_x = hdc.GetDeviceCaps(win32con.PHYSICALOFFSETX)
        off_y = hdc.GetDeviceCaps(win32con.PHYSICALOFFSETY)
        phys_w = hdc.GetDeviceCaps(win32con.PHYSICALWIDTH)
        phys_h = hdc.GetDeviceCaps(win32con.PHYSICALHEIGHT)
        h, w = img_bgr.shape[:2]
        # sayfa yatay ise görüntüyü çevir
        if (phys_w > phys_h) != (w > h):
            img_bgr = np.ascontiguousarray(np.rot90(img_bgr, -1))
            h, w = img_bgr.shape[:2]
        tw = int(round(w / 300.0 * dpi_x * profile.get("olcek_x", 1.0)))
        th = int(round(h / 300.0 * dpi_y * profile.get("olcek_y", 1.0)))
        # kağıdın ortasına (fiziksel) + kullanıcı kaydırması
        x = int((phys_w - tw) / 2 - off_x + profile.get("kaydir_x_mm", 0) / 25.4 * dpi_x)
        y = int((phys_h - th) / 2 - off_y + profile.get("kaydir_y_mm", 0) / 25.4 * dpi_y)
        pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        hdc.StartDoc(title)
        hdc.StartPage()
        ImageWin.Dib(pil).draw(hdc.GetHandleOutput(), (x, y, x + tw, y + th))
        hdc.EndPage()
        hdc.EndDoc()
        log(f"Yazdırıldı: {printer} {copies} kopya, {tw}x{th} @ {dpi_x}dpi")
    finally:
        hdc.DeleteDC()


def calibrate(profile: dict, olculen_yatay_mm: float, olculen_dikey_mm: float) -> dict:
    """Test sayfasında 80 mm ve 120 mm olması gereken cetveller ölçülür; ölçek düzeltmesi hesaplanır."""
    p = dict(profile)
    if olculen_yatay_mm > 0:
        p["olcek_x"] = round(p.get("olcek_x", 1.0) * 80.0 / olculen_yatay_mm, 4)
    if olculen_dikey_mm > 0:
        p["olcek_y"] = round(p.get("olcek_y", 1.0) * 120.0 / olculen_dikey_mm, 4)
    return p
