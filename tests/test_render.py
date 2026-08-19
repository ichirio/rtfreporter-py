"""Tests for the renderer output structure and the document driver."""

from helpers import assert_valid_rtf
from rtfreporter import (
    DefaultFormat,
    Page,
    RtfDocument,
    col_cell,
    footer,
    header,
    rtftable,
)
from rtfreporter.render import compute_cellx


def _simple_doc():
    return RtfDocument().add_table(
        {"A": [1, 2], "B": ["x", "y"]}, title=["T"], footnote=["F"]
    )


def test_document_header_tokens():
    rtf = _simple_doc().to_rtf()
    assert rtf.startswith("{\\rtf1\\ansi\\ansicpg1252")
    assert r"{\fonttbl{\f0\fnil\fcharset0 Courier;}}" in rtf
    assert r"\colortbl" in rtf


def test_landscape_letter_geometry():
    rtf = _simple_doc().to_rtf()
    # 11 x 8.5 in landscape = 15840 x 12240 twips; 0.75" margins = 1080 twips.
    assert r"\paperw15840\paperh12240\landscape" in rtf
    assert r"\margl1080\margr1080\margt1080\margb1080" in rtf


def test_portrait_a4_geometry():
    doc = RtfDocument(page=Page(paper_size="a4", orientation="portrait")).add_table({"A": [1]})
    rtf = doc.to_rtf()
    assert r"\landscape" not in rtf.split(r"\sectd")[0]
    # A4 portrait ~ 11905 x 16838 twips.
    assert r"\paperw11905\paperh16838" in rtf


def test_table_rows_and_cells_balanced():
    rtf = _simple_doc().to_rtf()
    assert_valid_rtf(rtf)
    # header row + 2 data rows = 3 \trowd for the table (plus maybe title/footnote)
    assert rtf.count(r"\trowd") >= 3


def test_data_row_values_present():
    rtf = _simple_doc().to_rtf()
    assert r"x\cell" in rtf and r"y\cell" in rtf


def test_header_footer_bands():
    doc = (
        RtfDocument()
        .add_section(
            header=header([{"l": "Proto", "r": "Page {AUTO_PAGE}"}]),
            footer=footer([{"c": "CONF"}]),
        )
        .add_table({"A": [1]})
    )
    rtf = doc.to_rtf()
    assert r"{\header " in rtf and r"{\footer " in rtf
    assert r"\chpgn" in rtf
    assert "CONF" in rtf


def test_pagination_multiple_pages_page_break():
    doc = RtfDocument().add_tables([{"A": [1]}, {"A": [2]}])
    rtf = doc.to_rtf()
    assert r"\page" in rtf  # page break between the two pages


def test_sections_use_section_break():
    doc = (
        RtfDocument()
        .add_section(header=header([{"c": "Sec1"}]), from_page=1)
        .add_table({"A": [1]})
        .add_section(header=header([{"c": "Sec2"}]), from_page=2)
        .add_table({"A": [2]})
    )
    rtf = doc.to_rtf()
    assert r"\sect" in rtf
    assert "Sec1" in rtf and "Sec2" in rtf


def test_static_page_token_promotes_to_sections():
    doc = (
        RtfDocument()
        .add_section(header=header([{"r": "Page {PAGE}"}]))
        .add_tables([{"A": [1]}, {"A": [2]}])
    )
    rtf = doc.to_rtf()
    # Each sub-page gets its own section so {PAGE} bakes a distinct number.
    assert "Page 1" in rtf and "Page 2" in rtf


def test_compute_cellx_relative_widths():
    tbl = rtftable({"A": [1], "B": [1], "C": [1]}, col_rel_width=[2, 1, 1], table_width_twips=8000)
    cellx = compute_cellx(3, 10000, tbl)
    assert cellx[-1] == 8000  # last absorbs rounding drift
    assert cellx[0] == 4000


def test_compute_cellx_absolute_widths():
    tbl = rtftable({"A": [1], "B": [1]}, column_widths_twips=[2880, 1440])
    assert compute_cellx(2, 10000, tbl) == [2880, 4320]


def test_font_size_default_format():
    doc = RtfDocument(default_format=DefaultFormat(font_size_half_points=20)).add_table({"A": [1]})
    rtf = doc.to_rtf()
    assert r"\fs20" in rtf


def test_spanning_header_group_underline():
    tbl = rtftable(
        {"Base": ["Low"], "A1": [1], "A2": [2], "B1": [3], "B2": [4]},
        col_header=[
            [col_cell((1, 2), "Grp A"), col_cell((3, 4), "Grp B")],
            ["Base", "n", "pct", "n", "pct"],
        ],
        border="tfl",
    )
    rtf = RtfDocument().add_table(tbl).to_rtf()
    # The multi-column spanning cell gets a bottom rule (group underline).
    assert "Grp A" in rtf
    assert r"\clbrdrb\brdrs" in rtf
    assert_valid_rtf(rtf)


def test_none_border_document():
    rtf = RtfDocument().add_table(rtftable({"A": [1]}, border="none")).to_rtf()
    assert_valid_rtf(rtf)
    # No cell borders drawn anywhere in the body.
    body = rtf.split(r"\sectd")[-1]
    assert r"\clbrdr" not in body
