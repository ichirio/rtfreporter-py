"""Border construction, merge/effective helpers, colour collection, coercion."""

import pytest

import rtfreporter as rr
from rtfreporter.borders import (
    Border,
    TableBorder,
    collect_border_colors,
    collect_table_border_colors,
    effective_row_border,
    merge_border,
    normalize_table_border,
)

# -- BorderSide validation ----------------------------------------------------


def test_border_side_bad_style_raises():
    with pytest.raises(ValueError, match="style"):
        rr.rtf_border_side(style="squiggle")


def test_border_side_zero_width_raises():
    with pytest.raises(ValueError, match="positive"):
        rr.rtf_border_side(width=0)


def test_border_side_none_style_ignores_width():
    side = rr.rtf_border_side(style="none", width=0)
    assert side.style == "none"


def test_border_side_bad_color_raises():
    with pytest.raises(ValueError, match="hex"):
        rr.rtf_border_side(color="red")


def test_border_side_accepts_hex_color():
    assert rr.rtf_border_side(color="#003366").color == "#003366"


# -- constructors -------------------------------------------------------------


def test_rtf_border_box_all_sides():
    b = rr.rtf_border_box()
    assert all(s is not None for s in (b.top, b.bottom, b.left, b.right))


def test_rtf_border_top_only():
    b = rr.rtf_border_top()
    assert b.top is not None and b.bottom is None


def test_rtf_border_none_all_unset():
    b = rr.rtf_border_none()
    assert (b.top, b.bottom, b.left, b.right) == (None, None, None, None)


def test_rtf_border_tfl_header_top_and_bottom():
    tb = rr.rtf_border_tfl()
    assert tb.header.top is not None and tb.header.bottom is not None
    assert tb.body is None


def test_with_sides_replaces_only_supplied():
    b = rr.rtf_border(top=rr.rtf_border_side())
    b2 = b.with_sides(bottom=rr.rtf_border_side(style="double"))
    assert b2.top is b.top
    assert b2.bottom.style == "double"


# -- merge_border / effective_row_border --------------------------------------


def test_merge_border_base_none():
    over = Border(top=rr.rtf_border_side())
    assert merge_border(None, over) is over


def test_merge_border_over_none():
    base = Border(top=rr.rtf_border_side())
    assert merge_border(base, None) is base


def test_merge_border_override_wins_per_side():
    base = Border(top=rr.rtf_border_side(width=15), bottom=rr.rtf_border_side(width=15))
    over = Border(top=rr.rtf_border_side(width=40))
    merged = merge_border(base, over)
    assert merged.top.width == 40
    assert merged.bottom.width == 15  # inherited from base


def test_effective_row_border_over_none_returns_base():
    base = Border(top=rr.rtf_border_side())
    assert effective_row_border(base, None) is base


def test_effective_row_border_base_none_returns_over():
    over = Border(top=rr.rtf_border_side())
    assert effective_row_border(None, over) is over


# -- colour collection --------------------------------------------------------


def test_collect_border_colors_none():
    assert collect_border_colors(None) == []


def test_collect_border_colors_dedupes_by_presence():
    b = Border(
        top=rr.rtf_border_side(color="#111111"),
        bottom=rr.rtf_border_side(color="#222222"),
        left=rr.rtf_border_side(),  # no colour
    )
    assert collect_border_colors(b) == ["#111111", "#222222"]


def test_collect_table_border_colors_across_zones():
    tb = TableBorder(
        header=Border(top=rr.rtf_border_side(color="#AA0000")),
        body=Border(bottom=rr.rtf_border_side(color="#00BB00")),
    )
    assert collect_table_border_colors(tb) == ["#AA0000", "#00BB00"]


def test_collect_table_border_colors_none():
    assert collect_table_border_colors(None) == []


# -- normalize_table_border ---------------------------------------------------


def test_normalize_table_border_none_and_string_none():
    assert normalize_table_border(None) is None
    assert normalize_table_border("none") is None


def test_normalize_table_border_tfl_preset():
    tb = normalize_table_border("tfl")
    assert isinstance(tb, TableBorder) and tb.header is not None


def test_normalize_table_border_unknown_preset_raises():
    with pytest.raises(ValueError, match="Unknown border preset"):
        normalize_table_border("fancy")


def test_normalize_table_border_passthrough_tableborder():
    tb = TableBorder(body=Border(top=rr.rtf_border_side()))
    assert normalize_table_border(tb) is tb


def test_normalize_table_border_border_goes_to_header_zone():
    b = Border(top=rr.rtf_border_side())
    tb = normalize_table_border(b)
    assert tb.header is b


def test_normalize_table_border_bad_type_raises():
    with pytest.raises(TypeError, match="TableBorder"):
        normalize_table_border(123)
