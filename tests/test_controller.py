from types import SimpleNamespace
from pathlib import Path

from meeting_pipeline import config as config_mod
from meeting_pipeline import pipeline as pipe
from meeting_pipeline.state import State


def _import_controller():
    import importlib.util
    repo_root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "menubar_app", repo_root / "menubar_app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cfg(tmp_path):
    return config_mod.deep_merge(config_mod.DEFAULTS, {
        "recordings_dir": str(tmp_path / "recordings"),
        "notes_dir": str(tmp_path / "notes"),
        "work_dir": str(tmp_path / "work"),
    })


def test_scan_once_processes_and_notifies(tmp_path):
    mod = _import_controller()
    rec = tmp_path / "recordings"
    rec.mkdir()
    (rec / "demo.opus").write_bytes(b"x")
    events = []

    def fake_process_one(path, cfg, **kw):
        return pipe.ProcessResult("done", "demo", "ok", tmp_path / "notes" / "demo.md")

    ctrl = mod.WatcherController(
        _cfg(tmp_path), tmp_path / "watcher-config.json",
        process_one=fake_process_one, notify=lambda t, m: events.append((t, m)))
    results = ctrl.scan_once()
    assert [r.status for r in results] == ["done"]
    assert events  # a notification fired


def test_scan_once_serializes_via_scan_lock(tmp_path):
    """A re-entrant scan_once (simulating an overlapping daemon thread) returns []
    because _scan_lock is held; the outer scan still processes each file once."""
    mod = _import_controller()
    rec = tmp_path / "recordings"
    rec.mkdir()
    (rec / "a.opus").write_bytes(b"x")
    (rec / "b.opus").write_bytes(b"x")

    calls = []
    reentrant_results = []
    ctrl_holder = {}

    def fake_process_one(path, cfg, **kw):
        calls.append(path.name)
        if len(calls) == 1:
            # Simulate an overlapping scan starting while this one runs.
            reentrant_results.append(ctrl_holder["ctrl"].scan_once())
        return pipe.ProcessResult("done", path.stem, "ok",
                                  tmp_path / "notes" / f"{path.stem}.md")

    ctrl = mod.WatcherController(
        _cfg(tmp_path), tmp_path / "watcher-config.json",
        process_one=fake_process_one, notify=lambda t, m: None)
    ctrl_holder["ctrl"] = ctrl

    results = ctrl.scan_once()
    # Re-entrant scan was blocked by _scan_lock and returned [].
    assert reentrant_results == [[]]
    # Each pending file processed exactly once (no duplicates).
    assert sorted(calls) == ["a.opus", "b.opus"]
    assert [r.status for r in results] == ["done", "done"]


def test_scan_once_uses_cfg_snapshot_despite_midscan_apply(tmp_path):
    """If apply_config swaps self.cfg mid-scan, the in-flight items must still
    see the ORIGINAL cfg snapshot, not the swapped one."""
    mod = _import_controller()
    rec = tmp_path / "recordings"
    rec.mkdir()
    (rec / "a.opus").write_bytes(b"x")
    (rec / "b.opus").write_bytes(b"x")

    original_notes = str(tmp_path / "notes")
    seen_notes = []
    ctrl_holder = {}

    def fake_process_one(path, cfg, **kw):
        seen_notes.append(cfg["notes_dir"])
        if len(seen_notes) == 1:
            swapped = config_mod.deep_merge(ctrl_holder["ctrl"].cfg, {
                "notes_dir": str(tmp_path / "OTHER-notes"),
            })
            ctrl_holder["ctrl"].apply_config(swapped)
        return pipe.ProcessResult("done", path.stem, "ok",
                                  tmp_path / "notes" / f"{path.stem}.md")

    ctrl = mod.WatcherController(
        _cfg(tmp_path), tmp_path / "watcher-config.json",
        process_one=fake_process_one, notify=lambda t, m: None)
    ctrl_holder["ctrl"] = ctrl
    ctrl.scan_once()

    # Both processed items saw the ORIGINAL notes_dir snapshot.
    assert seen_notes == [original_notes, original_notes]
    # The swap still took effect on the live config.
    assert ctrl.cfg["notes_dir"] == str(tmp_path / "OTHER-notes")


def test_deferred_tracked_and_cleared_on_allow_local(tmp_path):
    mod = _import_controller()
    rec = tmp_path / "recordings"
    rec.mkdir()
    (rec / "demo.opus").write_bytes(b"x")

    def fake_process_one(path, cfg, **kw):
        if not cfg["summarise"]["allow_local_fallback"]:
            return pipe.ProcessResult("deferred_need_local", "demo", "need local")
        return pipe.ProcessResult("done", "demo", "ok", tmp_path / "notes" / "demo.md")

    cfg_path = tmp_path / "watcher-config.json"
    ctrl = mod.WatcherController(
        _cfg(tmp_path), cfg_path,
        process_one=fake_process_one, notify=lambda t, m: None)
    ctrl.scan_once()
    assert ctrl.has_deferred()
    ctrl.set_allow_local(True)
    assert cfg_path.exists()  # persisted
    ctrl.scan_once()
    assert not ctrl.has_deferred()


def test_set_interval_persists(tmp_path):
    mod = _import_controller()
    cfg_path = tmp_path / "watcher-config.json"
    ctrl = mod.WatcherController(
        _cfg(tmp_path), cfg_path,
        process_one=lambda *a, **k: None, notify=lambda t, m: None)
    ctrl.set_interval(60)
    assert config_mod.load_config(cfg_path)["watch_interval_seconds"] == 60


def test_retry_failed_clears_markers_and_reprocesses(tmp_path):
    """After a recording is failed, scan_once skips it; retry_failed reprocesses it."""
    mod = _import_controller()
    rec = tmp_path / "recordings"
    rec.mkdir()
    (rec / "bad.opus").write_bytes(b"x")

    call_count = {"n": 0}

    def fake_process_one(path, cfg, **kw):
        call_count["n"] += 1
        note = tmp_path / "notes" / "bad.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("# Meeting notes")
        return pipe.ProcessResult("done", "bad", "ok", note)

    cfg_path = tmp_path / "watcher-config.json"
    cfg = _cfg(tmp_path)

    # Manually plant a .failed marker in the state dir
    work_dir = Path(cfg["work_dir"])
    state = State(work_dir / ".state", tmp_path / "notes")
    state.mark_failed("bad", "previous ffmpeg error")

    ctrl = mod.WatcherController(
        cfg, cfg_path,
        process_one=fake_process_one, notify=lambda t, m: None)

    # scan_once must NOT call process_one (bad.opus is failed)
    ctrl.scan_once()
    assert call_count["n"] == 0, "scan_once should skip failed recordings"

    # retry_failed must clear the marker and reprocess
    ctrl.retry_failed()
    assert call_count["n"] == 1, "retry_failed should reprocess the failed recording"


def test_startup_clears_stale_processing(tmp_path):
    """A crash leaves a .processing marker; a fresh controller clears it on
    startup so the recording becomes pending again."""
    mod = _import_controller()
    rec = tmp_path / "recordings"
    rec.mkdir()
    (rec / "stuck.opus").write_bytes(b"x")

    cfg = _cfg(tmp_path)
    work_dir = Path(cfg["work_dir"])
    state = State(work_dir / ".state", tmp_path / "notes")
    state.mark_processing("stuck")
    assert state.is_processing("stuck")

    calls = []

    def fake_process_one(path, cfg, **kw):
        calls.append(path.name)
        return pipe.ProcessResult("done", path.stem, "ok",
                                  tmp_path / "notes" / f"{path.stem}.md")

    ctrl = mod.WatcherController(
        cfg, tmp_path / "watcher-config.json",
        process_one=fake_process_one, notify=lambda t, m: None)

    # Startup cleared the stale marker.
    assert not state.is_processing("stuck")
    # So a scan now picks it up.
    ctrl.scan_once()
    assert calls == ["stuck.opus"]


def test_retry_failed_clears_processing(tmp_path):
    mod = _import_controller()
    cfg = _cfg(tmp_path)
    work_dir = Path(cfg["work_dir"])
    state = State(work_dir / ".state", tmp_path / "notes")
    state.mark_processing("ghost")

    ctrl = mod.WatcherController(
        cfg, tmp_path / "watcher-config.json",
        process_one=lambda *a, **k: None, notify=lambda t, m: None)
    # Re-plant to test retry_failed independently of startup.
    state.mark_processing("ghost")
    assert state.is_processing("ghost")
    ctrl.retry_failed()
    assert not state.is_processing("ghost")


def test_deferred_notifies_only_on_transition(tmp_path):
    """Two deferred results for the same base produce exactly one notification."""
    mod = _import_controller()
    notes = []
    ctrl = mod.WatcherController(
        _cfg(tmp_path), tmp_path / "watcher-config.json",
        process_one=lambda *a, **k: None,
        notify=lambda t, m: notes.append((t, m)))
    notes.clear()  # ignore any startup notifications
    r = pipe.ProcessResult("deferred_need_local", "demo", "need local")
    ctrl._handle_result(r)
    ctrl._handle_result(r)
    deferred_notes = [n for n in notes if "Ollama offline" in n[0]]
    assert len(deferred_notes) == 1


def test_last_transcript_text_after_done(tmp_path):
    mod = _import_controller()
    tdir = tmp_path / "work"
    tdir.mkdir(parents=True)
    tfile = tdir / "demo.transcript.clean.txt"
    tfile.write_text("[SPEAKER_00]\nhello there\n")
    ctrl = mod.WatcherController(
        _cfg(tmp_path), tmp_path / "watcher-config.json",
        process_one=lambda *a, **k: None, notify=lambda t, m: None)
    assert ctrl.last_transcript_text() is None  # nothing done yet
    note = tmp_path / "notes" / "demo.md"
    ctrl._handle_result(pipe.ProcessResult("done", "demo", "ok", note, tfile))
    assert ctrl.last_transcript_text() == "[SPEAKER_00]\nhello there\n"
    assert ctrl.last_note_path() == note


def test_apply_config_persists_swaps_and_clears_deferred(tmp_path):
    mod = _import_controller()
    cfg_path = tmp_path / "watcher-config.json"
    ctrl = mod.WatcherController(
        _cfg(tmp_path), cfg_path,
        process_one=lambda *a, **k: None, notify=lambda t, m: None)
    ctrl._deferred.add("demo")  # pretend something was deferred
    new = config_mod.deep_merge(ctrl.cfg, {
        "watch_interval_seconds": 99,
        "summarise": {"allow_local_fallback": True},
    })
    ctrl.apply_config(new)
    # persisted
    assert config_mod.load_config(cfg_path)["watch_interval_seconds"] == 99
    # swapped live
    assert ctrl.cfg["watch_interval_seconds"] == 99
    # allow_local turned on clears deferred
    assert not ctrl.has_deferred()
