"""Geliştirme/test sunucusu: arayüzü tarayıcıda çalıştırır (pywebview olmadan)."""
import json
import os
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.api import Api  # noqa

API = Api()
UI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=UI, **k)

    def log_message(self, *a):
        pass

    def do_POST(self):
        name = self.path.split("/api/", 1)[1]
        n = int(self.headers.get("Content-Length", 0))
        args = json.loads(self.rfile.read(n) or b"[]")
        res = getattr(API, name)(*args)
        body = json.dumps(res, default=lambda o: o.item() if hasattr(o, "item") else str(o)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
