import pytest

from meeting_pipeline.summarise import (
    SummariseError,
    build_prompt,
    ollama_reachable,
    summarise,
)

OPTIONS = {"temperature": 0.1, "num_ctx": 1024, "num_predict": 256}


def test_build_prompt_includes_owner_and_transcript():
    prompt = build_prompt("[SPEAKER_00]\nhello", "Alex", "SPEAKER_00")
    assert "Alex" in prompt
    assert "SPEAKER_00" in prompt
    assert "[SPEAKER_00]\nhello" in prompt
    assert "British English" in prompt


class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def test_ollama_reachable_true_on_200():
    assert ollama_reachable("http://x:30068", get=lambda u, timeout: _Resp(200, {}))


def test_ollama_reachable_false_on_exception():
    def boom(u, timeout):
        raise OSError("refused")
    assert ollama_reachable("http://x:30068", get=boom) is False


def test_summarise_returns_text_and_raw():
    def fake_post(url, json=None, timeout=None):
        assert url == "http://x:30068/api/generate"
        assert json["model"] == "gemma4:latest"
        return _Resp(200, {"response": "# Meeting notes\n\nok"})

    text, raw = summarise(
        "[SPEAKER_00]\nhi",
        url="http://x:30068", model="gemma4:latest", options=OPTIONS,
        note_owner="Alex", user_speaker="SPEAKER_00", post=fake_post,
    )
    assert text.startswith("# Meeting notes")
    assert raw["response"]


def test_summarise_raises_on_empty():
    def fake_post(url, json=None, timeout=None):
        return _Resp(200, {"response": "   "})
    with pytest.raises(SummariseError):
        summarise("x", url="http://x:30068", model="m", options=OPTIONS,
                  note_owner="Alex", user_speaker="unknown", post=fake_post)
