"""Constructing RtfTable from the various accepted inputs (rtftable-construction)."""

import pytest

from rtfreporter import ColSpec, HeaderRow, RtfTable, rtftable
from rtfreporter.table import _coerce_data


def test_from_dict_of_columns():
    t = rtftable({"A": [1, 2], "B": ["x", "y"]})
    assert t.column_names == ["A", "B"]
    assert t.rows == [[1, "x"], [2, "y"]]
    assert t.ncols == 2 and t.nrows == 2


def test_from_names_rows_pair():
    t = rtftable((["A", "B"], [[1, 2], [3, 4]]))
    assert t.column_names == ["A", "B"]
    assert t.rows == [[1, 2], [3, 4]]


def test_from_list_of_row_dicts():
    t = rtftable([{"A": 1, "B": 2}, {"A": 3, "C": 4}])
    # Union of keys, in first-seen order.
    assert t.column_names == ["A", "B", "C"]
    assert t.rows[0] == [1, 2, None]
    assert t.rows[1] == [3, None, 4]


def test_ragged_dict_padded_with_none():
    t = rtftable({"A": [1, 2, 3], "B": ["x"]})
    assert t.nrows == 3
    assert t.rows[1][1] is None and t.rows[2][1] is None


def test_ncols_nrows_properties():
    t = rtftable({"A": [1], "B": [2], "C": [3]})
    assert t.ncols == 3
    assert t.nrows == 1


def test_empty_columns_zero_rows():
    t = rtftable({"A": [], "B": []})
    assert t.ncols == 2 and t.nrows == 0


def test_default_border_is_tfl():
    t = rtftable({"A": [1]})
    assert t.border is not None
    assert t.border.header is not None


def test_border_none_string():
    t = rtftable({"A": [1]}, border="none")
    assert t.border is None


def test_col_spec_defaults_one_per_column():
    t = rtftable({"A": [1], "B": [2]})
    assert len(t.col_spec) == 2
    assert all(isinstance(s, ColSpec) for s in t.col_spec)


def test_col_header_defaults_to_names():
    t = rtftable({"Age": [1], "Sex": [2]})
    assert t.col_header[0].kind == "labels"
    assert t.col_header[0].labels == ["Age", "Sex"]


def test_copy_is_independent():
    t = rtftable({"A": [1, 2]})
    c = t.copy()
    c.rows[0][0] = 99
    c.col_spec[0].bold = True
    assert t.rows[0][0] == 1
    assert t.col_spec[0].bold is False


def test_copy_returns_rtftable():
    assert isinstance(rtftable({"A": [1]}).copy(), RtfTable)


def test_table_align_stored():
    t = rtftable({"A": [1]}, table_align="center")
    assert t.table_align == "center"


def test_cell_valign_stored():
    t = rtftable({"A": [1]}, cell_valign="top")
    assert t.cell_valign == "top"


def test_blank_rows_default_empty():
    assert rtftable({"A": [1]}).blank_rows == []


def test_markup_none_leaves_none():
    assert rtftable({"A": [1]}).markup is None


def test_markup_resolved_when_given():
    t = rtftable({"A": [1]}, markup="all")
    assert t.markup == frozenset({"script", "relational"})


def test_column_widths_stored():
    t = rtftable({"A": [1], "B": [2]}, column_widths_twips=[1000, 2000])
    assert t.column_widths_twips == [1000, 2000]


def test_col_rel_width_stored_as_floats():
    t = rtftable({"A": [1], "B": [2]}, col_rel_width=[2, 1])
    assert t.col_rel_width == [2.0, 1.0]


def test_table_width_pct_to_fraction():
    t = rtftable({"A": [1]}, table_width_pct=50)
    assert t.table_width_pct_of_writable == 0.5


def test_coerce_data_dict():
    names, rows = _coerce_data({"A": [1], "B": [2]})
    assert names == ["A", "B"]
    assert rows == [[1, 2]]


def test_coerce_data_records():
    names, rows = _coerce_data([{"x": 1}, {"x": 2, "y": 3}])
    assert names == ["x", "y"]
    assert rows == [[1, None], [2, 3]]


def test_header_row_dataclass_shape():
    hr = HeaderRow(kind="labels", labels=["A"])
    assert hr.kind == "labels" and hr.labels == ["A"]


def test_titles_footnotes_default_none():
    t = rtftable({"A": [1]})
    assert t.titles is None and t.footnotes is None


def test_padding_stored():
    t = rtftable({"A": [1]}, cell_padding_left_twips=30, cell_padding_right_twips=40)
    assert t.cell_padding_left_twips == 30
    assert t.cell_padding_right_twips == 40


def test_row_heights_stored():
    t = rtftable({"A": [1]}, row_height_twips=300, header_row_height_twips=250,
                 blank_row_height_twips=100)
    assert t.row_height_twips == 300
    assert t.header_row_height_twips == 250
    assert t.blank_row_height_twips == 100


@pytest.mark.parametrize("data", [
    {"A": [1], "B": [2]},
    (["A", "B"], [[1, 2]]),
    [{"A": 1, "B": 2}],
])
def test_equivalent_inputs_same_body(data):
    t = rtftable(data)
    assert t.column_names == ["A", "B"]
    assert t.rows == [[1, 2]]
