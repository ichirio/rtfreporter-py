"""Page geometry, orientation, and text width (rtf-page, page-orientation, text-width)."""

import pytest

from rtfreporter import Page, rtftable
from rtfreporter.page import DefaultFormat
from rtfreporter.render import compute_cellx, content_width_twips

# -- geometry -----------------------------------------------------------------

def test_letter_landscape_default():
    g = Page().geometry()
    assert g["orientation"] == "landscape"
    assert g["width_twips"] == 15840 and g["height_twips"] == 12240


def test_letter_portrait():
    g = Page(orientation="portrait").geometry()
    assert g["orientation"] == "portrait"
    assert g["width_twips"] == 12240 and g["height_twips"] == 15840


def test_legal_landscape():
    g = Page(paper_size="legal").geometry()
    assert g["width_twips"] == 20160  # 14in


def test_a4_portrait():
    g = Page(paper_size="a4", orientation="portrait").geometry()
    assert g["width_twips"] == 11905 and g["height_twips"] == 16838


def test_a3_dimensions():
    g = Page(paper_size="a3", orientation="portrait").geometry()
    assert g["height_twips"] == pytest.approx(23811, abs=2)


def test_default_margins_075in():
    g = Page().geometry()
    assert g["margin_left_twips"] == 1080
    assert g["margin_top_twips"] == 1080


def test_custom_margins():
    g = Page(margin_left_in=1.0, margin_right_in=0.5).geometry()
    assert g["margin_left_twips"] == 1440
    assert g["margin_right_twips"] == 720


def test_explicit_width_height_infers_landscape():
    g = Page(width_in=11.0, height_in=8.5).geometry()
    assert g["orientation"] == "landscape"


def test_explicit_width_height_infers_portrait():
    g = Page(width_in=8.5, height_in=11.0).geometry()
    assert g["orientation"] == "portrait"


def test_header_footer_distance_defaults_to_margin():
    g = Page().geometry()
    assert g["header_dist_twips"] == g["margin_top_twips"]
    assert g["footer_dist_twips"] == g["margin_bottom_twips"]


def test_explicit_header_dist():
    g = Page(header_dist_in=0.5).geometry()
    assert g["header_dist_twips"] == 720


def test_bad_orientation_raises():
    with pytest.raises(ValueError):
        Page(orientation="sideways")


def test_unknown_paper_size_raises():
    with pytest.raises(ValueError):
        Page(paper_size="tabloid").geometry()


# -- column widths / text width -----------------------------------------------

def test_equal_widths_split():
    t = rtftable({"A": [1], "B": [1]})
    assert compute_cellx(2, 10000, t) == [5000, 10000]


def test_last_column_absorbs_rounding():
    t = rtftable({"A": [1], "B": [1], "C": [1]})
    cx = compute_cellx(3, 10000, t)
    assert cx[-1] == 10000


def test_relative_widths():
    t = rtftable({"A": [1], "B": [1], "C": [1]}, col_rel_width=[2, 1, 1], table_width_twips=8000)
    cx = compute_cellx(3, 10000, t)
    assert cx[0] == 4000 and cx[-1] == 8000


def test_absolute_widths():
    t = rtftable({"A": [1], "B": [1]}, column_widths_twips=[2880, 1440])
    assert compute_cellx(2, 10000, t) == [2880, 4320]


def test_table_width_pct():
    t = rtftable({"A": [1], "B": [1]}, table_width_pct=50)
    cx = compute_cellx(2, 10000, t)
    assert cx[-1] == 5000


def test_content_width_of_table():
    t = rtftable({"A": [1], "B": [1]}, table_width_twips=6000)
    assert content_width_twips(t, 10000) == 6000


def test_content_width_default_full_writable():
    t = rtftable({"A": [1]})
    assert content_width_twips(t, 9000) == 9000


def test_rel_width_must_be_positive():
    t = rtftable({"A": [1], "B": [1]}, col_rel_width=[1, 1])
    t.col_rel_width = [1.0, -1.0]
    with pytest.raises(ValueError):
        compute_cellx(2, 10000, t)


# -- DefaultFormat ------------------------------------------------------------

def test_default_format_font_courier():
    assert DefaultFormat().font == "Courier"


def test_default_format_font_size_18():
    assert DefaultFormat().font_size_half_points == 18


def test_default_format_bad_font_size():
    with pytest.raises(ValueError):
        DefaultFormat(font_size_half_points=0)


def test_default_format_bad_title_format():
    with pytest.raises(ValueError):
        DefaultFormat(title_format="fancy")
