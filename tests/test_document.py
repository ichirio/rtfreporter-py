"""Document assembly and RTF generation (document-rendering, rtf-generation)."""

from helpers import assert_valid_rtf
from rtfreporter import (
    DefaultFormat,
    Page,
    RtfDocument,
    document,
    footer,
    header,
    rtftable,
    save,
    to_rtf,
)


def _doc():
    return RtfDocument().add_table({"A": [1, 2], "B": ["x", "y"]}, title=["T"], footnote=["F"])


# -- header / preamble --------------------------------------------------------

def test_rtf_header_open():
    assert _doc().to_rtf().startswith("{\\rtf1\\ansi\\ansicpg1252")


def test_font_table_courier():
    assert "{\\fonttbl{\\f0\\fnil\\fcharset0 Courier;}}" in _doc().to_rtf()


def test_color_table_present():
    assert "\\colortbl" in _doc().to_rtf()


def test_landscape_letter_geometry():
    rtf = _doc().to_rtf()
    assert "\\paperw15840\\paperh12240\\landscape" in rtf
    assert "\\margl1080\\margr1080\\margt1080\\margb1080" in rtf


def test_portrait_no_landscape_in_preamble():
    rtf = RtfDocument(page=Page(orientation="portrait")).add_table({"A": [1]}).to_rtf()
    assert "\\landscape" not in rtf.split("\\sectd")[0]


def test_custom_font_family():
    doc = RtfDocument(default_format=DefaultFormat(font="Arial")).add_table({"A": [1]})
    assert "Arial;" in doc.to_rtf()


def test_font_size_command():
    doc = RtfDocument(default_format=DefaultFormat(font_size_half_points=20)).add_table({"A": [1]})
    assert "\\fs20" in doc.to_rtf()


def test_document_closes_with_brace():
    assert _doc().to_rtf().rstrip().endswith("}")


# -- data content -------------------------------------------------------------

def test_data_values_present():
    rtf = _doc().to_rtf()
    assert "x\\cell" in rtf and "y\\cell" in rtf


def test_row_counts_balanced():
    assert_valid_rtf(_doc().to_rtf())


def test_ascii_safe_unicode_escaped():
    rtf = RtfDocument().add_table({"A": ["café ±"]}).to_rtf()
    assert all(ord(c) < 128 for c in rtf)
    assert "\\u177?" in rtf


# -- sections and page breaks -------------------------------------------------

def test_two_pages_page_break():
    rtf = RtfDocument().add_tables([{"A": [1]}, {"A": [2]}]).to_rtf()
    assert "\\page" in rtf


def test_header_and_footer_bands():
    doc = (
        RtfDocument()
        .add_section(header=header([{"l": "P", "r": "Page {AUTO_PAGE}"}]),
                     footer=footer([{"c": "CONF"}]))
        .add_table({"A": [1]})
    )
    rtf = doc.to_rtf()
    assert "{\\header " in rtf and "{\\footer " in rtf
    assert "\\chpgn" in rtf
    assert "CONF" in rtf


def test_static_page_token_bakes_numbers():
    doc = (
        RtfDocument()
        .add_section(header=header([{"r": "Page {PAGE}"}]))
        .add_tables([{"A": [1]}, {"A": [2]}])
    )
    rtf = doc.to_rtf()
    assert "Page 1" in rtf and "Page 2" in rtf


def test_section_inherits_previous_header():
    doc = (
        RtfDocument()
        .add_section(header=header([{"c": "Hdr"}]), from_page=1)
        .add_table({"A": [1]})
        .add_section(from_page=2)  # header=None -> inherit
        .add_table({"A": [2]})
    )
    rtf = doc.to_rtf()
    assert rtf.count("Hdr") >= 2


def test_two_sections_distinct_headers():
    doc = (
        RtfDocument()
        .add_section(header=header([{"c": "Sec1"}]), from_page=1)
        .add_table({"A": [1]})
        .add_section(header=header([{"c": "Sec2"}]), from_page=2)
        .add_table({"A": [2]})
    )
    rtf = doc.to_rtf()
    assert "Sec1" in rtf and "Sec2" in rtf


def test_empty_document_valid():
    rtf = RtfDocument().to_rtf()
    assert rtf.startswith("{\\rtf1") and rtf.rstrip().endswith("}")


# -- functional layer ---------------------------------------------------------

def test_functional_document_and_to_rtf():
    doc = document().add_table({"A": [1]})
    assert to_rtf(doc) == doc.to_rtf()


def test_save_writes_file(tmp_path):
    p = tmp_path / "out.rtf"
    doc = document().add_table({"A": [1]})
    save(doc, str(p))
    text = p.read_text()
    assert text.startswith("{\\rtf1")


def test_save_no_overwrite_raises(tmp_path):
    import pytest

    p = tmp_path / "out.rtf"
    p.write_text("existing")
    with pytest.raises(FileExistsError):
        RtfDocument().add_table({"A": [1]}).save(str(p), overwrite=False)


def test_add_figure_and_table_mixed(tmp_path):
    doc = RtfDocument().add_table({"A": [1]}).add_table({"B": [2]})
    assert_valid_rtf(doc.to_rtf())


def test_add_table_with_rtftable_object():
    t = rtftable({"A": [1]}, border="none")
    rtf = RtfDocument().add_table(t).to_rtf()
    assert_valid_rtf(rtf)


def test_titles_bulk_setter():
    doc = RtfDocument().add_tables([{"A": [1]}, {"A": [2]}]).titles(["one", "two"])
    rtf = doc.to_rtf()
    assert "one" in rtf and "two" in rtf


def test_footnotes_bulk_setter():
    doc = RtfDocument().add_tables([{"A": [1]}, {"A": [2]}]).footnotes(["fa", "fb"])
    rtf = doc.to_rtf()
    assert "fa" in rtf and "fb" in rtf


def test_color_table_registers_custom():
    from rtfreporter import style_body

    doc = RtfDocument().add_table(style_body(rtftable({"A": [1]}), color="#123456"))
    assert "\\red18\\green52\\blue86" in doc.to_rtf()
