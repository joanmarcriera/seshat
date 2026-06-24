"""Load/save the watcher's JSON settings, applying defaults for missing keys."""

from __future__ import annotations

import copy
import json
from pathlib import Path

# Base directory for resolving bare-relative path settings (e.g. "notes").
# Absolute and ~-prefixed settings are honoured as-is; only bare-relative
# values are joined onto this base — never the install/repo directory.
DATA_BASE_DIR: Path = Path.home() / "Documents" / "MeetingNotes"

DEFAULTS: dict = {
    "watch_interval_seconds": 20,
    "recordings_dir": "~/Documents/MeetingNotes/recordings",
    "notes_dir": "~/Documents/MeetingNotes/notes",
    "work_dir": "~/Library/Application Support/MeetingNotes/work",
    "transcribe": {
        "whisperx_url": "http://127.0.0.1:9000",
        "model": "medium",
        "language": "en",
        "diarize": True,
        "num_speakers": 2,
    },
    "summarise": {
        "backend": "server",
        "server": {"url": "http://127.0.0.1:11434", "model": "llama3.1:8b"},
        "local": {
            "url": "http://127.0.0.1:11434",
            "model": "llama3.1:8b",
        },
        "allow_local_fallback": False,
        "options": {
            "num_ctx": 65536,
            "temperature": 0.1,
            "top_p": 0.85,
            "seed": 42,
            "num_predict": 6144,
            "repeat_penalty": 1.15,
            "repeat_last_n": 512,
        },
    },
    "note_owner": "Me",
    "user_speaker": "unknown",
}


class ConfigError(Exception):
    """Raised when the config file exists but cannot be parsed."""


def deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        save_config(path, DEFAULTS)
        return copy.deepcopy(DEFAULTS)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ConfigError(f"Could not read config {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"Config {path} must be a JSON object.")
    return deep_merge(DEFAULTS, raw)


def save_config(path: Path, cfg: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_path(value: str) -> Path:
    """Resolve a path setting to an absolute Path.

    Expands ``~``; absolute values are returned unchanged; bare-relative
    values resolve under ``DATA_BASE_DIR`` (~/Documents/MeetingNotes), never
    against the install/repo directory.
    """
    expanded = Path(value).expanduser()
    if expanded.is_absolute():
        return expanded
    return (DATA_BASE_DIR / expanded).resolve()
