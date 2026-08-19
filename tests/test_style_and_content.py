"""Tests for style verbs, titles/footnotes, figures, and blank-row specs."""

import struct
import zlib

from helpers import assert_valid_rtf
from rtfreporter import (
    Border,
    BorderSide,
    RtfDocument,
    blank_rows_by_change,
    blank_rows_by_rule,
    rtfplot,
    rtftable,
    style_body,
    style_cols,
    style_header,
    style_zone,
)
from rtfreporter.render import render_rtftable


def _render(tbl):
    return "".join(render_rtftable(tbl, 12000))


def test_style_body_bold_returns_copy():
    tbl = rtftable({"A": [1], "B": [2]})
    styled = style_body(tbl, cols=0, bold=True)
    assert styled is not tbl
    assert styled.col_spec[0].bold is True
    assert tbl.col_spec[0].bold is False  # original untouched
    assert r"\b " in _render(styled)


def test_style_cols_align():
    tbl = rtftable({"A": [1], "B": [2]})
    styled = style_cols(tbl, cols="B", align="right")
    assert styled.col_spec[1].align == "right"
    assert r"\qr" in _render(styled)


def test_style_header_align_and_bold():
    tbl = rtftable({"A": [1]})
    styled = style_header(tbl, align="center", bold=True)
    assert styled.col_spec[0].header_align == "center"
    assert styled.col_spec[0].header_bold is True


def test_style_zone_sets_body_border():
    tbl = rtftable({"A": [1]}, border="tfl")
    styled = style_zone(tbl, "last_row", Border(bottom=BorderSide("double", 20)))
    assert styled.border.last_row is not None
    assert r"\brdrdb" in _render(styled)


def test_title_renders_as_paragraph():
    doc = RtfDocument().add_table({"A": [1]}, title=["My Title"])
    rtf = doc.to_rtf()
    assert r"\pard\qc" in rtf  # centered title paragraph
    assert "My Title" in rtf


def test_footnote_table_has_separator_rule():
    doc = RtfDocument().add_table({"A": [1]}, footnote=["Source: X"])
    rtf = doc.to_rtf()
    # footnote default format is a content-width table with a top rule.
    assert "Source: X" in rtf
    assert r"\clbrdrt\brdrs" in rtf


def test_blank_rows_by_change_positions():
    tbl = rtftable(
        {"grp": ["A", "A", "B"], "v": [1, 2, 3]},
        blank_rows=blank_rows_by_change("grp"),
    )
    assert 2 in tbl.blank_rows


def test_blank_rows_by_rule_before():
    tbl = rtftable(
        {"grp": ["Sex", "Total"], "v": [1, 2]},
        blank_rows=blank_rows_by_rule("grp", "^Total", where="before"),
    )
    assert 1 in tbl.blank_rows


def test_blank_rows_integer_positions():
    tbl = rtftable({"A": [1, 2, 3]}, blank_rows=[0, -1])
    assert 0 in tbl.blank_rows and 3 in tbl.blank_rows


def _make_png(path, width, height, dpi=None):
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    out = sig + chunk(b"IHDR", ihdr)
    if dpi:
        ppm = int(round(dpi / 0.0254))
        out += chunk(b"pHYs", struct.pack(">IIB", ppm, ppm, 1))
    raw = b"\x00" + b"\x00\x00\x00" * width
    out += chunk(b"IDAT", zlib.compress(raw * height))
    out += chunk(b"IEND", b"")
    path.write_bytes(out)


def test_figure_png_native_dpi(tmp_path):
    p = tmp_path / "fig.png"
    _make_png(p, 300, 150, dpi=150)
    fig = rtfplot(str(p))
    assert fig.img_type == "png" and fig.img_width == 300
    assert round(fig.dpi_x) == 150
    disp = fig.display_twips()
    assert disp["w"] == int(round(300 / 150 * 1440))  # 2880 twips = 2 inches


def test_figure_explicit_width(tmp_path):
    p = tmp_path / "fig.png"
    _make_png(p, 300, 150)
    fig = rtfplot(str(p), width_twips=7200)
    assert fig.display_twips()["w"] == 7200


def test_figure_embedded_in_document(tmp_path):
    p = tmp_path / "fig.png"
    _make_png(p, 100, 100, dpi=96)
    doc = RtfDocument().add_figure(str(p), width_twips=5000, title=["Figure 1"])
    rtf = doc.to_rtf()
    assert r"\pngblip" in rtf
    assert_valid_rtf(rtf)
