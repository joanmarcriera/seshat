from pathlib import Path
from types import SimpleNamespace

import pytest

from meeting_pipeline import config as config_mod
from meeting_pipeline.pipeline import SUPPORTED_EXTENSIONS, process_one


def _cfg(tmp_path):
    cfg = config_mod.deep_merge(config_mod.DEFAULTS, {
        "recordings_dir": str(tmp_path / "recordings"),
        "notes_dir": str(tmp_path / "notes"),
        "work_dir": str(tmp_path / "work"),
    })
    return cfg


def _fake_deps(reachable=True, summary="# Meeting notes\n\nGood."):
    return SimpleNamespace(
        convert_to_wav=lambda src, dest: dest.write_bytes(b"RIFF"),
        transcribe=lambda wav, tcfg: {"segments": [
            {"speaker": "SPEAKER_00", "text": "hello there"}]},
        ollama_reachable=lambda url: reachable,
        summarise=lambda text, **kw: (summary, {"response": summary}),
    )


def test_supported_extensions_cover_real_formats():
    for ext in [".wav", ".m4a", ".opus", ".mp3", ".mov"]:
        assert ext in SUPPORTED_EXTENSIONS


def test_process_one_writes_note_on_success(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir(parents=True)
    src = rec / "demo.opus"
    src.write_bytes(b"x")
    result = process_one(src, _cfg(tmp_path), deps=_fake_deps(), stable_delay=0)
    assert result.status == "done"
    assert result.note_path.exists()
    assert result.note_path.read_text().startswith("# Meeting notes")


def test_process_one_nested_recording_uses_subfolder_aware_base(tmp_path):
    rec = tmp_path / "recordings"
    (rec / "Anglia-water").mkdir(parents=True)
    src = rec / "Anglia-water" / "recording.opus"
    src.write_bytes(b"x")
    result = process_one(src, _cfg(tmp_path), deps=_fake_deps(), stable_delay=0)
    assert result.status == "done"
    assert result.base == "Anglia-water__recording"
    assert result.note_path.name == "Anglia-water__recording.md"
    assert result.note_path.exists()


def test_process_one_skips_when_note_exists(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir(parents=True)
    src = rec / "demo.opus"
    src.write_bytes(b"x")
    cfg = _cfg(tmp_path)
    notes = tmp_path / "notes"
    notes.mkdir(parents=True)
    (notes / "demo.md").write_text("already")
    result = process_one(src, cfg, deps=_fake_deps(), stable_delay=0)
    assert result.status == "skipped"


def test_process_one_defers_when_server_down_and_local_not_allowed(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir(parents=True)
    src = rec / "demo.opus"
    src.write_bytes(b"x")
    cfg = _cfg(tmp_path)  # allow_local_fallback defaults False
    result = process_one(src, cfg, deps=_fake_deps(reachable=False), stable_delay=0)
    assert result.status == "deferred_need_local"
    assert not (tmp_path / "notes" / "demo.md").exists()


def test_process_one_uses_local_when_allowed_and_server_down(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir(parents=True)
    src = rec / "demo.opus"
    src.write_bytes(b"x")
    cfg = _cfg(tmp_path)
    cfg["summarise"]["allow_local_fallback"] = True
    result = process_one(src, cfg, deps=_fake_deps(reachable=False), stable_delay=0)
    assert result.status == "done"


def test_process_one_marks_failed_on_bad_summary(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir(parents=True)
    src = rec / "demo.opus"
    src.write_bytes(b"x")
    deps = _fake_deps(summary="word word word word word " * 50)
    result = process_one(src, _cfg(tmp_path), deps=deps, stable_delay=0)
    assert result.status == "failed"
    # Note is still written so nothing is lost.
    assert result.note_path.exists()


def test_process_one_writes_clean_transcript(tmp_path):
    rec = tmp_path / "recordings"
    rec.mkdir(parents=True)
    src = rec / "demo.opus"
    src.write_bytes(b"x")
    result = process_one(src, _cfg(tmp_path), deps=_fake_deps(), stable_delay=0)
    assert result.status == "done"
    assert result.transcript_path is not None
    assert result.transcript_path.exists()
    text = result.transcript_path.read_text()
    assert "[SPEAKER_00]" in text
    assert "hello there" in text
