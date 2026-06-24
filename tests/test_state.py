from pathlib import Path

from meeting_pipeline.state import (
    State,
    base_for,
    iter_pending,
    safe_stem,
    wait_until_stable,
)

EXTS = {".wav", ".m4a", ".opus"}


def test_safe_stem_sanitises():
    assert safe_stem("WhatsApp Audio 2026.opus") == "WhatsApp_Audio_2026"
    assert safe_stem("a b/c") == "a_b_c"
    assert safe_stem("") == "recording"


def test_base_for_nested_path():
    rec = Path("/recordings")
    assert base_for(rec, rec / "Anglia-water" / "recording.opus") == "Anglia-water__recording"


def test_base_for_top_level_path():
    rec = Path("/recordings")
    assert base_for(rec, rec / "demo.opus") == "demo"


def test_base_for_dotted_dates_do_not_collide():
    """Regression: dotted filenames must keep internal dots so distinct dates
    yield distinct bases (previously both collapsed to 'call.2026.01')."""
    rec = Path("/recordings")
    b15 = base_for(rec, rec / "call.2026.01.15.opus")
    b16 = base_for(rec, rec / "call.2026.01.16.opus")
    assert b15 == "call.2026.01.15"
    assert b16 == "call.2026.01.16"
    assert b15 != b16


def test_base_for_nested_dotted_distinct():
    rec = Path("/recordings")
    ab = base_for(rec, rec / "Sub" / "a.b.opus")
    ac = base_for(rec, rec / "Sub" / "a.c.opus")
    assert ab == "Sub__a.b"
    assert ac == "Sub__a.c"
    assert ab != ac


def test_base_for_not_under_dir_falls_back_to_name():
    rec = Path("/recordings")
    assert base_for(rec, Path("/elsewhere/recording.opus")) == "recording"


def test_iter_pending_distinct_bases_for_same_name_in_subfolders(tmp_path):
    rec = tmp_path / "recordings"
    (rec / "Anglia-water").mkdir(parents=True)
    (rec / "Dsit").mkdir(parents=True)
    (rec / "Anglia-water" / "recording.opus").write_bytes(b"x")
    (rec / "Dsit" / "recording.opus").write_bytes(b"x")
    state = State(tmp_path / ".state", tmp_path / "notes")
    pending = iter_pending(rec, state, EXTS)
    bases = sorted(base_for(rec, p) for p in pending)
    assert bases == ["Anglia-water__recording", "Dsit__recording"]


def test_state_done_via_note_or_marker(tmp_path):
    state = State(tmp_path / ".state", tmp_path / "notes")
    assert not state.is_done("meeting")
    state.mark_done("meeting")
    assert state.is_done("meeting")

    state2 = State(tmp_path / ".state2", tmp_path / "notes2")
    state2.note_path("x").parent.mkdir(parents=True, exist_ok=True)
    state2.note_path("x").write_text("# note")
    assert state2.is_done("x")


def test_processing_markers(tmp_path):
    state = State(tmp_path / ".state", tmp_path / "notes")
    state.mark_processing("m")
    assert state.is_processing("m")
    state.clear_processing("m")
    assert not state.is_processing("m")


def test_wait_until_stable_true_when_size_constant(tmp_path):
    f = tmp_path / "a.wav"
    f.write_bytes(b"12345")
    assert wait_until_stable(f, checks=2, delay=0, sleep=lambda s: None) is True


def test_iter_pending_recurses_and_filters(tmp_path):
    rec = tmp_path / "recordings"
    (rec / "sub").mkdir(parents=True)
    (rec / "a.opus").write_bytes(b"x")
    (rec / "sub" / "b.m4a").write_bytes(b"x")
    (rec / "note.txt").write_text("ignore")  # unsupported ext
    state = State(tmp_path / ".state", tmp_path / "notes")
    state.mark_done("a")  # already processed by stem
    pending = iter_pending(rec, state, EXTS)
    names = sorted(p.name for p in pending)
    assert names == ["b.m4a"]


def test_iter_pending_skips_failed_recordings(tmp_path):
    """Failed recordings must not be reprocessed on every watcher cycle."""
    rec = tmp_path / "recordings"
    rec.mkdir(parents=True)
    (rec / "bad.opus").write_bytes(b"x")
    (rec / "good.opus").write_bytes(b"x")
    state = State(tmp_path / ".state", tmp_path / "notes")
    state.mark_failed("bad", "ffmpeg error")

    # 'bad' should be excluded; 'good' should still be pending
    pending = iter_pending(rec, state, EXTS)
    names = sorted(p.name for p in pending)
    assert names == ["good.opus"]


def test_clear_failed_makes_recording_pending_again(tmp_path):
    """After clear_failed, a previously-failed recording re-enters the pending list."""
    rec = tmp_path / "recordings"
    rec.mkdir(parents=True)
    (rec / "bad.opus").write_bytes(b"x")
    state = State(tmp_path / ".state", tmp_path / "notes")
    state.mark_failed("bad", "some error")

    # Confirm excluded while failed
    assert iter_pending(rec, state, EXTS) == []

    # Clear the failure marker (simulates manual "Process now" / retry)
    state.clear_failed("bad")

    # Now it should be pending again
    pending = iter_pending(rec, state, EXTS)
    assert [p.name for p in pending] == ["bad.opus"]
