"""Post-hoc table verbs: guards, header edits, combine, header-source."""

import pytest

import rtfreporter as rr
from rtfreporter import col_cell


def _tbl():
    return rr.rtftable(
        {"row_label": ["A", "B"], "g1": [1, 2], "g2": [3, 4], "Total": [5, 6]}
    )


# -- guards / _map_pages ------------------------------------------------------


def test_rtf_columns_wrong_type_raises():
    with pytest.raises(TypeError, match="RtfTable"):
        rr.rtf_columns(42)


def test_rtf_columns_empty_list():
    assert rr.rtf_columns([]) == []


def test_rtf_columns_list_of_non_tables_raises():
    with pytest.raises(TypeError):
        rr.rtf_columns([1, 2])


def test_collapse_repeats_wrong_type_raises():
    with pytest.raises(TypeError, match="RtfTable"):
        rr.collapse_repeats(42, [0])


def test_add_header_row_page_containing_non_table_raises():
    with pytest.raises(TypeError):
        rr.add_header_row([_tbl(), "not a table"], ["a", "b", "c", "d"])


# -- col_header_from_names ----------------------------------------------------


def test_col_header_from_names_reads_column_names_attr():
    ch = rr.col_header_from_names(_tbl())
    assert ch[0].kind == "labels"


def test_col_header_from_names_reads_columns_attr():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"A": [1], "B": [2]})
    ch = rr.col_header_from_names(df)
    assert ch[0].labels == ["A", "B"]


def test_col_header_from_names_empty_raises():
    with pytest.raises(ValueError, match="non-empty"):
        rr.col_header_from_names([])


# -- add_col_header_row / add_header_row --------------------------------------


def test_add_col_header_row_bad_position():
    with pytest.raises(ValueError, match='"top" or "bottom"'):
        rr.add_col_header_row(["A"], ["x"], position="middle")


def test_add_header_row_bad_position():
    with pytest.raises(ValueError, match='"top" or "bottom"'):
        rr.add_header_row(_tbl(), ["a", "b", "c", "d"], position="middle")


def test_add_header_row_bottom_appends():
    orig = _tbl()
    t = rr.add_header_row(orig, ["p", "q", "r", "s"], position="bottom")
    assert len(t.col_header) == len(orig.col_header) + 1
    assert t.col_header[-1].labels == ["p", "q", "r", "s"]


# -- set_col_header -----------------------------------------------------------


def test_set_col_header_single_row():
    t = rr.set_col_header(_tbl(), ["a", "b", "c", "d"])
    assert t.col_header[0].labels == ["a", "b", "c", "d"]


def test_set_col_header_clear_when_no_rows():
    # Passing no rows falls back to a single labels row of the column names.
    t = rr.set_col_header(_tbl())
    assert len(t.col_header) == 1
    assert t.col_header[0].kind == "labels"
    assert t.col_header[0].labels == ["row_label", "g1", "g2", "Total"]


def test_set_col_header_bad_align_value():
    with pytest.raises(ValueError, match="left"):
        rr.set_col_header(_tbl(), ["a", "b", "c", "d"], align=["bad"] * 4)


# -- set_header_cell ----------------------------------------------------------


def test_set_header_cell_no_cells_raises():
    with pytest.raises(ValueError, match="at least one"):
        rr.set_header_cell(_tbl(), row=0)


def test_set_header_cell_no_header_raises():
    t = _tbl()
    t.col_header = []  # a table with no header rows at all
    with pytest.raises(ValueError, match="no column header"):
        rr.set_header_cell(t, col_cell(0, "x"), row=0)


def test_set_header_cell_row_out_of_range():
    with pytest.raises(ValueError, match="header rows"):
        rr.set_header_cell(_tbl(), col_cell(0, "x"), row=5)


def test_set_header_cell_non_colcell_raises():
    with pytest.raises(TypeError, match="col_cell"):
        rr.set_header_cell(_tbl(), "notacell", row=0)


def test_set_header_cell_overlap_raises():
    with pytest.raises(ValueError, match="overlap"):
        rr.set_header_cell(
            _tbl(), col_cell((0, 1), "A"), col_cell((1, 2), "B"), row=0
        )


def test_set_header_cell_single_pos_covered():
    t = rr.set_header_cell(_tbl(), col_cell(0, "Cat"), row=0)
    spans = [(s.start, s.end, s.label) for s in t.col_header[0].spans]
    assert (0, 0, "Cat") in spans


# -- combine_sections ---------------------------------------------------------


def test_combine_sections_single_table_promoted():
    t = _tbl()
    sec = rr.combine_sections(Only=t)
    assert len(sec) == 1 and sec[0].name == "Only"


def test_combine_sections_bad_type_raises():
    with pytest.raises(TypeError, match="RtfTable or a"):
        rr.combine_sections(bad=42)


def test_combine_sections_empty_group_skipped():
    sec = rr.combine_sections(Empty=[], Real=_tbl())
    assert [t.name for t in sec] == ["Real"]


# -- rtf_header_source --------------------------------------------------------


def test_rtf_header_source_spanning_and_no_snippet():
    t = rr.set_col_header(
        _tbl(),
        [col_cell(0, ""), col_cell((1, 2), "Treatment"), col_cell(3, "")],
        ["Cat", "Low", "High", "Total"],
    )
    body = rr.rtf_header_source(t, snippet=False)
    assert "col_cell((1, 2), 'Treatment')" in body
    assert "set_col_header" not in body


def test_rtf_header_source_on_page_list():
    pages = rr.as_rtftables({"A": [1, 2], "B": [3, 4]}, split="rows", split_rows=1)
    src = rr.rtf_header_source(pages)
    assert "set_col_header(" in src


def test_rtf_header_source_falls_back_to_column_names():
    # A table with no explicit header still yields a labels row from names.
    t = rr.rtftable({"A": [1], "B": [2]})
    t.col_header = []
    src = rr.rtf_header_source(t, snippet=False)
    assert "['A', 'B']" in src
