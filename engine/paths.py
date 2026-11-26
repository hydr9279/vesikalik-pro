"""Dosya yolları: program klasörü, modeller, kullanıcı verisi."""
import os
import sys

APP_NAME = "Hayal Medya Vesikalık Pro"
VERSION = "1.4.1"


def app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def res_dir() -> str:
    return getattr(sys, "_MEIPASS", app_dir())


def find(rel: str) -> str:
    for base in (app_dir(), res_dir()):
        p = os.path.join(base, rel)
        if os.path.exists(p):
            return p
    return os.path.join(app_dir(), rel)


def extra_model_dir() -> str:
    """Kullanıcının içe aktardığı modeller (Program Files yazılamayabilir; bu klasör kullanıcıya aittir)."""
    d = os.path.join(data_dir(), "modeller")
    os.makedirs(d, exist_ok=True)
    return d


def model_path(name: str) -> str:
    ek = os.path.join(extra_model_dir(), name)
    if os.path.exists(ek):
        return ek
    return find(os.path.join("models", name))


def data_dir() -> str:
    """Ayarlar, arşiv veritabanı, profiller, kayıtlar (kullanıcı başına)."""
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    d = os.path.join(base, "HayalMedyaVesikalikPro")
    os.makedirs(d, exist_ok=True)
    return d
