"""Phase 4: post-hoc helpers, options machinery, table style, widths, stub."""

import os

import pytest

import rtfreporter as rr
from rtfreporter import col_cell


@pytest.fixture(autouse=True)
def _reset_options():
    rr.rtfreporter_reset_defaults()
    yield
    rr.rtfreporter_reset_defaults()


# -- options machinery -------------------------------------------------------


def test_options_snapshot_defaults():
    snap = rr.rtfreporter_options()
    assert snap["font"] == "Courier"
    assert snap["page.margin_left_in"] == 0.75
    assert snap["markup"] == "script"


def test_options_set_returns_prior():
    prior = rr.rtfreporter_options(font="Arial")
    assert prior["font"] == "Courier"
    assert rr.rtfreporter_options()["font"] == "Arial"


def test_options_unknown_key_raises():
    with pytest.raises(KeyError):
        rr.rtfreporter_options(nonsense=1)


def test_reset_defaults():
    rr.rtfreporter_options(font="Arial")
    restored = rr.rtfreporter_reset_defaults()
    assert restored["font"] == "Courier"
    assert rr.rtfreporter_options()["font"] == "Courier"


def test_option_resolution_order_in_rtf_page():
    rr.rtfreporter_options(**{"page.margin_left_in": 0.5})
    assert rr.rtf_page().margin_left_in == 0.5  # option beats factory
    assert rr.rtf_page(margin_left_in=1.0).margin_left_in == 1.0  # explicit beats option


def test_rtf_default_format_uses_option():
    rr.rtfreporter_options(markup="all")
    assert rr.rtf_default_format().markup == "all"
    assert rr.rtf_default_format(markup="script").markup == "script"


def test_rtf_default_format_validation():
    with pytest.raises(ValueError):
        rr.rtf_default_format(row_height_twips=-5)


# -- text_width / auto_col_widths --------------------------------------------


def test_text_width_scales_with_size():
    single = rr.text_width_in("abc")[0]
    doubled = rr.text_width_in("abc", size_half_points=36)[0]
    assert doubled == pytest.approx(single * 2)


def test_text_width_list_and_none():
    assert rr.text_width_in(["a", None, "abc"]) == pytest.approx(
        [rr.text_width_in("a")[0], 0.0, rr.text_width_in("abc")[0]]
    )


def test_auto_col_widths_min_width():
    widths = rr.auto_col_widths({"A": ["x"], "B": ["y"]}, min_col_width_twips=720)
    assert all(w >= 720 for w in widths)


def test_auto_col_widths_scales_to_table_width():
    widths = rr.auto_col_widths(
        {"A": ["xxxxx"], "B": ["y"]}, table_width_twips=5000
    )
    assert sum(widths) == 5000


def test_auto_col_widths_protect_cols():
    widths = rr.auto_col_widths(
        {"label": ["aaaaaaaaaa"], "v1": ["1"], "v2": ["2"]},
        table_width_twips=6000,
        protect_cols=[0],
    )
    assert sum(widths) == 6000


# -- stub_cols ----------------------------------------------------------------


def test_stub_cols_basic_layout():
    fr = rr.stub_cols(
        {"soc": ["Cardiac", "Cardiac", "GI"], "pt": ["AFib", "Brady", "Nausea"],
         "n": ["3", "1", "5"]},
        vars=["soc", "pt"],
    )
    assert fr.column_names == ["soc / pt", "n"]
    assert fr.rows[0] == ["Cardiac", None]  # un-indented label row
    assert fr.rows[1][0].endswith("AFib") and fr.rows[1][0].startswith(" ")
    assert fr.rows[3] == ["GI", None]


def test_stub_cols_custom_label():
    fr = rr.stub_cols({"a": ["x"], "b": ["y"], "n": ["1"]}, vars=["a", "b"], label="Grp")
    assert fr.column_names[0] == "Grp"


def test_stub_cols_group_summary_empty_leaf():
    # A summary row (empty leaf) folds its stats onto the SOC label row.
    fr = rr.stub_cols(
        {"soc": ["Cardiac", "Cardiac"], "pt": ["", "AFib"], "n": ["4", "3"]},
        vars=["soc", "pt"],
        group_summary="empty",
    )
    assert fr.rows[0] == ["Cardiac", "4"]  # summary folded onto label row


def test_stub_cols_requires_two_vars():
    with pytest.raises(ValueError, match="at least two"):
        rr.stub_cols({"a": ["x"], "n": ["1"]}, vars=["a"])


def test_stub_cols_feeds_rtftable():
    fr = rr.stub_cols({"a": ["x", "x"], "b": ["p", "q"], "n": [1, 2]}, vars=["a", "b"])
    tbl = rr.rtftable(fr)
    assert tbl.column_names == ["a / b", "n"]


# -- rtf_table_style family ---------------------------------------------------


def test_rtf_table_style_tfl_border():
    st = rr.rtf_table_style_tfl()
    assert st.border.header is not None


def test_rtf_table_style_with_override():
    st = rr.rtf_table_style_with(rr.rtf_table_style_tfl(), align="center", bold=True)
    assert st.align == "center" and st.bold is True


def test_rtf_table_style_with_unknown_field():
    with pytest.raises(ValueError, match="Unknown style field"):
        rr.rtf_table_style_with(rr.rtf_table_style_tfl(), nope=1)


def test_style_applies_text_defaults_to_cols():
    st = rr.rtf_table_style(bold=True, align="center", header_bold=True)
    tbl = rr.rtftable({"A": ["x"], "B": ["y"]}, style=st)
    assert all(c.bold for c in tbl.col_spec)
    assert all(c.align == "center" for c in tbl.col_spec)
    assert all(c.header_bold for c in tbl.col_spec)


def test_explicit_col_spec_overrides_style():
    st = rr.rtf_table_style(bold=True)
    tbl = rr.rtftable({"A": ["x"], "B": ["y"]}, style=st,
                      col_spec=[{"col": 0, "bold": False}])
    assert tbl.col_spec[0].bold is False
    assert tbl.col_spec[1].bold is True


# -- rtf_border_with ----------------------------------------------------------


def test_rtf_border_with_replaces_side():
    b = rr.rtf_border(top=rr.rtf_border_side())
    b2 = rr.rtf_border_with(b, bottom=rr.rtf_border_side())
    assert b2.top is not None and b2.bottom is not None


def test_rtf_border_with_none_start():
    b = rr.rtf_border_with(None, top=rr.rtf_border_side())
    assert b.top is not None and b.bottom is None


def test_rtf_border_with_bad_side():
    with pytest.raises(TypeError):
        rr.rtf_border_with(rr.rtf_border(), top="notaside")


# -- post-hoc header verbs ----------------------------------------------------


def _tbl():
    return rr.rtftable({"row_label": ["A", "B"], "g1": [1, 2], "g2": [3, 4], "Total": [5, 6]})


def test_rtf_columns():
    assert rr.rtf_columns(_tbl()) == ["row_label", "g1", "g2", "Total"]


def test_rtf_columns_on_page_list():
    pages = rr.as_rtftables({"A": [1, 2], "B": [3, 4]}, split="rows", split_rows=1)
    assert rr.rtf_columns(pages) == ["A", "B"]


def test_set_col_header_replaces():
    t = rr.set_col_header(
        _tbl(),
        [col_cell("row_label", ""), col_cell(("g1", "g2"), "Treatment"), col_cell("Total", "")],
        ["Category", "Low", "High", "Total"],
    )
    assert t.col_header[0].kind == "spanning"
    assert t.col_header[1].kind == "labels"


def test_set_col_header_align():
    t = rr.set_col_header(_tbl(), ["a", "b", "c", "d"], align="right")
    assert all(c.header_align == "right" for c in t.col_spec)


def test_set_col_header_align_bad_length():
    with pytest.raises(ValueError, match="length"):
        rr.set_col_header(_tbl(), ["a", "b", "c", "d"], align=["left", "right"])


def test_add_header_row_top_and_copy():
    orig = _tbl()
    t = rr.add_header_row(orig, ["x", "y", "z", "w"], position="top")
    assert len(t.col_header) == len(orig.col_header) + 1
    assert len(orig.col_header) == 1  # original untouched


def test_set_header_cell_merges():
    t = rr.set_header_cell(_tbl(), col_cell(("g1", "g2"), "Stats"), row=0)
    spans = [(s.start, s.end, s.label) for s in t.col_header[0].spans]
    assert (1, 2, "Stats") in spans


def test_set_header_cell_boundary_error():
    # Spanning header of g1..Total; splitting it mid-span must error.
    t = rr.set_col_header(_tbl(), [col_cell(0, ""), col_cell((1, 3), "All")], ["a", "b", "c", "d"])
    with pytest.raises(ValueError, match="boundaries"):
        rr.set_header_cell(t, col_cell((1, 2), "X"), row=0)


def test_set_header_cell_requires_row():
    with pytest.raises(TypeError):
        rr.set_header_cell(_tbl(), col_cell(0, "x"))


# -- col_header_from_names / add_col_header_row ------------------------------


def test_col_header_from_names_spanning():
    ch = rr.col_header_from_names(
        ["Item", "Drug A____N", "Drug A____Mean", "Drug B____N", "Drug B____Mean"]
    )
    assert ch[0].kind == "spanning"


def test_col_header_from_names_flat():
    ch = rr.col_header_from_names(["A", "B", "C"])
    assert len(ch) == 1 and ch[0].kind == "labels"


def test_add_col_header_row_top_bottom():
    assert rr.add_col_header_row(["A", "B"], ["x", "y"], position="top") == [["x", "y"], "A", "B"]
    assert rr.add_col_header_row(["A", "B"], ["x", "y"]) == ["A", "B", ["x", "y"]]


# -- collapse_repeats ---------------------------------------------------------


def test_collapse_repeats_table():
    tbl = rr.rtftable({"grp": ["A", "A", "B"], "v": [1, 2, 3]})
    out = rr.collapse_repeats(tbl, ["grp"])
    assert [r[0] for r in out.rows] == ["A", "", "B"]


def test_collapse_repeats_pages_independent():
    pages = rr.as_rtftables({"grp": ["A", "A", "A", "A"], "v": [1, 2, 3, 4]},
                            split="rows", split_rows=2)
    out = rr.collapse_repeats(pages, ["grp"])
    assert [r[0] for r in out[0].rows] == ["A", ""]
    assert out[1].rows[0][0] == "A"  # run restarts per page


# -- combine_sections ---------------------------------------------------------


def test_combine_sections_names_first_page():
    dm = rr.as_rtftables({"C": ["Age"], "V": ["75"]})
    ae = rr.as_rtftables({"C": ["a", "b", "c"], "V": [1, 2, 3]}, split="rows", split_rows=2)
    sec = rr.combine_sections(Demographics=dm, AdverseEvents=ae)
    assert [t.name for t in sec] == ["Demographics", "AdverseEvents", None]


def test_combine_sections_rejects_non_table():
    with pytest.raises(TypeError):
        rr.combine_sections(bad=[123])


# -- set_blank_rows -----------------------------------------------------------


def test_set_blank_rows_between_groups():
    fr = rr.set_blank_rows(
        {"g": ["A", "A", "B", "B"], "v": [1, 2, 3, 4]},
        blank_rows="between_groups",
        blank_row_first=True,
    )
    tbl = rr.rtftable(fr)
    assert tbl.blank_rows == [0, 2]


def test_set_blank_rows_explicit_positions():
    fr = rr.set_blank_rows({"a": [1, 2, 3]}, blank_rows=[1])
    tbl = rr.rtftable(fr)
    assert 2 in tbl.blank_rows  # after data row 1 -> internal 2


def test_set_blank_rows_group_by_indent():
    """All four R group_by modes work here too."""
    nbsp = chr(0xA0)
    frame = rr.set_blank_rows(
        {"g": ["SOC1", nbsp + "PT a", "SOC2", nbsp + "PT b"]},
        blank_rows="between_groups",
        group_by="indent",
    )
    assert rr.rtftable(frame).blank_rows == [2]


def test_set_blank_rows_rejects_an_unknown_group_by():
    with pytest.raises(ValueError, match="group_by"):
        rr.set_blank_rows({"g": ["A", "B"]}, blank_rows="between_groups", group_by="sideways")


# -- update_header_row / update_footer_row ------------------------------------


def test_update_header_row_replace_and_copy():
    h = rr.rtf_header([{"l": "P", "r": "Page {AUTO_PAGE}"}])
    h2 = rr.update_header_row(h, 1, {"c": "Draft"})
    assert len(h2.rows) == 2
    assert len(h.rows) == 1  # original untouched


def test_update_header_row_fills_gap():
    h = rr.rtf_header([{"l": "P"}])
    h2 = rr.update_header_row(h, 3, {"c": "x"})
    assert len(h2.rows) == 4
    assert h2.rows[1] == {"c": ""}


def test_update_footer_row():
    f = rr.rtf_footer([{"c": "a"}])
    f2 = rr.update_footer_row(f, 0, {"c": "b"})
    assert f2.rows[0] == {"c": "b"}


def test_update_header_row_negative():
    with pytest.raises(ValueError):
        rr.update_header_row(rr.rtf_header([{"c": "x"}]), -1, {"c": "y"})


# -- rtf_replace_text ---------------------------------------------------------


def test_rtf_replace_text_to_new_file(tmp_path):
    src = tmp_path / "t.rtf"
    src.write_text("{\\rtf1 DRAFT vX.Y}")
    out = rr.rtf_replace_text(str(src), ["DRAFT", "vX.Y"], ["FINAL", "v1.0"],
                              output_file=str(tmp_path / "o.rtf"))
    assert "FINAL v1.0" in open(out).read()


def test_rtf_replace_text_in_place_backup(tmp_path):
    src = tmp_path / "t.rtf"
    src.write_text("hello DRAFT")
    rr.rtf_replace_text(str(src), "DRAFT", "FINAL")
    assert "FINAL" in src.read_text()
    assert os.path.exists(str(src) + ".bak")


def test_rtf_replace_text_case_insensitive(tmp_path):
    src = tmp_path / "t.rtf"
    src.write_text("Draft draft DRAFT")
    rr.rtf_replace_text(str(src), "draft", "X", case_insensitive=True, backup=False)
    assert src.read_text() == "X X X"


def test_rtf_replace_text_missing_file():
    with pytest.raises(FileNotFoundError):
        rr.rtf_replace_text("/nonexistent/nope.rtf", "a", "b")


def test_rtf_replace_text_length_mismatch(tmp_path):
    src = tmp_path / "t.rtf"
    src.write_text("a b")
    with pytest.raises(ValueError):
        rr.rtf_replace_text(str(src), ["a", "b"], ["x", "y", "z"])


# -- rtf_header_source --------------------------------------------------------


def test_rtf_header_source_snippet():
    t = rr.set_col_header(_tbl(), ["Cat", "Low", "High", "Total"])
    src = rr.rtf_header_source(t)
    assert "set_col_header(" in src


def test_rtf_config_merges_page():
    doc = rr.rtf_document()
    doc2 = rr.rtf_config(doc, page={"paper_size": "a4"})
    assert doc2.page.paper_size == "a4"
    assert doc.page.paper_size == "letter"  # original untouched


def test_rtf_config_font_table_not_supported():
    with pytest.raises(NotImplementedError):
        rr.rtf_config(rr.rtf_document(), font_table={})
