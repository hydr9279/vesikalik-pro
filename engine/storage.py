"""Ayarlar, yönetici kilidi, arşiv kayıtları, dosya adları, günlük rapor, ayar taşıma."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import secrets
import threading
import zipfile

from .paths import data_dir

_lock = threading.Lock()
SETTINGS_FILE = os.path.join(data_dir(), "ayarlar.json")
ARCHIVE_FILE = os.path.join(data_dir(), "arsiv.jsonl")


def _hash(pw: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 120_000).hex()


def _default_settings() -> dict:
    return {
        "tema": "koyu",
        "vurgu": "#F2B544",
        "varsayilan_klasor": "",
        "arsiv_no": 1,
        "yonetici": {"ad": "HAYDAR", "tuz": "hm-vp-1b7e4c9a", "ozet": "8929c402f45bdaafc9eb2862310bd405bfa878e8e7f8b270e32475a1129d3eaf"},
        "yazicilar": {},          # ad -> profil
        "varsayilan_yazici": "",
        "rotus_profilleri": {},   # ad -> rötuş ayarları
        "ozel_fonlar": [],
        "tekli_jpg": True,
        "son_kontrol": True,
        "hizli_mod": False,
        "gpu_kullan": True,
        "sablon_goster": True,
        "model": "auto",
        "kenar_modu": "uzat",      # fotoğraf dışı kenarlar: uzat | doldur | yumusat
        "ogrenme_kayit": True,     # yerel, yalnız sayısal rötuş ayarları; fotoğraf/isim içermez
    }


def load_settings() -> dict:
    with _lock:
        d = _default_settings()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    d.update(json.load(f))
            except Exception:
                pass
        else:
            _write(d)
        return d


def _write(d):
    tmp = SETTINGS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, SETTINGS_FILE)


def save_settings(d: dict) -> None:
    with _lock:
        _write(d)


# Yönetici korumalı alanlar: değiştirmek için şifre gerekir
PROTECTED = {"arsiv_no", "yonetici"}


def check_admin(pw: str) -> bool:
    s = load_settings()
    y = s["yonetici"]
    return secrets.compare_digest(_hash(pw or "", y["tuz"]), y["ozet"])


def reset_archive(ad: str, pw: str) -> int:
    """Arşiv ve günlük rapor kayıtlarını sıfırlar (yönetici adı + şifre gerekir). Silmeden önce yedek alır.
    Arşiv numarası sayacı korunur (numaralar tekrar etmesin). Silinen kayıt sayısını döndürür."""
    y = load_settings()["yonetici"]
    if (ad or "").strip().casefold() != str(y["ad"]).casefold() or not check_admin(pw):
        raise PermissionError("Yönetici adı veya şifresi hatalı.")
    n = 0
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
            n = sum(1 for ln in f if ln.strip())
        if n:
            import shutil, datetime
            yedek = os.path.join(data_dir(), f"arsiv_yedek_{datetime.datetime.now():%Y%m%d_%H%M%S}.jsonl")
            shutil.copy2(ARCHIVE_FILE, yedek)
        open(ARCHIVE_FILE, "w", encoding="utf-8").close()
    return n


def update_settings(changes: dict, pw: str = "") -> dict:
    s = load_settings()
    if any(k in PROTECTED for k in changes) and not check_admin(pw):
        raise PermissionError("Bu ayar için yönetici şifresi gerekir.")
    if "yeni_sifre" in changes:
        if not check_admin(pw):
            raise PermissionError("Mevcut şifre hatalı.")
        salt = secrets.token_hex(8)
        s["yonetici"] = {"ad": s["yonetici"]["ad"], "tuz": salt, "ozet": _hash(changes.pop("yeni_sifre"), salt)}
    changes.pop("yonetici", None)
    s.update(changes)
    save_settings(s)
    return s


def public_settings() -> dict:
    s = load_settings()
    s = dict(s)
    s["yonetici"] = {"ad": s["yonetici"]["ad"]}
    return s


# ---------------------------------------------------------------- dosya adları
def clean_name(n: str) -> str:
    n = re.sub(r'[\\/:*?"<>|]+', " ", (n or "").strip())
    return re.sub(r"\s+", " ", n)[:60]


def size_label(fmt: dict) -> str:
    def f(v):
        v = round(v / 10, 2)
        return (f"{v:.2f}".rstrip("0").rstrip(".")).replace(",", ".")
    return f"{f(fmt['gen_mm'])}x{f(fmt['yuk_mm'])}"


def file_names(no: str, adet: int, fmt: dict, musteri: str = "") -> dict:
    base = f"{no} {adet}_{fmt['kisa']}"
    m = clean_name(musteri)
    if m:
        base += f"_{m}"
    return {"orijinal": base + "_orijinal.jpg", "tekli": base + f"_{size_label(fmt)}.jpg", "sayfa": base + "_10x15.jpg",
            "online": base + f"_{size_label(fmt)}_online.jpg"}


def next_archive_no() -> int:
    return int(load_settings().get("arsiv_no", 1))


def bump_archive_no(used: int) -> None:
    with _lock:
        d = _default_settings()
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                d.update(json.load(f))
        if int(used) >= int(d.get("arsiv_no", 1)):
            d["arsiv_no"] = int(used) + 1
        _write(d)


# ---------------------------------------------------------------- arşiv
def add_record(rec: dict) -> None:
    rec = dict(rec)
    rec["tarih"] = datetime.datetime.now().isoformat(timespec="seconds")
    with _lock, open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def records() -> list:
    if not os.path.exists(ARCHIVE_FILE):
        return []
    out = []
    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def search(q: str, limit: int = 100) -> list:
    q = (q or "").lower().strip()
    rs = records()[::-1]
    if q:
        rs = [r for r in rs if q in str(r.get("no", "")).lower() or q in (r.get("musteri") or "").lower()]
    return rs[:limit]


def daily_report(day: str = "") -> dict:
    day = day or datetime.date.today().isoformat()
    rs = [r for r in records() if r.get("tarih", "").startswith(day)]
    by = {}
    for r in rs:
        k = r.get("tur", "?")
        by.setdefault(k, {"is": 0, "adet": 0, "baski": 0})
        by[k]["is"] += 1
        by[k]["adet"] += int(r.get("adet", 0))
        by[k]["baski"] += 1 if r.get("yazdirildi") else 0
    return {"gun": day, "toplam_is": len(rs), "toplam_adet": sum(int(r.get("adet", 0)) for r in rs), "turler": by}


# ---------------------------------------------------------------- ayar taşıma
def export_settings(path: str) -> str:
    from .job import styles_dir
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        s = load_settings()
        s.pop("arsiv_no", None)
        z.writestr("ayarlar.json", json.dumps(s, ensure_ascii=False, indent=1))
        for f in os.listdir(styles_dir()):
            z.write(os.path.join(styles_dir(), f), "stiller/" + f)
    return path


def import_settings(path: str, pw: str) -> None:
    if not check_admin(pw):
        raise PermissionError("Ayar aktarımı için yönetici şifresi gerekir.")
    from .job import styles_dir
    with zipfile.ZipFile(path) as z:
        incoming = json.loads(z.read("ayarlar.json").decode("utf-8"))
        cur = load_settings()
        for k in ("arsiv_no",):
            incoming.pop(k, None)
        cur.update(incoming)
        save_settings(cur)
        for n in z.namelist():
            if n.startswith("stiller/") and n.endswith(".npy"):
                with open(os.path.join(styles_dir(), os.path.basename(n)), "wb") as f:
                    f.write(z.read(n))


# ---------------------------------------------------------------- öğrenme günlüğü (yerel, yalnız sayılar)
LEARN_FILE = os.path.join(data_dir(), "ogrenme.jsonl")

def learn_log(rec: dict) -> None:
    """Her kayıtta rötuş ayar sayılarını yerel dosyaya ekler. Fotoğraf, müşteri adı ya da dosya yolu YAZILMAZ."""
    try:
        if not load_settings().get("ogrenme_kayit", True):
            return
        def num(v):
            if isinstance(v, bool): return v
            if isinstance(v, (int, float)): return v
            if isinstance(v, dict): return {k: num(x) for k, x in v.items() if num(x) is not None}
            if isinstance(v, (list, tuple)) and all(isinstance(x, (int, float)) for x in v): return list(v)
            return None
        r = {k: num(v) for k, v in rec.items()}
        r = {k: v for k, v in r.items() if v is not None}
        r["t"] = datetime.datetime.now().isoformat(timespec="seconds")
        with open(LEARN_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    except Exception:
        pass

def learn_count() -> int:
    try:
        with open(LEARN_FILE, encoding="utf-8") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0

def learn_clear() -> int:
    n = learn_count()
    try: os.remove(LEARN_FILE)
    except OSError: pass
    return n
