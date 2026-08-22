"""Post-processing text replacement in rendered RTF files (extra cases)."""

import pytest

import rtfreporter as rr


def test_replace_input_must_be_path():
    with pytest.raises(TypeError, match="single file path"):
        rr.rtf_replace_text(["a", "b"], "x", "y")


def test_replace_empty_target_raises(tmp_path):
    src = tmp_path / "t.rtf"
    src.write_text("hello")
    with pytest.raises(ValueError, match="empty"):
        rr.rtf_replace_text(str(src), [], "y")


def test_replace_single_replacement_broadcasts(tmp_path):
    src = tmp_path / "t.rtf"
    src.write_text("aXbYc")
    rr.rtf_replace_text(str(src), ["X", "Y"], ["_"], backup=False)
    assert src.read_text() == "a_b_c"


def test_replace_regex_mode(tmp_path):
    src = tmp_path / "t.rtf"
    src.write_text("page 12 and 345")
    rr.rtf_replace_text(str(src), r"\d+", "N", use_regex=True, backup=False)
    assert src.read_text() == "page N and N"


def test_replace_no_backup_when_disabled(tmp_path):
    src = tmp_path / "t.rtf"
    src.write_text("DRAFT")
    rr.rtf_replace_text(str(src), "DRAFT", "FINAL", backup=False)
    assert not (tmp_path / "t.rtf.bak").exists()


def test_replace_returns_abspath(tmp_path):
    src = tmp_path / "t.rtf"
    src.write_text("x")
    out = rr.rtf_replace_text(str(src), "x", "y", backup=False)
    assert out == str(src.resolve())
