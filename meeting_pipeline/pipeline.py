"""Orchestrate one recording: convert -> transcribe -> clean -> summarise -> note."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from . import transcribe as transcribe_mod
from . import summarise as summarise_mod
from .cleaning import clean_transcript, segments_from_result
from .config import resolve_path
from .state import State, base_for, wait_until_stable
from .validate import validate_summary

SUPPORTED_EXTENSIONS = {
    ".wav", ".m4a", ".mp3", ".opus", ".ogg", ".flac", ".aac", ".m4b",
    ".mov", ".mp4", ".m4v", ".3gp", ".webm", ".mkv",
}


@dataclass
class ProcessResult:
    status: str
    base: str
    message: str
    note_path: Path | None = None
    transcript_path: Path | None = None


def _default_deps() -> SimpleNamespace:
    return SimpleNamespace(
        convert_to_wav=transcribe_mod.convert_to_wav,
        transcribe=transcribe_mod.transcribe,
        ollama_reachable=summarise_mod.ollama_reachable,
        summarise=summarise_mod.summarise,
    )


def _choose_ollama(cfg: dict, deps: SimpleNamespace) -> tuple[dict, bool]:
    """Return (chosen target dict, deferred). target has url+model."""
    scfg = cfg["summarise"]
    server = scfg["server"]
    local = scfg["local"]
    if scfg.get("backend") == "local":
        return local, False
    if deps.ollama_reachable(server["url"]):
        return server, False
    if scfg.get("allow_local_fallback"):
        return local, False
    return {}, True


def process_one(
    path: Path,
    cfg: dict,
    *,
    deps: Any = None,
    stable_checks: int = 3,
    stable_delay: float = 2.0,
) -> ProcessResult:
    deps = deps or _default_deps()
    recordings_dir = resolve_path(cfg["recordings_dir"])
    base = base_for(recordings_dir, path)

    notes_dir = resolve_path(cfg["notes_dir"])
    work_dir = resolve_path(cfg["work_dir"])
    state = State(work_dir / ".state", notes_dir)

    if state.is_done(base):
        return ProcessResult("skipped", base, "already processed",
                             state.note_path(base))

    if not wait_until_stable(path, checks=stable_checks, delay=stable_delay):
        return ProcessResult("skipped", base, "file still changing")

    if state.is_processing(base):
        return ProcessResult("skipped", base, "already being processed")

    target, deferred = _choose_ollama(cfg, deps)
    if deferred:
        return ProcessResult(
            "deferred_need_local", base,
            "Server Ollama offline; local fallback not allowed yet")

    state.mark_processing(base)
    notes_dir.mkdir(parents=True, exist_ok=True)
    note_path = state.note_path(base)

    try:
        wav_path = work_dir / f"{base}.wav"
        deps.convert_to_wav(path, wav_path)

        result = deps.transcribe(wav_path, cfg["transcribe"])
        segments = segments_from_result(result)
        clean = clean_transcript(segments)
        if not clean.strip():
            state.mark_failed(base, "empty transcript")
            return ProcessResult("failed", base, "empty transcript")

        transcript_path = work_dir / f"{base}.transcript.clean.txt"
        transcript_path.write_text(clean + "\n", encoding="utf-8")

        summary, _raw = deps.summarise(
            clean,
            url=target["url"], model=target["model"],
            options=cfg["summarise"]["options"],
            note_owner=cfg["note_owner"], user_speaker=cfg["user_speaker"],
        )
        note_path.write_text(summary, encoding="utf-8")

        failures = validate_summary(summary)
        if failures:
            state.mark_failed(base, "; ".join(failures))
            return ProcessResult("failed", base, "; ".join(failures), note_path,
                                 transcript_path)

        state.mark_done(base)
        return ProcessResult("done", base, "note written", note_path, transcript_path)

    except Exception as exc:  # transcribe/summarise/convert errors
        state.mark_failed(base, f"{type(exc).__name__}: {exc}")
        return ProcessResult("failed", base, str(exc),
                             note_path if note_path.exists() else None)
