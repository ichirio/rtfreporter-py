"""Header/footer band normalisation, row updates, and coercion."""

import pytest

import rtfreporter as rr
from rtfreporter.header_footer import HeaderFooter, _normalize_row, normalize_hf

# -- _normalize_row -----------------------------------------------------------


def test_normalize_row_none_is_centered_blank():
    assert _normalize_row(None) == {"c": ""}


def test_normalize_row_str_is_centered():
    assert _normalize_row("hi") == {"c": "hi"}


def test_normalize_row_dict_keeps_positions():
    assert _normalize_row({"l": "a", "r": "b"}) == {"l": "a", "r": "b"}


def test_normalize_row_dict_none_value_becomes_blank():
    assert _normalize_row({"l": None}) == {"l": ""}


def test_normalize_row_empty_dict_is_centered_blank():
    assert _normalize_row({}) == {"c": ""}


def test_normalize_row_dict_bad_key_raises():
    with pytest.raises(ValueError, match="'l', 'c', or 'r'"):
        _normalize_row({"x": "a"})


def test_normalize_row_empty_sequence():
    assert _normalize_row([]) == {"c": ""}


def test_normalize_row_one_element_sequence():
    assert _normalize_row(["only"]) == {"c": "only"}


def test_normalize_row_two_element_sequence():
    assert _normalize_row(["L", "R"]) == {"l": "L", "r": "R"}


def test_normalize_row_three_element_sequence():
    assert _normalize_row(["L", "C", "R"]) == {"l": "L", "c": "C", "r": "R"}


def test_normalize_row_four_elements_raises():
    with pytest.raises(ValueError, match="up to 3 columns"):
        _normalize_row([1, 2, 3, 4])


def test_normalize_row_bad_type_raises():
    with pytest.raises(TypeError, match="str, dict, or sequence"):
        _normalize_row(42)


# -- rtf_header / rtf_footer --------------------------------------------------


def test_rtf_header_normalizes_rows_and_flags():
    h = rr.rtf_header(["title", {"l": "a", "r": "b"}])
    assert isinstance(h, HeaderFooter)
    assert h.is_footer is False
    assert h.rows == [{"c": "title"}, {"l": "a", "r": "b"}]


def test_rtf_footer_sets_is_footer():
    f = rr.rtf_footer(["foot"])
    assert f.is_footer is True


def test_rtf_header_carries_options():
    b = rr.rtf_border_bottom()
    h = rr.rtf_header(["x"], border=b, row_height_twips=200, width_twips=9000)
    assert h.border is b
    assert h.row_height_twips == 200
    assert h.width_twips == 9000


# -- update_header_row / _update_hf_rows --------------------------------------


def test_update_header_row_wrong_type_raises():
    with pytest.raises(TypeError, match="rtf_header"):
        rr.update_header_row("not a band", 0, "x")


def test_update_header_row_appends_at_end():
    h = rr.rtf_header(["a"])
    h2 = rr.update_header_row(h, 1, "b")
    assert h2.rows == [{"c": "a"}, {"c": "b"}]


# -- normalize_hf -------------------------------------------------------------


def test_normalize_hf_none():
    assert normalize_hf(None) is None


def test_normalize_hf_passthrough_band():
    h = rr.rtf_header(["a"])
    assert normalize_hf(h) is h


def test_normalize_hf_from_list():
    hf = normalize_hf(["a", {"l": "x"}])
    assert isinstance(hf, HeaderFooter)
    assert hf.rows == [{"c": "a"}, {"l": "x"}]


def test_normalize_hf_from_str():
    hf = normalize_hf("banner")
    assert hf.rows == [{"c": "banner"}]


def test_normalize_hf_from_dict():
    hf = normalize_hf({"l": "left"})
    assert hf.rows == [{"l": "left"}]


def test_normalize_hf_bad_type_raises():
    with pytest.raises(TypeError, match="HeaderFooter"):
        normalize_hf(42)
