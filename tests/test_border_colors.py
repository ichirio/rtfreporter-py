"""Border colour collection and emission (border-colors)."""

from helpers import render
from rtfreporter import (
    Border,
    BorderSide,
    RtfDocument,
    TableBorder,
    rtftable,
)
from rtfreporter.borders import (
    collect_border_colors,
    collect_table_border_colors,
)
from rtfreporter.render import build_border_commands


def test_collect_border_colors_single_side():
    b = Border(bottom=BorderSide(color="#003366"))
    assert collect_border_colors(b) == ["#003366"]


def test_collect_border_colors_multiple_sides():
    b = Border(top=BorderSide(color="#111111"), bottom=BorderSide(color="#222222"))
    assert set(collect_border_colors(b)) == {"#111111", "#222222"}


def test_collect_border_colors_none():
    assert collect_border_colors(None) == []


def test_collect_border_colors_uncolored():
    assert collect_border_colors(Border(top=BorderSide())) == []


def test_collect_table_border_colors_all_zones():
    tb = TableBorder(
        header=Border(top=BorderSide(color="#AAAAAA")),
        body=Border(bottom=BorderSide(color="#BBBBBB")),
    )
    assert set(collect_table_border_colors(tb)) == {"#AAAAAA", "#BBBBBB"}


def test_collect_table_border_colors_none():
    assert collect_table_border_colors(None) == []


def test_build_border_commands_with_color_map():
    b = Border(bottom=BorderSide(color="#003366"))
    out = build_border_commands(b, {"#003366": 3})
    assert "\\brdrcf3" in out


def test_build_border_commands_color_without_map_omitted():
    b = Border(bottom=BorderSide(color="#003366"))
    out = build_border_commands(b)
    assert "\\brdrcf" not in out


def test_document_registers_border_color():
    tb = TableBorder(header=Border(bottom=BorderSide(color="#003366")))
    rtf = RtfDocument().add_table(rtftable({"A": [1]}, border=tb)).to_rtf()
    assert "\\red0\\green51\\blue102" in rtf
    assert "\\brdrcf3" in rtf


def test_colored_border_side_invalid_hex():
    import pytest

    with pytest.raises(ValueError):
        BorderSide(color="003366")  # missing '#'


def test_render_without_map_drops_color_command():
    tb = TableBorder(header=Border(bottom=BorderSide(color="#123456")))
    rtf = render(rtftable({"A": [1]}, border=tb))
    assert "\\brdrcf" not in rtf
