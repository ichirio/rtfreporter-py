"""The rounding rule (num_format.py) and the per-element style checks
(element_style.py), exercised directly."""

import math

import pytest

from rtfreporter import element_style as es
from rtfreporter import num_format as nf
from rtfreporter import rtfreporter_options

# -- rounding -----------------------------------------------------------------


def test_round_num_halves_follow_the_rule():
    assert nf.round_num([0.5, 1.5, 2.5, -0.5]) == [0.0, 2.0, 2.0, -0.0]
    assert nf.round_num([0.5, 1.5, 2.5, -0.5], rounding="sas") == [1.0, 2.0, 3.0, -1.0]
    # SAS fuzz: 2.675 is stored as 2.67499..., SAS still gives 2.68
    assert nf.round_num(2.675, 2, rounding="sas") == 2.68


def test_round_num_passes_none_nan_inf_and_zero():
    assert nf.round_num(None) is None
    assert math.isnan(nf.round_num(float("nan"), rounding="sas"))
    assert math.isnan(nf.round_num(float("nan")))
    assert nf.round_num(float("inf"), rounding="sas") == float("inf")
    assert nf.round_num(float("-inf")) == float("-inf")
    assert nf.round_num(0, rounding="sas") == 0.0
    assert nf.round_num((1.25, None), 1, rounding="sas") == [1.3, None]


def test_round_num_refuses_non_numbers_and_bad_digits():
    with pytest.raises(TypeError, match="numeric"):
        nf.round_num("1.5")
    with pytest.raises(TypeError, match="numeric"):
        nf.round_num(True)
    for bad in (-1, "x", None, True):
        with pytest.raises(ValueError, match="non-negative integer"):
            nf.round_num(1.5, digits=bad)


def test_rounding_type_reads_the_option_and_checks_it():
    assert nf.rounding_type("r") == "r"
    assert nf.rounding_type("sas") == "sas"
    old = rtfreporter_options()["rounding"]
    try:
        rtfreporter_options(rounding="sas")
        assert nf.rounding_type() == "sas"
        assert nf.round_num(0.5) == 1.0          # the option decides ...
        assert nf.round_num(0.5, rounding="r") == 0.0   # ... an explicit value wins
    finally:
        rtfreporter_options(rounding=old)
    for bad in ("R", "even", 1):
        with pytest.raises(ValueError, match="rounding"):
            nf.rounding_type(bad)


# -- per-element style ---------------------------------------------------------


def test_font_size_row_height_align_checks():
    assert es.check_font_size(None, "a") is None
    assert es.check_font_size(16, "a") == 16
    for bad in (0, -2, "x", True):
        with pytest.raises(ValueError, match="positive integer"):
            es.check_font_size(bad, "a")
    assert es.check_row_height(None, "b") is None
    assert es.check_row_height(0, "b") == 0
    for bad in (-1, "x", False):
        with pytest.raises(ValueError, match="non-negative integer"):
            es.check_row_height(bad, "b")
    assert es.check_align(None, "c") is None
    assert es.check_align("right", "c") == "right"
    for bad in ("middle", 1):
        with pytest.raises(ValueError, match="left"):
            es.check_align(bad, "c")


def test_per_element_font_is_not_ported_yet():
    assert es.check_font(None, "font") is None
    with pytest.raises(NotImplementedError, match="not supported yet"):
        es.check_font("Arial", "font")


def test_font_size_and_row_height_resolve_together():
    # nothing of its own: the document's
    assert es.resolve_element_metrics(None, None, 18, 300) == (18, 300)
    # a size of its own recomputes the height for that size
    fs, rh = es.resolve_element_metrics(24, None, 18, 300)
    assert fs == 24 and rh != 300
    # an explicit height always wins
    assert es.resolve_element_metrics(24, 500, 18, 300) == (24, 500)
    # no document values at all: the package defaults
    fs, rh = es.resolve_element_metrics(None, None, None, None)
    assert fs == 18 and rh > 0


def test_fs_cmd_only_when_it_differs():
    assert es.fs_cmd_for(None, 18) == ""
    assert es.fs_cmd_for(18, 18) == ""
    assert es.fs_cmd_for(16, 18) == "\\fs16"


def test_element_style_drops_unset_entries():
    assert es.element_style() == {}
    st = es.element_style(font_size_half_points=16, row_height_twips=240,
                          align="left", verb="rtf_titles")
    assert st == {"font_size_half_points": 16, "row_height_twips": 240,
                  "align": "left"}
    with pytest.raises(ValueError, match=r"rtf_titles\(align\)"):
        es.element_style(align="middle", verb="rtf_titles")


def test_block_width_checks_and_resolution():
    assert es.check_block_width(None, "w") is None
    assert es.check_block_width("page", "w") == "page"
    assert es.check_block_width(0.5, "w") == 0.5
    for bad in ("wide", 0, -1, True, [1]):
        with pytest.raises(ValueError, match="content"):
            es.check_block_width(bad, "w")
    assert es.resolve_block_width(None, 9000, 12000) == 9000
    assert es.resolve_block_width(None, 9000, 12000, default="page") == 12000
    assert es.resolve_block_width("page", 9000, 12000) == 12000
    assert es.resolve_block_width(0.5, 9000, 12000) == 6000
    assert es.resolve_block_width(7000, 9000, 12000) == 7000
