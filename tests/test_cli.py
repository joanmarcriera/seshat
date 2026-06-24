import importlib.util
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_cli():
    spec = importlib.util.spec_from_file_location(
        "process_recordings", REPO_ROOT / "process-recordings.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_processes_pending(tmp_path, monkeypatch):
    cli = _load_cli()
    rec = tmp_path / "recordings"
    rec.mkdir()
    (rec / "demo.opus").write_bytes(b"x")
    cfg_path = tmp_path / "watcher-config.json"

    # Point config at temp dirs and stub the pipeline.
    import meeting_pipeline.pipeline as pipe

    def fake_process_one(path, cfg, **kw):
        note = tmp_path / "notes" / "demo.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("# Meeting notes")
        return pipe.ProcessResult("done", "demo", "ok", note)

    monkeypatch.setattr(pipe, "process_one", fake_process_one)

    rc = cli.main([
        "--config", str(cfg_path),
        "--recordings-dir", str(rec),
        "--notes-dir", str(tmp_path / "notes"),
        "--work-dir", str(tmp_path / "work"),
    ])
    assert rc == 0
    assert (tmp_path / "notes" / "demo.md").exists()
