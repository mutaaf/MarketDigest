#!/usr/bin/env python3
"""Family portal on port 80 — azizfamily.local.

Serves the XP-desktop site from ~/projects/family-portal and powers it:

  Static     /                       XP desktop (login UI included)
             /kids/<kid>/<proj>/     kids' published pages   (signed-in only)
  Auth       POST /api/login         passcode -> signed cookie (per-user, 30d)
             POST /api/logout, GET /api/me
  Apps       GET  /api/projects      links + managed apps + kids' projects
             POST /api/app/<id>/start|stop   launch/stop a dev server (parent)
             GET  /api/app/<id>/log          last lines of the app's log
             GET  /app/<id>          302 to the app's port on this host
             /compass, /marketdigest 302 to :8550 (any signed-in user)
  Kids       POST /api/kids/new      {kid, name} -> scaffold a starter page
             GET  /api/kids/file?kid=&proj=   read a project's index.html
             POST /api/kids/file     {kid, proj, content} -> save it

Users (parent/kid roles), passcodes and the signing secret live in
~/.config/azizfamily-portal.json; the launchable-app registry lives in
~/.config/azizfamily-projects.json. Both are outside the web root.

Kids can create/edit only inside their own space; parents everywhere.
macOS allows non-root binding to port 80 since Mojave.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import signal
import socket
import subprocess
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

PORTAL_DIR = Path.home() / "projects" / "family-portal"
KIDS_DIR = PORTAL_DIR / "kids"
CONFIG_PATH = Path.home() / ".config" / "azizfamily-portal.json"
REGISTRY_PATH = Path.home() / ".config" / "azizfamily-projects.json"
LOG_DIR = Path.home() / "Library" / "Logs" / "azizfamily"
APP_PORT = 8550
COOKIE = "azizportal"
SESSION_SECONDS = 30 * 86400
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")

_failed = {}  # ip -> [timestamps of failed logins]

DEFAULT_USERS = [
    {"id": "family", "name": "Aziz Family", "passcode": "bliss",
     "role": "parent", "avatar": "avatar", "theme": "day"},
    {"id": "astro", "name": "Astro", "passcode": "comet",
     "role": "kid", "avatar": "astro", "theme": "sunset"},
    {"id": "robo", "name": "Robo", "passcode": "beep",
     "role": "kid", "avatar": "robo", "theme": "spring"},
]


def load_config():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            cfg = {}
    changed = False
    if not cfg.get("secret"):
        cfg["secret"] = secrets.token_hex(32)
        changed = True
    if not cfg.get("users"):
        # migrate the old single-passcode config
        cfg["users"] = [dict(u) for u in DEFAULT_USERS]
        if cfg.get("passcode"):
            cfg["users"][0]["passcode"] = cfg["passcode"]
        changed = True
    if changed:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")
    return cfg


CFG = load_config()


def users():
    return CFG.get("users", [])


def user_by_id(uid):
    return next((u for u in users() if u["id"] == uid), None)


_registry_cache = {"mtime": 0, "data": {"links": [], "apps": []}}


def registry():
    try:
        mtime = REGISTRY_PATH.stat().st_mtime
        if mtime != _registry_cache["mtime"]:
            _registry_cache["data"] = json.loads(REGISTRY_PATH.read_text())
            _registry_cache["mtime"] = mtime
    except (OSError, json.JSONDecodeError):
        pass
    return _registry_cache["data"]


def app_entry(app_id):
    return next((a for a in registry().get("apps", []) if a["id"] == app_id), None)


# ---- signed cookie: "<expiry>|<userid>" -----------------------------------
def sign(value: str) -> str:
    mac = hmac.new(CFG["secret"].encode(), value.encode(), hashlib.sha256)
    return f"{value}.{mac.hexdigest()}"


def token_user(token):
    """Return the user dict for a valid token, else None."""
    if not token or "." not in token:
        return None
    value, mac = token.rsplit(".", 1)
    good = hmac.new(CFG["secret"].encode(), value.encode(),
                    hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, good):
        return None
    try:
        exp, uid = value.split("|", 1)
        if float(exp) < time.time():
            return None
    except ValueError:
        return None
    return user_by_id(uid)


# ---- process manager -------------------------------------------------------
SPAWN_ENV = dict(os.environ,
                 PATH="/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", ""),
                 HOME=str(Path.home()))


def port_alive(port):
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=0.25):
            return True
    except OSError:
        return False


def pidfile(app_id):
    return LOG_DIR / f"{app_id}.pid"


def app_pid(app_id):
    try:
        pid = int(pidfile(app_id).read_text().strip())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


def start_app(entry):
    if port_alive(entry["port"]):
        return {"ok": True, "note": "already running"}
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = open(LOG_DIR / f"{entry['id']}.log", "ab")
    log.write(f"\n===== portal start {time.strftime('%F %T')} =====\n".encode())
    proc = subprocess.Popen(
        entry["cmd"], shell=True, cwd=entry["dir"],
        stdout=log, stderr=log, env=SPAWN_ENV,
        start_new_session=True)   # own process group -> clean stop
    pidfile(entry["id"]).write_text(str(proc.pid))
    return {"ok": True, "pid": proc.pid}


def stop_app(entry):
    pid = app_pid(entry["id"])
    if pid:
        try:
            os.killpg(pid, signal.SIGTERM)
            for _ in range(20):
                time.sleep(0.15)
                if app_pid(entry["id"]) is None:
                    break
            else:
                os.killpg(pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            pidfile(entry["id"]).unlink()
        except OSError:
            pass
        return {"ok": True}
    if port_alive(entry["port"]):
        return {"error": "Running, but it wasn't started from the portal — "
                         "stop it from the terminal."}
    return {"ok": True, "note": "not running"}


# ---- kids' spaces ----------------------------------------------------------
KID_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — an original by {owner}</title>
<meta property="og:site_name" content="Aziz Family XP">
<meta property="og:title" content="{title} — hot off the family web press! 👨‍🍳">
<meta property="og:description" content="Handcrafted HTML by {owner}, baked fresh on the Aziz family server. Quality-checked by absolutely nobody.">
<meta property="og:image" content="http://azizfamily.local/og.png">
<link rel="icon" type="image/png" href="/favicon-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<style>
  /* CSS makes things PRETTY. Try changing these colors! */
  body {{ font-family: "Comic Sans MS", "Chalkboard SE", sans-serif;
         background: linear-gradient(#7ec8ff, #eaf7ff); min-height: 100vh;
         display: flex; flex-direction: column; align-items: center;
         justify-content: center; gap: 20px; margin: 0; text-align: center; }}
  h1 {{ font-size: 3em; color: #1446a0; margin: 0; }}
  button {{ font-size: 1.5em; padding: 12px 24px; border-radius: 14px;
           border: 3px solid #1446a0; background: #ffd23f; cursor: pointer; }}
  button:active {{ transform: scale(.94); }}
</style>
</head>
<body>
  <!-- HTML is the STUFF on the page. Change these words! -->
  <h1>{title}</h1>
  <p>Made by {owner} on the Aziz family server 🖥️</p>
  <button onclick="party()">Press me!</button>

<script>
// JavaScript makes the page DO things. This one makes emoji rain!
function party() {{
  for (let i = 0; i < 40; i++) {{
    const e = document.createElement("div");
    e.textContent = ["🎉","⭐","🚀","🤖","🌈"][i % 5];
    e.style.cssText = "position:fixed;top:-40px;font-size:28px;left:" +
      Math.random() * 100 + "vw;transition:top 2.5s linear " +
      Math.random() + "s";
    document.body.appendChild(e);
    setTimeout(() => e.style.top = "110vh", 20);
    setTimeout(() => e.remove(), 4000);
  }}
}}
</script>
</body>
</html>
"""


def kid_ids():
    return [u["id"] for u in users() if u.get("role") == "kid"]


def kid_projects(kid):
    base = KIDS_DIR / kid
    out = []
    if base.is_dir():
        for d in sorted(base.iterdir()):
            if d.is_dir() and (d / "index.html").exists():
                out.append({"name": d.name,
                            "url": f"/kids/{kid}/{d.name}/",
                            "mtime": (d / "index.html").stat().st_mtime})
    return out


def kid_file(kid, proj):
    """Validated path to a kid project's index.html, or None."""
    if kid not in kid_ids() or not NAME_RE.match(proj or ""):
        return None
    return KIDS_DIR / kid / proj / "index.html"


# ---- HTTP handler ----------------------------------------------------------
class PortalHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PORTAL_DIR), **kwargs)

    def _cookie(self):
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            part = part.strip()
            if part.startswith(COOKIE + "="):
                return unquote(part[len(COOKIE) + 1:])
        return None

    def _user(self):
        return token_user(self._cookie() or "")

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

    def _go(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    # ---- GET ----
    def do_GET(self):
        host = (self.headers.get("Host") or "localhost").split(":")[0]
        parsed = urlparse(self.path)
        path = parsed.path
        user = self._user()

        if path == "/api/me":
            if not user:
                return self._json({"ok": False})
            return self._json({"ok": True, "user": {
                "id": user["id"], "name": user["name"], "role": user["role"],
                "avatar": user.get("avatar", "avatar"),
                "theme": user.get("theme", "day")}})

        if path == "/api/users":   # login tiles (no passcodes!)
            return self._json({"users": [
                {"id": u["id"], "name": u["name"], "role": u["role"],
                 "avatar": u.get("avatar", "avatar")} for u in users()]})

        if path.startswith("/compass") or path.rstrip("/") == "/marketdigest":
            if not user:
                return self._go("/")
            if path.startswith("/compass"):
                return self._go(f"http://{host}:{APP_PORT}{self.path}")
            return self._go(f"http://{host}:{APP_PORT}/")

        if path == "/api/projects":
            if not user:
                return self._json({"error": "sign in first"}, 401)
            reg = registry()
            apps = []
            for a in reg.get("apps", []):
                apps.append({"id": a["id"], "label": a["label"],
                             "icon": a.get("icon", "briefcase"),
                             "desc": a.get("desc", ""), "port": a["port"],
                             "live": port_alive(a["port"]),
                             "startedByPortal": app_pid(a["id"]) is not None})
            links = []
            for l in reg.get("links", []):
                links.append({**l, "live": port_alive(l.get("port", 0))})
            kids = {k: kid_projects(k) for k in kid_ids()}
            return self._json({"links": links, "apps": apps, "kids": kids,
                               "role": user["role"]})

        if path.startswith("/api/app/") and path.endswith("/log"):
            if not user:
                return self._json({"error": "sign in first"}, 401)
            app_id = path[len("/api/app/"):-len("/log")]
            entry = app_entry(app_id)
            if not entry:
                return self._json({"error": "unknown app"}, 404)
            try:
                lines = (LOG_DIR / f"{app_id}.log").read_text(
                    errors="replace").splitlines()[-80:]
            except OSError:
                lines = ["(no log yet)"]
            return self._json({"log": "\n".join(lines)})

        if path.startswith("/app/"):
            if not user:
                return self._go("/")
            entry = app_entry(path[len("/app/"):].strip("/"))
            if not entry:
                return self._json({"error": "unknown app"}, 404)
            return self._go(f"http://{host}:{entry['port']}/")

        if path == "/api/kids/file":
            if not user:
                return self._json({"error": "sign in first"}, 401)
            q = parse_qs(parsed.query)
            kid = (q.get("kid") or [""])[0]
            proj = (q.get("proj") or [""])[0]
            f = kid_file(kid, proj)
            if not f or not f.exists():
                return self._json({"error": "not found"}, 404)
            if user["role"] != "parent" and user["id"] != kid:
                return self._json({"error": "that's not your project"}, 403)
            return self._json({"content": f.read_text(errors="replace")})

        # kids' pages require sign-in; everything else static is the shell
        if path.startswith("/kids/") and not user:
            return self._go("/")
        if any(seg.startswith(".") for seg in path.split("/") if seg):
            return self._json({"error": "not found"}, 404)
        return super().do_GET()

    # ---- POST ----
    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(min(length, 500_000)) or b"{}")
        except json.JSONDecodeError:
            data = {}
        user = self._user()

        if path == "/api/login":
            ip = self.client_address[0]
            now = time.time()
            tries = [t for t in _failed.get(ip, []) if now - t < 60]
            if len(tries) >= 8:
                _failed[ip] = tries
                return self._json({"error": "Too many tries. Wait a minute."}, 429)
            code = str(data.get("passcode", ""))
            uid = str(data.get("user", ""))
            u = user_by_id(uid)
            if u and code and code == str(u.get("passcode")):
                _failed.pop(ip, None)
                value = f"{now + SESSION_SECONDS}|{u['id']}"
                cookie = (f"{COOKIE}={quote(sign(value))}; "
                          f"Max-Age={SESSION_SECONDS}; Path=/; HttpOnly; "
                          f"SameSite=Lax")
                return self._json({"ok": True}, set_cookie=cookie)
            tries.append(now)
            _failed[ip] = tries
            return self._json({"error": "Incorrect passcode."}, 403)

        if path == "/api/logout":
            return self._json({"ok": True},
                              set_cookie=f"{COOKIE}=; Max-Age=0; Path=/")

        if not user:
            return self._json({"error": "sign in first"}, 401)

        if path.startswith("/api/app/") and path.endswith("/start"):
            if user["role"] != "parent":
                return self._json({"error": "ask a parent to start apps"}, 403)
            entry = app_entry(path[len("/api/app/"):-len("/start")])
            if not entry:
                return self._json({"error": "unknown app"}, 404)
            return self._json(start_app(entry))

        if path.startswith("/api/app/") and path.endswith("/stop"):
            if user["role"] != "parent":
                return self._json({"error": "ask a parent to stop apps"}, 403)
            entry = app_entry(path[len("/api/app/"):-len("/stop")])
            if not entry:
                return self._json({"error": "unknown app"}, 404)
            return self._json(stop_app(entry))

        if path == "/api/kids/new":
            kid = str(data.get("kid", ""))
            raw = str(data.get("name", "")).strip().lower()
            proj = re.sub(r"[^a-z0-9-]+", "-", raw).strip("-")[:40]
            if user["role"] != "parent" and user["id"] != kid:
                return self._json({"error": "you can only build in your own space"}, 403)
            f = kid_file(kid, proj)
            if not f:
                return self._json({"error": "pick a name with letters or numbers"}, 400)
            if f.exists():
                return self._json({"error": "you already have a project with that name"}, 400)
            owner = user_by_id(kid)
            f.parent.mkdir(parents=True, exist_ok=True)
            title = str(data.get("name", proj)).strip()[:60] or proj
            f.write_text(KID_TEMPLATE.format(
                title=title, owner=(owner or {}).get("name", "me")))
            return self._json({"ok": True, "name": proj,
                               "url": f"/kids/{kid}/{proj}/"})

        if path == "/api/kids/file":
            kid = str(data.get("kid", ""))
            proj = str(data.get("proj", ""))
            content = str(data.get("content", ""))
            if user["role"] != "parent" and user["id"] != kid:
                return self._json({"error": "that's not your project"}, 403)
            f = kid_file(kid, proj)
            if not f or not f.exists():
                return self._json({"error": "not found"}, 404)
            if len(content) > 400_000:
                return self._json({"error": "too big"}, 400)
            f.write_text(content)
            return self._json({"ok": True})

        return self._json({"error": "not found"}, 404)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    PORTAL_DIR.mkdir(parents=True, exist_ok=True)
    KIDS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer(("0.0.0.0", 80), PortalHandler).serve_forever()
