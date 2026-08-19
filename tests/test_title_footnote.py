"""Title and footnote rendering (title-footnote)."""

from helpers import assert_valid_rtf
from rtfreporter import DefaultFormat, RtfDocument, rtftable


def test_title_text_centered_paragraph():
    rtf = RtfDocument().add_table({"A": [1]}, title=["My Title"]).to_rtf()
    assert "\\pard\\qc" in rtf
    assert "My Title" in rtf


def test_title_multiple_lines():
    rtf = RtfDocument().add_table({"A": [1]}, title=["L1", "L2", "L3"]).to_rtf()
    assert "L1" in rtf and "L2" in rtf and "L3" in rtf


def test_title_blank_line_kept():
    rtf = RtfDocument().add_table({"A": [1]}, title=["A", "", "B"]).to_rtf()
    # blank title line -> an empty paragraph
    assert rtf.count("\\par") >= 3


def test_footnote_table_has_top_rule():
    rtf = RtfDocument().add_table({"A": [1]}, footnote=["Source: X"]).to_rtf()
    assert "Source: X" in rtf
    assert "\\clbrdrt\\brdrs" in rtf


def test_footnote_default_format_is_table():
    # footnote renders as a bordered content-width table cell/row
    rtf = RtfDocument().add_table({"A": [1]}, footnote=["note text"]).to_rtf()
    assert "note text\\cell" in rtf


def test_title_as_string():
    rtf = RtfDocument().add_table({"A": [1]}, title="Solo").to_rtf()
    assert "Solo" in rtf


def test_footnote_text_format_option():
    doc = RtfDocument(
        default_format=DefaultFormat(footnote_format="text")
    ).add_table({"A": [1]}, footnote=["note"])
    rtf = doc.to_rtf()
    assert "note" in rtf


def test_title_table_format_option():
    doc = RtfDocument(
        default_format=DefaultFormat(title_format="table")
    ).add_table({"A": [1]}, title=["Titled"])
    rtf = doc.to_rtf()
    assert "Titled" in rtf


def test_title_dict_row_bold_default():
    rtf = RtfDocument().add_table({"A": [1]}, title=[{"text": "Bold?"}]).to_rtf()
    assert "\\b Bold?\\b0" in rtf


def test_title_dict_align_left():
    rtf = RtfDocument().add_table(
        {"A": [1]}, title=[{"text": "Left", "align": "left"}]
    ).to_rtf()
    assert "\\pard\\ql" in rtf


def test_footnote_dict_underline():
    doc = RtfDocument(
        default_format=DefaultFormat(footnote_format="text")
    ).add_table({"A": [1]}, footnote=[{"text": "u", "underline": True}])
    assert "\\ul " in doc.to_rtf()


def test_title_and_footnote_valid_rtf():
    rtf = RtfDocument().add_table(
        {"A": [1]}, title=["T", "", "T2"], footnote=["F1", "F2"]
    ).to_rtf()
    assert_valid_rtf(rtf)


def test_no_title_no_footnote_still_valid():
    assert_valid_rtf(RtfDocument().add_table({"A": [1]}).to_rtf())


def test_title_special_chars_escaped():
    rtf = RtfDocument().add_table({"A": [1]}, title=["a{b}"]).to_rtf()
    assert "a\\{b\\}" in rtf


def test_table_titles_attribute_used_as_default():
    t = rtftable({"A": [1]})
    t.titles = ["FromTable"]
    rtf = RtfDocument().add_table(t).to_rtf()
    assert "FromTable" in rtf
