#!/usr/bin/env python3
"""Headless: process every pending recording once (no GUI). For testing/cron."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import pipeline as pipe
from .config import load_config, resolve_path
from .state import State, iter_pending

CONFIG_PATH = (
    Path.home() / "Library" / "Application Support" / "Scribed"
    / "watcher-config.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--recordings-dir")
    parser.add_argument("--notes-dir")
    parser.add_argument("--work-dir")
    args = parser.parse_args(argv)

    cfg = load_config(Path(args.config))
    for key, value in (
        ("recordings_dir", args.recordings_dir),
        ("notes_dir", args.notes_dir),
        ("work_dir", args.work_dir),
    ):
        if value:
            cfg[key] = value

    recordings_dir = resolve_path(cfg["recordings_dir"])
    work_dir = resolve_path(cfg["work_dir"])
    notes_dir = resolve_path(cfg["notes_dir"])
    state = State(work_dir / ".state", notes_dir)

    pending = iter_pending(recordings_dir, state, pipe.SUPPORTED_EXTENSIONS)
    if not pending:
        print("No pending recordings.")
        return 0

    failures = 0
    for path in pending:
        print(f"Processing {path.name} ...")
        result = pipe.process_one(path, cfg)
        print(f"  -> {result.status}: {result.message}")
        if result.status in {"failed", "deferred_need_local"}:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
