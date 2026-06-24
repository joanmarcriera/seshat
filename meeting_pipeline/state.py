"""Deterministic naming, processing markers, and pending-file detection."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Callable

_UNSAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_stem(name: str) -> str:
    stem = Path(name).stem if ("." in name and "/" not in name) else name
    safe = _UNSAFE_RE.sub("_", stem).strip("._-")
    return safe or "recording"


def _sanitize_joined(name: str) -> str:
    """Sanitize an already-joined relative path WITHOUT re-stripping extensions.

    Replaces ``/`` and runs of unsafe chars with ``_``, strips leading/trailing
    ``._-``, and keeps internal dots intact. Falls back to ``"recording"``.
    """
    safe = _UNSAFE_RE.sub("_", name.replace("/", "_")).strip("._-")
    return safe or "recording"


def base_for(recordings_dir: Path, path: Path) -> str:
    """Subfolder-aware base name so same-named files in different folders don't collide.

    e.g. recordings/Anglia-water/recording.opus -> "Anglia-water__recording".
    Strips only the real audio suffix once, preserving internal dots so that
    e.g. call.2026.01.15.opus and call.2026.01.16.opus get distinct bases.
    Falls back to the filename stem if ``path`` is not under ``recordings_dir``.
    """
    recordings_dir = Path(recordings_dir)
    path = Path(path)
    try:
        rel = path.relative_to(recordings_dir)
    except ValueError:
        rel = Path(path.name)
    rel = rel.with_suffix("")  # strip only the real audio suffix, once
    return "__".join(_sanitize_joined(part) for part in rel.parts)


def wait_until_stable(
    path: Path,
    *,
    checks: int = 3,
    delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    last_size = -1
    stable = 0
    while stable < checks:
        if not path.exists():
            return False
        size = path.stat().st_size
        if size == last_size:
            stable += 1
        else:
            stable = 0
            last_size = size
        sleep(delay)
    return True


class State:
    def __init__(self, state_dir: Path, notes_dir: Path) -> None:
        self.state_dir = Path(state_dir)
        self.notes_dir = Path(notes_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def note_path(self, base: str) -> Path:
        return self.notes_dir / f"{base}.md"

    def _marker(self, base: str, suffix: str) -> Path:
        return self.state_dir / f"{base}.{suffix}"

    def is_done(self, base: str) -> bool:
        return self.note_path(base).exists() or self._marker(base, "done").exists()

    def is_processing(self, base: str) -> bool:
        return self._marker(base, "processing").exists()

    def is_failed(self, base: str) -> bool:
        return self._marker(base, "failed").exists()

    def mark_processing(self, base: str) -> None:
        self._marker(base, "processing").write_text("processing\n", encoding="utf-8")

    def clear_processing(self, base: str) -> None:
        self._marker(base, "processing").unlink(missing_ok=True)

    def mark_done(self, base: str) -> None:
        self._marker(base, "done").write_text("done\n", encoding="utf-8")
        self.clear_processing(base)
        self.clear_failed(base)

    def mark_failed(self, base: str, error: str) -> None:
        self._marker(base, "failed").write_text(error + "\n", encoding="utf-8")
        self.clear_processing(base)

    def clear_failed(self, base: str) -> None:
        self._marker(base, "failed").unlink(missing_ok=True)


def iter_pending(recordings_dir: Path, state: State, extensions: set[str]) -> list[Path]:
    recordings_dir = Path(recordings_dir)
    if not recordings_dir.exists():
        return []
    pending: list[Path] = []
    for path in sorted(recordings_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in extensions:
            continue
        base = base_for(recordings_dir, path)
        if state.is_done(base) or state.is_processing(base) or state.is_failed(base):
            continue
        pending.append(path)
    return pending
