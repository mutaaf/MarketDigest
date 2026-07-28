#!/usr/bin/env python3
"""Family portal on port 80.

Serves the static landing page from ~/projects/family-portal (the XP-desktop
site) and provides short deep links into local projects:

    /             -> the landing page (XP desktop; shows Welcome screen if not
                     signed in)
    /compass...   -> redirect to the Compass app on :8550   (passcode required)
    /marketdigest -> redirect to the Market Digest Command Center on :8550
                     (passcode required)

Auth: a family passcode entered on the XP Welcome screen. POST /api/login sets
an HMAC-signed cookie good for 30 days. Config (passcode + signing secret)
lives outside the web root in ~/.config/azizfamily-portal.json.

macOS allows non-root binding to port 80 since Mojave.
"""

import hashlib
import hmac
import json
import secrets
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote

PORTAL_DIR = Path.home() / "projects" / "family-portal"
CONFIG_PATH = Path.home() / ".config" / "azizfamily-portal.json"
APP_PORT = 8550
COOKIE = "azizportal"
SESSION_SECONDS = 30 * 86400

_failed = {}  # ip -> [timestamps of failed logins]


def load_config():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            cfg = {}
    changed = False
    if not cfg.get("passcode"):
        cfg["passcode"] = "bliss"
        changed = True
    if not cfg.get("secret"):
        cfg["secret"] = secrets.token_hex(32)
        changed = True
    if changed:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")
    return cfg


CFG = load_config()


def sign(value: str) -> str:
    mac = hmac.new(CFG["secret"].encode(), value.encode(), hashlib.sha256)
    return f"{value}.{mac.hexdigest()}"


def token_valid(token: str) -> bool:
    if not token or "." not in token:
        return False
    value, mac = token.rsplit(".", 1)
    good = hmac.new(CFG["secret"].encode(), value.encode(),
                    hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, good):
        return False
    try:
        return float(value) > time.time()
    except ValueError:
        return False


class PortalHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PORTAL_DIR), **kwargs)

    # ---- helpers --------------------------------------------------------
    def _cookie(self):
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            part = part.strip()
            if part.startswith(COOKIE + "="):
                return unquote(part[len(COOKIE) + 1:])
        return None

    def _authed(self):
        return token_valid(self._cookie() or "")

    def _json(self, obj, status=200, set_cookie=None):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()
        self.wfile.write(body)

    def _go(self, url: str):
        self.send_response(302)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ---- routes ---------------------------------------------------------
    def do_GET(self):
        host = (self.headers.get("Host") or "localhost").split(":")[0]
        path = self.path.split("?")[0]
        if path == "/api/me":
            return self._json({"ok": self._authed()})
        if path.startswith("/compass") or path.rstrip("/") == "/marketdigest":
            if not self._authed():
                return self._go("/")
            if path.startswith("/compass"):
                return self._go(f"http://{host}:{APP_PORT}{self.path}")
            return self._go(f"http://{host}:{APP_PORT}/")
        # dotfiles are never served
        if any(seg.startswith(".") for seg in path.split("/") if seg):
            return self._json({"error": "not found"}, 404)
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(min(length, 4096)) or b"{}")
        except json.JSONDecodeError:
            data = {}
        if path == "/api/login":
            ip = self.client_address[0]
            now = time.time()
            tries = [t for t in _failed.get(ip, []) if now - t < 60]
            if len(tries) >= 5:
                _failed[ip] = tries
                return self._json(
                    {"error": "Too many tries. Wait a minute."}, 429)
            if str(data.get("passcode", "")) == str(CFG["passcode"]):
                _failed.pop(ip, None)
                exp = str(now + SESSION_SECONDS)
                cookie = (f"{COOKIE}={quote(sign(exp))}; "
                          f"Max-Age={SESSION_SECONDS}; Path=/; HttpOnly; "
                          f"SameSite=Lax")
                return self._json({"ok": True}, set_cookie=cookie)
            tries.append(now)
            _failed[ip] = tries
            return self._json({"error": "Incorrect passcode."}, 403)
        if path == "/api/logout":
            return self._json({"ok": True},
                              set_cookie=f"{COOKIE}=; Max-Age=0; Path=/")
        return self._json({"error": "not found"}, 404)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    PORTAL_DIR.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer(("0.0.0.0", 80), PortalHandler).serve_forever()
