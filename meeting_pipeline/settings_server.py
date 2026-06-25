"""A localhost settings page for the menu-bar watcher.

Serves a styled HTML form from the live config, validates POSTed values,
persists via the caller's on_save callback, and exposes a connection test.
Bound to 127.0.0.1 only — it can write config and must not be reachable.
"""

from __future__ import annotations

import copy
import html
import json
import secrets
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

import requests

from .links import donate_url

MODEL_CHOICES = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]
INTERVAL_CHOICES = [("10 seconds", 10), ("20 seconds", 20), ("60 seconds", 60),
                    ("5 minutes", 300)]


# --------------------------------------------------------------------------- #
# Pure helpers (testable without a server)
# --------------------------------------------------------------------------- #

def _set_nested(cfg: dict, dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    node = cfg
    for key in parts[:-1]:
        node = node[key]
    node[parts[-1]] = value


def _get_nested(cfg: dict, dotted: str) -> Any:
    node = cfg
    for key in dotted.split("."):
        node = node[key]
    return node


def _is_http_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def parse_form(form: dict[str, str], base_cfg: dict) -> tuple[dict, list[str]]:
    cfg = copy.deepcopy(base_cfg)
    errors: list[str] = []

    def validate_url(dotted: str, label: str) -> None:
        """Empty -> error; non-empty non-http(s) -> error and keep the old value."""
        value = _get_nested(cfg, dotted)
        if not value:
            errors.append(f"{label} URL must not be empty")
        elif not _is_http_url(value):
            errors.append(f"{label} URL must start with http:// or https://")
            _set_nested(cfg, dotted, _get_nested(base_cfg, dotted))

    # Interval
    raw_interval = form.get("watch_interval_seconds", "").strip()
    try:
        interval = int(raw_interval)
        if interval <= 0:
            raise ValueError
        cfg["watch_interval_seconds"] = interval
    except ValueError:
        errors.append("watch interval must be a positive integer (seconds)")

    # Plain string fields
    for key in ("recordings_dir", "notes_dir", "work_dir", "note_owner", "user_speaker"):
        if key in form:
            cfg[key] = form[key].strip()

    # Transcribe
    for dotted in ("transcribe.whisperx_url", "transcribe.model",
                   "transcribe.language"):
        if dotted in form:
            _set_nested(cfg, dotted, form[dotted].strip())
    validate_url("transcribe.whisperx_url", "WhisperX")

    raw_speakers = form.get("transcribe.num_speakers", "").strip()
    if raw_speakers:
        try:
            speakers = int(raw_speakers)
            if speakers < 1:
                raise ValueError
            cfg["transcribe"]["num_speakers"] = speakers
        except ValueError:
            errors.append("number of speakers must be an integer >= 1")
    cfg["transcribe"]["diarize"] = form.get("transcribe.diarize") is not None

    # Summarise
    backend = form.get("summarise.backend", "server").strip()
    cfg["summarise"]["backend"] = backend if backend in ("server", "local") else "server"
    for dotted in ("summarise.server.url", "summarise.server.model",
                   "summarise.local.url", "summarise.local.model"):
        if dotted in form:
            _set_nested(cfg, dotted, form[dotted].strip())
    validate_url("summarise.server.url", "Server Ollama")
    validate_url("summarise.local.url", "Local Ollama")
    cfg["summarise"]["allow_local_fallback"] = (
        form.get("summarise.allow_local_fallback") is not None)

    return cfg, errors


def check_connections(cfg: dict, *, get: Callable[..., Any] | None = None) -> dict:
    get = get or requests.get

    def ok(url: str, path: str) -> bool:
        try:
            resp = get(url.rstrip("/") + path, timeout=4)
            return getattr(resp, "status_code", 500) < 500
        except Exception:
            return False

    return {
        "whisperx": ok(cfg["transcribe"]["whisperx_url"], "/docs"),
        "ollama_server": ok(cfg["summarise"]["server"]["url"], "/api/tags"),
        "ollama_local": ok(cfg["summarise"]["local"]["url"], "/api/tags"),
    }


# --------------------------------------------------------------------------- #
# HTML rendering
# --------------------------------------------------------------------------- #

def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _text(label: str, name: str, value: Any, *, placeholder: str = "") -> str:
    return (
        f'<label class="row"><span>{_esc(label)}</span>'
        f'<input type="text" name="{name}" value="{_esc(value)}" '
        f'placeholder="{_esc(placeholder)}"></label>')


def _number(label: str, name: str, value: Any) -> str:
    return (
        f'<label class="row"><span>{_esc(label)}</span>'
        f'<input type="number" name="{name}" value="{_esc(value)}" min="1"></label>')


def _select(label: str, name: str, value: Any, options: list) -> str:
    opts = []
    for opt in options:
        text, val = (opt, opt) if not isinstance(opt, tuple) else opt
        sel = " selected" if str(val) == str(value) else ""
        opts.append(f'<option value="{_esc(val)}"{sel}>{_esc(text)}</option>')
    return (f'<label class="row"><span>{_esc(label)}</span>'
            f'<select name="{name}">{"".join(opts)}</select></label>')


def _checkbox(label: str, name: str, checked: bool) -> str:
    ck = " checked" if checked else ""
    return (f'<label class="row check"><input type="checkbox" name="{name}"{ck}>'
            f'<span>{_esc(label)}</span></label>')


def _radio(label: str, name: str, current: Any, options: list[tuple[str, str]]) -> str:
    radios = []
    for text, val in options:
        ck = " checked" if str(val) == str(current) else ""
        radios.append(
            f'<label class="radio"><input type="radio" name="{name}" '
            f'value="{_esc(val)}"{ck}><span>{_esc(text)}</span></label>')
    return (f'<div class="row"><span>{_esc(label)}</span>'
            f'<div class="radios">{"".join(radios)}</div></div>')


def render_settings_page(cfg: dict, *, saved: bool = False,
                         errors: list[str] | None = None,
                         token: str = "") -> str:
    errors = errors or []
    t = cfg["transcribe"]
    s = cfg["summarise"]
    banner = ""
    if errors:
        items = "".join(f"<li>{_esc(e)}</li>" for e in errors)
        banner = f'<div class="banner error"><strong>Could not save:</strong><ul>{items}</ul></div>'
    elif saved:
        banner = '<div class="banner ok">Saved — applied immediately.</div>'

    donate = donate_url()
    support_card = (
        '<div class="card"><h2>Support</h2>'
        '<div class="row"><span>Scribed is free &amp; open-source. '
        'If it saves you time, you can chip in.</span>'
        f'<a class="donate" href="{_esc(donate)}" target="_blank" '
        'rel="noopener">Buy me a coffee ☕</a></div></div>'
        if donate else ""
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scribed — Settings</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
         margin: 0; background: #f5f5f7; color: #1d1d1f; }}
  @media (prefers-color-scheme: dark) {{ body {{ background:#1c1c1e; color:#f5f5f7; }}
    .card {{ background:#2c2c2e !important; }} input,select {{ background:#1c1c1e; color:#f5f5f7;
      border-color:#48484a !important; }} }}
  .wrap {{ max-width: 640px; margin: 0 auto; padding: 24px 20px 120px; }}
  h1 {{ font-size: 22px; font-weight: 600; }}
  .card {{ background:#fff; border-radius:12px; padding:8px 18px; margin:16px 0;
          box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  .card h2 {{ font-size:13px; text-transform:uppercase; letter-spacing:.05em;
             color:#86868b; margin:14px 4px 8px; }}
  .row {{ display:flex; align-items:center; justify-content:space-between; gap:12px;
         padding:10px 4px; border-top:1px solid rgba(0,0,0,.06); }}
  .card .row:first-of-type {{ border-top:none; }}
  .row > span {{ font-size:14px; }}
  input[type=text], input[type=number], select {{ flex:1; max-width:320px; font-size:14px;
    padding:7px 9px; border:1px solid #d2d2d7; border-radius:8px; }}
  .row.check {{ justify-content:flex-start; gap:10px; }}
  .radios {{ display:flex; gap:16px; }} .radio {{ display:flex; gap:6px; align-items:center; }}
  .footer {{ position:fixed; left:0; right:0; bottom:0; padding:14px 20px;
            background:rgba(245,245,247,.85); backdrop-filter:saturate(180%) blur(20px);
            border-top:1px solid rgba(0,0,0,.1); text-align:center; }}
  @media (prefers-color-scheme: dark) {{ .footer {{ background:rgba(28,28,30,.85); }} }}
  button {{ font-size:15px; font-weight:500; padding:9px 22px; border:none; border-radius:8px;
           background:#0071e3; color:#fff; cursor:pointer; }}
  button.secondary {{ background:#e8e8ed; color:#1d1d1f; margin-right:8px; }}
  a.donate {{ font-size:14px; font-weight:500; padding:7px 16px; border-radius:8px;
            background:#0071e3; color:#fff; text-decoration:none; white-space:nowrap; }}
  .banner {{ padding:12px 16px; border-radius:10px; margin:12px 0; font-size:14px; }}
  .banner.ok {{ background:#e3f5e8; color:#1d6b33; }}
  .banner.error {{ background:#fde7e9; color:#9b1c2e; }} .banner ul {{ margin:6px 0 0 18px; }}
  .dots {{ display:flex; gap:18px; padding:10px 4px; font-size:13px; }}
  .dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; background:#c7c7cc;
         margin-right:6px; vertical-align:middle; }}
  .dot.up {{ background:#34c759; }} .dot.down {{ background:#ff3b30; }}
</style></head>
<body><div class="wrap">
  <h1>📝 Scribed — Settings</h1>
  {banner}
  <form method="post" action="/save">
    <input type="hidden" name="_token" value="{_esc(token)}">
    <div class="card"><h2>General</h2>
      {_select("Watch interval", "watch_interval_seconds", cfg["watch_interval_seconds"], INTERVAL_CHOICES)}
      {_text("Watch folder", "recordings_dir", cfg["recordings_dir"])}
      {_text("Notes folder", "notes_dir", cfg["notes_dir"])}
      {_text("Work folder", "work_dir", cfg["work_dir"])}
      {_text("Note owner", "note_owner", cfg["note_owner"])}
      {_text("Your speaker label", "user_speaker", cfg["user_speaker"], placeholder="e.g. SPEAKER_00 or unknown")}
    </div>
    <div class="card"><h2>Transcription (WhisperX)</h2>
      {_text("WhisperX URL", "transcribe.whisperx_url", t["whisperx_url"])}
      {_select("Model", "transcribe.model", t["model"], MODEL_CHOICES)}
      {_text("Language", "transcribe.language", t["language"])}
      {_number("Number of speakers", "transcribe.num_speakers", t["num_speakers"])}
      {_checkbox("Diarize (separate speakers)", "transcribe.diarize", bool(t["diarize"]))}
    </div>
    <div class="card"><h2>Summarisation (Ollama)</h2>
      {_radio("Backend", "summarise.backend", s["backend"], [("Server (GPU)", "server"), ("Local Mac", "local")])}
      {_text("Server Ollama URL", "summarise.server.url", s["server"]["url"])}
      {_text("Server model", "summarise.server.model", s["server"]["model"])}
      {_text("Local Ollama URL", "summarise.local.url", s["local"]["url"])}
      {_text("Local model", "summarise.local.model", s["local"]["model"])}
      {_checkbox("Allow local Ollama fallback (loads this Mac)", "summarise.allow_local_fallback", bool(s["allow_local_fallback"]))}
    </div>
    <div class="card"><h2>Connections</h2>
      <div class="dots" id="conn">
        <span><span class="dot" id="d-whisperx"></span>WhisperX</span>
        <span><span class="dot" id="d-ollama_server"></span>Server Ollama</span>
        <span><span class="dot" id="d-ollama_local"></span>Local Ollama</span>
      </div>
      <div class="row"><button type="button" class="secondary" onclick="testConn()">Test connection</button></div>
    </div>
    {support_card}
    <div class="footer"><button type="submit">Save</button></div>
  </form>
</div>
<script>
async function testConn() {{
  for (const k of ["whisperx","ollama_server","ollama_local"])
    document.getElementById("d-"+k).className = "dot";
  try {{
    const r = await fetch("/api/test"); const j = await r.json();
    for (const k of Object.keys(j))
      document.getElementById("d-"+k).className = "dot " + (j[k] ? "up" : "down");
  }} catch (e) {{}}
}}
</script>
</body></html>"""


# --------------------------------------------------------------------------- #
# HTTP server
# --------------------------------------------------------------------------- #

class SettingsServer:
    def __init__(self, get_cfg: Callable[[], dict], on_save: Callable[[dict], None],
                 *, host: str = "127.0.0.1", port: int = 0) -> None:
        self._get_cfg = get_cfg
        self._on_save = on_save
        self._host = host
        self._port = port
        self._token = secrets.token_urlsafe(32)
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def _allowed_hosts(self) -> set[str]:
        port = self.port
        return {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _allowed_origins(self) -> set[str]:
        port = self.port
        return {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    @property
    def port(self) -> int:
        return self._httpd.server_address[1] if self._httpd else self._port

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self.port}"

    def start(self) -> None:
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # silence console spam
                pass

            def _send(self, code, body, content_type="text/html; charset=utf-8"):
                data = body.encode("utf-8") if isinstance(body, str) else body
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _host_ok(self) -> bool:
                """DNS-rebind guard: Host must be a known loopback host:port."""
                host = self.headers.get("Host", "")
                return host in server._allowed_hosts()

            def do_GET(self):
                try:
                    if not self._host_ok():
                        self._send(403, "Forbidden", "text/plain; charset=utf-8")
                        return
                    if self.path.startswith("/api/test"):
                        result = check_connections(server._get_cfg())
                        self._send(200, json.dumps(result), "application/json")
                        return
                    self._send(200, render_settings_page(
                        server._get_cfg(), token=server._token))
                except Exception:
                    self._send(500, "Internal error", "text/plain; charset=utf-8")

            def do_POST(self):
                try:
                    if not self._host_ok():
                        self._send(403, "Forbidden", "text/plain; charset=utf-8")
                        return
                    origin = self.headers.get("Origin")
                    if origin is not None and origin not in server._allowed_origins():
                        self._send(403, "Forbidden", "text/plain; charset=utf-8")
                        return
                    length = int(self.headers.get("Content-Length", 0))
                    raw = self.rfile.read(length).decode("utf-8")
                    form = {k: v[-1] for k, v in urllib.parse.parse_qs(
                        raw, keep_blank_values=True).items()}
                    if not secrets.compare_digest(
                            form.get("_token", ""), server._token):
                        self._send(403, "Forbidden", "text/plain; charset=utf-8")
                        return
                    new_cfg, errors = parse_form(form, server._get_cfg())
                    if errors:
                        self._send(200, render_settings_page(
                            new_cfg, errors=errors, token=server._token))
                        return
                    server._on_save(new_cfg)
                    self._send(200, render_settings_page(
                        new_cfg, saved=True, token=server._token))
                except Exception:
                    self._send(500, "Internal error", "text/plain; charset=utf-8")

        self._httpd = ThreadingHTTPServer((self._host, self._port), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
