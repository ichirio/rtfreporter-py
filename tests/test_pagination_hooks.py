"""Phase 3: pagination factory functions, paginate(), and the custom split hook."""

import pytest

import rtfreporter as rr
from rtfreporter.pagination import Frame, PaginationError, as_frame


def _df():
    return {
        "label": ["A", "A", "B", "B", "B", "C"],
        "v": [1, 2, 3, 4, 5, 6],
    }


# -- as_frame / Frame --------------------------------------------------------


def test_as_frame_from_dict():
    fr = as_frame({"a": [1, 2], "b": [3, 4]})
    assert isinstance(fr, Frame)
    assert fr.column_names == ["a", "b"]
    assert fr.rows == [[1, 3], [2, 4]]


def test_as_frame_passthrough():
    fr = Frame(["a"], [[1]])
    assert as_frame(fr) is fr


def test_as_frame_from_pair():
    fr = as_frame((["a", "b"], [[1, 2]]))
    assert fr.column_names == ["a", "b"]
    assert fr.rows == [[1, 2]]


# -- paginate() built-in strategies ------------------------------------------


def test_paginate_none_one_page():
    pages = rr.paginate(_df(), split="none")
    assert len(pages) == 1
    assert len(pages[0].rows) == 6


def test_paginate_rows():
    pages = rr.paginate(_df(), split="rows", split_rows=2)
    assert [len(p.rows) for p in pages] == [2, 2, 2]


def test_paginate_rows_requires_split_rows():
    with pytest.raises(PaginationError, match="split_rows"):
        rr.paginate(_df(), split="rows")


def test_paginate_by_value_names_pages():
    pages = rr.paginate(_df(), split="by_value", group_col="label")
    assert [p.name for p in pages] == ["A", "B", "C"]
    assert [len(p.rows) for p in pages] == [2, 3, 1]


def test_paginate_group_safe_requires_max_rows():
    with pytest.raises(PaginationError, match="max_rows"):
        rr.paginate(_df(), split="group_safe", group_col="label")


def test_paginate_group_force():
    pages = rr.paginate(_df(), split="group_force", max_rows=3, group_col="label")
    assert sum(len(p.rows) for p in pages) >= 6  # cont rows may be added


def test_paginate_unknown_strategy():
    with pytest.raises(ValueError, match="Unknown split"):
        rr.paginate(_df(), split="nonsense")


def test_paginate_sort_by():
    data = {"g": ["b", "a", "c"], "v": [1, 2, 3]}
    pages = rr.paginate(data, split="none", sort_by="g")
    assert [r[0] for r in pages[0].rows] == ["a", "b", "c"]


# -- factory functions -------------------------------------------------------


def test_page_split_none_factory():
    f = rr.page_split_none()
    out = f(Frame(["a"], [[1], [2]]))
    assert len(out) == 1
    assert out[0].rows == [[1], [2]]


def test_page_split_rows_factory():
    f = rr.page_split_rows(2)
    out = f(Frame(["a"], [[1], [2], [3], [4]]))
    assert [len(p.rows) for p in out] == [2, 2]


def test_page_split_rows_factory_missing_config():
    f = rr.page_split_rows()
    with pytest.raises(PaginationError, match="split_rows"):
        f(Frame(["a"], [[1], [2]]))


def test_page_split_by_value_factory():
    f = rr.page_split_by_value(group_col="label")
    out = f(as_frame(_df()))
    assert [p.name for p in out] == ["A", "B", "C"]


def test_page_split_group_safe_factory():
    f = rr.page_split_group_safe(max_rows=3, group_col="label")
    out = f(as_frame(_df()))
    assert all(len(p.rows) <= 4 for p in out)  # +cont allowance


def test_page_split_group_force_missing_max_rows():
    f = rr.page_split_group_force()
    with pytest.raises(PaginationError, match="max_rows"):
        f(as_frame(_df()))


def test_factory_group_by_not_implemented():
    f = rr.page_split_by_value(group_col="label", group_by="indent")
    with pytest.raises(NotImplementedError):
        f(as_frame(_df()))


# -- as_rtftables with a factory callable ------------------------------------


def test_as_rtftables_accepts_factory_callable():
    tables = rr.as_rtftables(_df(), split=rr.page_split_by_value(group_col="label"))
    assert [t.name for t in tables] == ["A", "B", "C"]


def test_as_rtftables_string_and_callable_equivalent():
    a = rr.as_rtftables(_df(), split="by_value", group_col="label")
    b = rr.as_rtftables(_df(), split=rr.page_split_by_value(group_col="label"))
    assert [t.name for t in a] == [t.name for t in b]


# -- custom split hook -------------------------------------------------------


def test_custom_split_hook():
    def head_tail(frame: Frame) -> list[Frame]:
        return [
            Frame(frame.column_names, frame.rows[:1]),
            Frame(frame.column_names, frame.rows[1:]),
        ]

    tables = rr.as_rtftables(_df(), split=head_tail)
    assert len(tables) == 2


def test_custom_split_named_pages():
    def one_page(frame: Frame) -> list[Frame]:
        return [Frame(frame.column_names, frame.rows, name="Whole")]

    tables = rr.as_rtftables(_df(), split=one_page)
    assert tables[0].name == "Whole"


def test_custom_split_bad_return_type():
    with pytest.raises(PaginationError, match="list of Frame"):
        rr.paginate(_df(), split=lambda f: "nope")


def test_custom_split_bad_element_type():
    with pytest.raises(PaginationError, match="Frame objects"):
        rr.paginate(_df(), split=lambda f: [Frame(f.column_names, f.rows), 42])


def test_resolve_split_bad_type():
    from rtfreporter.pagination import resolve_split

    with pytest.raises(TypeError, match="strategy name or a split callable"):
        resolve_split(123)


# -- add_cont_label ----------------------------------------------------------


def test_add_cont_label_prepends_row():
    fr = rr.add_cont_label(Frame(["label", "v"], [[3, "x"]]), "Group B")
    assert fr.rows[0] == ["Group B (Cont.)", ""]
    assert fr.rows[1] == [3, "x"]


def test_add_cont_label_custom_suffix_and_col():
    fr = rr.add_cont_label(
        Frame(["a", "b"], [[1, 2]]), "G", cont_label=" [more]", col=1
    )
    assert fr.rows[0] == ["", "G [more]"]


def test_add_cont_label_requires_string_label():
    with pytest.raises(TypeError, match="single string"):
        rr.add_cont_label(Frame(["a"], [[1]]), ["not", "a", "string"])
