"""Input validation and error paths (rtftable-validation)."""

import pytest

from rtfreporter import col_cell, rtftable
from rtfreporter.borders import Border


def test_bad_table_align():
    with pytest.raises(ValueError):
        rtftable({"A": [1]}, table_align="middle")


def test_bad_cell_valign():
    with pytest.raises(ValueError):
        rtftable({"A": [1]}, cell_valign="sideways")


def test_table_width_pct_zero():
    with pytest.raises(ValueError):
        rtftable({"A": [1]}, table_width_pct=0)


def test_table_width_pct_over_100():
    with pytest.raises(ValueError):
        rtftable({"A": [1]}, table_width_pct=150)


def test_column_widths_length_mismatch():
    with pytest.raises(ValueError):
        rtftable({"A": [1], "B": [2]}, column_widths_twips=[100])


def test_col_rel_width_length_mismatch():
    with pytest.raises(ValueError):
        rtftable({"A": [1], "B": [2]}, col_rel_width=[1])


def test_cell_styles_length_mismatch():
    with pytest.raises(ValueError):
        rtftable({"A": [1, 2]}, cell_styles=[{}])


def test_col_spec_missing_col_key():
    with pytest.raises(ValueError):
        rtftable({"A": [1]}, col_spec=[{"align": "left"}])


def test_col_spec_unknown_field():
    with pytest.raises(ValueError):
        rtftable({"A": [1]}, col_spec=[{"col": 0, "wiggle": True}])


def test_col_spec_unknown_column_name():
    with pytest.raises(ValueError):
        rtftable({"A": [1]}, col_spec=[{"col": "Z", "bold": True}])


def test_col_spec_index_out_of_range():
    with pytest.raises(ValueError):
        rtftable({"A": [1]}, col_spec=[{"col": 5, "bold": True}])


def test_col_spec_bad_align_value():
    with pytest.raises(ValueError):
        rtftable({"A": [1]}, col_spec=[{"col": 0, "align": "up"}])


def test_col_spec_must_be_dict():
    with pytest.raises(TypeError):
        rtftable({"A": [1]}, col_spec=["not a dict"])


def test_col_header_align_length_mismatch():
    with pytest.raises(ValueError):
        rtftable({"A": [1], "B": [2]}, col_header_align=["left"])


def test_col_cell_bad_align():
    with pytest.raises(ValueError):
        col_cell(0, "L", align="up")


def test_col_cell_bad_border_type():
    with pytest.raises(TypeError):
        col_cell(0, "L", border="thick")


def test_col_cell_accepts_border_object():
    c = col_cell(0, "L", border=Border())
    assert c.label == "L"


def test_coerce_data_bad_type():
    with pytest.raises(TypeError):
        rtftable(42)


def test_bad_border_preset_string():
    with pytest.raises(ValueError):
        rtftable({"A": [1]}, border="fancy")


def test_bad_border_type():
    with pytest.raises(TypeError):
        rtftable({"A": [1]}, border=123)


def test_unknown_column_name_in_col_header_align_ok_str():
    # A single string is broadcast, so it never raises for name reasons.
    t = rtftable({"A": [1], "B": [2]}, col_header_align="center")
    assert t.col_spec[0].header_align == "center"
