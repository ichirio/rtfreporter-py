"""Count / percent display-width formatters (format-count-pct)."""

import pytest

from rtfreporter import (
    as_rtftables,
    fmt_count_paren,
    fmt_count_paren_bare,
    fmt_right_align,
    format_count_pct,
    realign_count_pct,
)

SP = " "  # plain-space variant for readable assertions


# -- format_count_pct: numeric inputs ----------------------------------------


def test_format_count_pct_fraction_width10():
    out = format_count_pct([5, 14, 30], [0.053, 0.500, 1.000])
    assert [len(s) for s in out] == [10, 10, 10]


def test_format_count_pct_percent_unit():
    out = format_count_pct([5, 14, 30], [5, 50, 100], pct_unit="percent")
    assert [len(s) for s in out] == [10, 10, 10]
    assert "100" in out[2]


def test_format_count_pct_100_branch_exact():
    out = format_count_pct([5, 14, 30], [5, 50, 100], pct_unit="percent", nbsp=SP)
    assert out == ["  5  (5.0)", " 14 (50.0)", " 30  (100)"]
    assert all(s.endswith(")") for s in out)
    assert all(s.index(")") == 9 for s in out)  # ')' at column 10 (0-based 9)


def test_format_count_pct_zero_and_na_branch():
    out0 = format_count_pct(0, 0.0)
    out_na = format_count_pct(None, None)
    assert len(out0[0]) == 10
    assert len(out_na[0]) == 10
    assert "(" not in out0[0]


def test_format_count_pct_small_vs_big_branch():
    small = format_count_pct(1, 5, pct_unit="percent", nbsp=SP)
    big = format_count_pct(7, 33.3, pct_unit="percent", nbsp=SP)
    assert "(5.0)" in small[0]
    assert "(33.3)" in big[0]


def test_format_count_pct_plain_spaces():
    out = format_count_pct(7, 0.333, nbsp=SP)
    assert out[0] == "  7 (33.3)"


def test_format_count_pct_recycles_length1():
    assert len(format_count_pct([5, 14, 30], 0.5)) == 3
    assert len(format_count_pct(2, [0.10, 0.50, 0.95])) == 3


def test_format_count_pct_mismatched_length_raises():
    with pytest.raises(ValueError, match="same length"):
        format_count_pct([1, 2, 3], [0.1, 0.2])


def test_format_count_pct_non_numeric_raises():
    with pytest.raises(TypeError):
        format_count_pct(["a"], [0.1])


def test_format_count_pct_pct_sign_wider_and_aligned():
    a = format_count_pct([5, 14, 30], [5, 50, 100], pct_unit="percent", nbsp=SP,
                         pct_sign=True)
    assert all(len(s) == len(a[0]) for s in a)
    assert all(s.endswith("%)") for s in a)
    b = format_count_pct(14, 50, pct_unit="percent", nbsp=SP)
    assert "%" not in b[0]


def test_format_count_pct_uses_nbsp_by_default():
    out = format_count_pct(7, 0.333)
    assert " " in out[0]


def test_format_count_pct_bad_pct_unit():
    with pytest.raises(ValueError):
        format_count_pct(1, 0.5, pct_unit="ratio")


# -- realign_count_pct: string inputs ----------------------------------------


def test_realign_reformats_matching_passes_others():
    inp = ["5 (33.3)", "12 (100.0)", "0 (0.0)", "not a count", "1 (5.0)"]
    out = realign_count_pct(inp, nbsp=SP)
    for idx in (0, 1, 2, 4):
        assert len(out[idx]) == 10
    assert out[3] == "not a count"


def test_realign_empty_none_numeric():
    assert realign_count_pct([]) == []
    assert realign_count_pct(None) is None
    assert realign_count_pct([1, 2]) == ["1", "2"]


def test_realign_percent_sign_cells_keep_percent():
    out = realign_count_pct(["8 (28.6%)", "10 (35.7%)", "3 (100%)", "5 (5.0%)"],
                            nbsp=SP)
    assert all(len(s) == len(out[0]) for s in out)
    assert all(s.endswith("%)") for s in out)


def test_realign_bare_zero_expands_to_count_only_aligned():
    # A "0 (0.0)" cell collapses to an aligned count-only cell (no parens),
    # sharing the fixed 10-char width with the paren cells.
    out = realign_count_pct(["0 (0.0)", "5 (33.3)"], nbsp=SP)
    assert len(out[0]) == 10 and len(out[1]) == 10
    assert "(" not in out[0]


# -- fmt_right_align ----------------------------------------------------------


def test_fmt_right_align():
    out = fmt_right_align(["5", "120", "7"], nbsp=SP)
    assert out == ["  5", "120", "  7"]


def test_fmt_right_align_empty_cells_stay_empty():
    out = fmt_right_align(["", "12", ""], nbsp=SP)
    assert out[0] == "" and out[2] == ""


# -- fmt_count_paren / fmt_count_paren_bare -----------------------------------


def test_fmt_count_paren_only_paren_cells():
    out = fmt_count_paren(["1 (1.2%)", "0", "11 (3.6%)", "108 (35.3%)"], nbsp=SP)
    # bare "0" untouched; paren cells aligned to a common width.
    assert out[1] == "0"
    paren = [out[0], out[2], out[3]]
    assert len({len(s) for s in paren}) == 1
    assert all(s.endswith(")") for s in paren)


def test_fmt_count_paren_bare_pads_bare_only_with_paren_cells():
    # With paren cells present, the bare "0" is padded into the count field.
    out = fmt_count_paren_bare(["1 (1.2%)", "0", "11 (3.6%)", "108 (35.3%)"], nbsp=SP)
    assert len({len(s) for s in out}) == 1  # every cell the same width
    assert out[1].startswith("  0")


def test_fmt_count_paren_bare_no_paren_column_not_padded_wide():
    # An integer-only column: bare counts right-justify to their own width only
    # (no phantom parenthesis field).
    out = fmt_count_paren_bare(["3", "12"], nbsp=SP)
    assert out == [" 3", "12"]


def test_fmt_count_paren_leaves_continuous_stat():
    out = fmt_count_paren(["75.2 (8.6)", "16 (53.3%)"], nbsp=SP)
    assert out[0] == "75.2 (8.6)"  # count is not a bare integer -> unchanged


# -- as_rtftables integration: align_count_pct / cell_format ------------------


def test_align_count_pct_realigns_columns():
    data = {
        "label": ["Sex", "  Female", "  Male"],
        "a": ["", "16 (53.3)", "14 (46.7)"],
        "b": ["", "1 (5.0)", "12 (100.0)"],
    }
    pages = as_rtftables(data, align_count_pct=True, border="none")
    rows = pages[0].rows
    col_a = [r[1] for r in rows if str(r[1]).strip()]
    assert len({len(s) for s in col_a}) == 1
    assert col_a[0].rstrip("  ").endswith(")")


def test_align_count_pct_false_leaves_untouched():
    data = {"label": ["Sex", "  F"], "a": ["", "5 (33.3)"]}
    pages = as_rtftables(data, border="none")
    assert pages[0].rows[1][1] == "5 (33.3)"


def test_align_count_pct_integer_only_column_untouched():
    data = {"label": ["Group", "  A", "  B"], "n": ["", "3", "12"]}
    pages = as_rtftables(data, align_count_pct=True, border="none")
    assert [r[1] for r in pages[0].rows] == ["", "3", "12"]


def test_align_count_pct_first_column_untouched():
    # The first column (row label) is never reformatted.
    data = {"a": ["5 (33.3)", "6 (44.4)"], "b": ["1 (5.0)", "12 (100.0)"]}
    pages = as_rtftables(data, align_count_pct=True, border="none")
    assert [r[0] for r in pages[0].rows] == ["5 (33.3)", "6 (44.4)"]


def test_cell_format_single_callable():
    data = {"label": ["A", "B"], "v": ["5", "120"]}
    pages = as_rtftables(data, cell_format=fmt_right_align, border="none")
    assert [r[1] for r in pages[0].rows] == ["  5", "120"]


def test_cell_format_takes_precedence_over_align_count_pct():
    data = {"label": ["A", "B"], "v": ["5", "120"]}
    pages = as_rtftables(
        data, cell_format=fmt_right_align, align_count_pct=True, border="none"
    )
    assert [r[1] for r in pages[0].rows] == ["  5", "120"]


def test_cell_format_list_positional():
    data = {"a": ["5", "120"], "b": ["7", "300"]}
    pages = as_rtftables(data, cell_format=[None, fmt_right_align], border="none")
    # Column a (None) untouched; column b right-aligned to width 3.
    assert [r[0] for r in pages[0].rows] == ["5", "120"]
    col_b = [r[1] for r in pages[0].rows]
    assert [len(s) for s in col_b] == [3, 3]
    assert col_b[1] == "300"


def test_cell_format_wrong_length_raises():
    def bad(col):
        return ["only-one"]

    with pytest.raises(ValueError, match="same length"):
        as_rtftables({"label": ["A", "B"], "v": ["1", "2"]}, cell_format=bad,
                     border="none")
