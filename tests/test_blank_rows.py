"""Blank separator rows: specs, resolution, and rendering (blank-rows, set-blank-rows)."""

import pytest

from helpers import render
from rtfreporter import (
    AFTER_LAST,
    BEFORE_FIRST,
    blank_rows_by_change,
    blank_rows_by_rule,
    rtftable,
)
from rtfreporter.blank_rows import BlankRowsByChange, BlankRowsByRule


def test_integer_position_after_first():
    # 0-based: position 1 = after data row 1 -> internal position 2.
    t = rtftable({"A": [1, 2, 3]}, blank_rows=[1])
    assert t.blank_rows == [2]


def test_before_first_sentinel():
    t = rtftable({"A": [1, 2]}, blank_rows=[BEFORE_FIRST])
    assert 0 in t.blank_rows


def test_after_last_sentinel():
    t = rtftable({"A": [1, 2, 3]}, blank_rows=[AFTER_LAST])
    assert t.blank_rows == [3]


def test_bare_negative_int_raises():
    with pytest.raises(ValueError, match="AFTER_LAST"):
        rtftable({"A": [1, 2, 3]}, blank_rows=[-1])


def test_multiple_positions_sorted_unique():
    # after rows 3 and 1 -> internal 4 and 2.
    t = rtftable({"A": [1, 2, 3, 4]}, blank_rows=[3, 1, 1])
    assert t.blank_rows == [2, 4]


def test_positions_clamped_to_valid_range():
    t = rtftable({"A": [1, 2]}, blank_rows=[99])
    assert t.blank_rows == []  # out of range dropped


def test_by_change_positions():
    t = rtftable({"g": ["A", "A", "B"], "v": [1, 2, 3]}, blank_rows=blank_rows_by_change("g"))
    assert 2 in t.blank_rows


def test_by_change_no_change_no_blank():
    t = rtftable({"g": ["A", "A", "A"]}, blank_rows=blank_rows_by_change("g"))
    assert t.blank_rows == []


def test_by_change_include_before_first():
    spec = blank_rows_by_change("g", include_before_first=True)
    pos = spec.positions(["g"], [["A"], ["A"], ["B"]])
    assert 0 in pos


def test_by_change_include_after_last():
    spec = blank_rows_by_change("g", include_after_last=True)
    pos = spec.positions(["g"], [["A"], ["B"]])
    assert 2 in pos


def test_by_rule_before():
    t = rtftable(
        {"g": ["Sex", "Total"]},
        blank_rows=blank_rows_by_rule("g", "^Total", where="before"),
    )
    assert 1 in t.blank_rows


def test_by_rule_after():
    t = rtftable(
        {"g": ["Total", "Sex"]},
        blank_rows=blank_rows_by_rule("g", "^Total", where="after"),
    )
    assert 1 in t.blank_rows


def test_by_rule_no_match():
    t = rtftable({"g": ["a", "b"]}, blank_rows=blank_rows_by_rule("g", "^Z"))
    assert t.blank_rows == []


def test_by_rule_bad_where_raises():
    import pytest

    spec = BlankRowsByRule("g", "x", where="sideways")
    with pytest.raises(ValueError):
        spec.positions(["g"], [["x"]])


def test_mixed_spec_list_unions_positions():
    t = rtftable(
        {"g": ["A", "A", "B"]},
        blank_rows=[BEFORE_FIRST, blank_rows_by_change("g")],
    )
    assert 0 in t.blank_rows and 2 in t.blank_rows


def test_factory_returns_dataclasses():
    assert isinstance(blank_rows_by_change("g"), BlankRowsByChange)
    assert isinstance(blank_rows_by_rule("g", "x"), BlankRowsByRule)


def test_blank_row_rendered_in_rtf():
    t = rtftable({"A": [1, 2]}, blank_rows=[1])
    rtf = render(t)
    assert "\\trgaph0\\trleft0" in rtf  # blank-row signature


def test_blank_row_before_first_rendered():
    t = rtftable({"A": [1]}, blank_rows=[BEFORE_FIRST])
    rtf = render(t)
    assert rtf.count("\\row") == 3  # header + blank + data


def test_blank_row_height_custom():
    t = rtftable({"A": [1, 2]}, blank_rows=[1], blank_row_height_twips=99)
    assert "\\trrh99" in render(t)


def test_collapse_adjacent_blank_rows():
    # two specs both landing at position 1 collapse to a single blank row
    t = rtftable(
        {"A": [1, 2, 3]},
        blank_rows=[1],
    )
    rtf = render(t)
    # exactly one blank row rendered
    assert rtf.count("\\trgaph0\\trleft0") == 1


def test_detect_empty_row_becomes_blank():
    t = rtftable({"A": ["", ""], "B": ["", ""]})
    rtf = render(t)
    assert "\\trgaph0\\trleft0" in rtf
