"""R-aligned public API: renamed constructors, the pipe API, and new arguments."""

import pytest

import rtfreporter as rr
from rtfreporter import (
    AFTER_LAST,
    BEFORE_FIRST,
    Border,
    BorderSide,
    TableBorder,
    as_rtftables,
    col_cell,
    generate_rtfreport,
    rtf_border,
    rtf_border_bottom,
    rtf_border_box,
    rtf_border_none,
    rtf_border_side,
    rtf_border_tfl,
    rtf_border_top,
    rtf_col_header,
    rtf_document,
    rtf_figures,
    rtf_footer,
    rtf_footnotes,
    rtf_header,
    rtf_page,
    rtf_section,
    rtf_table_border,
    rtf_tables,
    rtf_titles,
    rtftable,
)

# -- renamed border constructors ---------------------------------------------


def test_rtf_border_side_is_border_side():
    assert isinstance(rtf_border_side("double", 30, "#112233"), BorderSide)


def test_rtf_border_constructors_return_expected_types():
    assert isinstance(rtf_border(top=rtf_border_side()), Border)
    assert isinstance(rtf_border_none(), Border)
    assert isinstance(rtf_border_top(), Border)
    assert isinstance(rtf_border_bottom(), Border)
    assert isinstance(rtf_border_box(), Border)
    assert isinstance(rtf_border_tfl(), TableBorder)


def test_rtf_table_border_zones():
    tb = rtf_table_border(header=rtf_border_top(), body=rtf_border_bottom())
    assert isinstance(tb, TableBorder)
    assert tb.header is not None and tb.body is not None


def test_old_names_are_gone():
    # Clean break: the un-prefixed constructor names must not be exported.
    for name in ("border", "border_side", "header", "footer", "document"):
        assert name not in rr.__all__, f"{name} should have been removed from __all__"


# -- rtf_page / rtf_col_header ------------------------------------------------


def test_rtf_page_builds_page():
    p = rtf_page(paper_size="a4", orientation="portrait")
    geo = p.geometry()
    assert geo["orientation"] == "portrait"


def test_rtf_col_header_collects_rows():
    hdr = rtf_col_header(
        [col_cell(0, ""), col_cell((1, 2), "Treatment")],
        ["Item", "N", "Mean"],
    )
    t = rtftable({"a": [1], "b": [2], "c": [3]}, col_header=hdr)
    assert len(t.col_header) == 2


# -- the pipe API -------------------------------------------------------------


def test_pipe_api_builds_valid_rtf(tmp_path):
    doc = rtf_document()
    doc = rtf_tables(doc, {"Subject": ["001", "002"], "Age": [34, 45]})
    doc = rtf_section(doc, header=rtf_header([{"l": "Proto", "r": "Page {AUTO_PAGE}"}]),
                      footer=rtf_footer([{"c": "CONF"}]))
    doc = rtf_titles(doc, ["Demographics"])
    doc = rtf_footnotes(doc, ["Source: ADSL"])
    out = tmp_path / "r.rtf"
    path = generate_rtfreport(doc, str(out))
    rtf = out.read_text()
    assert path == str(out)
    assert rtf.startswith("{\\rtf1")
    assert rtf.count("{") == rtf.count("}")


def test_rtf_tables_accepts_list_of_frames():
    doc = rtf_tables(rtf_document(), [rtftable({"A": [1]}), rtftable({"A": [2]})])
    assert len(doc._pages) == 2


def test_rtf_tables_single_row_dict_list_is_one_table():
    doc = rtf_tables(rtf_document(), [{"A": 1}, {"A": 2}])
    assert len(doc._pages) == 1


def test_rtf_titles_common_to_all():
    doc = rtf_tables(rtf_document(), [rtftable({"A": [1]}), rtftable({"A": [2]})])
    doc = rtf_titles(doc, ["Common Title"])
    assert doc._pages[0]["title"] == "Common Title"
    assert doc._pages[1]["title"] == "Common Title"


def test_rtf_titles_before_content_raises():
    with pytest.raises(ValueError):
        rtf_titles(rtf_document(), ["x"])


def test_generate_rtfreport_no_overwrite(tmp_path):
    out = tmp_path / "e.rtf"
    out.write_text("existing")
    with pytest.raises(FileExistsError):
        generate_rtfreport(rtf_tables(rtf_document(), {"A": [1]}), str(out))


def test_rtf_figures_requires_document():
    with pytest.raises(TypeError):
        rtf_figures("notadoc", [])


# -- row_title ----------------------------------------------------------------


def test_row_title_default_first_col_left_rest_center():
    t = rtftable({"A": [1], "B": [2], "C": [3]})
    assert t.col_spec[0].align == "left"
    assert t.col_spec[1].align == "center"
    assert t.col_spec[2].align == "center"


def test_row_title_explicit_multiple():
    t = rtftable({"A": [1], "B": [2], "C": [3]}, row_title=[0, 1])
    assert t.col_spec[0].align == "left"
    assert t.col_spec[1].align == "left"
    assert t.col_spec[2].align == "center"


def test_row_title_by_name():
    t = rtftable({"A": [1], "B": [2]}, row_title="B")
    assert t.col_spec[1].align == "left"
    assert t.col_spec[0].align == "center"


def test_row_title_out_of_range_raises():
    with pytest.raises(ValueError):
        rtftable({"A": [1], "B": [2]}, row_title=5)


def test_col_spec_align_overrides_row_title_default():
    t = rtftable({"A": [1], "B": [2]}, col_spec=[{"col": 0, "align": "right"}])
    assert t.col_spec[0].align == "right"


# -- spanning_header ----------------------------------------------------------


def test_spanning_header_prepended():
    t = rtftable(
        {"A": [1], "B": [2], "C": [3]},
        spanning_header=[{"from": 1, "to": 2, "label": "Treatment", "underline": True}],
    )
    assert t.col_header[0].kind == "spanning"
    span = t.col_header[0].spans[0]
    assert span.start == 1 and span.end == 2 and span.label == "Treatment"
    assert span.border is not None and span.border.bottom is not None


def test_spanning_header_by_name():
    t = rtftable(
        {"A": [1], "B": [2]},
        spanning_header=[{"from": "A", "to": "B", "label": "Both"}],
    )
    assert t.col_header[0].spans[0].label == "Both"


def test_spanning_header_bad_range_raises():
    with pytest.raises(ValueError):
        rtftable({"A": [1], "B": [2]}, spanning_header=[{"from": 1, "to": 0}])


# -- read_attributes ----------------------------------------------------------


def test_read_attributes_folds_blank_rows():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"A": [1, 2, 3]})
    df.attrs["rtf_blank_rows"] = [BEFORE_FIRST, AFTER_LAST]
    t = rtftable(df)
    assert 0 in t.blank_rows and 3 in t.blank_rows


def test_read_attributes_false_ignores():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"A": [1, 2, 3]})
    df.attrs["rtf_blank_rows"] = [BEFORE_FIRST]
    t = rtftable(df, read_attributes=False)
    assert t.blank_rows == []


# -- style --------------------------------------------------------------------


class _DuckStyle:
    border = "none"
    table_align = "center"
    align = "right"
    cell_padding_left_twips = 40


def test_style_applies_defaults_under_explicit_args():
    t = rtftable({"A": [1], "B": [2]}, style=_DuckStyle())
    assert t.table_align == "center"
    assert t.border is None  # style border="none"
    assert t.col_spec[0].align == "right"  # style align wins over row_title
    assert t.cell_padding_left_twips == 40


def test_explicit_arg_overrides_style():
    t = rtftable({"A": [1]}, style=_DuckStyle(), table_align="right")
    assert t.table_align == "right"


# -- table_width_pct_of_writable ---------------------------------------------


def test_table_width_pct_of_writable_fraction():
    t = rtftable({"A": [1]}, table_width_pct_of_writable=0.5)
    assert t.table_width_pct_of_writable == 0.5


def test_table_width_pct_of_writable_out_of_range():
    with pytest.raises(ValueError):
        rtftable({"A": [1]}, table_width_pct_of_writable=1.5)


def test_table_width_pct_and_fraction_conflict():
    with pytest.raises(ValueError):
        rtftable({"A": [1]}, table_width_pct_of_writable=0.5, table_width_pct=50)


# -- as_rtftables new arguments ----------------------------------------------


def test_stub_vars_argument():
    data = {"Cat": ["Sex", "Sex"], "Sub": ["M", "F"], "N": [10, 12]}
    pages = as_rtftables(data, stub_vars=[0, 1], border="none")
    assert len(pages) == 1
    # The stub merged the two hierarchy columns into one leading column.
    assert pages[0].column_names[0] != "Cat" or len(pages[0].column_names) == 2


@pytest.mark.parametrize(
    "kwargs",
    [
        {"group_by": "indent"},
        {"count_blank_rows": True},
        {"auto_width": True},
        {"stub_group_summary": "parent"},
    ],
)
def test_as_rtftables_unimplemented_paths_raise(kwargs):
    with pytest.raises(NotImplementedError):
        as_rtftables({"A": [1, 2]}, **kwargs)


def test_as_rtftables_forwards_table_width_twips():
    pages = as_rtftables({"A": [1, 2]}, table_width_twips=5000, border="none")
    assert pages[0].table_width_twips == 5000
