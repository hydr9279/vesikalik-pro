"""Arayüzün çağırdığı işlevler (pywebview js_api). Tüm uzun işlemler ilerleme bilgisi yayınlar."""
from __future__ import annotations

import base64
import datetime
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid

import cv2
import numpy as np

from . import extras, models, printing, storage
from .formats import FORMATS, GRADIENTS, public_formats, photo_px
from .imgutil import imread_any, save_jpeg, to_b64, learn_lut, is_image, IMG_EXTS
from .job import Job, save_style, list_styles, DEFAULT_RETOUCH, DEFAULT_MATTE, DEFAULT_BG, DEFAULT_GEOM
from .layout import sheet_for, test_page
from .log import log, log_exc, log_dir
from .paths import APP_NAME, VERSION

EDIT_MULT = 2  # düzenleme önizlemesi: 600 px/inç


class Api:
    def __init__(self):
        self.window = None
        self.jobs: dict = {}
        self._prog = {"aktif": False, "yuzde": 0, "mesaj": "", "basla": 0}
        self._plock = threading.Lock()

    # ---------------------------------------------------------- yardımcılar
    def _p(self, pct, msg):
        with self._plock:
            if not self._prog["aktif"]:
                self._prog.update(aktif=True, basla=time.time())
            self._prog.update(yuzde=float(pct), mesaj=msg)

    def _done(self):
        with self._plock:
            self._prog.update(aktif=False, yuzde=1.0, mesaj="")

    def progress(self):
        with self._plock:
            p = dict(self._prog)
        if p["aktif"] and p["yuzde"] > 0.05:
            el = time.time() - p["basla"]
            p["kalan"] = max(0, el / p["yuzde"] - el)
        return p

    def _safe(self, fn, *a, **k):
        try:
            return {"ok": True, **(fn(*a, **k) or {})}
        except PermissionError as e:
            return {"ok": False, "hata": str(e), "yetki": True}
        except Exception as e:
            log_exc(f"{fn.__name__} hatası")
            return {"ok": False, "hata": str(e)}
        finally:
            self._done()

    def _fmt(self, fid):
        return FORMATS[fid]

    def _view(self, j: Job, fid: str, mode: str = "sonuc"):
        fmt = self._fmt(fid)
        M, (Wc, Hc), ppm, s = j.transform(fmt, EDIT_MULT)
        if mode == "maske" and j.A is not None:
            a = cv2.warpAffine(j.A, M, (Wc, Hc), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            img = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        elif mode == "koruma" and j.analyzed:
            base = j.Wr if j.Wr is not None else j.W
            ov = j.protect_overlay(base)
            img = cv2.warpAffine(ov, M, (Wc, Hc), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        elif mode == "once" or not j.matted:
            img = cv2.warpAffine(j.W, M, (Wc, Hc), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        else:
            img = j.render(fmt, preview=True, mult=EDIT_MULT)
        return to_b64(img, max_side=1600)

    def _to_work(self, j, fid, x, y):
        """Önizleme koordinatı (0..1) → çalışma görüntüsü koordinatı (0..1)."""
        M, (Wc, Hc), ppm, s = j.transform(self._fmt(fid), EDIT_MULT)
        inv = cv2.invertAffineTransform(M)
        p = inv[:, :2] @ np.array([x * Wc, y * Hc]) + inv[:, 2]
        H, W = j.W.shape[:2]
        return float(p[0] / W), float(p[1] / H), s

    def _state(self, j: Job, fid: str, mode="sonuc"):
        fmt = self._fmt(fid)
        out = {"id": j.id, "gorsel": self._view(j, fid, mode)}
        if j.analyzed:
            out["olcu"] = j.measures(fmt)
            out["uygunluk"] = j.compliance(fmt)
        out["donanim"] = models.provider_info()["name"]
        out["model"] = getattr(j, "matte_model", "")
        out["matte"] = {k: v for k, v in j.matte_params.items()}
        out["rotus"] = {k: v for k, v in j.retouch_params.items() if k not in ("spots", "geri_al", "fircalar", "koruma_fircalar", "klon", "manuel")}
        out["manuel_var"] = [j.manuel_m is not None, j.manuel_Am is not None]
        out["klon_sayisi"] = len(j.retouch_params.get("klon") or [])
        out["sekil_sayisi"] = len(j.shape_ops)
        out["omuz"] = j.omuz
        try:
            out["omuz_fark"] = j.omuz_fark() if j.matted else None
        except Exception:
            out["omuz_fark"] = None
        out["bg"] = dict(j.bg)
        out["geom"] = dict(j.geom)
        out["duzeltme_sayisi"] = len(j.edits)
        if j.matted:
            M, (Wc, Hc), ppm, s = j.transform(fmt, EDIT_MULT)
            H, W = j.W.shape[:2]
            boxes = []
            for b in getattr(j, "suspicious", []):
                p0 = M[:, :2] @ np.array([b["x"] * W, b["y"] * H]) + M[:, 2]
                p1 = M[:, :2] @ np.array([(b["x"] + b["w"]) * W, (b["y"] + b["h"]) * H]) + M[:, 2]
                x0, y0, x1, y1 = p0[0] / Wc, p0[1] / Hc, p1[0] / Wc, p1[1] / Hc
                cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(1, x1), min(1, y1)
                full = max(1e-6, (x1 - x0) * (y1 - y0))
                if cx1 <= cx0 or cy1 <= cy0 or (cx1 - cx0) * (cy1 - cy0) / full < 0.5:
                    continue  # fotoğraf karesinin dışında kalan bölge
                boxes.append({"ad": b["ad"], "x": cx0, "y": cy0, "w": cx1 - cx0, "h": cy1 - cy0})
            out["supheli"] = boxes
            po = []
            for wx, wy in (j.retouch_params.get("pro") or {}).get("ornekler", []):
                q = M[:, :2] @ np.array([wx * W, wy * H]) + M[:, 2]
                po.append([q[0] / Wc, q[1] / Hc])
            out["pro_ornekler"] = po
            spots = []
            for sx, sy in j.spots_found:
                p = M[:, :2] @ np.array([sx * W, sy * H]) + M[:, 2]
                spots.append([p[0] / Wc, p[1] / Hc, 0])
            for sx, sy, sr in j.retouch_params.get("spots", []):
                p = M[:, :2] @ np.array([sx * W, sy * H]) + M[:, 2]
                spots.append([p[0] / Wc, p[1] / Hc, 1])
            out["lekeler"] = spots
            out["firca_sayisi"] = [len(j.retouch_params.get("fircalar", [])), len(j.retouch_params.get("koruma_fircalar", []))]
        return out

    # ---------------------------------------------------------- başlangıç
    @staticmethod
    def _yazicilar():
        """Ağ yazıcısı yanıt vermese bile açılış en çok 3 sn beklesin."""
        out = {"v": []}
        def go():
            try:
                out["v"] = printing.list_printers()
            except Exception:
                pass
        t = threading.Thread(target=go, daemon=True); t.start(); t.join(3.0)
        return out["v"]

    def init(self):
        _t = time.time()
        try:
            try:
                models.set_gpu(bool(storage.load_settings().get("gpu_kullan", True)))
                models.set_disabled(storage.load_settings().get("model_kapali", []))
            except Exception:
                pass
            s = storage.public_settings()
            return {"surum": VERSION, "ad": APP_NAME, "formatlar": public_formats(), "degradeler": GRADIENTS,
                    "ayarlar": s, "stiller": list_styles(), "yazicilar": self._yazicilar(),
                    "varsayilanlar": {"rotus": DEFAULT_RETOUCH, "matte": DEFAULT_MATTE, "bg": DEFAULT_BG, "geom": DEFAULT_GEOM},
                    "modeller": {k: models.has_model(k) for k in models.MODELS}, "windows": printing.WIN}
        finally:
            try:
                from .log import log as _log
                _log(f"Açılış · init tamamlandı: {time.time() - _t:.2f} sn")
            except Exception:
                pass

    def pick_files(self):
        if not self.window:
            return []
        import webview
        r = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True,
                                           file_types=("Fotoğraflar (" + ";".join("*" + e for e in IMG_EXTS) + ")", "Tüm dosyalar (*.*)"))
        return list(r or [])

    def pick_folder(self, start=""):
        if not self.window:
            return ""
        import webview
        r = self.window.create_file_dialog(webview.FOLDER_DIALOG, directory=start or "")
        return (r[0] if isinstance(r, (list, tuple)) and r else r) or ""

    def add_files(self, paths):
        out = []
        exts = IMG_EXTS
        for p in paths:
            if os.path.isdir(p):
                paths += [os.path.join(p, f) for f in sorted(os.listdir(p))]
                continue
            if not p.lower().endswith(exts):
                continue
            try:
                j = Job(p)
                j.id = uuid.uuid4().hex[:8]
                self.jobs[j.id] = j
                th = cv2.resize(j.orig, (120, int(120 * j.orig.shape[0] / j.orig.shape[1])), interpolation=cv2.INTER_AREA)
                out.append({"id": j.id, "ad": j.name, "kucuk": to_b64(th, 160, 80), "yol": p})
            except Exception as e:
                log_exc(f"Dosya açılamadı: {p}")
                out.append({"hata": f"{os.path.basename(p)}: {e}"})
        return out

    def add_upload(self, name, data_url):
        """Sürükle-bırakta tam yol gelmezse (geliştirme) içerik geçici dosyaya yazılır."""
        d = os.path.join(tempfile.gettempdir(), "vp_yuklenen")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, os.path.basename(name))
        with open(p, "wb") as f:
            f.write(base64.b64decode(data_url.split(",", 1)[1]))
        return self.add_files([p])

    def remove_job(self, jid):
        self.jobs.pop(jid, None)
        return {"ok": True}

    def analyze(self, jid, fid):
        def go():
            j = self.jobs[jid]
            if not j.analyzed:
                j.analyze(self._p)
            j.bg = dict(DEFAULT_BG)
            # ön kontrol için hızlı maske
            st = self._state(j, fid, "once")
            st["orijinal"] = to_b64(j.orig, 1400)
            st["arsiv_no"] = storage.next_archive_no()
            return st
        return self._safe(go)

    # ---------------------------------------------------------- arka plan
    def matte(self, jid, fid, params=None, force=False):
        def go():
            j = self.jobs[jid]
            if params:
                if (params.get("model") and params["model"] != j.matte_params.get("model")) or \
                        ("vitmatte" in params and params["vitmatte"] != j.matte_params.get("vitmatte")):
                    force_ = True
                else:
                    force_ = force
                j.matte_params.update(params)
            else:
                force_ = force
            j.matte(self._p, force=force_)
            if j.Wr is None:
                j.retouch_params.update({"leke": 0, "yumusatma": 0, "parlama": 0, "gozalti": 0})
                j.retouch(self._p)
                j.retouch_params.update({k: DEFAULT_RETOUCH[k] for k in ("leke", "yumusatma", "parlama", "gozalti")})
                j._retouch_key = None
            j.rebuild_alpha()
            self._p(0.95, "Görüntü hazırlanıyor")
            return self._state(j, fid)
        return self._safe(go)

    def set_matte(self, jid, fid, params):
        def go():
            j = self.jobs[jid]
            j.matte_params.update(params)
            self._p(0.5, "Kenarlar güncelleniyor")
            j.rebuild_alpha()
            return self._state(j, fid)
        return self._safe(go)

    # ---------------------------------------------------------- Manuel düzenleme ekranları
    def manuel_ac(self, jid, fid, mod):
        """Manuel ekran için veri: tek seferde yüklenir, sonrası istemci tarafında anlık çalışır."""
        def go():
            j = self.jobs[jid]
            if mod == "rotus":
                if j.Wr is None:
                    j.retouch(self._p)
                ok, buf = cv2.imencode(".jpg", j.Wr, [cv2.IMWRITE_JPEG_QUALITY, 93])
                h_, w_ = j.Wr.shape[:2]
                return {"w": w_, "h": h_, "gorsel": "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()}
            # dekupe / saç
            if not j.matted:
                j.matte(self._p)
            ok, buf = cv2.imencode(".jpg", j.W, [cv2.IMWRITE_JPEG_QUALITY, 93])
            h_, w_ = j.W.shape[:2]
            def small(img):
                sm = cv2.resize((np.clip(img, 0, 1) * 255).astype(np.uint8), (max(8, w_ // 8), max(8, h_ // 8)), interpolation=cv2.INTER_AREA)
                ok2, b2 = cv2.imencode(".png", sm)
                return "data:image/png;base64," + base64.b64encode(b2.tobytes()).decode()
            from .imgutil import png_b64
            return {"w": w_, "h": h_, "gorsel": "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode(),
                    "alfa": png_b64((j.A * 255).astype(np.uint8)),
                    "plaka_b": small(j.Bplate[..., ::-1] if False else j.Bplate), "plaka_f": small(j.Fplate)}
        return self._safe(go)

    @staticmethod
    def _png_oku(data_url):
        raw = base64.b64decode(data_url.split(",", 1)[1])
        return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_UNCHANGED)

    def manuel_uygula_rotus(self, jid, fid, x, y, png):
        """Değişen bölgenin RGBA yaması (alfa>0 = değişen piksel) çalışma görüntüsü koordinatında uygulanır."""
        def go():
            j = self.jobs[jid]
            im = self._png_oku(png)          # BGRA
            if im is None or im.ndim != 3 or im.shape[2] != 4:
                raise ValueError("Yama okunamadı")
            H, W = j.W.shape[:2]
            if j.manuel_rgb is None or j.manuel_rgb.shape[:2] != (H, W):
                j.manuel_rgb = np.zeros((H, W, 3), np.uint8)
                j.manuel_m = np.zeros((H, W), bool)
            x0, y0, h_, w_ = int(x), int(y), im.shape[0], im.shape[1]
            x1, y1 = min(W, x0 + w_), min(H, y0 + h_)
            sub = im[: y1 - y0, : x1 - x0]
            m = sub[..., 3] > 0
            j.manuel_rgb[y0:y1, x0:x1][m] = sub[..., :3][m]
            j.manuel_m[y0:y1, x0:x1] |= m
            j.retouch_params["manuel"] = int(j.retouch_params.get("manuel", 0)) + 1
            j.retouch(self._p)
            return self._state(j, fid)
        return self._safe(go)

    def manuel_uygula_dekupe(self, jid, fid, alfa_png, maske_png):
        """Manuel maske: alfa (gri PNG, çalışma boyutu) + değişen piksellerin maskesi."""
        def go():
            j = self.jobs[jid]
            a = self._png_oku(alfa_png)
            m = self._png_oku(maske_png)
            if a.ndim == 3: a = a[..., 0]
            if m.ndim == 3: m = m[..., 0]
            if a.shape != j.A.shape:
                raise ValueError("Maske boyutu uyuşmuyor")
            j.manuel_A = a.astype(np.float32) / 255.0
            j.manuel_Am = m > 127
            j.rebuild_alpha()
            return self._state(j, fid)
        return self._safe(go)

    def manuel_sifirla(self, jid, fid, mod):
        def go():
            j = self.jobs[jid]
            if mod == "rotus":
                j.manuel_rgb = j.manuel_m = None
                j.retouch_params["manuel"] = int(j.retouch_params.get("manuel", 0)) + 1
                j.retouch(self._p)
            else:
                j.manuel_A = j.manuel_Am = None
                j.rebuild_alpha()
            return self._state(j, fid)
        return self._safe(go)

    # ---------------------------------------------------------- Model Laboratuvarı / Model Yöneticisi
    _DOSYA_ESLE = (("hr", "birefnet_hr"), ("matting", "birefnet_matting"), ("ben2", "ben2"), ("rmbg", "rmbg2"),
                   ("vitmatte", "vitmatte"), ("general", "birefnet_general"), ("portrait", "birefnet"))

    def model_listesi(self):
        def go():
            kapali = set(storage.load_settings().get("model_kapali", []))
            out = []
            for k in models.MATTE_ORDER + ["vitmatte"]:
                m = models.MODELS[k]
                yol = models.model_path(m["file"])
                var = os.path.exists(yol)
                from .paths import extra_model_dir
                out.append({"key": k, "ad": m["ad"], "var": var, "lisans": m["lisans"], "ticari": m["ticari"],
                            "not": m.get("not", ""), "agir": bool(m.get("agir")), "ek": bool(m.get("ek")),
                            "mb": round(os.path.getsize(yol) / 1e6) if var else 0, "kapali": k in kapali,
                            "kaldirilabilir": var and os.path.dirname(yol) == extra_model_dir()})
            return {"modeller": out}
        return self._safe(go)

    def model_ice_aktar(self):
        """Seçilen .onnx dosyalarını dosya adından tanıyıp kullanıcı klasörüne kopyalar."""
        def go():
            import shutil
            from .paths import extra_model_dir
            if not self.window:
                return {"eklenen": []}
            import webview
            r = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=("ONNX modeller (*.onnx)", "Tüm dosyalar (*.*)"))
            eklenen, taninmayan = [], []
            for src in (r or []):
                low = os.path.basename(src).lower()
                key = next((k for pat, k in self._DOSYA_ESLE if pat in low), None)
                if key is None:
                    taninmayan.append(os.path.basename(src)); continue
                if "hr" in low and "matting" in low:
                    key = "birefnet_hr"
                shutil.copy2(src, os.path.join(extra_model_dir(), models.MODELS[key]["file"]))
                models._SESSIONS.pop(key, None)
                eklenen.append(models.MODELS[key]["ad"])
            return {"eklenen": eklenen, "taninmayan": taninmayan}
        return self._safe(go)

    def model_kaldir(self, key):
        def go():
            from .paths import extra_model_dir
            yol = os.path.join(extra_model_dir(), models.MODELS[key]["file"])
            if os.path.exists(yol):
                models._SESSIONS.pop(key, None)
                os.remove(yol)
            return {}
        return self._safe(go)

    def model_kapat(self, key, kapali):
        def go():
            s = storage.load_settings()
            lst = set(s.get("model_kapali", []))
            (lst.add if kapali else lst.discard)(key)
            storage.update_settings({"model_kapali": sorted(lst)})
            models.set_disabled(sorted(lst))
            return {}
        return self._safe(go)

    def model_karsilastir(self, jid, fid, keys, zeminler=None):
        """Seçilen modellerin sonucunu aynı fotoğrafta, farklı zeminlerde yan yana üretir (durum değişmez)."""
        def go():
            import copy
            j = self.jobs[jid]
            fmt = self._fmt(fid)
            zl = list(zeminler or ["#FFFFFF", "#23272F", "#2E7D5B"])
            sonuc, alfalar = [], {}
            for i, k in enumerate(keys):
                if k not in models.MODELS or not models.has_model(k):
                    continue
                self._p(0.1 + 0.8 * i / max(1, len(keys)), f"Karşılaştırma: {models.MODELS[k]['ad']}")
                c = copy.copy(j)
                c.matte_params = copy.deepcopy(j.matte_params)
                c.matte_params["model"] = k
                c.edits = list(j.edits)
                c.bg = dict(j.bg)
                c.matted = False
                t0 = __import__("time").time()
                try:
                    c.matte(force=True)
                except Exception as e:
                    log_exc(f"karşılaştırma modeli başarısız: {k}")
                    sonuc.append({"key": k, "ad": models.MODELS[k]["ad"], "hata": str(e)[:120]}); continue
                sure = __import__("time").time() - t0
                imgs = []
                for z in zl:
                    c.bg = {**j.bg, "tip": "solid", "renk": z}
                    im = c.render(fmt, preview=True)
                    h_, w_ = im.shape[:2]
                    crop = im[: int(h_ * 0.62)]
                    imgs.append(to_b64(crop, 360))
                a = cv2.resize(c.A, (192, 192), interpolation=cv2.INTER_AREA)
                alfalar[k] = a
                belirsiz = float(((c.A > 0.1) & (c.A < 0.9)).mean() * 100)
                sonuc.append({"key": k, "ad": models.MODELS[k]["ad"], "gorseller": imgs, "sure": round(sure, 1),
                              "belirsiz": round(belirsiz, 2), "lisans": models.MODELS[k]["lisans"], "ticari": models.MODELS[k]["ticari"]})
            oneri = None
            if len(alfalar) >= 3:   # uzlaşı: diğerlerine en yakın sonuç
                ks = list(alfalar)
                skor = {k: float(np.mean([np.abs(alfalar[k] - alfalar[o]).mean() for o in ks if o != k])) for k in ks}
                oneri = min(skor, key=skor.get)
            self._p(0.98, "Karşılaştırma hazır")
            return {"sonuclar": sonuc, "oneri": oneri, "zeminler": zl}
        return self._safe(go)

    SAC_MODLARI = {
        "otomatik": {"fon_ayikla": 60, "sac_detay": 70, "yumusaklik": 30, "sac_temizle": 0, "daraltma": 1},
        "kivircik": {"fon_ayikla": 85, "sac_detay": 85, "yumusaklik": 20, "sac_temizle": 0, "daraltma": 1},
        "dalgali": {"fon_ayikla": 75, "sac_detay": 80, "yumusaklik": 25, "sac_temizle": 0, "daraltma": 1},
        "duz": {"fon_ayikla": 65, "sac_detay": 90, "yumusaklik": 25, "sac_temizle": 10, "daraltma": 1},
        "az": {"fon_ayikla": 55, "sac_detay": 55, "yumusaklik": 35, "sac_temizle": 15, "daraltma": 1},
        "ortulu": {"fon_ayikla": 50, "sac_detay": 45, "yumusaklik": 35, "sac_temizle": 20, "daraltma": 1},
    }

    def sac_modu(self, jid, fid, mod):
        def go():
            j = self.jobs[jid]
            j.matte_params.update(self.SAC_MODLARI.get(mod, self.SAC_MODLARI["otomatik"]))
            j.matte_params["sac_modu"] = mod
            self._p(0.5, "Saç kenarları güncelleniyor")
            j.rebuild_alpha()
            return self._state(j, fid)
        return self._safe(go)

    def edit(self, jid, fid, e):
        """e: {t:'sam', x,y, pos} veya {t:'brush', pts:[[x,y]...], r, add, hard} (önizleme koordinatı 0..1)."""
        def go():
            j = self.jobs[jid]
            self._p(0.3, "Seçim yeniden hesaplanıyor (SAM)" if e["t"] == "sam" else "Fırça uygulanıyor")
            if e["t"] == "sam":
                x, y, s = self._to_work(j, fid, e["x"], e["y"])
                j.add_edit({"t": "sam", "x": x, "y": y, "pos": bool(e["pos"])})
            else:
                pts = []
                s = 1
                for px, py in e["pts"]:
                    x, y, s = self._to_work(j, fid, px, py)
                    pts.append((x, y))
                M, (Wc, Hc), ppm, s = j.transform(self._fmt(fid), EDIT_MULT)
                r = e["r"] * Wc / s / j.W.shape[1]
                j.add_edit({"t": "brush", "pts": pts, "r": r, "add": bool(e["add"]), "hard": e.get("hard", 0.6)})
            return self._state(j, fid)
        return self._safe(go)

    def undo_edit(self, jid, fid):
        def go():
            j = self.jobs[jid]
            j.undo_edit()
            return self._state(j, fid)
        return self._safe(go)

    def view(self, jid, fid, mode):
        def go():
            return {"gorsel": self._view(self.jobs[jid], fid, mode)}
        return self._safe(go)

    def set_bg(self, jid, fid, bg):
        def go():
            j = self.jobs[jid]
            j.bg.update(bg)
            return self._state(j, fid)
        return self._safe(go)

    # ---------------------------------------------------------- rötuş
    def retouch(self, jid, fid, params):
        def go():
            j = self.jobs[jid]
            p = dict(params)
            for k in ("spots", "geri_al", "fircalar", "koruma_fircalar", "klon", "pro_ornekler", "manuel"):
                p.pop(k, None)
            if "pro" in p:   # örnek noktaları motorda tutulur; arayüz yalnız ayarları gönderir
                p["pro"] = {**(p["pro"] or {}), "ornekler": (j.retouch_params.get("pro") or {}).get("ornekler", [])}
            j.retouch_params.update(p)
            j.retouch(self._p)
            self._p(0.95, "Görüntü hazırlanıyor")
            return self._state(j, fid)
        return self._safe(go)

    def rotus_firca(self, jid, fid, e):
        """e: {pts:[[x,y]..] önizleme 0..1, r (önizleme genişliğine oranla), val 0..1, tur:'geri'|'koru'}"""
        def go():
            j = self.jobs[jid]
            pts, s = [], 1
            for px, py in e["pts"]:
                x, y, s = self._to_work(j, fid, px, py)
                pts.append((x, y))
            M, (Wc, Hc), ppm, s = j.transform(self._fmt(fid), EDIT_MULT)
            r = e["r"] * Wc / s / j.W.shape[1]
            key = "koruma_fircalar" if e.get("tur") == "koru" else "fircalar"
            j.retouch_params.setdefault(key, []).append({"pts": pts, "r": r, "val": float(e.get("val", 1.0)), "hard": float(e.get("hard", 0.4))})
            self._p(0.4, "Fırça uygulanıyor")
            j.retouch(self._p)
            return self._state(j, fid)
        return self._safe(go)

    def klon_firca(self, jid, fid, e):
        """Klon damgası. e: {pts, src:[x,y], r, hard, val} — önizleme koordinatları (0..1)."""
        def go():
            j = self.jobs[jid]
            pts = []
            for px, py in e["pts"]:
                x, y, s = self._to_work(j, fid, px, py)
                pts.append((x, y))
            sx, sy, _ = self._to_work(j, fid, e["src"][0], e["src"][1])
            M, (Wc, Hc), ppm, s = j.transform(self._fmt(fid), EDIT_MULT)
            r = e["r"] * Wc / s / j.W.shape[1]
            j.retouch_params.setdefault("klon", []).append({"pts": pts, "src": [sx, sy], "r": r,
                                                           "val": float(e.get("val", 1.0)), "hard": float(e.get("hard", 0.4))})
            self._p(0.4, "Klon damgası uygulanıyor")
            j.retouch(self._p)
            return self._state(j, fid)
        return self._safe(go)

    def sekil_firca(self, jid, fid, e):
        """Şekillendir. e: {tur:'it'|'sis'|'kuc', pts (önizleme 0..1), r (önizleme genişliğine oranla), guc 0..1}"""
        def go():
            j = self.jobs[jid]
            pts = []
            for px, py in e["pts"]:
                x, y, s = self._to_work(j, fid, px, py)
                pts.append((x, y))
            M, (Wc, Hc), ppm, s = j.transform(self._fmt(fid), EDIT_MULT)
            r = e["r"] * Wc / s / j.W.shape[1]
            j.shape_ops.append({"t": e["tur"], "pts": pts, "r": r, "guc": float(e.get("guc", 0.6))})
            return self._state(j, fid)
        return self._safe(go)

    def sekil_geri_al(self, jid, fid, hepsi=False):
        def go():
            j = self.jobs[jid]
            if hepsi:
                j.shape_ops.clear(); j.omuz = 0.0
            elif j.shape_ops:
                j.shape_ops.pop()
            return self._state(j, fid)
        return self._safe(go)

    def sekil_omuz(self, jid, fid, miktar):
        """Otomatik omuz hizalama. miktar: 0 (kapalı) … 1 (tam düzeltme)."""
        def go():
            j = self.jobs[jid]
            j.omuz = max(0.0, min(1.0, float(miktar)))
            return self._state(j, fid)
        return self._safe(go)

    def klon_geri_al(self, jid, fid, hepsi=False):
        def go():
            j = self.jobs[jid]
            k = j.retouch_params.get("klon") or []
            if hepsi: k.clear()
            elif k: k.pop()
            j.retouch(self._p)
            return self._state(j, fid)
        return self._safe(go)

    def pro_ornek(self, jid, fid, x=None, y=None, temizle=False):
        """Gelişmiş portre rötuşu için ten örneği ekler (önizleme koordinatı) ya da temizler."""
        def go():
            j = self.jobs[jid]
            pro = j.retouch_params.setdefault("pro", {})
            lst = pro.setdefault("ornekler", [])
            if temizle: lst.clear()
            elif x is not None:
                wx, wy, _ = self._to_work(j, fid, x, y)
                if len(lst) < 6: lst.append([wx, wy])
            pro["acik"] = True
            j.retouch(self._p)
            return self._state(j, fid)
        return self._safe(go)

    def rotus_firca_geri_al(self, jid, fid, tur="geri"):
        def go():
            j = self.jobs[jid]
            key = "koruma_fircalar" if tur == "koru" else "fircalar"
            if j.retouch_params.get(key):
                j.retouch_params[key].pop()
            j.retouch(self._p)
            return self._state(j, fid)
        return self._safe(go)

    def leke_sil(self, jid, fid, idx):
        """Otomatik bulunan (idx < bulunan sayısı) ya da elle eklenen lekeyi kaldırır."""
        def go():
            j = self.jobs[jid]
            n = len(j.spots_found)
            if 0 <= idx < n:
                j.retouch_params.setdefault("geri_al", []).append(list(j.spots_found[idx]))
            elif 0 <= idx - n < len(j.retouch_params.get("spots", [])):
                j.retouch_params["spots"].pop(idx - n)
            self._p(0.4, "Leke işareti kaldırılıyor")
            j.retouch(self._p)
            return self._state(j, fid)
        return self._safe(go)

    def spot(self, jid, fid, x, y, r=0.012):
        """Leke fırçası: tıklanan yer bulunan bir lekeyse geri al, değilse leke olarak işaretle."""
        def go():
            j = self.jobs[jid]
            wx, wy, s = self._to_work(j, fid, x, y)
            near = [p for p in j.spots_found if abs(p[0] - wx) < 0.01 and abs(p[1] - wy) < 0.01]
            if near:
                j.retouch_params.setdefault("geri_al", []).append([wx, wy])
            else:
                M, (Wc, Hc), ppm, s2 = j.transform(self._fmt(fid), EDIT_MULT)
                j.retouch_params.setdefault("spots", []).append([wx, wy, r * Wc / s2 / j.W.shape[1]])
            self._p(0.4, "Leke onarılıyor")
            j.retouch(self._p)
            return self._state(j, fid)
        return self._safe(go)

    def learn_style(self, name, pairs):
        def go():
            self._p(0.2, "Stil öğreniliyor")
            imgs = [(imread_any(a), imread_any(b)) for a, b in pairs]
            lut = learn_lut(imgs)
            save_style(name, lut)
            return {"stiller": list_styles()}
        return self._safe(go)

    # ---------------------------------------------------------- kadraj
    def set_geom(self, jid, fid, geom):
        def go():
            j = self.jobs[jid]
            j.geom.update(geom)
            return self._state(j, fid)
        return self._safe(go)

    def reset_geom(self, jid, fid):
        return self.set_geom(jid, fid, dict(DEFAULT_GEOM))

    # ---------------------------------------------------------- baskı ve kayıt
    def sheet(self, jid, fid, adet):
        def go():
            j = self.jobs[jid]
            fmt = self._fmt(fid)
            self._p(0.4, "Son çıktı hazırlanıyor (300 DPI)")
            photo = j.render(fmt, preview=False)
            j._final = photo
            sh = sheet_for(fid, fmt, photo, adet)
            j._sheet = sh
            return {"sayfa": to_b64(sh, 1800, 92), "tekli": to_b64(photo, 900, 92)}
        return self._safe(go)

    def save(self, jid, fid, opts):
        def go():
            j = self.jobs[jid]
            fmt = self._fmt(fid)
            folder = opts.get("klasor") or ""
            if not folder or not os.path.isdir(folder):
                raise ValueError("Kayıt klasörü seçilmedi.")
            no = str(opts.get("no") or storage.next_archive_no())
            adet = int(opts.get("adet", 4))
            names = storage.file_names(no, adet, fmt, opts.get("musteri", ""))
            self._p(0.3, "Fotoğraf işleniyor (300 DPI)")
            photo = getattr(j, "_final", None)
            if photo is None:
                photo = j.render(fmt, preview=False)
            sh = sheet_for(fid, fmt, photo, adet)
            paths = {}
            self._p(0.6, "Kaydediliyor")
            p = os.path.join(folder, names["orijinal"])
            # orijinal ham dosya: baytları aynen kopyala (kalite kaybı yok)
            with open(j.path, "rb") as fi, open(p, "wb") as fo:
                fo.write(fi.read())
            paths["orijinal"] = p
            if opts.get("tekli", True):
                p = os.path.join(folder, names["tekli"])
                save_jpeg(photo, p, 100)
                paths["tekli"] = p
            p = os.path.join(folder, names["sayfa"])
            save_jpeg(sh, p, 100)
            paths["sayfa"] = p
            if opts.get("online"):
                p = os.path.join(folder, names["online"])
                _save_online(photo, p, opts.get("online_kb", 240), opts.get("online_px", 600))
                paths["online"] = p
            printed = False
            if opts.get("yazdir"):
                self._p(0.85, "Yazıcıya gönderiliyor")
                pr = opts.get("yazici") or storage.load_settings().get("varsayilan_yazici")
                prof = storage.load_settings().get("yazicilar", {}).get(pr) or printing.default_profile(pr)
                sheets = max(1, adet // 4) if fmt["dizim"] != "ortali" else 1
                printing.print_image(sh, pr, prof, copies=sheets)
                printed = True
            storage.add_record({"no": no, "musteri": opts.get("musteri", ""), "tur": fmt["ad"], "fid": fid, "adet": adet,
                                "dosyalar": paths, "klasor": folder, "yazdirildi": printed, "kaynak": j.path,
                                "geom": j.geom, "bg": j.bg, "matte": {k: v for k, v in j.matte_params.items()},
                                "rotus": {k: v for k, v in j.retouch_params.items() if k not in ("spots", "geri_al", "fircalar", "koruma_fircalar")}})
            storage.bump_archive_no(int(no) if str(no).isdigit() else 0)
            log(f"Kaydedildi: {no} {fmt['ad']} → {folder}")
            return {"dosyalar": paths, "yazdirildi": printed, "sonraki_no": storage.next_archive_no()}
        return self._safe(go)

    def musteri_ayar(self, jid, fid, ad, uygula=True):
        """Aynı müşterinin arşivdeki son ayarlarını (rötuş, fon, saç tipi) bulur ve uygular."""
        def go():
            ad2 = (ad or "").strip().lower()
            if not ad2:
                return {"bulundu": False}
            rec = next((r for r in reversed(storage.records()) if (r.get("musteri") or "").strip().lower() == ad2), None)
            if not rec:
                return {"bulundu": False}
            if not uygula:
                return {"bulundu": True, "tarih": rec.get("tarih", "")}
            j = self.jobs[jid]
            if rec.get("rotus"):
                for k, v in rec["rotus"].items():
                    if k in DEFAULT_RETOUCH:
                        j.retouch_params[k] = v
            if rec.get("bg"):
                j.bg.update(rec["bg"])
            if rec.get("matte"):
                j.matte_params.update({k: v for k, v in rec["matte"].items() if k in DEFAULT_MATTE})
                if j.matted:
                    j.rebuild_alpha()
            if j.analyzed:
                j.retouch(self._p)
            st = self._state(j, fid)
            st["bulundu"] = True
            return st
        return self._safe(go)

    def reprint(self, rec_index, printer=""):
        def go():
            recs = storage.records()
            r = recs[int(rec_index)]
            sh = imread_any(r["dosyalar"]["sayfa"])
            pr = printer or storage.load_settings().get("varsayilan_yazici")
            prof = storage.load_settings().get("yazicilar", {}).get(pr) or printing.default_profile(pr)
            printing.print_image(sh, pr, prof, copies=1)
            return {}
        return self._safe(go)

    # ---------------------------------------------------------- ayarlar, yazıcı, rapor
    def settings(self):
        return storage.public_settings()

    def update_settings(self, changes, pw=""):
        return self._safe(lambda: {"ayarlar": (storage.update_settings(changes, pw), storage.public_settings())[1]})

    def arsiv_sifirla(self, ad, pw):
        return self._safe(lambda: {"silinen": storage.reset_archive(ad, pw)})

    def check_admin(self, pw):
        return {"ok": storage.check_admin(pw)}

    # ---------------------------------------------------------- Polaroid / Serbest baskı
    def _mimg(self, path, full=False):
        cache = self.__dict__.setdefault("_mc", {})
        if full:
            return imread_any(path)
        if path not in cache:
            im = imread_any(path)
            s = 1800.0 / max(im.shape[:2])
            cache[path] = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else im
            if len(cache) > 40:
                cache.pop(next(iter(cache)))
        return cache[path]

    def modul_dosyalar(self, paths):
        out = []
        for p in paths:
            if os.path.isdir(p):
                paths += [os.path.join(p, f) for f in sorted(os.listdir(p))]
            elif is_image(p):
                out.append({"yol": p, "ad": os.path.basename(p)})
        return out

    def modul_onizle(self, tur, path, params, paper="10x15"):
        def go():
            img = self._mimg(path)
            if tur == "polaroid":
                out = extras.polaroid_card(img, params)
            else:
                out = extras.free_print(img, paper, params)
            return {"gorsel": to_b64(out, max_side=900)}
        return self._safe(go)

    def polaroid_sayfalar(self, items):
        def go():
            cards = [extras.polaroid_card(self._mimg(i["yol"]), i.get("p")) for i in items]
            return {"sayfalar": [to_b64(pg, max_side=900) for pg in extras.polaroid_sheets(cards)]}
        return self._safe(go)

    def polaroid_kaydet(self, items, opts):
        def go():
            self._p(0.1, "Polaroid kartları hazırlanıyor")
            cards = [extras.polaroid_card(self._mimg(i["yol"], True), i.get("p")) for i in items]
            pages = extras.polaroid_sheets(cards)
            os.makedirs(opts["klasor"], exist_ok=True)
            files = []
            for n, pg in enumerate(pages, 1):
                path = os.path.join(opts["klasor"], f"{opts.get('no', '')} Polaroid_{opts.get('musteri', '')}_sayfa{n}.jpg".strip().replace("  ", " "))
                save_jpeg(pg, path, 100)
                files.append(path)
                self._p(0.1 + 0.8 * n / len(pages), f"Kaydediliyor {n}/{len(pages)}")
            printed = False
            if opts.get("yazdir"):
                pr = opts.get("yazici") or storage.load_settings().get("varsayilan_yazici")
                prof = storage.load_settings().get("yazicilar", {}).get(pr) or printing.default_profile(pr)
                for pg in pages:
                    printing.print_image(pg, pr, prof, copies=int(opts.get("kopya", 1)), title="Polaroid")
                printed = True
            return {"dosyalar": files, "yazdirildi": printed}
        return self._safe(go)

    def serbest_yazicilar(self):
        """Serbest baskıda Mitsubishi kullanılmaz: yalnız diğer yazıcılar."""
        s = storage.load_settings()
        names = [n for n in printing.list_printers() if not any(k in n.lower() for k in ("d70", "mitsubishi", "cp-d"))]
        return {"yazicilar": names, "varsayilan": next((n for n in names if "epson" in n.lower()), names[0] if names else "")}

    def serbest_kaydet(self, items, paper, opts):
        """items: [{yol, adet, p}] — her foto kağıt boyutunda ayrı baskı; 'Baskıya Hazır' klasörüne kaydedilir."""
        def go():
            files = []
            printed = 0
            for n, it in enumerate(items):
                self._p(0.05 + 0.9 * n / max(1, len(items)), f"Baskı hazırlanıyor {n + 1}/{len(items)}")
                img = self._mimg(it["yol"], True)
                out = extras.free_print(img, paper, it.get("p"))
                folder = opts.get("klasor") or os.path.join(os.path.dirname(it["yol"]), "Baskıya Hazır")
                os.makedirs(folder, exist_ok=True)
                path = os.path.join(folder, extras.free_name(it["yol"], paper, int(it.get("adet", 1))))
                save_jpeg(out, path, 100)
                files.append(path)
                if opts.get("yazdir"):
                    pr = opts.get("yazici")
                    prof = storage.load_settings().get("yazicilar", {}).get(pr) or printing.default_profile(pr)
                    printing.print_image(out, pr, prof, copies=int(it.get("adet", 1)), title="Serbest baskı")
                    printed += int(it.get("adet", 1))
            return {"dosyalar": files, "klasor": os.path.dirname(files[0]) if files else "", "basilan": printed}
        return self._safe(go)

    def gpu_durum(self):
        return {"ad": models.provider_info()["name"], "gpu_acik": storage.load_settings().get("gpu_kullan", True),
                "saglayicilar": models.available_providers()}

    def gpu_ayarla(self, acik):
        def go():
            storage.update_settings({"gpu_kullan": bool(acik)})
            models.set_gpu(bool(acik))
            return self.gpu_durum()
        return self._safe(go)

    def toplu_isle(self, jids, fid):
        """Sırayla analiz → maske → rötuş (hızlı mod gibi); sorunlu olanları işaretler."""
        def go():
            out = []
            for n, jid in enumerate(jids):
                j = self.jobs.get(jid)
                if not j:
                    continue
                self._p(n / max(1, len(jids)), f"Toplu işlem {n + 1}/{len(jids)}: {j.name}")
                try:
                    if not j.analyzed:
                        j.analyze(self._p)
                    j.matte(self._p)
                    j.retouch(self._p)
                    bad = [c for c in j.compliance(self._fmt(fid)) if c.get("durum") == "bad"]
                    out.append({"id": jid, "ok": True, "sorun": len(bad), "ad": j.name})
                except Exception as e:
                    log_exc(f"Toplu işlem hatası {j.name}")
                    out.append({"id": jid, "ok": False, "hata": str(e), "ad": j.name})
            return {"sonuc": out}
        return self._safe(go)

    def printers(self):
        s = storage.load_settings()
        names = printing.list_printers()
        return {"yazicilar": [{"ad": n, "profil": s.get("yazicilar", {}).get(n) or printing.default_profile(n)} for n in names],
                "varsayilan": s.get("varsayilan_yazici") or printing.default_printer()}

    def printer_props(self, name):
        def go():
            s = storage.load_settings()
            prof = s.get("yazicilar", {}).get(name) or printing.default_profile(name)
            dm = printing.printer_dialog(name, prof.get("devmode"))
            if dm:
                prof["devmode"] = dm
                s.setdefault("yazicilar", {})[name] = prof
                storage.save_settings(s)
            return {"profil": prof}
        return self._safe(go)

    def save_printer(self, name, profile, make_default=False):
        def go():
            s = storage.load_settings()
            old = s.get("yazicilar", {}).get(name, {})
            prof = {**printing.default_profile(name), **old, **profile}
            s.setdefault("yazicilar", {})[name] = prof
            if make_default:
                s["varsayilan_yazici"] = name
            storage.save_settings(s)
            return {"profil": prof}
        return self._safe(go)

    def test_print(self, name):
        def go():
            s = storage.load_settings()
            prof = s.get("yazicilar", {}).get(name) or printing.default_profile(name)
            printing.print_image(test_page(), name, prof, 1, "Vesikalik Pro test sayfasi")
            return {}
        return self._safe(go)

    def test_page_preview(self):
        return {"gorsel": to_b64(test_page(), 900)}

    def calibrate(self, name, yatay, dikey):
        def go():
            s = storage.load_settings()
            prof = s.get("yazicilar", {}).get(name) or printing.default_profile(name)
            prof = printing.calibrate(prof, float(yatay), float(dikey))
            s.setdefault("yazicilar", {})[name] = prof
            storage.save_settings(s)
            return {"profil": prof}
        return self._safe(go)

    def archive(self, q=""):
        recs = storage.records()
        idx = {id(r): i for i, r in enumerate(recs)}
        found = storage.search(q)
        return {"kayitlar": [dict(r, _i=recs.index(r)) for r in found]}

    def report(self, day=""):
        return storage.daily_report(day)

    def export_settings(self):
        def go():
            folder = self.pick_folder()
            if not folder:
                return {"iptal": True}
            p = os.path.join(folder, f"VesikalikPro_ayarlar_{datetime.date.today()}.zip")
            storage.export_settings(p)
            return {"yol": p}
        return self._safe(go)

    def import_settings(self, pw):
        def go():
            fs = self.pick_files()
            if not fs:
                return {"iptal": True}
            storage.import_settings(fs[0], pw)
            return {"ayarlar": storage.public_settings()}
        return self._safe(go)

    def open_folder(self, path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # noqa
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass
        return {"ok": True}

    def sorun_bildir(self):
        """Hata kayıtları + (şifresiz) ayarlar + sistem bilgisi tek zip. Fotoğraf İÇERMEZ. Masaüstüne kaydedilir."""
        def go():
            import platform, zipfile, json as _j
            desk = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.isdir(desk):
                desk = os.path.expanduser("~")
            p = os.path.join(desk, f"VesikalikPro_sorun_raporu_{datetime.datetime.now():%Y%m%d_%H%M}.zip")
            info = {"surum": VERSION, "sistem": platform.platform(), "python": platform.python_version(),
                    "donanim": models.provider_info(), "saglayicilar": models.available_providers(),
                    "modeller": {k: models.has_model(k) for k in models.MODELS}}
            with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("sistem_bilgisi.json", _j.dumps(info, ensure_ascii=False, indent=2, default=str))
                z.writestr("ayarlar.json", _j.dumps(storage.public_settings(), ensure_ascii=False, indent=2, default=str))
                ld = log_dir()
                if os.path.isdir(ld):
                    for f in sorted(os.listdir(ld))[-14:]:
                        fp = os.path.join(ld, f)
                        if os.path.isfile(fp):
                            z.write(fp, "kayitlar/" + f)
            try:
                os.startfile(os.path.dirname(p))
            except Exception:
                pass
            return {"yol": p}
        return self._safe(go)

    def open_logs(self):
        return self.open_folder(log_dir())

    def poll_camera(self):
        """Kamera klasöründeki yeni çekimleri sıraya ekler (ilk çağrıda mevcutlar yok sayılır)."""
        s = storage.load_settings()
        d = s.get("kamera_klasoru")
        if not (s.get("kamera_izle") and d and os.path.isdir(d)):
            return {"yeni": []}
        exts = IMG_EXTS
        now = {os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(exts)}
        if getattr(self, "_cam_dir", None) != d:
            self._cam_dir, self._cam_seen = d, now
            return {"yeni": []}
        new = []
        for p in sorted(now - self._cam_seen):
            try:
                s1 = os.path.getsize(p); time.sleep(0.3)
                if os.path.getsize(p) != s1:
                    continue  # hâlâ yazılıyor
            except OSError:
                continue
            new.append(p)
            self._cam_seen.add(p)
        return {"yeni": self.add_files(new) if new else []}

    def log_js_error(self, msg):
        log(f"Arayüz hatası: {msg}", "ERROR")
        return {"ok": True}


def _save_online(photo, path, max_kb=240, px=600):
    h, w = photo.shape[:2]
    s = px / max(h, w)
    img = cv2.resize(photo, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    from PIL import Image
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    for q in range(95, 30, -5):
        pil.save(path, "JPEG", quality=q, dpi=(300, 300))
        if os.path.getsize(path) <= max_kb * 1024:
            break
