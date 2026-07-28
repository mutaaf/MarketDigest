#!/usr/bin/env python3
"""Port-80 convenience redirector.

Lets the family type just `yourmac.local/compass` (no port) — every request
is redirected to the real server on :8550, preserving host and path.
macOS allows non-root binding to port 80 since Mojave.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TARGET_PORT = 8550


class Redirect(BaseHTTPRequestHandler):
    def _redirect(self):
        host = (self.headers.get("Host") or "localhost").split(":")[0]
        path = self.path if self.path.startswith("/") else "/"
        if path == "/":
            path = "/compass"  # bare hostname lands on the family app
        self.send_response(302)
        self.send_header("Location", f"http://{host}:{TARGET_PORT}{path}")
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_GET = do_HEAD = do_POST = _redirect

    def log_message(self, *args):  # keep the log quiet
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 80), Redirect).serve_forever()
