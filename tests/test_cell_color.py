"""Cell text colour and the document colour table (cell-color)."""

from helpers import render
from rtfreporter import RtfDocument, rtftable, style_body
from rtfreporter.render import (
    build_color_index_map,
    build_color_table_rtf,
    collect_report_colors,
)


def test_color_table_base_has_black_and_white():
    out = build_color_table_rtf([])
    assert "\\red0\\green0\\blue0" in out
    assert "\\red255\\green255\\blue255" in out


def test_color_table_entry_rgb():
    out = build_color_table_rtf(["#003366"])
    assert "\\red0\\green51\\blue102" in out


def test_color_table_multiple_entries_order():
    out = build_color_table_rtf(["#FF0000", "#00FF00"])
    assert out.index("\\red255\\green0\\blue0") < out.index("\\red0\\green255\\blue0")


def test_color_index_map_starts_at_three():
    m = build_color_index_map(["#111111", "#222222"])
    assert m == {"#111111": 3, "#222222": 4}


def test_collect_report_colors_dedups_and_skips_bw():
    doc = (
        RtfDocument()
        .add_table(style_body(rtftable({"A": [1]}), color="#003366"))
    )
    colors = collect_report_colors(doc._report())
    assert colors == ["#003366"]


def test_black_and_white_excluded_from_collection():
    doc = RtfDocument().add_table(style_body(rtftable({"A": [1]}), color="#000000"))
    assert collect_report_colors(doc._report()) == []


def test_document_registers_color_and_uses_index():
    doc = RtfDocument().add_table(style_body(rtftable({"A": [1]}), color="#003366"))
    rtf = doc.to_rtf()
    assert "\\red0\\green51\\blue102" in rtf
    assert "\\cf3 1\\cf1 " in rtf  # first custom color -> index 3


def test_body_color_render_helper_has_no_map_by_default():
    # Without a color index map, the color command is omitted.
    t = style_body(rtftable({"A": [1]}), color="#003366")
    assert "\\cf" not in render(t)


def test_two_colors_get_distinct_indices():
    doc = RtfDocument().add_table(
        style_body(style_body(rtftable({"A": [1], "B": [2]}), cols=0, color="#FF0000"),
                   cols=1, color="#00FF00")
    )
    rtf = doc.to_rtf()
    assert "\\cf3 " in rtf and "\\cf4 " in rtf
