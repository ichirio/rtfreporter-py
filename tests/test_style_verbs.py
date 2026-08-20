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


def test_style_body_returns_copy():
    t = rtftable({"A": [1]})
    s = style_body(t, bold=True)
    assert s is not t
    assert t.col_spec[0].bold is False
    assert s.col_spec[0].bold is True


def test_style_body_by_index():
    t = style_body(rtftable({"A": [1], "B": [2]}), cols=1, align="right")
    assert t.col_spec[1].align == "right"
    assert t.col_spec[0].align == "left"  # row-title column default


def test_style_body_by_name():
    t = style_body(rtftable({"A": [1], "B": [2]}), cols="B", bold=True)
    assert t.col_spec[1].bold is True


def test_style_body_all_columns():
    t = style_body(rtftable({"A": [1], "B": [2]}), align="center")
    assert all(s.align == "center" for s in t.col_spec)


def test_style_body_list_of_cols():
    t = style_body(rtftable({"A": [1], "B": [2], "C": [3]}), cols=[0, 2], italic=True)
    assert t.col_spec[0].italic and t.col_spec[2].italic
    assert not t.col_spec[1].italic


def test_style_body_rejects_header_field():
    with pytest.raises(ValueError):
        style_body(rtftable({"A": [1]}), header_align="center")


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
    t = style_header(rtftable({"A": [1]}, border="none"),
                     border=Border(bottom=BorderSide()))
    assert t.col_spec[0].border is not None


def test_style_zone_sets_border():
    t = style_zone(rtftable({"A": [1]}, border="tfl"), "body", Border(top=BorderSide()))
    assert t.border.body is not None


def test_style_zone_invalid_zone():
    with pytest.raises(ValueError):
        style_zone(rtftable({"A": [1]}), "middle", Border())


def test_style_zone_bad_border_type():
    with pytest.raises(TypeError):
        style_zone(rtftable({"A": [1]}), "body", "thick")


def test_style_zone_clear_with_none():
    t = style_zone(rtftable({"A": [1]}, border="tfl"), "header", None)
    assert t.border.header is None


def test_chained_verbs_compose():
    t = rtftable({"A": [1], "B": [2]})
    t2 = style_header(style_body(t, cols=1, align="right"), bold=True)
    assert t2.col_spec[1].align == "right"
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
    t = style_zone(rtftable({"A": [1, 2]}, border="tfl"), "last_row",
                   Border(bottom=BorderSide("double", 20)))
    assert "\\brdrdb" in render(t)
