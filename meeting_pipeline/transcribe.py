"""Convert any ffmpeg-readable recording to wav and send it to WhisperX."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

import requests


class TranscribeError(Exception):
    pass


# Common ffmpeg locations, in case PATH is minimal (e.g. under a launchd login
# agent, which does not inherit the user's shell PATH and so misses Homebrew).
_FFMPEG_FALLBACKS = ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg")


def ffmpeg_binary() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    for candidate in _FFMPEG_FALLBACKS:
        if Path(candidate).exists():
            return candidate
    raise TranscribeError(
        "ffmpeg not found. Install it with 'brew install ffmpeg'. "
        "(If running as a login agent, PATH may exclude /opt/homebrew/bin.)"
    )


def convert_to_wav(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_binary(), "-y", "-i", str(src),
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not dest.exists() or dest.stat().st_size == 0:
        raise TranscribeError(
            f"ffmpeg failed for {src.name}: {proc.stderr.strip()[-500:]}"
        )


def transcribe(
    wav_path: Path,
    transcribe_cfg: dict[str, Any],
    *,
    timeout: int = 3600,
    post: Callable[..., Any] | None = None,
) -> dict:
    post = post or requests.post
    url = transcribe_cfg["whisperx_url"].rstrip("/") + "/asr"
    # WhisperX (learnedmachine/whisperx-asr-service) reads these as QUERY
    # parameters, not multipart form fields. Sending them as form data leaves
    # `model` empty server-side and the request 500s with "Invalid model size".
    params = {
        "language": transcribe_cfg.get("language", "en"),
        "model": transcribe_cfg.get("model", "medium"),
        "output_format": "json",
        "diarize": str(transcribe_cfg.get("diarize", True)).lower(),
        "num_speakers": str(transcribe_cfg.get("num_speakers", 2)),
    }
    try:
        with wav_path.open("rb") as audio:
            response = post(
                url,
                params=params,
                files={"audio_file": (wav_path.name, audio, "audio/wav")},
                timeout=timeout,
            )
        response.raise_for_status()
        return response.json()
    except TranscribeError:
        raise
    except Exception as exc:
        raise TranscribeError(f"WhisperX request failed: {exc}") from exc
