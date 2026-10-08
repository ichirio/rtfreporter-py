"""The pre-CRAN API review of the R package (0.8.2.9013 / .9014 / #544):
renamed and retired functions and arguments warn once a session, still work,
and are removed in 0.9.0 -- and the replacements they name."""

import warnings

import pytest

import rtfreporter as rr
from rtfreporter.borders import _reset_deprecations


@pytest.fixture(autouse=True)
def fresh_session():
    _reset_deprecations()
    yield
    _reset_deprecations()


def _once(fn, match):
    """``fn()`` warns the first time, not the second; its value is returned."""
    with pytest.warns(DeprecationWarning, match=match):
        out = fn()
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        fn()
    return out


def _tbl():
    return rr.rtftable({"a": [1], "g1": [2], "g2": [3]})


def test_rtf_border_line_replaces_rtf_border_side():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        line = rr.rtf_border_line("double", 30, "#112233")
    old = _once(lambda: rr.rtf_border_side("double", 30, "#112233"), "rtf_border_line")
    assert old == line and isinstance(line, rr.BorderSide)


def test_header_helpers_are_deprecated():
    assert _once(lambda: rr.add_col_header_row(["A", "B"], ["x", "y"], position="top"),
                 r"rtf_col_header\(\)") == [["x", "y"], "A", "B"]
    assert len(_once(lambda: rr.col_header_from_names(["A____x", "A____y"]),
                     "header_sep")) == 2
    t = _once(lambda: rr.set_header_cell(_tbl(), rr.col_cell(("g1", "g2"), "S"), row=0),
              "style_header")
    assert t.col_header[0].spans[-1].label == "S"


def test_update_header_and_footer_row_are_deprecated():
    h = _once(lambda: rr.update_header_row(rr.rtf_header([{"l": "a"}]), 0, {"c": "b"}),
              r"rtf_header\(rows=\)")
    f = _once(lambda: rr.update_footer_row(rr.rtf_footer([{"l": "a"}]), 1, "x"),
              r"rtf_footer\(rows=\)")
    assert h.rows == [{"c": "b"}] and len(f.rows) == 2


def test_paginate_is_deprecated():
    pages = _once(lambda: rr.paginate({"a": [1, 2, 3]}, split="rows", max_rows=2),
                  r"as_rtftables\(\)")
    assert len(pages) == 2


def test_spanning_header_is_deprecated_and_byte_identical():
    data = {"a": [1], "b": [2], "c": [3]}
    span = [rr.col_cell((1, 2), "Treatment")]
    old = _once(lambda: rr.rtftable(data, spanning_header=span, col_header=["", "B", "C"]),
                "spanning_header")
    new = rr.rtftable(data, col_header=[span, ["", "B", "C"]])
    doc = rr.rtf_document()
    assert rr.rtf_tables(doc, old).to_rtf() == rr.rtf_tables(doc, new).to_rtf()
    # the rtf_tables() override warns too
    _reset_deprecations()
    with pytest.warns(DeprecationWarning, match="spanning_header"):
        rr.rtf_tables(doc, rr.rtftable(data), spanning_header=span)


def test_stub_vars_family_is_deprecated():
    data = {"grp": ["A", "A"], "item": ["x", "y"], "v": [1, 2]}
    old = _once(lambda: rr.as_rtftables(data, stub_vars=["grp", "item"]), "stub=stub_spec")
    new = rr.as_rtftables(data, stub=["grp", "item"])
    assert old[0].column_names == new[0].column_names
    _reset_deprecations()
    with pytest.warns(DeprecationWarning, match="stub_indent"):
        rr.as_rtftables(data, stub_indent=2)
    # `stub` alone says nothing
    _reset_deprecations()
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        rr.as_rtftables(data, stub=rr.stub_spec(["grp", "item"], indent=2))


def test_set_blank_rows_and_add_cont_label_take_data():
    data = {"g": ["a", "a", "b"], "v": [1, 2, 3]}
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        new = rr.set_blank_rows(data=data, blank_rows="between_groups", group_col="g")
        lab = rr.add_cont_label(data=data, label="a")
        assert rr.set_blank_rows(data, "between_groups", group_col="g").blank_rows == new.blank_rows
    old = _once(lambda: rr.set_blank_rows(df=data, blank_rows="between_groups", group_col="g"),
                r"set_blank_rows\(df=\)")
    assert old.blank_rows == new.blank_rows == [1]
    old_lab = _once(lambda: rr.add_cont_label(chunk=data, label="a"), r"add_cont_label\(chunk=\)")
    assert old_lab.rows == lab.rows
    with pytest.raises(TypeError, match="`data`"):
        rr.set_blank_rows()


def test_rtf_table_style_align_default_keeps_each_columns_own():
    # R #522: an unset align no longer left-aligns every column
    style = rr.rtf_table_style()
    assert style.align is None and rr.rtf_table_style_tfl().align is None
    t = rr.rtftable({"Parameter": ["Age"], "Value": ["75.1"]}, style=style)
    assert [c.align for c in t.col_spec] == ["left", "center"]
    t = rr.rtftable({"Parameter": ["Age"], "Value": ["75.1"]},
                    style=rr.rtf_table_style(align="left"))
    assert [c.align for c in t.col_spec] == ["left", "left"]
