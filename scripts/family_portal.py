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
     "role": "parent", "avatar": "avatar", "theme": "day", "onboarded": True},
    {"id": "astro", "name": "Astro", "passcode": "",
     "role": "kid", "avatar": "astro", "theme": "sunset", "onboarded": False},
    {"id": "robo", "name": "Robo", "passcode": "",
     "role": "kid", "avatar": "robo", "theme": "spring", "onboarded": False},
]

AVATAR_CHOICES = {"astro", "robo", "cat", "dino"}
THEME_CHOICES = {"day", "sunset", "spring", "night"}


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
    for u in cfg["users"]:
        if "onboarded" not in u:
            # kids run the setup wizard on first sign-in; parents don't
            u["onboarded"] = u.get("role") == "parent"
            changed = True
    if changed:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")
    return cfg


CFG = load_config()


def save_users():
    """Persist CFG to disk after in-place user edits."""
    CONFIG_PATH.write_text(json.dumps(CFG, indent=2) + "\n")


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
<script src="/guestbook.js" defer></script>
</body>
</html>
"""

# ---- curriculum: missions, progress, guestbook, visits ---------------------
MISSIONS_PATH = Path.home() / ".config" / "azizfamily-missions.json"

DEFAULT_MISSIONS = {
    "_help": ("Quest Log missions. Tracks are assigned per kid in 'assign'. "
              "check types: claim (honor button), contains {pattern,n?}, "
              "not_contains {pattern}, projects {n}, visits {n}, "
              "gb_given {n}, robot {level}. Patterns are regexes matched "
              "against the kid's pages. Edit freely; restart the portal."),
    "assign": {"astro": "builder", "robo": "explorer"},
    "tracks": {
        "explorer": [
            {"id": "e1", "title": "Secret Agent Sign-In", "xp": 20,
             "story": "Sign in all by yourself. Your passcode is a SECRET — that's rule one of computers.",
             "std": "Digital citizenship: passwords",
             "check": {"type": "claim"}},
            {"id": "e2", "title": "Word Wizard", "xp": 25,
             "story": "Open the Code Editor and change what your button says. Words on pages are just code you can edit!",
             "std": "HTML: text", "check": {"type": "not_contains", "pattern": "Press me!"}},
            {"id": "e3", "title": "Color Changer", "xp": 25,
             "story": "Find the sky color #7ec8ff in your code and change it to a new color. Try 'hotpink'!",
             "std": "CSS: properties", "check": {"type": "not_contains", "pattern": "#7ec8ff"}},
            {"id": "e4", "title": "Robot Steps", "xp": 30,
             "story": "Open the Robot Playground and beat level 2. Robots only do EXACTLY what you tell them.",
             "std": "Sequences (CSTA 1A-AP-10)", "check": {"type": "robot", "level": 2}},
            {"id": "e5", "title": "Loop-de-Loop", "xp": 40, "badge": "refresh",
             "story": "Beat the Robot Playground level that needs the repeat block. Loops save so much tapping!",
             "std": "Loops (CSTA 1A-AP-10)", "check": {"type": "robot", "level": 5}},
            {"id": "e6", "title": "Master Builder", "xp": 30,
             "story": "Use 'Build Something New!' to make a second project about anything you love.",
             "std": "Creating digital artifacts", "check": {"type": "projects", "n": 2}},
            {"id": "e7", "title": "Famous!", "xp": 25,
             "story": "Get 5 visits on your pages. Every visit is a computer asking our server for your page!",
             "std": "How the web works", "check": {"type": "visits", "n": 5}},
            {"id": "e8", "title": "Kind Visitor", "xp": 25, "badge": "heart",
             "story": "Sign someone else's guestbook with something NICE. The internet remembers what we write.",
             "std": "Digital citizenship: kindness", "check": {"type": "gb_given", "n": 1}},
            {"id": "e9", "title": "Wifi Detective", "xp": 20,
             "story": "Find 5 things in our house that use wifi and tell a parent. (Hint: some are hiding!)",
             "std": "Networks (CSTA 1A-NI-04)", "check": {"type": "claim"}},
            {"id": "e10", "title": "Demo Star", "xp": 50, "badge": "star",
             "story": "Show your page to everyone at Family Demo Day and tell us how you built it!",
             "std": "Communicating about computing", "check": {"type": "claim"}},
        ],
        "builder": [
            {"id": "b1", "title": "Make It Yours", "xp": 20,
             "story": "Open the Code Editor and change what your button says.",
             "std": "HTML: text", "check": {"type": "not_contains", "pattern": "Press me!"}},
            {"id": "b2", "title": "Style Master", "xp": 25,
             "story": "Your heading color is #1446a0. Find it in the CSS and pick your own color.",
             "std": "CSS (CSTA 1B-AP-12: modify programs)",
             "check": {"type": "not_contains", "pattern": "color:\\s*#1446a0"}},
            {"id": "b3", "title": "Headline Act", "xp": 25,
             "story": "Add a brand-new <h2> headline anywhere on a page.",
             "std": "HTML structure", "check": {"type": "contains", "pattern": "<h2"}},
            {"id": "b4", "title": "Picture Perfect", "xp": 30,
             "story": "Add a picture with an <img> tag. Ask a parent to help find an image address.",
             "std": "HTML media", "check": {"type": "contains", "pattern": "<img"}},
            {"id": "b5", "title": "Button Boss", "xp": 35,
             "story": "Add a SECOND button that does something different when clicked.",
             "std": "Events (CSTA 1B-AP-15)",
             "check": {"type": "contains", "pattern": "onclick", "n": 2}},
            {"id": "b6", "title": "List Legend", "xp": 25,
             "story": "Add a list (<ul> and <li>) of your top 3 anythings.",
             "std": "HTML structure", "check": {"type": "contains", "pattern": "<[uo]l"}},
            {"id": "b7", "title": "Serial Builder", "xp": 25,
             "story": "Ship a second project with 'Build Something New!'",
             "std": "Creating digital artifacts", "check": {"type": "projects", "n": 2}},
            {"id": "b8", "title": "Linked Up", "xp": 30,
             "story": "Make a link (<a href=\"...\">) from one of your pages to any other kid page.",
             "std": "Hyperlinks + networks",
             "check": {"type": "contains", "pattern": "href=[\"']/kids/"}},
            {"id": "b9", "title": "Robot Navigator", "xp": 35,
             "story": "Beat Robot Playground level 5 — you'll need the repeat block.",
             "std": "Loops (CSTA 1B-AP-10)", "check": {"type": "robot", "level": 5}},
            {"id": "b10", "title": "Robot Coder", "xp": 45, "badge": "robo",
             "story": "Beat a code-mode level by TYPING the commands. That's real programming syntax.",
             "std": "Programming (CSTA 1B-AP-11)", "check": {"type": "robot", "level": 8}},
            {"id": "b11", "title": "Crowd Pleaser", "xp": 30,
             "story": "Get 10 visits across your pages. Tell the family at dinner!",
             "std": "How the web works", "check": {"type": "visits", "n": 10}},
            {"id": "b12", "title": "Good Neighbor", "xp": 25, "badge": "heart",
             "story": "Sign 2 guestbooks with kind, helpful comments.",
             "std": "Digital citizenship", "check": {"type": "gb_given", "n": 2}},
            {"id": "b13", "title": "The Teacher", "xp": 40,
             "story": "Help your sibling finish one of THEIR missions. Teaching is the final boss of learning.",
             "std": "Collaboration (CSTA 1B-IC-22)", "check": {"type": "claim"}},
            {"id": "b14", "title": "Demo Star", "xp": 50, "badge": "star",
             "story": "Present a project at Family Demo Day: what it does, and one thing that was hard.",
             "std": "Communicating about computing", "check": {"type": "claim"}},
        ],
    },
}


def missions_cfg():
    if not MISSIONS_PATH.exists():
        MISSIONS_PATH.write_text(json.dumps(DEFAULT_MISSIONS, indent=2) + "\n")
    try:
        return json.loads(MISSIONS_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return DEFAULT_MISSIONS


def _read_json(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def progress_path(kid):
    return KIDS_DIR / kid / ".progress.json"


def stats_path(kid):
    return KIDS_DIR / kid / ".stats.json"


def guestbook_path(kid):
    return KIDS_DIR / kid / ".guestbook.json"


def kid_pages_text(kid):
    out = []
    for p in kid_projects(kid):
        f = kid_file(kid, p["name"])
        if f and f.exists():
            out.append(f.read_text(errors="replace"))
    return out


def run_check(kid, check):
    ctype = check.get("type")
    if ctype == "claim":
        return False   # only completes via explicit claim
    if ctype == "contains":
        n = int(check.get("n", 1))
        pat = re.compile(check.get("pattern", ""), re.I)
        return any(len(pat.findall(text)) >= n for text in kid_pages_text(kid))
    if ctype == "not_contains":
        pat = re.compile(check.get("pattern", ""), re.I)
        pages = kid_pages_text(kid)
        return bool(pages) and any(not pat.search(t) for t in pages)
    if ctype == "projects":
        return len(kid_projects(kid)) >= int(check.get("n", 2))
    if ctype == "visits":
        stats = _read_json(stats_path(kid), {})
        return sum(stats.values()) >= int(check.get("n", 5))
    if ctype == "gb_given":
        count = 0
        for other in kid_ids():
            if other == kid:
                continue
            for entry in _read_json(guestbook_path(other), []):
                if entry.get("from_id") == kid:
                    count += 1
        return count >= int(check.get("n", 1))
    if ctype == "robot":
        prog = _read_json(progress_path(kid), {})
        return int(prog.get("robot", 0)) >= int(check.get("level", 1))
    return False


def kid_track(kid):
    cfg = missions_cfg()
    track = cfg.get("assign", {}).get(kid, "explorer")
    return track, cfg.get("tracks", {}).get(track, [])


def quest_state(kid, claim_id=None):
    """Evaluate all missions; auto-award newly passed ones. Returns state."""
    _, missions = kid_track(kid)
    prog = _read_json(progress_path(kid), {})
    done = prog.setdefault("done", {})
    changed = False
    for m in missions:
        if m["id"] in done:
            continue
        passed = run_check(kid, m.get("check", {}))
        if not passed and claim_id == m["id"] and \
                m.get("check", {}).get("type") == "claim":
            passed = True
        if passed:
            done[m["id"]] = time.time()
            changed = True
    prog["xp"] = sum(m["xp"] for m in missions if m["id"] in done)
    if changed or not progress_path(kid).exists():
        _write_json(progress_path(kid), prog)
    return {
        "track": kid_track(kid)[0],
        "xp": prog["xp"],
        "level": prog["xp"] // 100 + 1,
        "robot": int(prog.get("robot", 0)),
        "missions": [{**m, "done": m["id"] in done} for m in missions],
        "badges": [m["badge"] for m in missions
                   if m["id"] in done and m.get("badge")],
    }


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
                 "avatar": u.get("avatar", "avatar"),
                 "onboarded": bool(u.get("onboarded", True))} for u in users()]})

        if path == "/api/admin/config":
            if not user or user["role"] != "parent":
                return self._json({"error": "parents only"}, 403)
            return self._json({
                "users": [{k: u.get(k) for k in
                           ("id", "name", "role", "avatar", "theme",
                            "passcode", "onboarded")} for u in users()],
                "missions_raw": MISSIONS_PATH.read_text()
                    if MISSIONS_PATH.exists() else "{}",
                "registry_raw": REGISTRY_PATH.read_text()
                    if REGISTRY_PATH.exists() else "{}",
                "avatars": sorted(AVATAR_CHOICES | {"avatar"}),
                "themes": sorted(THEME_CHOICES)})

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
            for link in reg.get("links", []):
                links.append({**link, "live": port_alive(link.get("port", 0))})
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

        if path == "/api/quests":
            if not user:
                return self._json({"error": "sign in first"}, 401)
            q = parse_qs(parsed.query)
            kid = (q.get("kid") or [user["id"]])[0]
            if user["role"] != "parent" and user["id"] != kid:
                return self._json({"error": "not your quest log"}, 403)
            if kid not in kid_ids():
                return self._json({"error": "not a kid account"}, 404)
            return self._json(quest_state(kid))

        if path == "/api/guestbook":
            if not user:
                return self._json({"error": "sign in first"}, 401)
            q = parse_qs(parsed.query)
            kid = (q.get("kid") or [""])[0]
            proj = (q.get("proj") or [""])[0]
            if not kid_file(kid, proj):
                return self._json({"error": "not found"}, 404)
            entries = [e for e in _read_json(guestbook_path(kid), [])
                       if e.get("proj") == proj]
            visits = _read_json(stats_path(kid), {}).get(proj, 0)
            return self._json({"entries": entries[-30:], "visits": visits,
                               "me": user["name"]})

        if path == "/api/demo":
            if not user:
                return self._json({"error": "sign in first"}, 401)
            pages = []
            for kid in kid_ids():
                owner = user_by_id(kid)
                for p in kid_projects(kid):
                    pages.append({"kid": kid,
                                  "owner": (owner or {}).get("name", kid),
                                  "name": p["name"], "url": p["url"]})
            return self._json({"pages": pages})

        # kids' pages require sign-in; everything else static is the shell
        if path.startswith("/kids/"):
            if not user:
                return self._go("/")
            m = re.match(r"^/kids/([^/]+)/([^/]+)/(index\.html)?$", path)
            if m and kid_file(m.group(1), m.group(2)):
                stats = _read_json(stats_path(m.group(1)), {})
                stats[m.group(2)] = stats.get(m.group(2), 0) + 1
                _write_json(stats_path(m.group(1)), stats)
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
            fresh_kid = u and u.get("role") == "kid" and not u.get("onboarded")
            if u and (fresh_kid or (code and code == str(u.get("passcode")))):
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

        if path == "/api/onboard":
            if user["role"] != "kid":
                return self._json({"error": "only kids run the setup wizard"}, 403)
            name = str(data.get("name", "")).strip()[:24]
            avatar = str(data.get("avatar", ""))
            theme = str(data.get("theme", ""))
            passcode = str(data.get("passcode", "")).strip()
            if len(name) < 1:
                return self._json({"error": "tell us your name!"}, 400)
            if avatar not in AVATAR_CHOICES or theme not in THEME_CHOICES:
                return self._json({"error": "pick a look and a world"}, 400)
            if not (3 <= len(passcode) <= 30):
                return self._json({"error": "passcode needs at least 3 letters"}, 400)
            u = user_by_id(user["id"])
            u.update(name=name, avatar=avatar, theme=theme,
                     passcode=passcode, onboarded=True)
            save_users()
            return self._json({"ok": True})

        if path == "/api/admin/user":
            if user["role"] != "parent":
                return self._json({"error": "parents only"}, 403)
            u = user_by_id(str(data.get("id", "")))
            if not u:
                return self._json({"error": "no such user"}, 404)
            if data.get("reset"):
                u.update(passcode="", onboarded=False)
            else:
                name = str(data.get("name", "")).strip()[:24]
                if name:
                    u["name"] = name
                if data.get("avatar") in AVATAR_CHOICES | {"avatar"}:
                    u["avatar"] = data["avatar"]
                if data.get("theme") in THEME_CHOICES:
                    u["theme"] = data["theme"]
                pc = str(data.get("passcode", "")).strip()
                if pc:
                    u["passcode"] = pc
                    u["onboarded"] = True
            save_users()
            return self._json({"ok": True})

        if path == "/api/admin/save":
            if user["role"] != "parent":
                return self._json({"error": "parents only"}, 403)
            which = str(data.get("which", ""))
            content = str(data.get("content", ""))
            target = {"missions": MISSIONS_PATH,
                      "registry": REGISTRY_PATH}.get(which)
            if not target:
                return self._json({"error": "unknown config"}, 404)
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                return self._json({"error": f"Not valid JSON: {e}"}, 400)
            target.write_text(content if content.endswith("\n") else content + "\n")
            return self._json({"ok": True})

        if path == "/api/quests/check":
            kid = user["id"] if user["role"] != "parent" else \
                str(data.get("kid", ""))
            if kid not in kid_ids():
                return self._json({"error": "not a kid account"}, 404)
            before = {m["id"] for m in quest_state(kid)["missions"] if m["done"]}
            state = quest_state(kid, claim_id=str(data.get("mission", "")))
            after = {m["id"] for m in state["missions"] if m["done"]}
            return self._json({**state, "new": sorted(after - before)})

        if path == "/api/robot":
            if user["role"] != "kid":
                return self._json({"ok": True, "note": "parents play for fun"})
            level = max(0, min(20, int(data.get("level", 0) or 0)))
            prog = _read_json(progress_path(user["id"]), {})
            if level > int(prog.get("robot", 0)):
                prog["robot"] = level
                _write_json(progress_path(user["id"]), prog)
            return self._json({"ok": True, "robot": prog.get("robot", 0)})

        if path == "/api/guestbook":
            kid = str(data.get("kid", ""))
            proj = str(data.get("proj", ""))
            msg = str(data.get("msg", "")).strip()[:300]
            if not kid_file(kid, proj):
                return self._json({"error": "not found"}, 404)
            if not msg:
                return self._json({"error": "write something first!"}, 400)
            entries = _read_json(guestbook_path(kid), [])
            entries.append({"proj": proj, "from_id": user["id"],
                            "from": user["name"], "msg": msg,
                            "ts": time.time()})
            _write_json(guestbook_path(kid), entries[-200:])
            return self._json({"ok": True})

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
