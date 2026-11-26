"""Yapay zeka modelleri: yükleme, donanım seçimi (CUDA → DirectML → CPU)."""
from __future__ import annotations

import os
import threading

import numpy as np

from .paths import model_path
from .log import log

try:
    import onnxruntime as ort
    ort.set_default_logger_severity(3)
    # NVIDIA: CUDA/cuDNN kütüphanelerini pip paketlerinden yükle (onnxruntime-gpu[cuda,cudnn])
    if "CUDAExecutionProvider" in ort.get_available_providers() and hasattr(ort, "preload_dlls"):
        try:
            ort.preload_dlls()
        except Exception:
            pass
except Exception:  # pragma: no cover
    ort = None

_LOCK = threading.Lock()
_SESSIONS: dict = {}
_PROVIDER_INFO = {"name": "CPU", "detail": ""}
_FORCE_CPU = False


def set_gpu(acik: bool) -> None:
    """Ekran kartını aç/kapat. Kapalıysa tüm modeller yalnızca işlemci (CPU) ile çalışır; oturumlar yeniden yüklenir."""
    global _FORCE_CPU
    with _LOCK:
        if _FORCE_CPU == (not acik):
            return
        _FORCE_CPU = not acik
        _SESSIONS.clear()
        _PROVIDER_INFO.update(name="İşlemci (CPU)" if _FORCE_CPU else "CPU")
    log(f"Ekran kartı {'açık' if acik else 'KAPALI (yalnız işlemci)'}")


# Modeller ve özellikleri
IMN = ((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
MODELS = {
    "birefnet": {"file": "birefnet_portrait.onnx", "size": 1024, "mean": IMN[0], "std": IMN[1], "sigmoid": True,
                 "ad": "BiRefNet Portre", "grup": "matte", "lisans": "MIT", "ticari": True,
                 "not": "Portre için eğitilmiş; saç ve omuz kenarında çok iyi (varsayılan)."},
    "birefnet_matting": {"file": "birefnet_matting.onnx", "size": 1024, "mean": IMN[0], "std": IMN[1], "sigmoid": True,
                         "ad": "BiRefNet Matting", "grup": "matte", "lisans": "MIT", "ticari": True, "ek": True,
                         "not": "Yumuşak (alfa) kenarlı matting; ince saç telleri."},
    "birefnet_hr": {"file": "birefnet_hr_matting.onnx", "size": 2048, "mean": IMN[0], "std": IMN[1], "sigmoid": True,
                    "ad": "BiRefNet HR Matting (2048)", "grup": "matte", "lisans": "MIT", "ticari": True, "ek": True, "agir": True,
                    "not": "Yüksek çözünürlük; en ince detay. Ağır: ekran kartı önerilir, yavaştır."},
    "birefnet_general": {"file": "birefnet_general.onnx", "size": 1024, "mean": IMN[0], "std": IMN[1], "sigmoid": True,
                         "ad": "BiRefNet Genel", "grup": "matte", "lisans": "MIT", "ticari": True, "ek": True,
                         "not": "Genel amaçlı; şapka, aksesuar ve karışık sahneler."},
    "ben2": {"file": "ben2_base.onnx", "size": 1024, "mean": (0.0, 0.0, 0.0), "std": (1.0, 1.0, 1.0), "sigmoid": None,
             "ad": "BEN2 Base", "grup": "matte", "lisans": "MIT", "ticari": True, "ek": True,
             "not": "Saç ve yarı saydam kenarlarda güçlü; ayrı bir bakış açısı."},
    "rmbg2": {"file": "rmbg2.onnx", "size": 1024, "mean": IMN[0], "std": IMN[1], "sigmoid": None,
              "ad": "RMBG-2.0", "grup": "matte", "lisans": "CC BY-NC 4.0", "ticari": False, "ek": True,
              "not": "Ticari olmayan lisans. Sorumluluk kullanıcıya aittir."},
    "vitmatte": {"file": "vitmatte.onnx", "size": 0, "mean": (0.485, 0.456, 0.406), "std": (0.229, 0.224, 0.225), "sigmoid": None,
                 "ad": "ViTMatte (trimap rafine)", "grup": "rafine", "lisans": "Ağırlıklar ticari değil", "ticari": False, "ek": True,
                 "not": "Mevcut maskenin belirsiz kenarını rafine eder. Ticari olmayan lisans."},
    "isnet": {"file": "isnet-general-use.onnx", "size": 1024, "mean": (0.5, 0.5, 0.5), "std": (1.0, 1.0, 1.0), "sigmoid": False,
              "ad": "ISNet", "grup": "matte", "lisans": "Apache 2.0", "ticari": True, "not": "Detaylı, hafif; yedek."},
    "u2net": {"file": "u2net_human_seg.onnx", "size": 320, "mean": IMN[0], "std": IMN[1], "sigmoid": False,
              "ad": "U²-Net İnsan", "grup": "matte", "lisans": "Apache 2.0", "ticari": True, "not": "Hızlı; en düşük kalite."},
    "parse": {"file": "face_parsing_resnet34.onnx"},
    "lama": {"file": "lama.onnx"},
    "sam": {"file": "efficientsam.onnx"},
    "yunet": {"file": "yunet.onnx"},
}
MATTE_ORDER = ["birefnet", "birefnet_matting", "birefnet_hr", "birefnet_general", "ben2", "rmbg2", "isnet", "u2net"]
_KAPALI: set = set()   # ayarlardan kapatılan modeller


def set_disabled(keys) -> None:
    _KAPALI.clear()
    _KAPALI.update(keys or [])


def matte_models() -> list:
    """Kullanılabilir (dosyası var, kapatılmamış) arka plan modelleri."""
    return [k for k in MATTE_ORDER if k in MODELS and has_model(k) and k not in _KAPALI]


def available_providers() -> list:
    if ort is None:
        return []
    return ort.get_available_providers()


def provider_info() -> dict:
    return dict(_PROVIDER_INFO)


def _providers(force_cpu=False):
    av = available_providers()
    if force_cpu:
        return ["CPUExecutionProvider"]
    order = []
    if "CUDAExecutionProvider" in av:
        order.append(("CUDAExecutionProvider", {"cudnn_conv_algo_search": "HEURISTIC"}))
    if "DmlExecutionProvider" in av:
        order.append("DmlExecutionProvider")
    order.append("CPUExecutionProvider")
    return order


def session(key: str):
    """Modeli bir kez yükler. GPU başarısız olursa CPU'ya düşer."""
    with _LOCK:
        if key in _SESSIONS:
            return _SESSIONS[key]
        path = model_path(MODELS[key]["file"])
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model dosyası bulunamadı: {os.path.basename(path)}")
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        so.log_severity_level = 3
        # Büyük modeller için bellek dostu çalıştırma (16 GB RAM'li bilgisayar)
        if key.startswith("birefnet") or key in ("rmbg2", "ben2"):
            so.enable_mem_pattern = False
            so.enable_cpu_mem_arena = False
        last_err = None
        for force_cpu in ((True,) if _FORCE_CPU else (False, True)):
            try:
                s = ort.InferenceSession(path, so, providers=_providers(force_cpu))
                used = s.get_providers()[0]
                name = {"CUDAExecutionProvider": "NVIDIA CUDA", "DmlExecutionProvider": "DirectML",
                        "CPUExecutionProvider": "İşlemci (CPU)"}.get(used, used)
                if key in ("birefnet", "isnet", "lama", "parse") or key in MATTE_ORDER:
                    _PROVIDER_INFO.update(name=name)
                log(f"Model yüklendi: {key} → {name}")
                _SESSIONS[key] = s
                return s
            except Exception as e:  # GPU sürücü sorunu vb.
                last_err = e
                log(f"Model yükleme hatası ({key}, cpu={force_cpu}): {e}", "WARN")
        raise RuntimeError(f"Model açılamadı: {key}: {last_err}")


def has_model(key: str) -> bool:
    return os.path.exists(model_path(MODELS[key]["file"]))


def run(key: str, feeds: dict):
    s = session(key)
    try:
        return s.run(None, feeds)
    except Exception as e:
        # GPU'da bellek yetmezse CPU ile tekrar dene
        log(f"Çalıştırma hatası ({key}): {e} — CPU ile tekrar deneniyor", "WARN")
        with _LOCK:
            so = ort.SessionOptions()
            so.enable_mem_pattern = False
            so.enable_cpu_mem_arena = False
            s2 = ort.InferenceSession(model_path(MODELS[key]["file"]), so, providers=["CPUExecutionProvider"])
            _SESSIONS[key] = s2
        return s2.run(None, feeds)


def best_matte_model(pref: str = "auto") -> str:
    if pref in MATTE_ORDER and has_model(pref) and pref not in _KAPALI:
        return pref
    for k in ("birefnet", "isnet", "u2net"):
        if has_model(k) and _fits(k):
            return k
    return "u2net"


def _fits(key: str) -> bool:
    """BiRefNet CPU'da ~9 GB ister; GPU yoksa ve RAM azsa ISNet'e geç."""
    if key not in ("birefnet", "birefnet_general", "birefnet_matting", "birefnet_hr"):
        return True
    if any(p in available_providers() for p in ("CUDAExecutionProvider", "DmlExecutionProvider")):
        return True
    return mem_total() >= 14 * 1024 ** 3


def mem_total() -> int:
    """Toplam RAM (bayt)."""
    try:
        import psutil
        return psutil.virtual_memory().total
    except Exception:
        pass
    try:
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong), ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return int(m.ullTotalPhys)
    except Exception:
        pass
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except Exception:
        return 16 * 1024 ** 3


def norm_input(img_bgr: np.ndarray, size: int, mean, std) -> np.ndarray:
    import cv2
    x = cv2.resize(img_bgr, (size, size), interpolation=cv2.INTER_AREA)
    x = cv2.cvtColor(x, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    x = (x - np.array(mean, np.float32)) / np.array(std, np.float32)
    return x.transpose(2, 0, 1)[None].astype(np.float32)
