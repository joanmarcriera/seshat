import subprocess
from pathlib import Path

import pytest

from meeting_pipeline.transcribe import (
    TranscribeError,
    convert_to_wav,
    ffmpeg_binary,
    transcribe,
)


def test_ffmpeg_binary_returns_absolute_existing_path():
    # When ffmpeg is installed, resolve to a real absolute path so the pipeline
    # works even under a minimal launchd PATH. Skip where ffmpeg is absent
    # (the missing case is covered by test_ffmpeg_binary_raises_when_missing).
    try:
        path = ffmpeg_binary()
    except TranscribeError:
        pytest.skip("ffmpeg not installed")
    assert Path(path).is_absolute()
    assert Path(path).exists()


def test_ffmpeg_binary_raises_when_missing(monkeypatch):
    import meeting_pipeline.transcribe as tmod
    monkeypatch.setattr(tmod.shutil, "which", lambda name: None)
    monkeypatch.setattr(tmod, "_FFMPEG_FALLBACKS", ())
    with pytest.raises(TranscribeError):
        tmod.ffmpeg_binary()

DEFAULT_CFG = {
    "whisperx_url": "http://whisper.test:9000",
    "model": "medium",
    "language": "en",
    "diarize": True,
    "num_speakers": 2,
}


def _ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not installed")
def test_convert_to_wav_produces_a_wav(tmp_path):
    # Generate a 1s sine tone as a source .m4a, then convert it.
    src = tmp_path / "tone.m4a"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         str(src)],
        capture_output=True, check=True,
    )
    dest = tmp_path / "out.wav"
    convert_to_wav(src, dest)
    assert dest.exists() and dest.stat().st_size > 0


def test_convert_to_wav_raises_on_bad_input(tmp_path):
    src = tmp_path / "not-audio.m4a"
    src.write_text("garbage")
    with pytest.raises(TranscribeError):
        convert_to_wav(src, tmp_path / "out.wav")


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def test_transcribe_posts_and_returns_json(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF....")
    captured = {}

    def fake_post(url, params=None, files=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["files"] = files
        return _FakeResponse(200, {"segments": [{"speaker": "SPEAKER_00", "text": "hi"}]})

    result = transcribe(wav, DEFAULT_CFG, post=fake_post)
    assert captured["url"] == "http://whisper.test:9000/asr"
    # WhisperX params must be sent as query params, not form data.
    assert captured["params"]["model"] == "medium"
    assert captured["params"]["language"] == "en"
    assert "audio_file" in captured["files"]
    assert result["segments"][0]["text"] == "hi"


def test_transcribe_raises_on_http_error(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")

    def fake_post(url, params=None, files=None, timeout=None):
        return _FakeResponse(500, {})

    with pytest.raises(TranscribeError):
        transcribe(wav, DEFAULT_CFG, post=fake_post)
