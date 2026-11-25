"""Fotoğraf türleri, kadraj şablonları ve 10x15 dizim kuralları.

Kadraj, göz hattı ile çene arasındaki mesafeden ölçeklenir (saç ve örtü hacminden etkilenmez).
Biyometrik ve vesikalık değerleri Hayal Medya'nın kendi baskı örneklerinden ölçülmüştür.
"""
DPI = 300
MM = DPI / 25.4

PAPER_10x15 = {"ad": "10x15", "gen_mm": 100.0, "yuk_mm": 150.0, "px": (1181, 1772)}

# eye_mm / chin_mm: fotoğrafın üst kenarından göz hattı ve çene (mm)
FORMATS = {
    "bio56": {"ad": "Biyometrik 5x6", "kisa": "Biyometrik", "grup": "biyometrik", "gen_mm": 50, "yuk_mm": 60,
              "eye_mm": 26.9, "chin_mm": 45.6, "head_min": 32, "head_max": 44, "fon": "white", "strict": True,
              "dizim": "bitisik", "adetler": [4, 8], "ust_px": 107, "yasli": True,
              "aciklama": "Pasaport · Kimlik · Ehliyet"},
    "bio55": {"ad": "Biyometrik 5x5", "kisa": "Biyometrik", "grup": "biyometrik", "gen_mm": 50, "yuk_mm": 50,
              "eye_mm": 22.0, "chin_mm": 40.7, "head_min": 30, "head_max": 42, "fon": "white", "strict": True,
              "dizim": "bitisik", "adetler": [4, 8], "ust_px": 107, "yasli": True,
              "aciklama": "Kare biyometrik"},
    "ves45": {"ad": "Vesikalık 4,5x6", "kisa": "Vesikalik", "grup": "vesikalik", "gen_mm": 45, "yuk_mm": 60,
              "eye_mm": 18.1, "chin_mm": 31.7, "head_min": 22, "head_max": 34, "fon": "original", "strict": False,
              "dizim": "cerceveli", "adetler": [4, 8], "aciklama": "Okul · İş · Özlük"},
    # Vize ölçüleri: ICAO / ülke kuralları (baş = çene-tepe); göz-çene ≈ baş / 2
    "schengen": {"ad": "Schengen 3,5x4,5", "kisa": "Vize_Schengen", "grup": "vize", "gen_mm": 35, "yuk_mm": 45,
                 "eye_mm": 21.0, "chin_mm": 38.0, "head_min": 32, "head_max": 36, "fon": "white", "strict": True,
                 "dizim": "ortali", "adetler": [4, 8]},
    "abd": {"ad": "ABD 5x5", "kisa": "Vize_ABD", "grup": "vize", "gen_mm": 50.8, "yuk_mm": 50.8,
            "eye_mm": 19.5, "chin_mm": 34.5, "head_min": 25, "head_max": 35, "fon": "white", "strict": True,
            "dizim": "ortali", "adetler": [4]},
    "ingiltere": {"ad": "İngiltere 3,5x4,5", "kisa": "Vize_Ingiltere", "grup": "vize", "gen_mm": 35, "yuk_mm": 45,
                  "eye_mm": 20.75, "chin_mm": 36.5, "head_min": 29, "head_max": 34, "fon": "lightgray", "strict": True,
                  "dizim": "ortali", "adetler": [4, 8]},
    "kanada": {"ad": "Kanada 5x7", "kisa": "Vize_Kanada", "grup": "vize", "gen_mm": 50, "yuk_mm": 70,
               "eye_mm": 28.75, "chin_mm": 45.5, "head_min": 31, "head_max": 36, "fon": "white", "strict": True,
               "dizim": "ortali", "adetler": [4]},
    "cin": {"ad": "Çin 3,3x4,8", "kisa": "Vize_Cin", "grup": "vize", "gen_mm": 33, "yuk_mm": 48,
            "eye_mm": 19.25, "chin_mm": 34.5, "head_min": 28, "head_max": 33, "fon": "white", "strict": True,
            "dizim": "ortali", "adetler": [4, 8]},
    "hindistan": {"ad": "Hindistan 5x5", "kisa": "Vize_Hindistan", "grup": "vize", "gen_mm": 50.8, "yuk_mm": 50.8,
                  "eye_mm": 19.5, "chin_mm": 34.5, "head_min": 25, "head_max": 35, "fon": "white", "strict": True,
                  "dizim": "ortali", "adetler": [4]},
    "japonya": {"ad": "Japonya 3,5x4,5", "kisa": "Vize_Japonya", "grup": "vize", "gen_mm": 35, "yuk_mm": 45,
                "eye_mm": 21.0, "chin_mm": 38.0, "head_min": 32, "head_max": 36, "fon": "white", "strict": True,
                "dizim": "ortali", "adetler": [4, 8]},
    "rusya": {"ad": "Rusya 3,5x4,5", "kisa": "Vize_Rusya", "grup": "vize", "gen_mm": 35, "yuk_mm": 45,
              "eye_mm": 21.0, "chin_mm": 37.0, "head_min": 30, "head_max": 34, "fon": "white", "strict": True,
              "dizim": "ortali", "adetler": [4, 8]},
}

# Degrade fonlar (merkez rengi → kenar rengi); 12 = köşeden ışık
GRADIENTS = [
    {"no": 1, "ad": "Klasik Mavi", "ic": "#D4E6F7", "dis": "#4C77A6", "tip": "radyal"},
    {"no": 2, "ad": "Gök Mavisi", "ic": "#EAF4FC", "dis": "#8CB6DB", "tip": "radyal"},
    {"no": 3, "ad": "Çelik Mavi", "ic": "#C3D0DC", "dis": "#3D5266", "tip": "radyal"},
    {"no": 4, "ad": "Lacivert Portre", "ic": "#7896BC", "dis": "#1C2C45", "tip": "radyal"},
    {"no": 5, "ad": "Gümüş Gri", "ic": "#F4F4F4", "dis": "#9A9DA2", "tip": "radyal"},
    {"no": 6, "ad": "Antrasit", "ic": "#9A9DA2", "dis": "#2C2E32", "tip": "radyal"},
    {"no": 7, "ad": "Sıcak Bej", "ic": "#F6ECDE", "dis": "#B39674", "tip": "radyal"},
    {"no": 8, "ad": "Krem", "ic": "#FCF8EF", "dis": "#D6C4A6", "tip": "radyal"},
    {"no": 9, "ad": "Mint", "ic": "#E6F5EE", "dis": "#88B9A2", "tip": "radyal"},
    {"no": 10, "ad": "Lila", "ic": "#F0E9F6", "dis": "#A592BE", "tip": "radyal"},
    {"no": 11, "ad": "Pudra", "ic": "#F9ECEB", "dis": "#CC9F9C", "tip": "radyal"},
    {"no": 12, "ad": "Stüdyo Işığı", "ic": "#FFFFFF", "dis": "#8C9095", "tip": "kose"},
]
GRADIENT_DEFAULTS = {"merkez_x": 0.5, "merkez_y": 0.38, "yayilma": 0.75, "sertlik": 1.3}

SOLIDS = {"white": "#FFFFFF", "lightgray": "#EEEEEE", "offwhite": "#F6F4EF", "lightblue": "#CFE0F1"}


def mm2px(mm: float) -> int:
    return int(round(mm * MM))


def photo_px(fmt: dict) -> tuple:
    return mm2px(fmt["gen_mm"]), mm2px(fmt["yuk_mm"])


def head_mm_from(fmt: dict) -> float:
    """Şablondaki yaklaşık baş yüksekliği (çene-tepe)."""
    return (fmt["chin_mm"] - fmt["eye_mm"]) * 2.05


def public_formats() -> list:
    out = []
    for k, f in FORMATS.items():
        d = dict(f)
        d["id"] = k
        d["head_mm"] = round(head_mm_from(f), 1)
        out.append(d)
    return out
