"""Spanning-header alignment and decoration (spanning-align)."""

from helpers import render
from rtfreporter import col_cell, rtftable


def _span_table(**cell_kwargs):
    return rtftable(
        {"A": [1], "B": [2], "C": [3]},
        col_header=[[col_cell((0, 1), "Span", **cell_kwargs), col_cell(2, "C")], ["A", "B", "C"]],
        border="none",
    )


def test_span_default_center():
    assert "\\qc\\li0\\ri0 Span\\cell" in render(_span_table())


def test_span_explicit_left():
    assert "\\ql\\li0\\ri0 Span\\cell" in render(_span_table(align="left"))


def test_span_explicit_right():
    assert "\\qr\\li0\\ri0 Span\\cell" in render(_span_table(align="right"))


def test_span_inherits_header_align():
    t = rtftable(
        {"A": [1], "B": [2]},
        col_header=[[col_cell((0, 1), "S")], ["A", "B"]],
        col_header_align="left",
        border="none",
    )
    assert "\\ql\\li0\\ri0 S\\cell" in render(t)


def test_span_bold():
    assert "\\b Span\\b0" in render(_span_table(bold=True))


def test_span_italic():
    assert "\\i Span\\i0" in render(_span_table(italic=True))


def test_span_underline():
    assert "\\ul Span\\ulnone" in render(_span_table(underline=True))


def test_span_bold_and_italic_combined():
    rtf = render(_span_table(bold=True, italic=True))
    assert "\\b " in rtf and "\\i " in rtf


def test_uncovered_column_gets_empty_cell():
    # column C is a single cell in the span row -> empty label cell
    t = rtftable(
        {"A": [1], "B": [2], "C": [3]},
        col_header=[[col_cell((0, 1), "AB")], ["A", "B", "C"]],
        border="none",
    )
    rtf = render(t)
    assert "\\ql\\li0\\ri0 \\cell" in rtf  # the filler empty cell


def test_span_label_escaped():
    t = _span_table()
    t.col_header[0].spans[0].label = "a{b}"
    assert "a\\{b\\}" in render(t)
