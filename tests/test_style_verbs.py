"""Post-hoc style verbs (style-verbs, styles)."""

import pytest

from helpers import render
from rtfreporter import (
    Border,
    BorderSide,
    rtftable,
    style_body,
    style_cols,
    style_header,
    style_zone,
)


def _cs(t, key, row=0):
    return t.cell_styles[row][key]


def test_style_body_returns_copy():
    t = rtftable({"A": [1]})
    s = style_body(t, bold=True)
    assert s is not t
    assert t.cell_styles is None
    assert _cs(s, "bold") == [True]


def test_style_body_by_index():
    t = style_body(rtftable({"A": [1], "B": [2]}), cols=1, align="right")
    assert _cs(t, "align") == [None, "right"]


def test_style_body_by_name():
    t = style_body(rtftable({"A": [1], "B": [2]}), cols="B", bold=True)
    assert _cs(t, "bold") == [None, True]


def test_style_body_all_columns():
    t = style_body(rtftable({"A": [1], "B": [2]}), align="center")
    assert _cs(t, "align") == ["center", "center"]


def test_style_body_list_of_cols():
    t = style_body(rtftable({"A": [1], "B": [2], "C": [3]}), cols=[0, 2], italic=True)
    assert _cs(t, "italic") == [True, None, True]


def test_style_body_rejects_header_field():
    with pytest.raises(TypeError):
        style_body(rtftable({"A": [1]}), header_align="center")


def test_style_body_rows():
    t = rtftable({"Stat": ["n", "Mean", "SD"], "V": ["1", "2", "3"]})
    by_pos = style_body(t, rows=[1], bold=True)
    assert by_pos.cell_styles[0] is None and _cs(by_pos, "bold", 1) == [True, True]
    by_pred = style_body(t, rows=lambda r: r["Stat"] == "SD", background="#FFFF00")
    assert _cs(by_pred, "background", 2) == ["#FFFF00", "#FFFF00"]
    by_bool = style_body(t, rows=[True, False, True], cols="V", color="#FF0000")
    assert _cs(by_bool, "color", 2) == [None, "#FF0000"]
    with pytest.raises(ValueError, match="positions"):
        style_body(t, rows=[5], bold=True)
    with pytest.raises(ValueError, match="length 3"):
        style_body(t, rows=[True], bold=True)
    with pytest.raises(ValueError, match="ambiguous"):
        style_body([t, t], rows=[0], bold=True)
    pages = style_body([t, t], rows=lambda r: r["Stat"] == "n", bold=True)
    assert all(_cs(p, "bold", 0) == [True, True] for p in pages)


def test_style_cols_accepts_both():
    t = style_cols(rtftable({"A": [1]}), align="right", header_align="center")
    assert t.col_spec[0].align == "right"
    assert t.col_spec[0].header_align == "center"


def test_style_cols_unknown_field():
    with pytest.raises(ValueError):
        style_cols(rtftable({"A": [1]}), wiggle=True)


def test_style_header_maps_fields():
    t = style_header(rtftable({"A": [1]}), align="left", bold=True, italic=True)
    assert t.col_spec[0].header_align == "left"
    assert t.col_spec[0].header_bold is True
    assert t.col_spec[0].header_italic is True


def test_style_header_border():
    t = style_header(rtftable({"A": [1], "B": [2]}, border="none"), cols="B",
                     border=Border(bottom=BorderSide()))
    row = t.col_header[0]
    assert row.kind == "spanning"
    assert row.spans[0].border is None and row.spans[1].border is not None


def test_style_header_row_and_label():
    t = rtftable({"A": [1], "B": [2]}, col_header=[["x", "y"], ["a", "b"]])
    t2 = style_header(t, row=1, cols="B", label="Beta")
    assert t2.col_header[1].labels == ["a", "Beta"] and t2.col_header[0].labels == ["x", "y"]
    with pytest.warns(UserWarning, match="shared by ALL label rows"):
        style_header(t, row=0, bold=True)
    with pytest.raises(ValueError, match="row="):
        style_header(t, row=2, bold=True)


def test_style_zone_sets_border():
    t = style_zone(rtftable({"A": [1]}, border="tfl"), body=Border(top=BorderSide()))
    assert t.border.body is not None


def test_style_zone_invalid_zone():
    with pytest.raises(TypeError):
        style_zone(rtftable({"A": [1]}), middle=Border())


def test_style_zone_bad_border_type():
    with pytest.raises(TypeError):
        style_zone(rtftable({"A": [1]}), "body", "thick")


def test_style_zone_merges_side_by_side():
    # R #348: layering happens where a border is attached -- a second call
    # adds to the first instead of replacing it.
    t = style_zone(rtftable({"A": [1]}, border="tfl"), header=Border(left=BorderSide("double")))
    assert t.border.header.top == BorderSide()          # kept from "tfl"
    assert t.border.header.left == BorderSide("double")  # added
    assert style_zone(t).border == t.border             # nothing named: unchanged


def test_chained_verbs_compose():
    t = rtftable({"A": [1], "B": [2]})
    t2 = style_header(style_body(t, cols=1, align="right"), bold=True)
    assert t2.cell_styles[0]["align"] == [None, "right"]
    assert t2.col_spec[0].header_bold is True
    # original untouched (col B keeps its center default)
    assert t.col_spec[1].align == "center"


def test_style_body_unknown_column_raises():
    with pytest.raises(ValueError):
        style_body(rtftable({"A": [1]}), cols="Z", bold=True)


def test_style_body_index_out_of_range():
    with pytest.raises(ValueError):
        style_body(rtftable({"A": [1]}), cols=5, bold=True)


def test_style_zone_double_renders():
    t = style_zone(rtftable({"A": [1, 2]}, border="tfl"),
                   last_row=Border(bottom=BorderSide("double", 20)))
    assert "\\brdrdb" in render(t)
