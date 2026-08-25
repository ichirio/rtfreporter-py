"""Pagination split strategies and continuation markers (paginate, page-split-factories)."""

import pytest

import rtfreporter as rr

pd = pytest.importorskip("pandas")


def _ids(n):
    return pd.DataFrame({"ID": list(range(n))})


def test_split_none_single_page():
    pages = rr.as_rtftables(_ids(10), split="none")
    assert len(pages) == 1
    assert pages[0].nrows == 10


def test_split_rows_even():
    pages = rr.as_rtftables(_ids(10), split="rows", split_rows=5)
    assert [p.nrows for p in pages] == [5, 5]


def test_split_rows_remainder():
    """One cut position -> two pages; R gives 4 and 6 for the same call."""
    pages = rr.as_rtftables(_ids(10), split="rows", split_rows=4)
    assert [p.nrows for p in pages] == [4, 6]


def test_split_rows_explicit_cuts():
    pages = rr.as_rtftables(_ids(10), split="rows", split_rows=[3, 7])
    assert [p.nrows for p in pages] == [3, 4, 3]


def test_split_rows_by_max_rows():
    pages = rr.as_rtftables(_ids(9), split="rows", max_rows=3)
    assert [p.nrows for p in pages] == [3, 3, 3]


def test_by_value_one_page_per_group():
    df = pd.DataFrame({"g": ["A", "A", "B", "C"], "v": [1, 2, 3, 4]})
    pages = rr.as_rtftables(df, split="by_value", group_col="g")
    assert [p.nrows for p in pages] == [2, 1, 1]


def test_by_value_page_names():
    df = pd.DataFrame({"g": ["A", "B"], "v": [1, 2]})
    pages = rr.as_rtftables(df, split="by_value", group_col="g")
    assert [getattr(p, "name", None) for p in pages] == ["A", "B"]


def test_by_value_splits_large_group():
    df = pd.DataFrame({"g": ["A"] * 5, "v": list(range(5))})
    pages = rr.as_rtftables(df, split="by_value", group_col="g", max_rows=3)
    assert len(pages) == 2


def test_group_safe_keeps_groups_intact():
    df = pd.DataFrame({"g": ["A", "A", "A", "B", "B"], "v": list(range(5))})
    pages = rr.as_rtftables(df, split="group_safe", group_col="g", max_rows=4)
    # group A (3) fits; B (2) would overflow -> new page. A never split.
    assert [p.nrows for p in pages][0] == 3


def test_group_safe_requires_max_rows():
    df = pd.DataFrame({"g": ["A", "B"], "v": [1, 2]})
    with pytest.raises(ValueError):
        rr.as_rtftables(df, split="group_safe", group_col="g")


def test_group_force_splits_oversized_group():
    """A mid-group cut repeats the header, so the second page is 1 + 2 rows.

    Verified against the R package, which returns the same two pages:
    ``A|0, A|1, A|2`` then ``A (Cont.)|NA, A|3, A|4``.
    """
    df = pd.DataFrame({"g": ["A"] * 5, "v": list(range(5))})
    pages = rr.as_rtftables(df, split="group_force", group_col="g", max_rows=3)
    assert len(pages) == 2
    assert [p.nrows for p in pages] == [3, 3]
    assert pages[1].rows[0] == ["A (Cont.)", None]
    assert [r[1] for r in pages[1].rows[1:]] == [3, 4]


def test_group_force_cont_marker_in_second_page():
    df = pd.DataFrame({"g": ["A"] * 5, "v": list(range(5))})
    pages = rr.as_rtftables(df, split="group_force", group_col="g", max_rows=3)
    assert any("(Cont.)" in str(c) for c in pages[1].rows[0])


def test_custom_cont_label():
    df = pd.DataFrame({"g": ["A"] * 4, "v": list(range(4))})
    pages = rr.as_rtftables(
        df, split="group_force", group_col="g", max_rows=2, cont_label=" [more]"
    )
    assert any("[more]" in str(c) for c in pages[1].rows[0])


def test_unknown_split_raises():
    with pytest.raises(ValueError):
        rr.as_rtftables(_ids(3), split="diagonal")


def test_as_rtftable_single_page_no_split():
    df = pd.DataFrame({"g": ["A", "B"], "v": [1, 2]})
    t = rr.as_rtftable(df)  # always split="none"
    assert t.nrows == 2 and t.ncols == 2


def test_list_of_frames_flattened():
    a = pd.DataFrame({"X": [1]})
    b = pd.DataFrame({"X": [2, 3]})
    pages = rr.as_rtftables([a, b])
    assert len(pages) == 2


def test_paginate_blanks_between_groups_per_page():
    df = pd.DataFrame({"g": ["A", "A", "B", "B"], "v": [1, 2, 3, 4]})
    pages = rr.as_rtftables(
        df, split="none", group_col="g", blank_rows="between_groups"
    )
    assert 2 in pages[0].blank_rows


def test_blank_row_first_and_end():
    pages = rr.as_rtftables(_ids(4), split="rows", split_rows=4,
                            blank_row_first=True, blank_row_end=True)
    assert 0 in pages[0].blank_rows
    assert 4 in pages[0].blank_rows
