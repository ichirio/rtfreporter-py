"""Body-cell formatting emission (cell-format)."""

from helpers import render
from rtfreporter import rtftable, style_body
from rtfreporter.render import build_cell_content


def test_plain_cell_left_no_decoration():
    assert build_cell_content("x") == "\\ql\\li0\\ri0 x\\cell"


def test_align_right():
    assert build_cell_content("x", align="right").startswith("\\qr")


def test_align_center():
    assert build_cell_content("x", align="center").startswith("\\qc")


def test_unknown_align_defaults_left():
    assert build_cell_content("x", align="???").startswith("\\ql")


def test_bold_wraps_text():
    assert "\\b x\\b0 " in build_cell_content("x", bold=True)


def test_italic_wraps_text():
    assert "\\i x\\i0 " in build_cell_content("x", italic=True)


def test_underline_wraps_text():
    assert "\\ul x\\ulnone " in build_cell_content("x", underline=True)


def test_all_decorations_nested():
    out = build_cell_content("x", bold=True, italic=True, underline=True)
    assert "\\b " in out and "\\i " in out and "\\ul " in out


def test_indent_added_to_li():
    out = build_cell_content("x", indent_twips=120, pad_l=30)
    assert "\\li150" in out  # 120 + 30


def test_padding_left_right():
    out = build_cell_content("x", pad_l=44, pad_r=55)
    assert "\\li44\\ri55" in out


def test_color_index_wraps():
    out = build_cell_content("x", color_idx=5)
    assert "\\cf5 x\\cf1 " in out


def test_data_row_bold_via_style_body():
    t = style_body(rtftable({"A": [1]}), bold=True)
    assert "\\b 1\\b0" in render(t)


def test_data_row_right_align_via_style_body():
    t = style_body(rtftable({"A": [1]}), align="right")
    assert "\\qr\\li0\\ri0 1\\cell" in render(t)


def test_data_row_indent():
    t = style_body(rtftable({"A": [1]}), indent_twips=200)
    assert "\\li200" in render(t)


def test_data_row_underline_and_italic():
    t = style_body(rtftable({"A": [1]}), underline=True, italic=True)
    rtf = render(t)
    assert "\\ul " in rtf and "\\i " in rtf


def test_numeric_values_stringified():
    t = rtftable({"A": [3.14]})
    assert "3.14\\cell" in render(t)


def test_none_value_renders_empty_cell():
    # Keep the row non-empty (else blank-row detection collapses it).
    t = rtftable({"A": [None], "B": ["x"]})
    assert "\\ql\\li0\\ri0 \\cell" in render(t)


def test_special_chars_escaped_in_body():
    t = rtftable({"A": ["a{b}c\\d"]})
    assert "a\\{b\\}c\\\\d" in render(t)
