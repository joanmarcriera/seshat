"""Detect obvious repetition collapse / empty / overlong model output."""

from __future__ import annotations

import re
from collections import Counter

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")


def words_from(text: str) -> list[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def most_repeated_ngram(words: list[str], size: int) -> tuple[str, int]:
    if len(words) < size:
        return "", 0
    counts = Counter(
        tuple(words[i : i + size]) for i in range(len(words) - size + 1)
    )
    ngram, count = counts.most_common(1)[0]
    return " ".join(ngram), count


def validate_summary(
    text: str,
    ngram_size: int = 5,
    max_ngram_count: int = 16,
    max_chars: int = 50000,
) -> list[str]:
    failures: list[str] = []
    if not text.strip():
        failures.append("summary is empty")
    if len(text) > max_chars:
        failures.append(f"summary is unusually long ({len(text)} chars > {max_chars})")
    ngram, count = most_repeated_ngram(words_from(text), ngram_size)
    if count > max_ngram_count:
        failures.append(f"possible repetition collapse: '{ngram}' appears {count} times")
    return failures
