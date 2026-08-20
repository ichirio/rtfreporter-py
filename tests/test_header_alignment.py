"""Column-header alignment cascade (header-alignment)."""

from helpers import render
from rtfreporter import rtftable, style_header


def test_default_header_alignment_center():
    # A non-row-title column defaults to center for both body and header.
    t = rtftable({"A": [1], "B": [2]})
    assert t.col_spec[1].header_align == "center"
    assert "\\qc\\li0\\ri0 B\\cell" in render(t)


def test_row_title_column_header_left():
    # The first (row-title) column defaults to left, and the header follows.
    t = rtftable({"A": [1], "B": [2]})
    assert t.col_spec[0].align == "left"
    assert t.col_spec[0].header_align == "left"
    assert "\\ql\\li0\\ri0 A\\cell" in render(t)


def test_col_header_align_string_broadcast():
    t = rtftable({"A": [1], "B": [2]}, col_header_align="left")
    assert t.col_spec[0].header_align == "left"
    assert t.col_spec[1].header_align == "left"


def test_col_header_align_per_column():
    t = rtftable({"A": [1], "B": [2]}, col_header_align=["left", "right"])
    assert t.col_spec[0].header_align == "left"
    assert t.col_spec[1].header_align == "right"


def test_header_align_inherits_body_align():
    t = rtftable({"A": [1]}, col_spec=[{"col": 0, "align": "right"}])
    # No explicit header_align -> inherits body align.
    assert t.col_spec[0].header_align == "right"


def test_explicit_header_align_wins_over_body():
    t = rtftable(
        {"A": [1]},
        col_spec=[{"col": 0, "align": "right", "header_align": "center"}],
    )
    assert t.col_spec[0].header_align == "center"


def test_col_header_align_overrides_body_align():
    t = rtftable(
        {"A": [1]},
        col_spec=[{"col": 0, "align": "right"}],
        col_header_align="left",
    )
    assert t.col_spec[0].header_align == "left"


def test_style_header_sets_alignment():
    t = style_header(rtftable({"A": [1]}), align="right")
    assert t.col_spec[0].header_align == "right"
    assert "\\qr\\li0\\ri0 A\\cell" in render(t)


def test_header_left_alignment_renders_ql():
    t = rtftable({"A": [1]}, col_header_align="left")
    assert "\\ql\\li0\\ri0 A\\cell" in render(t)


def test_header_bold_flag_renders():
    t = rtftable({"A": [1]}, col_spec=[{"col": 0, "header_bold": True}])
    assert "\\b A\\b0" in render(t)


def test_header_italic_flag_renders():
    t = rtftable({"A": [1]}, col_spec=[{"col": 0, "header_italic": True}])
    assert "\\i A\\i0" in render(t)


def test_body_align_does_not_leak_to_header_render_when_center():
    # An explicit centered body column keeps its header centered too.
    t = rtftable({"A": [1], "B": [2]}, col_spec=[{"col": 1, "align": "center"}])
    rtf = render(t)
    assert "\\qc\\li0\\ri0 B\\cell" in rtf   # header follows center body align
    assert "\\qc\\li0\\ri0 2\\cell" in rtf   # data
