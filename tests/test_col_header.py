"""Column-header construction and rendering (col-header)."""

from helpers import render
from rtfreporter import col_cell, rtftable


def test_default_header_uses_column_names():
    t = rtftable({"Age": [1], "Sex": [2]})
    assert t.col_header[0].labels == ["Age", "Sex"]


def test_flat_label_list_single_row():
    t = rtftable({"A": [1], "B": [2]}, col_header=["Alpha", "Beta"])
    assert len(t.col_header) == 1
    assert t.col_header[0].labels == ["Alpha", "Beta"]


def test_flat_labels_padded_to_ncols():
    t = rtftable({"A": [1], "B": [2], "C": [3]}, col_header=["only"])
    assert t.col_header[0].labels == ["only", "", ""]


def test_flat_labels_truncated_to_ncols():
    t = rtftable({"A": [1], "B": [2]}, col_header=["a", "b", "c", "d"])
    assert t.col_header[0].labels == ["a", "b"]


def test_multiple_label_rows():
    t = rtftable(
        {"A": [1], "B": [2]},
        col_header=[["top1", "top2"], ["bot1", "bot2"]],
    )
    assert [r.kind for r in t.col_header] == ["labels", "labels"]
    assert t.col_header[1].labels == ["bot1", "bot2"]


def test_single_spanning_row_direct():
    t = rtftable(
        {"A": [1], "B": [2], "C": [3]},
        col_header=[col_cell((0, 1), "Grp"), col_cell(2, "C")],
    )
    assert t.col_header[0].kind == "spanning"
    spans = t.col_header[0].spans
    assert (spans[0].start, spans[0].end, spans[0].label) == (0, 1, "Grp")


def test_spanning_plus_labels_rows():
    t = rtftable(
        {"A": [1], "B": [2]},
        col_header=[[col_cell((0, 1), "Both")], ["A", "B"]],
    )
    assert [r.kind for r in t.col_header] == ["spanning", "labels"]


def test_col_cell_by_name_pair():
    t = rtftable(
        {"Low": [1], "High": [2]},
        col_header=[[col_cell(("Low", "High"), "Dose")], ["Low", "High"]],
    )
    sp = t.col_header[0].spans[0]
    assert (sp.start, sp.end) == (0, 1)


def test_col_cell_single_name():
    t = rtftable({"X": [1], "Y": [2]}, col_header=[[col_cell("Y", "why")], ["X", "Y"]])
    sp = t.col_header[0].spans[0]
    assert (sp.start, sp.end, sp.label) == (1, 1, "why")


def test_col_cell_reversed_range_normalized():
    t = rtftable(
        {"A": [1], "B": [2], "C": [3]},
        col_header=[[col_cell((2, 0), "rev")], ["A", "B", "C"]],
    )
    sp = t.col_header[0].spans[0]
    assert sp.start == 0 and sp.end == 2


def test_header_label_renders_in_rtf():
    t = rtftable({"A": [1]}, col_header=["Header!"])
    assert "Header!" in render(t)


def test_header_row_count_in_rtf():
    t = rtftable(
        {"A": [1], "B": [2]},
        col_header=[["t1", "t2"], ["b1", "b2"]],
    )
    rtf = render(t)
    # two header rows + one data row = 3 rows
    assert rtf.count("\\row") == 3


def test_none_labels_become_empty_strings():
    t = rtftable({"A": [1], "B": [2]}, col_header=[[None, "B"]])
    assert t.col_header[0].labels == ["", "B"]


def test_spanning_label_centered_by_default():
    # A span over non-row-title columns (B, C) defaults to center alignment.
    t = rtftable(
        {"A": [1], "B": [2], "C": [3]},
        col_header=[[col_cell(0, "A"), col_cell((1, 2), "Center")], ["A", "B", "C"]],
    )
    assert "\\qc\\li0\\ri0 Center\\cell" in render(t)
