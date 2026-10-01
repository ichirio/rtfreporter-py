"""rtf_tables() overrides of a pre-built table (R .override_rtftable_fields()).
Byte parity with R is in the xcheck cases rtf_tables_overrides_*."""

import pytest

import rtfreporter as rr
from rtfreporter.table import override_rtftable_fields


def _tbl(**kw):
    return rr.rtftable({"A": ["x", "y"], "B": ["1", "2"]}, **kw)


def test_nothing_passed_returns_the_same_table():
    t = _tbl()
    assert override_rtftable_fields(t, {}) is t
    assert override_rtftable_fields(t, {"not_a_formatting_arg": 1}) is t


def test_scalar_fields_are_normalised():
    t = override_rtftable_fields(_tbl(), {
        "column_widths_twips": [1000.0, 2000.0], "table_width_twips": 3000.0,
        "table_width_pct_of_writable": 0.5, "row_height_twips": 250.0,
        "row_height_exact": True, "header_row_height_twips": 300,
        "blank_row_height_twips": None, "cell_padding_left_twips": 10,
        "cell_padding_right_twips": 20, "cell_valign": "top",
        "font": "Arial", "font_size_half_points": 20,
    })
    assert t.column_widths_twips == [1000, 2000]
    assert t.table_width_twips == 3000 and t.table_width_pct_of_writable == 0.5
    assert (t.row_height_twips, t.row_height_exact, t.header_row_height_twips) == (250, True, 300)
    assert t.blank_row_height_twips is None
    assert (t.cell_padding_left_twips, t.cell_padding_right_twips) == (10, 20)
    assert t.cell_valign == "top" and t.font == "Arial" and t.font_size_half_points == 20


def test_widths_can_be_cleared():
    t = override_rtftable_fields(_tbl(col_rel_width=[1, 2], column_widths_twips=[1, 2]),
                                 {"col_rel_width": None, "column_widths_twips": None})
    assert t.col_rel_width is None and t.column_widths_twips is None


@pytest.mark.parametrize("ov, msg", [
    ({"table_width_pct": 0}, "table_width_pct"),
    ({"table_align": "middle"}, "table_align"),
    ({"row_height_exact": "yes"}, "row_height_exact"),
    ({"cell_valign": "middle"}, "cell_valign"),
    ({"col_spec": [{"bold": True}]}, "col"),
])
def test_bad_values_are_refused(ov, msg):
    with pytest.raises(ValueError, match=msg):
        override_rtftable_fields(_tbl(), ov)


def test_spanning_header_and_col_header_replace_their_own_rows():
    t = _tbl(spanning_header=[{"label": "Both", "from": 0, "to": 1}])
    assert t.spanning_rows == 1 and len(t.col_header) == 2
    t2 = override_rtftable_fields(t, {"col_header": ["a", "b"]})
    assert len(t2.col_header) == 2 and t2.col_header[-1].labels == ["a", "b"]
    t3 = override_rtftable_fields(t2, {"spanning_header": None})
    assert t3.spanning_rows == 0 and len(t3.col_header) == 1


def test_blank_rows_resolve_against_the_data():
    t = override_rtftable_fields(_tbl(), {"blank_rows": 0})
    assert t.blank_rows == [1]
    assert override_rtftable_fields(t, {"blank_rows": None}).blank_rows == []


def test_col_spec_by_name_and_an_unknown_column_is_skipped():
    t = override_rtftable_fields(_tbl(), {"col_spec": [{"col": "B", "align": "right"},
                                                       {"col": "nope", "bold": True}]})
    assert t.col_spec[1].align == "right" and t.col_spec[1].header_align == "right"


def test_col_header_align_per_column():
    t = override_rtftable_fields(_tbl(), {"col_header_align": ["right", "left"]})
    assert [s.header_align for s in t.col_spec] == ["right", "left"]


def test_rtf_tables_applies_overrides_to_prebuilt_pages_only():
    pages = rr.as_rtftables({"A": ["x"], "B": ["1"]})
    doc = rr.rtf_tables(rr.rtf_document(), pages + [{"A": ["y"], "B": ["2"]}],
                        font_size_half_points=24)
    rtf = doc.to_rtf()
    assert rtf.count(r"\fs24 x") == 1 and rtf.count(r"\fs24 y") == 1


def test_auto_title_needs_a_valid_alignment():
    with pytest.raises(ValueError, match="title_label_align"):
        rr.rtf_tables(rr.rtf_document(), rr.as_rtftables({"A": ["x"]}),
                      auto_title=True, title_label_align="middle")
