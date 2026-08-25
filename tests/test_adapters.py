"""Tests for as_rtftable/as_rtftables adapters and pagination."""

import pytest

import rtfreporter as rr
from helpers import assert_valid_rtf
from rtfreporter import RtfDocument

pd = pytest.importorskip("pandas")


def test_as_rtftable_from_pandas(demog_df):
    t = rr.as_rtftable(demog_df)
    assert t.ncols == 4 and t.nrows == 3
    assert t.column_names == ["Subject", "Arm", "Age", "Sex"]


def test_nan_becomes_blank():
    import math

    df = pd.DataFrame({"A": [1.0, math.nan], "B": ["x", None]})
    t = rr.as_rtftable(df)
    assert t.rows[1][0] is None
    assert t.rows[1][1] is None


def test_delimited_name_spanning_header():
    df = pd.DataFrame(
        {
            "Item": ["n"],
            "Drug A____N": [10],
            "Drug A____Mean": [1.1],
            "Drug B____N": [20],
            "Drug B____Mean": [2.2],
        }
    )
    t = rr.as_rtftable(df)
    assert [r.kind for r in t.col_header] == ["spanning", "labels"]
    spans = t.col_header[0].spans
    labelled = [(s.start, s.end, s.label) for s in spans if s.label]
    assert (1, 2, "Drug A") in labelled
    assert (3, 4, "Drug B") in labelled


def test_split_rows():
    df = pd.DataFrame({"ID": list(range(10))})
    pages = rr.as_rtftables(df, split="rows", split_rows=4)
    assert [p.nrows for p in pages] == [4, 4, 2]


def test_split_by_value_names_pages():
    df = pd.DataFrame({"grp": ["A", "A", "B"], "v": [1, 2, 3]})
    pages = rr.as_rtftables(df, split="by_value", group_col="grp")
    assert [getattr(p, "name", None) for p in pages] == ["A", "B"]
    assert [p.nrows for p in pages] == [2, 1]


def test_group_force_split_with_cont_marker():
    df = pd.DataFrame({"grp": ["A"] * 5, "v": list(range(5))})
    pages = rr.as_rtftables(
        df, split="group_force", group_col="grp", max_rows=3
    )
    assert len(pages) == 2
    # The continued group's first cell carries the (Cont.) marker.
    assert any("(Cont.)" in str(c) for c in pages[1].rows[0])


def test_sort_by():
    df = pd.DataFrame({"k": [3, 1, 2]})
    t = rr.as_rtftable(df, sort_by="k")
    assert [r[0] for r in t.rows] == [1, 2, 3]


def test_sort_desc():
    df = pd.DataFrame({"k": [3, 1, 2]})
    t = rr.as_rtftable(df, sort_by="k", sort_desc=[True])
    assert [r[0] for r in t.rows] == [3, 2, 1]


def test_drop_cols_hides_carrier():
    df = pd.DataFrame({"grp": ["A", "B"], "v": [1, 2]})
    t = rr.as_rtftable(df, drop_cols="grp")
    assert t.column_names == ["v"]
    assert t.ncols == 1


def test_collapse_repeats():
    df = pd.DataFrame({"grp": ["A", "A", "B"], "v": [1, 2, 3]})
    t = rr.as_rtftable(df, collapse_repeats="grp")
    assert t.rows[1][0] == ""  # repeat blanked
    assert t.rows[0][0] == "A"
    assert t.rows[2][0] == "B"


def test_blank_rows_between_groups():
    df = pd.DataFrame({"grp": ["A", "A", "B", "B"], "v": [1, 2, 3, 4]})
    t = rr.as_rtftable(df, group_col="grp")
    # A change from A->B after row 2 -> a blank position at 2.
    assert 2 in t.blank_rows


def test_stub_cols_indented():
    df = pd.DataFrame(
        {"Group": ["Age", "Age", "Sex"], "Stat": ["n", "Mean", "Male"], "Val": [86, 75, 40]}
    )
    t = rr.as_rtftable(df, stub_vars=["Group", "Stat"], stub_label="")
    stub_col = [r[0] for r in t.rows]
    assert "Age" in stub_col
    assert any(s.strip() == "n" and s.startswith(" ") for s in stub_col)


def test_polars_input():
    pl = pytest.importorskip("polars")
    df = pl.DataFrame({"A": [1, 2], "B": ["x", "y"]})
    t = rr.as_rtftable(df)
    assert t.column_names == ["A", "B"]
    assert t.nrows == 2


def test_great_tables_input():
    gt = pytest.importorskip("great_tables")
    df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    obj = gt.GT(df)
    t = rr.as_rtftable(obj)
    assert t.ncols == 2 and t.nrows == 2


def test_adapter_end_to_end_valid(demog_df):
    pages = rr.as_rtftables(demog_df, border="tfl")
    doc = RtfDocument()
    for p in pages:
        doc = doc.add_table(p)
    assert_valid_rtf(doc.to_rtf())
