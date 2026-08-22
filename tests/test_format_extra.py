"""Edge cases in count/percent formatting and cell_format machinery."""

import pytest

import rtfreporter as rr
from rtfreporter.format_count_pct import (
    apply_cell_format,
    realign_count_pct_df,
    resolve_cell_format,
)

NBSP = " "


# -- fmt_right_align ----------------------------------------------------------


def test_fmt_right_align_all_empty_returns_unchanged():
    # No cell has non-whitespace content, so nothing is padded.
    assert rr.fmt_right_align(["", "  ", None]) == ["", "  ", ""]


def test_fmt_right_align_pads_with_nbsp():
    out = rr.fmt_right_align(["7", "100"])
    assert out[0] == f"{NBSP}{NBSP}7"
    assert out[1] == "100"


def test_fmt_right_align_plain_space():
    out = rr.fmt_right_align(["7", "100"], nbsp=" ")
    assert out[0] == "  7"


# -- fmt_count_paren ----------------------------------------------------------


def test_fmt_count_paren_no_parens_unchanged():
    # No cell has parentheses -> nothing to align, returned as-is.
    assert rr.fmt_count_paren(["5", "12", ""]) == ["5", "12", ""]


def test_fmt_count_paren_aligns_and_uses_nbsp():
    out = rr.fmt_count_paren(["3 (4.0)", "10 (50.0)"])
    assert all(NBSP in v or v.startswith("10") for v in out)
    # widths line up: the shorter count is left-padded.
    assert out[0].replace(NBSP, " ").startswith(" 3 (")


def test_fmt_count_paren_bare_pads_lone_integers():
    out = rr.fmt_count_paren_bare(["3 (4)", "100"])
    # the bare 100 is widened to the count field.
    assert out[1].startswith("100")


# -- resolve_cell_format ------------------------------------------------------


def test_resolve_cell_format_none_returns_none():
    assert resolve_cell_format(None, 3) is None


def test_resolve_cell_format_zero_cols_returns_none():
    assert resolve_cell_format(lambda c: c, 0) is None


def test_resolve_cell_format_callable_skips_first_column():
    fl = resolve_cell_format(str.upper, 3)
    assert fl[0] is None
    assert fl[1] is str.upper and fl[2] is str.upper


def test_resolve_cell_format_list_positional():
    f = lambda c: c  # noqa: E731
    fl = resolve_cell_format([f, None, f], 3)
    assert fl[0] is f and fl[1] is None and fl[2] is f


def test_resolve_cell_format_bad_type_raises():
    with pytest.raises(TypeError, match="callable or a list"):
        resolve_cell_format(42, 3)


# -- apply_cell_format --------------------------------------------------------


def test_apply_cell_format_skips_non_character_column():
    rows = [["a", 1], ["b", 2]]  # column 1 is numeric -> skipped
    fl = [None, lambda col: ["X"] * len(col)]
    apply_cell_format(rows, ["c0", "c1"], fl)
    assert rows == [["a", 1], ["b", 2]]


def test_apply_cell_format_length_mismatch_raises():
    rows = [["a", "x"], ["b", "y"]]
    fl = [None, lambda col: ["only one"]]
    with pytest.raises(ValueError, match="same length"):
        apply_cell_format(rows, ["c0", "c1"], fl)


def test_apply_cell_format_transforms_character_column():
    rows = [["a", "x"], ["b", "y"]]
    fl = [None, lambda col: [c.upper() for c in col]]
    apply_cell_format(rows, ["c0", "c1"], fl)
    assert rows == [["a", "X"], ["b", "Y"]]


def test_realign_count_pct_df_single_column_noop():
    rows = [["3 (4.0)"], ["10 (50.0)"]]
    before = [r[:] for r in rows]
    realign_count_pct_df(rows, ["only"])
    assert rows == before
