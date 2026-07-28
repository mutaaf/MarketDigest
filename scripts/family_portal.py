#!/usr/bin/env python3
"""Family portal on port 80.

Serves the static landing page from ~/projects/family-portal (the XP-desktop
site) and provides short deep links into local projects:

    /            -> the landing page
    /compass...  -> redirect to the Compass app on :8550
    /marketdigest -> redirect to the Market Digest Command Center on :8550

macOS allows non-root binding to port 80 since Mojave.
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORTAL_DIR = Path.home() / "projects" / "family-portal"
APP_PORT = 8550

REDIRECTS = {
    "/marketdigest": "/",         # Command Center
    "/compass": "/compass",       # family investing app (prefix match)
}


class PortalHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PORTAL_DIR), **kwargs)

    def do_GET(self):
        host = (self.headers.get("Host") or "localhost").split(":")[0]
        if self.path.startswith("/compass"):
            return self._go(f"http://{host}:{APP_PORT}{self.path}")
        if self.path.rstrip("/") == "/marketdigest":
            return self._go(f"http://{host}:{APP_PORT}/")
        return super().do_GET()

    def _go(self, url: str):
        self.send_response(302)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    PORTAL_DIR.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer(("0.0.0.0", 80), PortalHandler).serve_forever()
