"""Hayal Medya Vesikalık Pro — başlatıcı."""
import os
import sys

from engine.api import Api
from engine.log import log, log_exc
from engine.paths import APP_NAME, VERSION, res_dir


def main():
    import webview
    api = Api()
    ui = os.path.join(res_dir(), "ui", "index.html")
    win = webview.create_window(f"{APP_NAME} {VERSION}", ui, js_api=api, width=1440, height=900,
                                min_size=(1180, 720), background_color="#0E1014")
    api.window = win
    log(f"Program başlatıldı v{VERSION}")
    webview.start(debug=("--debug" in sys.argv), private_mode=False)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_exc("Program başlatılamadı")
        raise
