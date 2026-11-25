"""Hata kaydı: %APPDATA%/HayalMedyaVesikalikPro/kayitlar/hata_YYYY-MM-DD.log"""
import datetime
import os
import threading
import traceback

from .paths import data_dir, VERSION

_lock = threading.Lock()


def log_dir() -> str:
    d = os.path.join(data_dir(), "kayitlar")
    os.makedirs(d, exist_ok=True)
    return d


def log(msg: str, level: str = "INFO") -> None:
    now = datetime.datetime.now()
    line = f"{now:%Y-%m-%d %H:%M:%S} [{level}] {msg}\n"
    with _lock:
        try:
            with open(os.path.join(log_dir(), f"hata_{now:%Y-%m-%d}.log"), "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass


def log_exc(context: str) -> str:
    tb = traceback.format_exc()
    log(f"{context} (v{VERSION})\n{tb}", "ERROR")
    return tb
