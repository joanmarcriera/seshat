import re

from meeting_pipeline.cleaning import (
    clean_transcript,
    normalise_space,
    segments_from_result,
)


def test_normalise_space_collapses_whitespace():
    assert normalise_space("  a\n\t b  ") == "a b"


def test_segments_from_result_extracts_speaker_and_text(whisperx_sample):
    segments = segments_from_result(whisperx_sample)
    assert len(segments) == 4
    assert segments[0]["speaker"] == "SPEAKER_00"
    assert segments[0]["text"] == "Hello, thanks for joining."


def test_clean_transcript_groups_turns_and_drops_timestamps(whisperx_sample):
    segments = segments_from_result(whisperx_sample)
    out = clean_transcript(segments)
    # No timestamp ranges like [0:00 - 0:02].
    assert not re.search(r"\[\d+:\d{2}", out)
    # Consecutive same-speaker turns are merged under one [SPEAKER_xx] header.
    assert out.count("[SPEAKER_00]") == 2
    assert out.count("[SPEAKER_01]") == 1
    assert "Hello, thanks for joining. Let's talk about the GPU cluster." in out


def test_clean_transcript_empty_when_no_segments():
    assert clean_transcript([]) == ""
