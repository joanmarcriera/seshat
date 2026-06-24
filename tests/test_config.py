import json

import pytest

from pathlib import Path

from meeting_pipeline.config import (
    ConfigError,
    DATA_BASE_DIR,
    DEFAULTS,
    deep_merge,
    load_config,
    resolve_path,
    save_config,
)


def test_load_writes_defaults_when_missing(tmp_path):
    cfg_path = tmp_path / "watcher-config.json"
    cfg = load_config(cfg_path)
    assert cfg_path.exists()
    assert cfg["watch_interval_seconds"] == 20
    assert cfg["summarise"]["backend"] == "server"


def test_load_merges_partial_over_defaults(tmp_path):
    cfg_path = tmp_path / "watcher-config.json"
    cfg_path.write_text(json.dumps({"watch_interval_seconds": 60}))
    cfg = load_config(cfg_path)
    assert cfg["watch_interval_seconds"] == 60
    # Missing nested keys still filled from defaults.
    assert cfg["transcribe"]["model"] == "medium"


def test_invalid_json_raises_configerror(tmp_path):
    cfg_path = tmp_path / "watcher-config.json"
    cfg_path.write_text("{not json")
    with pytest.raises(ConfigError):
        load_config(cfg_path)


def test_deep_merge_does_not_mutate_base():
    base = {"a": {"b": 1}}
    deep_merge(base, {"a": {"c": 2}})
    assert base == {"a": {"b": 1}}


def test_resolve_path_absolute_and_home(tmp_path):
    # Absolute values are honoured as-is.
    abs_dir = tmp_path / "recordings"
    assert resolve_path(str(abs_dir)) == abs_dir
    # ~-prefixed values expand to the home directory.
    assert resolve_path("~/x") == Path.home() / "x"


def test_resolve_path_bare_relative_uses_data_base_not_repo():
    # A bare-relative value resolves under ~/Documents/Scribed, NOT the repo.
    resolved = resolve_path("notes")
    assert resolved == (DATA_BASE_DIR / "notes").resolve()
    assert str(resolved).endswith("/Documents/Scribed/notes")
    # It must not be resolved against the install/repo directory.
    repo_root = Path(__file__).resolve().parent.parent
    assert repo_root not in resolved.parents


def test_save_then_load_roundtrip(tmp_path):
    cfg_path = tmp_path / "watcher-config.json"
    cfg = load_config(cfg_path)
    cfg["watch_interval_seconds"] = 10
    save_config(cfg_path, cfg)
    assert load_config(cfg_path)["watch_interval_seconds"] == 10
