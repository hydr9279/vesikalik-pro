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


def _splash_calis(hazir_dosya):
    """AYRI İŞLEMDE çalışır (ana uygulamayla hiçbir şey paylaşmaz, bu yüzden takılmaz).
    Ana uygulama arayüzü gösterince `hazir_dosya` oluşturur; bu pencere kendiliğinden kapanır."""
    import time
    import tkinter as tk
    t0 = time.time()
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
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        p = os.path.join(base, "ui", "assets", "logo_white.png")
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
        if os.path.exists(hazir_dosya) or time.time() - t0 > 90:
            r.destroy()
            return
        st["x"] += 9
        if st["x"] > bw:
            st["x"] = -120
        cv.coords(bar, max(0, st["x"]), 0, min(bw, st["x"] + 120), 8)
        r.after(25, tick)
    tick()
    r.mainloop()


class Acilis:
    """Yükleme ekranını ayrı bir işlem olarak başlatır; kapatma = hazır dosyası oluşturmak."""

    def __init__(self):
        import tempfile
        self._dosya = os.path.join(tempfile.gettempdir(), f"hmvp_hazir_{os.getpid()}")
        try:
            if os.path.exists(self._dosya):
                os.remove(self._dosya)
        except Exception:
            pass
        try:
            import subprocess
            if getattr(sys, "frozen", False):
                cmd = [sys.executable, "--splash", self._dosya]
            else:
                cmd = [sys.executable, os.path.abspath(__file__), "--splash", self._dosya]
            fl = 0x08000000 if os.name == "nt" else 0   # CREATE_NO_WINDOW
            self._pr = subprocess.Popen(cmd, creationflags=fl, close_fds=True)
        except Exception:
            self._pr = None

    def kapat(self):
        try:
            open(self._dosya, "w").close()
        except Exception:
            pass
        try:   # yedek: işlem hâlâ yaşıyorsa 2 sn sonra sonlandır
            pr = self._pr
            if pr:
                threading.Timer(2.0, lambda: (pr.poll() is None) and pr.terminate()).start()
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
        win.events.shown += lambda: threading.Timer(6.0, acilis.kapat).start()   # yedek: pencere görününce en geç 6 sn
    except Exception:
        pass
    log(f"Program başlatıldı v{VERSION}")
    webview.start(debug=("--debug" in sys.argv), private_mode=True)
    acilis.kapat()


if __name__ == "__main__":
    if "--splash" in sys.argv:
        try:
            _splash_calis(sys.argv[sys.argv.index("--splash") + 1])
        except Exception:
            pass
        sys.exit(0)
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
