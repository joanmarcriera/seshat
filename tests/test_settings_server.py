import json
import re
import urllib.error
import urllib.request
import urllib.parse

from meeting_pipeline import config as config_mod
from meeting_pipeline.settings_server import (
    SettingsServer,
    check_connections,
    parse_form,
    render_settings_page,
)


def _cfg():
    return config_mod.deep_merge(config_mod.DEFAULTS, {})


def test_render_includes_current_values_and_sections():
    html = render_settings_page(_cfg())
    assert "Scribed" in html
    assert "Summarisation" in html
    assert "127.0.0.1:9000" in html or "http://127.0.0.1:9000" in html
    assert "watch_interval_seconds" in html


def test_render_shows_saved_banner():
    assert "Saved" in render_settings_page(_cfg(), saved=True)


def test_render_shows_errors():
    html = render_settings_page(_cfg(), errors=["watch interval must be a positive integer"])
    assert "must be a positive integer" in html


def test_parse_form_updates_scalar_and_nested_values():
    base = _cfg()
    form = {
        "watch_interval_seconds": "60",
        "recordings_dir": "./recordings",
        "notes_dir": "./meeting-notes",
        "work_dir": "./whisperx-output",
        "transcribe.whisperx_url": "http://1.2.3.4:9000",
        "transcribe.model": "large-v3",
        "transcribe.language": "en",
        "transcribe.num_speakers": "3",
        # checkbox present => true
        "transcribe.diarize": "on",
        "summarise.backend": "local",
        "summarise.server.url": "http://10.0.0.5:30068",
        "summarise.server.model": "gemma4:latest",
        "summarise.local.url": "http://127.0.0.1:11434",
        "summarise.local.model": "gemma4-moe-research:64k-quality",
        # allow_local checkbox present => true
        "summarise.allow_local_fallback": "on",
        "note_owner": "Alex",
        "user_speaker": "SPEAKER_00",
    }
    new_cfg, errors = parse_form(form, base)
    assert errors == []
    assert new_cfg["watch_interval_seconds"] == 60
    assert new_cfg["transcribe"]["whisperx_url"] == "http://1.2.3.4:9000"
    assert new_cfg["transcribe"]["model"] == "large-v3"
    assert new_cfg["transcribe"]["num_speakers"] == 3
    assert new_cfg["transcribe"]["diarize"] is True
    assert new_cfg["summarise"]["backend"] == "local"
    assert new_cfg["summarise"]["allow_local_fallback"] is True
    assert new_cfg["user_speaker"] == "SPEAKER_00"


def test_parse_form_unchecked_checkboxes_become_false():
    base = _cfg()
    base["summarise"]["allow_local_fallback"] = True
    base["transcribe"]["diarize"] = True
    form = {"watch_interval_seconds": "20"}  # no checkbox keys present
    new_cfg, errors = parse_form(form, base)
    assert errors == []
    assert new_cfg["summarise"]["allow_local_fallback"] is False
    assert new_cfg["transcribe"]["diarize"] is False


def test_parse_form_rejects_bad_interval():
    base = _cfg()
    new_cfg, errors = parse_form({"watch_interval_seconds": "0"}, base)
    assert any("interval" in e for e in errors)


def test_parse_form_rejects_bad_num_speakers():
    base = _cfg()
    _, errors = parse_form(
        {"watch_interval_seconds": "20", "transcribe.num_speakers": "x"}, base)
    assert any("speaker" in e.lower() for e in errors)


def test_parse_form_rejects_empty_whisperx_url():
    base = _cfg()
    _, errors = parse_form(
        {"watch_interval_seconds": "20", "transcribe.whisperx_url": ""}, base)
    assert any("whisperx" in e.lower() for e in errors)


def test_check_connections_reports_each_endpoint():
    class R:
        status_code = 200
    cfg = _cfg()
    seen = []

    def fake_get(url, timeout=None):
        seen.append(url)
        return R()

    out = check_connections(cfg, get=fake_get)
    assert out == {"whisperx": True, "ollama_server": True, "ollama_local": True}
    assert len(seen) == 3


def test_check_connections_false_on_error():
    def boom(url, timeout=None):
        raise OSError("refused")
    out = check_connections(_cfg(), get=boom)
    assert out == {"whisperx": False, "ollama_server": False, "ollama_local": False}


def _valid_form(token):
    return {
        "_token": token,
        "watch_interval_seconds": "45",
        "recordings_dir": "./recordings",
        "notes_dir": "./meeting-notes",
        "work_dir": "./whisperx-output",
        "transcribe.whisperx_url": "http://10.0.0.5:9000",
        "transcribe.model": "medium",
        "transcribe.language": "en",
        "transcribe.num_speakers": "2",
        "transcribe.diarize": "on",
        "summarise.backend": "server",
        "summarise.server.url": "http://10.0.0.5:30068",
        "summarise.server.model": "gemma4:latest",
        "summarise.local.url": "http://127.0.0.1:11434",
        "summarise.local.model": "gemma4-moe-research:64k-quality",
        "note_owner": "Alex",
        "user_speaker": "unknown",
    }


def _scrape_token(body):
    m = re.search(r'name="_token" value="([^"]+)"', body)
    assert m, "no _token field in rendered form"
    return m.group(1)


def test_server_get_post_roundtrip(tmp_path):
    saved = {}
    state = {"cfg": _cfg()}

    def on_save(new_cfg):
        saved["cfg"] = new_cfg
        state["cfg"] = new_cfg

    server = SettingsServer(lambda: state["cfg"], on_save)
    server.start()
    try:
        # GET / and scrape the CSRF token.
        with urllib.request.urlopen(server.url) as resp:
            body = resp.read().decode()
            assert resp.status == 200
            assert "Scribed" in body
        token = _scrape_token(body)
        # POST /save with the token included.
        data = urllib.parse.urlencode(_valid_form(token)).encode()
        with urllib.request.urlopen(server.url + "/save", data=data) as resp:
            assert resp.status == 200
        assert saved["cfg"]["watch_interval_seconds"] == 45
    finally:
        server.stop()


def test_render_includes_token():
    html = render_settings_page(_cfg(), token="secret-tok")
    assert 'name="_token"' in html
    assert "secret-tok" in html


def test_post_without_token_rejected(tmp_path):
    saved = {}
    server = SettingsServer(_cfg, lambda c: saved.setdefault("cfg", c))
    server.start()
    try:
        form = _valid_form("")  # empty/missing token
        del form["_token"]
        data = urllib.parse.urlencode(form).encode()
        try:
            urllib.request.urlopen(server.url + "/save", data=data)
            assert False, "expected HTTP 403"
        except urllib.error.HTTPError as e:
            assert e.code == 403
        assert "cfg" not in saved  # nothing persisted
    finally:
        server.stop()


def test_post_with_bad_host_rejected(tmp_path):
    saved = {}
    server = SettingsServer(_cfg, lambda c: saved.setdefault("cfg", c))
    server.start()
    try:
        # Fetch a real token first so only the Host header is wrong.
        with urllib.request.urlopen(server.url) as resp:
            token = _scrape_token(resp.read().decode())
        data = urllib.parse.urlencode(_valid_form(token)).encode()
        req = urllib.request.Request(
            server.url + "/save", data=data,
            headers={"Host": "evil.example.com"})
        try:
            urllib.request.urlopen(req)
            assert False, "expected HTTP 403"
        except urllib.error.HTTPError as e:
            assert e.code == 403
        assert "cfg" not in saved
    finally:
        server.stop()


def test_parse_form_rejects_non_http_whisperx_url():
    base = _cfg()
    new_cfg, errors = parse_form(
        {"watch_interval_seconds": "20",
         "transcribe.whisperx_url": "ftp://x"}, base)
    assert any("whisperx" in e.lower() for e in errors)
    # The bad value must not be saved over the original.
    assert new_cfg["transcribe"]["whisperx_url"] != "ftp://x"


def test_server_binds_localhost_only():
    server = SettingsServer(_cfg, lambda c: None)
    server.start()
    try:
        assert server.url.startswith("http://127.0.0.1:")
    finally:
        server.stop()
