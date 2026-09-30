"""paginate_cols(), compared byte-for-byte with the R package
(``data-raw/xcheck/paginate_cols_r.R`` writes ``tests/xcheck_golden/paginate_cols/``)."""

import warnings
from pathlib import Path

import pytest

import rtfreporter as rr

GOLDEN = Path(__file__).parent / "xcheck_golden" / "paginate_cols"
WIDE = {"Param": ["Hgb", "ALT", "AST", "Bili"],
        "Placebo____Day 1": ["13", "30", "25", "0.5"],
        "Placebo____Day 7": ["12", "31", "26", "0.6"],
        "Drug____Day 1": ["14", "29", "24", "0.4"],
        "Drug____Day 7": ["15", "28", "23", "0.7"]}


def _rtf(pages, **kw):
    return rr.rtf_tables(rr.rtf_document(), pages, **kw).to_rtf()


def _golden(name):
    return (GOLDEN / f"{name}.rtf").read_text(encoding="ascii").replace("\r\n", "\n")


def test_at_across_and_down_match_r():
    rows2 = rr.as_rtftables(WIDE, header_sep=None, split="rows", split_rows=2)
    assert _rtf(rr.paginate_cols(rows2, at="Drug____Day 1")) == _golden("at_across")
    assert _rtf(rr.paginate_cols(rows2, at="Drug____Day 1", page_order="down")) \
        == _golden("at_down")


def test_by_names_with_groups_matches_r():
    long = {"Arm": ["Low"] * 4 + ["High"] * 4, **{k: v * 2 for k, v in WIDE.items()}}
    grp = rr.as_rtftables(long, header_sep=None, split="by_value", group_col="Arm",
                          drop_cols="Arm")
    pages = rr.paginate_cols(grp, by="____", col_header="names", page_order="down")
    assert _rtf(pages, auto_title=True) == _golden("by_names_groups")


def _t3():
    t = rr.rtftable(WIDE, col_rel_width=[2, 1, 1, 1.5, 1.5],
                    cell_styles=[None, {"bold": [None, None, True, None, True]}, None, None])
    return rr.set_decimal_split(t, cols=[1, 3])


def test_widths_fill_and_keep_match_r():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fill = rr.paginate_cols(_t3(), cols=[["Placebo____Day 1", "Placebo____Day 7"],
                                             ["Drug____Day 1"], ["Drug____Day 7"]])
    assert _rtf(fill) == _golden("widths_fill")
    keep = rr.paginate_cols(_t3(), at=["Placebo____Day 7", "Drug____Day 1"], width="keep")
    assert _rtf(keep) == _golden("widths_keep")


def test_sliced_header_matches_r():
    hdr = [[rr.col_cell(0, ""), rr.col_cell((1, 2), "Placebo"), rr.col_cell((3, 4), "Drug")],
           ["Parameter", "D1", "D7", "D1", "D7"]]
    pages = rr.paginate_cols(rr.rtftable(WIDE), at="Placebo____Day 7", col_header=hdr)
    assert _rtf(pages) == _golden("sliced_header")


def test_arguments_are_checked():
    t = rr.rtftable(WIDE)
    with pytest.raises(ValueError, match="not at and cols"):
        rr.paginate_cols(t, at=1, cols=[[1]])
    with pytest.raises(ValueError, match="is required"):
        rr.paginate_cols(t)
    with pytest.raises(ValueError, match="nothing before column 0"):
        rr.paginate_cols(t, at=0)
    with pytest.raises(ValueError, match="not an axis"):
        rr.paginate_cols(t, at=2, page_order=["cols", "pages"])
    hdr = [[rr.col_cell(0, ""), rr.col_cell((1, 4), "All")], list(WIDE)]
    with pytest.raises(ValueError, match="would break"):
        rr.paginate_cols(rr.rtftable(WIDE, col_header=hdr), at=3, allow_span_break=False)
    with pytest.warns(UserWarning, match="wider than the sheet"):
        rr.paginate_cols(t, cols=[[1], [2, 3, 4]])
