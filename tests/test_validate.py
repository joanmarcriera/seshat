from meeting_pipeline.validate import validate_summary, words_from


def test_words_from_lowercases_and_tokenises():
    assert words_from("Hello, World-2") == ["hello", "world-2"]


def test_valid_summary_has_no_failures():
    assert validate_summary("# Notes\n\nA short, healthy summary.") == []


def test_empty_summary_fails():
    assert any("empty" in f for f in validate_summary("   "))


def test_repetition_collapse_detected():
    text = "the model said the model said the model said " * 10
    failures = validate_summary(text, max_ngram_count=5)
    assert any("repetition" in f for f in failures)


def test_overlong_summary_fails():
    failures = validate_summary("x" * 60000, max_chars=50000)
    assert any("long" in f for f in failures)
