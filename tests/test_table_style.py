"""TableStyle construction, validation, and derivation."""

import pytest

import rtfreporter as rr
from rtfreporter.rtf_table_style import TableStyle


def test_rtf_table_style_border_property_assembles_zones():
    st = rr.rtf_table_style(
        border_header=rr.rtf_border_top(),
        border_body=rr.rtf_border_bottom(),
    )
    tb = st.border
    assert tb.header is not None and tb.body is not None


def test_rtf_table_style_bad_border_type():
    with pytest.raises(TypeError, match="Border object"):
        rr.rtf_table_style(border_header="not a border")


def test_rtf_table_style_bad_align_value():
    with pytest.raises(ValueError, match="'left', 'center'"):
        rr.rtf_table_style(align="middle")


def test_rtf_table_style_bad_header_align_value():
    with pytest.raises(ValueError, match="header_align"):
        rr.rtf_table_style(header_align="middle")


def test_rtf_table_style_with_non_style_raises():
    with pytest.raises(TypeError, match="TableStyle object"):
        rr.rtf_table_style_with("nope", bold=True)


def test_rtf_table_style_with_unknown_field():
    with pytest.raises(ValueError, match="Unknown style field"):
        rr.rtf_table_style_with(rr.rtf_table_style(), nope=1)


def test_rtf_table_style_with_derives_copy():
    base = rr.rtf_table_style(align="left")
    derived = rr.rtf_table_style_with(base, align="center", bold=True)
    assert isinstance(derived, TableStyle)
    assert derived.align == "center" and derived.bold is True
    assert base.align == "left"  # original untouched


def test_rtf_table_style_tfl_header_only_borders():
    st = rr.rtf_table_style_tfl()
    assert st.border.header is not None
    assert st.border.body is None
    assert st.header_bold is False
