"""Adapter reshaping: sort, drop, collapse, stub, group, headers-from-names."""

import pytest

import rtfreporter as rr

pd = pytest.importorskip("pandas")


# -- sort-by ------------------------------------------------------------------

def test_sort_ascending():
    t = rr.as_rtftable(pd.DataFrame({"k": [3, 1, 2]}), sort_by="k")
    assert [r[0] for r in t.rows] == [1, 2, 3]


def test_sort_descending():
    t = rr.as_rtftable(pd.DataFrame({"k": [3, 1, 2]}), sort_by="k", sort_desc=[True])
    assert [r[0] for r in t.rows] == [3, 2, 1]


def test_sort_multi_column():
    df = pd.DataFrame({"a": [1, 1, 2], "b": [2, 1, 3]})
    t = rr.as_rtftable(df, sort_by=["a", "b"])
    assert [r[1] for r in t.rows] == [1, 2, 3]


def test_sort_nones_last():
    df = pd.DataFrame({"k": [2.0, None, 1.0]})
    t = rr.as_rtftable(df, sort_by="k")
    assert t.rows[-1][0] is None


def test_sort_strings():
    t = rr.as_rtftable(pd.DataFrame({"s": ["b", "a", "c"]}), sort_by="s")
    assert [r[0] for r in t.rows] == ["a", "b", "c"]


# -- drop-cols ----------------------------------------------------------------

def test_drop_single_column():
    t = rr.as_rtftable(pd.DataFrame({"g": ["A"], "v": [1]}), drop_cols="g")
    assert t.column_names == ["v"]


def test_drop_multiple_columns():
    df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    t = rr.as_rtftable(df, drop_cols=["a", "c"])
    assert t.column_names == ["b"]


def test_drop_by_index():
    df = pd.DataFrame({"a": [1], "b": [2]})
    t = rr.as_rtftable(df, drop_cols=0)
    assert t.column_names == ["b"]


def test_drop_reindexes_spanning_header():
    df = pd.DataFrame({
        "key": ["x"],
        "Drug A____N": [1], "Drug A____Mean": [2],
    })
    t = rr.as_rtftable(df, drop_cols="key")
    assert t.column_names == ["Drug A____N", "Drug A____Mean"]
    # remaining spanning header covers cols 0..1
    span = t.col_header[0].spans[0]
    assert (span.start, span.end) == (0, 1)


# -- collapse-repeats ---------------------------------------------------------

def test_collapse_blanks_repeats():
    df = pd.DataFrame({"g": ["A", "A", "B"], "v": [1, 2, 3]})
    t = rr.as_rtftable(df, collapse_repeats="g")
    assert [r[0] for r in t.rows] == ["A", "", "B"]


def test_collapse_multiple_columns():
    df = pd.DataFrame({"a": ["x", "x"], "b": ["y", "y"]})
    t = rr.as_rtftable(df, collapse_repeats=["a", "b"])
    assert t.rows[1][0] == "" and t.rows[1][1] == ""


def test_collapse_resets_on_change():
    df = pd.DataFrame({"g": ["A", "B", "B"]})
    t = rr.as_rtftable(df, collapse_repeats="g")
    assert [r[0] for r in t.rows] == ["A", "B", ""]


# -- group-by / blank rows ----------------------------------------------------

def test_group_col_inserts_blank_at_change():
    df = pd.DataFrame({"g": ["A", "A", "B"], "v": [1, 2, 3]})
    t = rr.as_rtftable(df, group_col="g")
    assert 2 in t.blank_rows


def test_group_col_no_blank_single_group():
    df = pd.DataFrame({"g": ["A", "A"], "v": [1, 2]})
    t = rr.as_rtftable(df, group_col="g")
    assert t.blank_rows == []


# -- stub-cols ----------------------------------------------------------------

def test_stub_merges_hierarchy():
    df = pd.DataFrame({
        "Group": ["Age", "Age", "Sex"],
        "Stat": ["n", "Mean", "Male"],
        "Val": [86, 75, 40],
    })
    t = rr.as_rtftable(df, stub_cols=["Group", "Stat"], stub_label="")
    stub = [r[0] for r in t.rows]
    assert "Age" in stub
    assert any(s.strip() == "n" and s != "n" for s in stub)  # indented


def test_stub_label_becomes_first_col_name():
    df = pd.DataFrame({"Group": ["A"], "Stat": ["n"], "Val": [1]})
    t = rr.as_rtftable(df, stub_cols=["Group", "Stat"], stub_label="Characteristic")
    assert t.column_names[0] == "Characteristic"


def test_stub_indent_width():
    df = pd.DataFrame({"Group": ["A"], "Stat": ["n"], "Val": [1]})
    t = rr.as_rtftable(df, stub_cols=["Group", "Stat"], stub_label="", stub_indent=2)
    leaf = [r[0] for r in t.rows if r[0].strip() == "n"][0]
    assert leaf.startswith("  n")


def test_stub_single_level_no_indent():
    df = pd.DataFrame({"Group": ["A", "B"], "Val": [1, 2]})
    t = rr.as_rtftable(df, stub_cols=["Group"], stub_label="")
    assert [r[0] for r in t.rows] == ["A", "B"]


# -- col-header-from-names ----------------------------------------------------

def test_spanning_from_delimited_names():
    df = pd.DataFrame({
        "Item": ["n"],
        "A____N": [1], "A____Mean": [2],
        "B____N": [3], "B____Mean": [4],
    })
    t = rr.as_rtftable(df)
    assert [r.kind for r in t.col_header] == ["spanning", "labels"]
    labelled = [(s.start, s.end, s.label) for s in t.col_header[0].spans if s.label]
    assert (1, 2, "A") in labelled and (3, 4, "B") in labelled


def test_leaf_labels_from_names():
    df = pd.DataFrame({"A____N": [1], "A____Mean": [2]})
    t = rr.as_rtftable(df)
    assert t.col_header[-1].labels == ["N", "Mean"]


def test_no_delimiter_flat_header():
    df = pd.DataFrame({"Age": [1], "Sex": [2]})
    t = rr.as_rtftable(df)
    assert [r.kind for r in t.col_header] == ["labels"]


def test_custom_header_sep():
    df = pd.DataFrame({"A::N": [1], "A::Mean": [2]})
    t = rr.as_rtftable(df, header_sep="::")
    assert [r.kind for r in t.col_header] == ["spanning", "labels"]


def test_three_level_names():
    df = pd.DataFrame({"X____A____N": [1], "X____A____M": [2], "X____B____N": [3]})
    t = rr.as_rtftable(df)
    kinds = [r.kind for r in t.col_header]
    assert kinds.count("spanning") == 2


# -- missing values -----------------------------------------------------------

def test_nan_to_none():
    import math
    df = pd.DataFrame({"A": [1.0, math.nan]})
    t = rr.as_rtftable(df)
    assert t.rows[1][0] is None
