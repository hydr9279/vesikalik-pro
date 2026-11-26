"""Hayal Medya Vesikalık Pro — başlatıcı.
Açılışta: (1) tek kopya kilidi (çift tıklayınca ikinci uygulama açılmaz, açık olan öne gelir),
(2) ağır modüller yüklenirken hemen animasyonlu yükleme ekranı."""
import os
import sys
import threading

TITLE_PREFIX = "Hayal Medya Vesikalık Pro"
_MUTEX = None


def _tek_kopya() -> bool:
    """True: bu ilk kopya. False: zaten çalışıyor (açık pencere öne getirilir)."""
    global _MUTEX
    if os.name != "nt":
        return True
    import ctypes
    k32 = ctypes.windll.kernel32
    k32.CreateMutexW.restype = ctypes.c_void_p
    _MUTEX = k32.CreateMutexW(None, False, "Local\\HayalMedyaVesikalikPro_tek_kopya")
    if k32.GetLastError() != 183:   # ERROR_ALREADY_EXISTS
        return True
    try:   # çalışan pencereyi öne getir (henüz açılmadıysa yükleme ekranı zaten görünüyor)
        u32 = ctypes.windll.user32
        hwnds = []
        EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def cb(h, _):
            n = u32.GetWindowTextLengthW(h)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                u32.GetWindowTextW(h, buf, n + 1)
                if buf.value.startswith(TITLE_PREFIX) and u32.IsWindowVisible(h):
                    hwnds.append(h)
            return True
        u32.EnumWindows(EnumProc(cb), 0)
        for h in hwnds:
            u32.ShowWindow(h, 9)   # SW_RESTORE
            u32.SetForegroundWindow(h)
    except Exception:
        pass
    return False


class Acilis:
    """Çerçevesiz, animasyonlu yükleme ekranı (tkinter, ayrı iş parçacığında). Yoksa sessizce atlanır."""

    def __init__(self):
        self._kapat = threading.Event()
        self._t = threading.Thread(target=self._calis, daemon=True)
        self._t.start()

    def kapat(self):
        self._kapat.set()

    def _calis(self):
        try:
            import tkinter as tk
            r = tk.Tk()
            r.overrideredirect(True)
            r.attributes("-topmost", True)
            w, h = 520, 250
            r.geometry(f"{w}x{h}+{(r.winfo_screenwidth() - w) // 2}+{(r.winfo_screenheight() - h) // 2}")
            r.configure(bg="#0E1014")
            fr = tk.Frame(r, bg="#0E1014", highlightbackground="#2A2F3A", highlightthickness=1)
            fr.pack(fill="both", expand=True)
            logo = None
            try:
                from engine.paths import res_dir
                p = os.path.join(res_dir(), "ui", "assets", "logo_white.png")
                if os.path.exists(p):
                    logo = tk.PhotoImage(file=p)
                    k = max(1, logo.width() // 220)
                    logo = logo.subsample(k, k)
            except Exception:
                logo = None
            if logo:
                tk.Label(fr, image=logo, bg="#0E1014").pack(pady=(26, 6))
            else:
                tk.Label(fr, text="HAYAL MEDYA", fg="#F5B63F", bg="#0E1014", font=("Segoe UI", 22, "bold")).pack(pady=(40, 6))
            tk.Label(fr, text="Vesikalık Pro yükleniyor…", fg="#E6E8EC", bg="#0E1014", font=("Segoe UI", 12, "bold")).pack()
            tk.Label(fr, text="Yapay zeka modelleri hazırlanıyor, lütfen bekleyin. Tekrar tıklamanız gerekmez.",
                     fg="#8A92A0", bg="#0E1014", font=("Segoe UI", 9)).pack(pady=(4, 12))
            bw = 380
            cv = tk.Canvas(fr, width=bw, height=8, bg="#1B1F27", highlightthickness=0)
            cv.pack()
            bar = cv.create_rectangle(0, 0, 0, 8, fill="#F5B63F", width=0)
            st = {"x": -120}

            def tick():
                if self._kapat.is_set():
                    r.destroy()
                    return
                st["x"] += 9
                if st["x"] > bw:
                    st["x"] = -120
                cv.coords(bar, max(0, st["x"]), 0, min(bw, st["x"] + 120), 8)
                r.after(25, tick)
            tick()
            r.after(120000, lambda: self._kapat.set())   # güvenlik: en çok 2 dakika
            r.mainloop()
        except Exception:
            pass


def main(acilis):
    import webview
    from engine.api import Api
    from engine.log import log
    from engine.paths import APP_NAME, VERSION, res_dir
    api = Api()
    ui = os.path.join(res_dir(), "ui", "index.html")
    win = webview.create_window(f"{APP_NAME} {VERSION}", ui, js_api=api, width=1440, height=900,
                                min_size=(1180, 720), background_color="#0E1014")
    api.window = win
    try:
        win.events.loaded += lambda: acilis.kapat()
    except Exception:
        pass
    log(f"Program başlatıldı v{VERSION}")
    webview.start(debug=("--debug" in sys.argv), private_mode=True)
    acilis.kapat()


if __name__ == "__main__":
    if not _tek_kopya():
        sys.exit(0)
    acilis = Acilis()
    try:
        main(acilis)
    except Exception:
        acilis.kapat()
        try:
            from engine.log import log_exc
            log_exc("Program başlatılamadı")
        except Exception:
            pass
        raise
