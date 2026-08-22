"""Clinical indented stub construction (stub_cols)."""

import pytest

import rtfreporter as rr
from rtfreporter.stub import _resolve_group_summary

# -- _resolve_group_summary ---------------------------------------------------


def test_group_summary_none_is_empty_set():
    assert _resolve_group_summary(None) == set()


def test_group_summary_string_is_wrapped():
    assert _resolve_group_summary("empty") == {"empty"}


def test_group_summary_all_expands():
    assert _resolve_group_summary("all") == {"empty", "parent"}


def test_group_summary_none_keyword_clears():
    assert _resolve_group_summary(["none"]) == set()


def test_group_summary_unknown_raises():
    with pytest.raises(ValueError, match="subset"):
        _resolve_group_summary(["bogus"])


# -- stub_cols validation -----------------------------------------------------


def test_stub_cols_distinct_vars_required():
    with pytest.raises(ValueError, match="distinct"):
        rr.stub_cols({"a": ["x"], "n": ["1"]}, vars=["a", "a"])


def test_stub_cols_label_must_be_str():
    with pytest.raises(ValueError, match="label"):
        rr.stub_cols({"a": ["x"], "b": ["y"], "n": ["1"]}, vars=["a", "b"], label=5)


def test_stub_cols_negative_indent_raises():
    with pytest.raises(ValueError, match="indent"):
        rr.stub_cols({"a": ["x"], "b": ["y"], "n": ["1"]}, vars=["a", "b"], indent=-1)


# -- stub_cols behaviour ------------------------------------------------------


def test_stub_cols_indent_width_scales():
    fr = rr.stub_cols(
        {"soc": ["C", "C"], "pt": ["", "AFib"], "n": ["4", "3"]},
        vars=["soc", "pt"],
        indent=2,
        group_summary="none",
    )
    # leaf row is indented under its parent by `indent` non-breaking spaces.
    leaf = next(r[0] for r in fr.rows if r[0].strip() == "AFib")
    assert leaf.startswith("  ")


def test_stub_cols_empty_parent_skips_label_row():
    # A blank parent value at a level emits no label row for that level.
    fr = rr.stub_cols(
        {"soc": ["", ""], "pt": ["AFib", "Brady"], "n": ["1", "2"]},
        vars=["soc", "pt"],
        group_summary="none",
    )
    labels = [r[0].strip() for r in fr.rows]
    assert labels == ["AFib", "Brady"]


def test_stub_cols_parent_mode_folds_summary():
    fr = rr.stub_cols(
        {"soc": ["Cardiac", "Cardiac"], "pt": ["Cardiac", "AFib"], "n": ["9", "3"]},
        vars=["soc", "pt"],
        group_summary="parent",
    )
    # The leaf equal to its parent folds its stats onto the SOC label row.
    assert fr.rows[0] == ["Cardiac", "9"]


def test_stub_cols_default_label_joins_names():
    fr = rr.stub_cols(
        {"soc": ["A"], "pt": ["x"], "n": ["1"]}, vars=["soc", "pt"]
    )
    assert fr.column_names[0] == "soc / pt"


def test_stub_cols_by_index():
    fr = rr.stub_cols(
        {"soc": ["A", "A"], "pt": ["p", "q"], "n": ["1", "2"]}, vars=[0, 1]
    )
    assert fr.column_names == ["soc / pt", "n"]
