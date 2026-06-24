"""Turn a WhisperX result into a speaker-grouped, timestamp-free transcript."""

from __future__ import annotations

import re
from typing import Any, Iterable

_WS_RE = re.compile(r"\s+")


def normalise_space(value: str) -> str:
    return _WS_RE.sub(" ", value).strip()


def segments_from_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    raw_segments = result.get("segments")
    if isinstance(raw_segments, list):
        segments: list[dict[str, Any]] = []
        for item in raw_segments:
            if not isinstance(item, dict):
                continue
            text = normalise_space(str(item.get("text") or ""))
            if not text:
                continue
            segments.append(
                {
                    "speaker": item.get("speaker") or "SPEAKER_UNKNOWN",
                    "text": text,
                    "start": item.get("start"),
                    "end": item.get("end"),
                }
            )
        return segments

    text = result.get("text")
    if isinstance(text, list):
        segments = []
        for item in text:
            if isinstance(item, dict):
                line_text = normalise_space(str(item.get("text") or ""))
                speaker = item.get("speaker") or "SPEAKER_UNKNOWN"
            else:
                line_text = normalise_space(str(item or ""))
                speaker = "SPEAKER_UNKNOWN"
            if line_text:
                segments.append({"speaker": speaker, "text": line_text})
        return segments

    text_value = normalise_space(str(text or ""))
    if text_value:
        return [{"speaker": "SPEAKER_UNKNOWN", "text": text_value}]
    return []


def clean_transcript(
    segments: Iterable[dict[str, Any]],
    max_turn_chars: int = 1800,
) -> str:
    grouped: list[tuple[str, str]] = []
    current_speaker: str | None = None
    current_parts: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current_speaker, current_parts, current_len
        if current_speaker and current_parts:
            grouped.append((current_speaker, normalise_space(" ".join(current_parts))))
        current_speaker = None
        current_parts = []
        current_len = 0

    for segment in segments:
        speaker = str(segment.get("speaker") or "SPEAKER_UNKNOWN")
        text = normalise_space(str(segment.get("text") or ""))
        if not text:
            continue
        if current_speaker is not None and (
            speaker != current_speaker or current_len + len(text) > max_turn_chars
        ):
            flush()
        if current_speaker is None:
            current_speaker = speaker
        current_parts.append(text)
        current_len += len(text) + 1

    flush()
    return "\n\n".join(f"[{speaker}]\n{text}" for speaker, text in grouped)
