"""Tests for the full-featured great_tables (GT) adapter.

Covers: multi-level/nested spanners, tab_style cell styles (text + borders,
including the transparent-border gotcha), row groups as indented stub rows,
footnotes / source notes, title + subtitle, cols_label, hidden columns,
fmt_* rendered values, widths, and the read_meta token mechanism.
"""

import pytest

import rtfreporter as rr
from rtfreporter import RtfDocument
from rtfreporter.borders import Border
from rtfreporter.gt_adapter import (
    GT_META_TOKENS,
    _border_side_from_decl,
    _normalize_color,
    gt_to_result,
    is_gt,
    resolve_meta_tokens,
)
from rtfreporter.table import HeaderRow

pytest.importorskip("pandas")
pytest.importorskip("great_tables")

import pandas as pd  # noqa: E402
from great_tables import GT, loc, style  # noqa: E402


@pytest.fixture
def base_df():
    return pd.DataFrame(
        {
            "grp": ["A", "A", "B"],
            "lbl": ["x", "y", "z"],
            "n": [1, 2, 3],
            "pct": [0.1, 0.25, 1.0],
        }
    )


# -- detection & tokens -------------------------------------------------------


def test_is_gt_true_and_false(base_df):
    assert is_gt(GT(base_df))
    assert not is_gt(base_df)
    assert not is_gt({"a": [1]})


def test_resolve_meta_tokens_variants():
    assert resolve_meta_tokens(True, GT_META_TOKENS, "gt") == GT_META_TOKENS
    assert resolve_meta_tokens(False, GT_META_TOKENS, "gt") == ()
    assert resolve_meta_tokens(None, GT_META_TOKENS, "gt") == ()
    assert resolve_meta_tokens("titles", GT_META_TOKENS, "gt") == ("titles",)
    assert resolve_meta_tokens(["titles", "styles"], GT_META_TOKENS, "gt") == (
        "titles",
        "styles",
    )


def test_resolve_meta_tokens_rejects_unknown():
    with pytest.raises(ValueError, match="Unknown gt read_meta token"):
        resolve_meta_tokens(["nope"], GT_META_TOKENS, "gt")


# -- rendered / formatted body ------------------------------------------------


def test_fmt_values_are_read(base_df):
    t = GT(base_df).fmt_percent("pct", decimals=1)
    tbl = rr.as_rtftable(t)
    pct_col = tbl.column_names.index("pct")
    assert [r[pct_col] for r in tbl.rows] == ["10.0%", "25.0%", "100.0%"]


def test_hidden_columns_dropped(base_df):
    t = GT(base_df).cols_hide("pct")
    tbl = rr.as_rtftable(t)
    assert "pct" not in tbl.column_names
    assert "n" in tbl.column_names


def test_cols_label_used(base_df):
    t = GT(base_df).cols_label(n="Count", pct="Percent")
    tbl = rr.as_rtftable(t)
    labels = tbl.col_header[-1].labels
    assert "Count" in labels and "Percent" in labels


# -- spanners -----------------------------------------------------------------


def test_single_spanner(base_df):
    t = GT(base_df).tab_spanner(label="Stats", columns=["n", "pct"])
    tbl = rr.as_rtftable(t)
    assert [h.kind for h in tbl.col_header] == ["spanning", "labels"]
    labelled = [(s.start, s.end, s.label) for s in tbl.col_header[0].spans if s.label]
    assert labelled == [(2, 3, "Stats")]  # offset by leading stub column


def test_multi_level_nested_spanners(base_df):
    t = (
        GT(base_df)
        .tab_spanner(label="Inner", columns=["n", "pct"])
        .tab_spanner(label="Outer", columns=["n", "pct"], level=1)
    )
    tbl = rr.as_rtftable(t)
    kinds = [h.kind for h in tbl.col_header]
    assert kinds == ["spanning", "spanning", "labels"]
    # Outer (higher level) is rendered above Inner.
    top = [s.label for s in tbl.col_header[0].spans if s.label]
    mid = [s.label for s in tbl.col_header[1].spans if s.label]
    assert top == ["Outer"] and mid == ["Inner"]


def test_spanner_reordered_columns_render_contiguous(base_df):
    # great_tables moves spanned columns to be adjacent; the span must cover a
    # single contiguous run in the reshaped body.
    t = GT(base_df).tab_spanner(label="Split", columns=["lbl", "pct"])
    tbl = rr.as_rtftable(t)
    span = next(
        s
        for h in tbl.col_header
        if h.kind == "spanning"
        for s in h.spans
        if s.label == "Split"
    )
    assert span.end - span.start == 1  # exactly two adjacent columns


def test_noncontiguous_spanner_skipped_direct():
    # Directly exercise the contiguity guard via the internal builder.
    from rtfreporter.gt_adapter import _spanner_rows

    class _Sp:
        spanner_level = 0
        spanner_id = "S"
        spanner_label = "S"
        vars = ["a", "c"]

    class _FakeGT:
        _spanners = [_Sp()]

    rows = _spanner_rows(_FakeGT(), default_vars=["a", "b", "c"], stub_off=0, ncols=3, sty=None)
    labelled = [s.label for h in rows for s in h.spans if s.label]
    assert "S" not in labelled


# -- row groups ---------------------------------------------------------------


def test_row_groups_as_indented_stub(base_df):
    t = GT(base_df, rowname_col="lbl", groupname_col="grp")
    tbl = rr.as_rtftable(t)
    stub = [r[0] for r in tbl.rows]
    # Group label rows are un-indented; children indented by stub_indent (4).
    assert stub == ["A", "    x", "    y", "B", "    z"]
    # Group-label rows blank their non-stub cells.
    assert tbl.rows[0][1:] == [None, None]


def test_row_groups_preserve_group_order():
    df = pd.DataFrame({"grp": ["B", "A", "B"], "lbl": ["w", "x", "y"], "n": [1, 2, 3]})
    t = GT(df, rowname_col="lbl", groupname_col="grp")
    tbl = rr.as_rtftable(t)
    stub = [r[0] for r in tbl.rows]
    assert stub == ["B", "    w", "    y", "A", "    x"]


# -- tab_style: text ----------------------------------------------------------


def test_body_text_style_bold(base_df):
    t = GT(base_df).tab_style(
        style=style.text(weight="bold"), locations=loc.body(columns="n", rows=[0])
    )
    tbl = rr.as_rtftable(t)
    j = tbl.column_names.index("n")
    assert tbl.cell_styles[0]["bold"][j] is True
    assert all(cs is None or "bold" not in cs for cs in tbl.cell_styles[1:])


def test_body_text_color_and_align(base_df):
    t = GT(base_df).tab_style(
        style=style.text(color="#003366", align="center"),
        locations=loc.body(columns="pct", rows=[2]),
    )
    tbl = rr.as_rtftable(t)
    j = tbl.column_names.index("pct")
    assert tbl.cell_styles[2]["color"][j] == "#003366"
    assert tbl.cell_styles[2]["align"][j] == "center"


def test_body_style_row_mapping_with_groups(base_df):
    # Style targets data-row 2 (value z, group B); must land on the rendered row.
    t = GT(base_df, rowname_col="lbl", groupname_col="grp").tab_style(
        style=style.text(weight="bold"), locations=loc.body(columns="n", rows=[2])
    )
    tbl = rr.as_rtftable(t)
    j = tbl.column_names.index("n")
    # Rendered order: [A], x, y, [B], z  -> z is output row 4.
    assert tbl.cell_styles[4]["bold"][j] is True


# -- tab_style: borders -------------------------------------------------------


def test_body_border_style(base_df):
    t = GT(base_df).tab_style(
        style=style.borders(sides="bottom", color="red", style="dashed", weight="2px"),
        locations=loc.body(columns="n", rows=[1]),
    )
    tbl = rr.as_rtftable(t)
    j = tbl.column_names.index("n")
    b = tbl.cell_styles[1]["border"][j]
    assert isinstance(b, Border)
    assert b.bottom.style == "dash"
    assert b.bottom.width == 30  # 2px * 15
    assert b.bottom.color == "#FF0000"


def test_transparent_border_yields_no_border(base_df):
    t = GT(base_df).tab_style(
        style=style.borders(sides="all", color="transparent"),
        locations=loc.body(columns="n", rows=[0]),
    )
    tbl = rr.as_rtftable(t)
    # A transparent border carries no author intent -> no cell_styles produced.
    assert tbl.cell_styles is None or all(
        cs is None or "border" not in cs for cs in tbl.cell_styles
    )


def test_zero_alpha_hex_border_yields_no_border():
    assert _border_side_from_decl("#12345600", "solid", "1px") is None


def test_black_border_omits_color():
    side = _border_side_from_decl("#000000", "solid", "1px")
    assert side is not None and side.color is None


def test_pt_border_width_conversion():
    side = _border_side_from_decl("#111111", "solid", "2pt")
    assert side.width == 40  # 2pt * 20


# -- column-label styles ------------------------------------------------------


def test_label_text_style_to_header_spec(base_df):
    t = GT(base_df).tab_style(
        style=style.text(weight="bold", align="center"),
        locations=loc.column_labels(columns="n"),
    )
    tbl = rr.as_rtftable(t)
    j = tbl.column_names.index("n")
    assert tbl.col_spec[j].header_bold is True
    assert tbl.col_spec[j].header_align == "center"


def test_label_border_promotes_labels_to_spanning(base_df):
    t = GT(base_df).tab_style(
        style=style.borders(sides="bottom", color="#00AA00"),
        locations=loc.column_labels(columns="pct"),
    )
    tbl = rr.as_rtftable(t)
    # The bottom label row is promoted to single-column spanning cells.
    bottom = tbl.col_header[-1]
    assert bottom.kind == "spanning"
    j = tbl.column_names.index("pct")
    cell = next(c for c in bottom.spans if c.start == j)
    assert cell.border is not None and cell.border.bottom.color == "#00AA00"


# -- titles / footnotes -------------------------------------------------------


def test_title_and_subtitle(base_df):
    t = GT(base_df).tab_header(title="Table 1", subtitle="Demographics")
    tbl = rr.as_rtftable(t)
    assert tbl.titles == ["Table 1", "Demographics"]


def test_footnotes_and_source_notes(base_df):
    t = (
        GT(base_df)
        .tab_source_note("Source: ADSL")
        .tab_footnote("a note", locations=loc.body(columns="n", rows=[0]))
    )
    tbl = rr.as_rtftable(t)
    assert "a note" in tbl.footnotes
    assert "Source: ADSL" in tbl.footnotes


# -- alignment & widths -------------------------------------------------------


def test_alignment_read_into_col_spec(base_df):
    t = GT(base_df)  # numeric columns default to right-aligned
    tbl = rr.as_rtftable(t)
    j = tbl.column_names.index("n")
    assert tbl.col_spec[j].align == "right"


def test_px_widths_to_twips(base_df):
    t = GT(base_df.drop(columns=["grp", "lbl"])).cols_width({"n": "80px", "pct": "120px"})
    tbl = rr.as_rtftable(t)
    assert tbl.column_widths_twips == [80 * 15, 120 * 15]


def test_pct_widths_to_rel(base_df):
    t = GT(base_df.drop(columns=["grp", "lbl"])).cols_width({"n": "40%", "pct": "60%"})
    tbl = rr.as_rtftable(t)
    assert tbl.col_rel_width == [40.0, 60.0]


def test_partial_widths_dropped(base_df):
    t = GT(base_df.drop(columns=["grp", "lbl"])).cols_width({"n": "80px"})
    tbl = rr.as_rtftable(t)
    assert tbl.column_widths_twips is None and tbl.col_rel_width is None


# -- read_meta gating ---------------------------------------------------------


def test_read_meta_false_clean_body_only(base_df):
    t = (
        GT(base_df, rowname_col="lbl", groupname_col="grp")
        .tab_header(title="T")
        .tab_spanner(label="S", columns=["n", "pct"])
        .tab_style(style=style.text(weight="bold"), locations=loc.body(columns="n", rows=[0]))
    )
    tbl = rr.as_rtftable(t, read_meta=False)
    # Body still reshaped (groups -> indented stub), but no metadata channels.
    assert [r[0] for r in tbl.rows] == ["A", "    x", "    y", "B", "    z"]
    assert tbl.titles is None
    assert tbl.cell_styles is None
    assert all(h.kind == "labels" for h in tbl.col_header)


def test_read_meta_token_subset(base_df):
    t = GT(base_df).tab_header(title="Only Title").tab_spanner(label="S", columns=["n", "pct"])
    tbl = rr.as_rtftable(t, read_meta=["titles"])
    assert tbl.titles == ["Only Title"]
    # Spanning not requested -> no spanning header row.
    assert all(h.kind == "labels" for h in tbl.col_header)


# -- pagination + styles keep aligned ----------------------------------------


def test_pagination_keeps_cell_styles_aligned():
    df = pd.DataFrame({"lbl": list("abcd"), "n": [1, 2, 3, 4]})
    t = GT(df).tab_style(
        style=style.text(weight="bold"), locations=loc.body(columns="n", rows=[2])
    )
    pages = rr.as_rtftables(t, split="rows", split_rows=2)
    assert len(pages) == 2
    j = pages[1].column_names.index("n")
    # data-row 2 ('c') is the first row of page 2.
    assert pages[1].cell_styles[0]["bold"][j] is True
    assert pages[0].cell_styles is None or all(
        cs is None or "bold" not in cs for cs in pages[0].cell_styles
    )


def test_stub_cols_rejected_for_gt(base_df):
    t = GT(base_df).tab_style(
        style=style.text(weight="bold"), locations=loc.body(columns="n", rows=[0])
    )
    with pytest.raises(ValueError, match="not supported for great_tables"):
        rr.as_rtftables(t, stub_vars=[0])


# -- end-to-end ---------------------------------------------------------------


def test_full_featured_end_to_end(base_df):
    t = (
        GT(base_df, rowname_col="lbl", groupname_col="grp")
        .tab_header(title="Table X", subtitle="sub")
        .tab_spanner(label="Stats", columns=["n", "pct"])
        .cols_label(n="Count", pct="Percent")
        .fmt_percent("pct", decimals=1)
        .tab_style(style=style.text(weight="bold"), locations=loc.body(columns="n", rows=[0]))
        .tab_source_note("Source: xyz")
    )
    tbl = rr.as_rtftable(t)
    rtf = RtfDocument().add_table(tbl).to_rtf()
    assert rtf.startswith("{\\rtf1")
    assert rtf.count("{") == rtf.count("}")


def test_normalize_color_helpers():
    assert _normalize_color("#abc") == "#AABBCC"
    assert _normalize_color("red") == "#FF0000"
    assert _normalize_color("#11223344") == "#112233"
    assert _normalize_color("not-a-color") is None
    assert _normalize_color(None) is None


def test_gt_to_result_direct(base_df):
    res = gt_to_result(GT(base_df), read_meta=True)
    assert res.rows and res.column_names
    assert isinstance(res.col_header[-1], HeaderRow)
