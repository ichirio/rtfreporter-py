"""Header/zone border emission (header-borders)."""

from helpers import render
from rtfreporter import (
    Border,
    BorderSide,
    TableBorder,
    col_cell,
    rtftable,
    style_zone,
)


def test_tfl_header_single_row_has_top_and_bottom():
    rtf = render(rtftable({"A": [1]}, border="tfl"))
    assert "\\clbrdrt\\brdrs\\brdrw15" in rtf
    assert "\\clbrdrb\\brdrs\\brdrw15" in rtf


def test_none_border_no_cell_borders():
    rtf = render(rtftable({"A": [1]}, border="none"))
    assert "\\clbrdr" not in rtf


def test_top_rule_only_on_first_header_row():
    t = rtftable(
        {"A": [1], "B": [2]},
        col_header=[["top1", "top2"], ["bot1", "bot2"]],
        border=TableBorder(header=Border(top=BorderSide(), bottom=BorderSide())),
    )
    rtf = render(t)
    rows = rtf.split("\\row")
    # first header row: top present
    assert "\\clbrdrt" in rows[0]
    # bottom rule only on the last header row (rows[1])
    assert "\\clbrdrb" not in rows[0]
    assert "\\clbrdrb" in rows[1]


def test_body_zone_border_on_data_rows():
    t = rtftable({"A": [1], "B": [2]}, border=TableBorder(body=Border(bottom=BorderSide())))
    rtf = render(t)
    # both data rows get the body border
    assert rtf.count("\\clbrdrb\\brdrs") >= 2


def test_first_row_override():
    t = rtftable(
        {"A": [1, 2]},
        border=TableBorder(first_row=Border(top=BorderSide("double"))),
    )
    rtf = render(t)
    assert "\\brdrdb" in rtf


def test_last_row_override_double():
    t = style_zone(
        rtftable({"A": [1, 2, 3]}, border="tfl"),
        "last_row",
        Border(bottom=BorderSide("double", 20)),
    )
    rtf = render(t)
    assert "\\clbrdrb\\brdrdb\\brdrw20" in rtf


def test_spanning_group_underline_present():
    t = rtftable(
        {"A": [1], "B": [2], "C": [3]},
        col_header=[[col_cell((0, 1), "Grp")], ["A", "B", "C"]],
        border="tfl",
    )
    rtf = render(t)
    # the multi-column spanning cell gets a bottom rule (group underline)
    assert "\\clbrdrb\\brdrs" in rtf


def test_spanning_single_cell_no_group_underline_forced():
    # A one-column "span" is not multi-col, so no forced group underline zone.
    t = rtftable(
        {"A": [1], "B": [2]},
        col_header=[[col_cell(0, "x"), col_cell(1, "y")], ["A", "B"]],
        border="none",
    )
    rtf = render(t)
    assert "\\clbrdr" not in rtf


def test_thick_style_command():
    t = rtftable({"A": [1]}, border=TableBorder(header=Border(top=BorderSide("thick"))))
    assert "\\brdrth" in render(t)


def test_dash_and_dot_styles():
    t1 = rtftable({"A": [1]}, border=TableBorder(header=Border(top=BorderSide("dash"))))
    t2 = rtftable({"A": [1]}, border=TableBorder(header=Border(top=BorderSide("dot"))))
    assert "\\brdrdash" in render(t1)
    assert "\\brdrdot" in render(t2)


def test_border_width_reflected():
    t = rtftable({"A": [1]}, border=TableBorder(header=Border(bottom=BorderSide(width=40))))
    assert "\\brdrw40" in render(t)


def test_explicit_none_side_omitted():
    t = rtftable(
        {"A": [1]},
        border=TableBorder(header=Border(top=BorderSide("none"), bottom=BorderSide())),
    )
    rtf = render(t)
    assert "\\clbrdrt" not in rtf
    assert "\\clbrdrb\\brdrs" in rtf
