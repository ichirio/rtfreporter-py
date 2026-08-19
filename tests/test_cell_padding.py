"""Cell padding resolution (cell-padding)."""

from helpers import render
from rtfreporter import DefaultFormat, RtfDocument, rtftable


def test_default_padding_zero():
    assert "\\li0\\ri0" in render(rtftable({"A": [1]}))


def test_table_padding_overrides_default():
    t = rtftable({"A": [1]}, cell_padding_left_twips=40, cell_padding_right_twips=50)
    assert "\\li40\\ri50" in render(t)


def test_doc_padding_applied_when_table_unset():
    rtf = render(rtftable({"A": [1]}), doc_pad_l=30, doc_pad_r=35)
    assert "\\li30\\ri35" in render(rtftable({"A": [1]}), doc_pad_l=30, doc_pad_r=35) or "\\li30\\ri35" in rtf


def test_table_padding_wins_over_doc():
    rtf = render(rtftable({"A": [1]}, cell_padding_left_twips=99), doc_pad_l=30, doc_pad_r=0)
    assert "\\li99" in rtf


def test_document_default_format_padding():
    doc = RtfDocument(
        default_format=DefaultFormat(cell_padding_left_twips=25, cell_padding_right_twips=15)
    ).add_table({"A": [1]})
    rtf = doc.to_rtf()
    assert "\\li25\\ri15" in rtf


def test_padding_with_indent_adds():
    from rtfreporter import style_body

    t = style_body(rtftable({"A": [1]}, cell_padding_left_twips=20), indent_twips=100)
    assert "\\li120" in render(t)


def test_header_row_uses_padding():
    t = rtftable({"A": [1]}, cell_padding_left_twips=12, cell_padding_right_twips=8)
    rtf = render(t)
    # header cell also uses li/ri padding
    assert "\\li12\\ri8 A\\cell" in rtf


def test_zero_padding_explicit():
    t = rtftable({"A": [1]}, cell_padding_left_twips=0, cell_padding_right_twips=0)
    assert "\\li0\\ri0" in render(t)
