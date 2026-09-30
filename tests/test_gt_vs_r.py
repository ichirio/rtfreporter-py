"""great_tables input compared byte-for-byte with the R package's gt input
(``data-raw/xcheck/gt_r.R`` writes ``tests/xcheck_golden/gt/``): the source
column names kept verbatim (R #458), and the table's own metadata --
alignment, widths, cell styles, labels, spanners -- following its columns
through ``drop_cols`` and ``stub``."""

from pathlib import Path

import pandas as pd
import pytest

import rtfreporter as rr

gt = pytest.importorskip("great_tables")
from great_tables import loc, style  # noqa: E402

GOLDEN = Path(__file__).parent / "xcheck_golden" / "gt"
SRC = pd.DataFrame({
    "Characteristic": ["Age, Mean (SD)", "Sex, n (%)", "Weight, kg"],
    "Drug A (N=60)": ["54.2 (11.3)", "31 (51.7)", "70.1"],
    "2024 total": ["112", "58", "69.8"],
})
AE = pd.DataFrame({"SOC": ["Cardiac", "Cardiac", "Skin"],
                   "PT": ["Palpitations", "Tachycardia", "Rash"],
                   "n": ["3", "1", "5"]})


def _rtf(pages):
    return rr.rtf_tables(rr.rtf_document(), pages).to_rtf()


def _golden(name):
    return (GOLDEN / f"{name}.rtf").read_text(encoding="ascii").replace("\r\n", "\n")


def test_names_kept_verbatim_matches_r():
    pages = rr.as_rtftables(gt.GT(SRC))
    names = (GOLDEN / "names_verbatim.txt").read_text(encoding="utf-8").splitlines()
    assert pages[0].column_names == names == list(SRC.columns)
    pages = [rr.set_col_header(p, {"Drug A (N=60)": "Drug A"}) for p in pages]
    assert _rtf(pages) == _golden("names_verbatim")


def test_drop_cols_alignment_and_widths_match_r():
    g = (gt.GT(SRC)
         .cols_align("center", columns="Drug A (N=60)")
         .cols_align("right", columns="2024 total")
         .cols_width({"Characteristic": "50%", "Drug A (N=60)": "30%", "2024 total": "20%"}))
    assert _rtf(rr.as_rtftables(g, drop_cols="Drug A (N=60)")) == _golden("drop_align_width")


def test_drop_cols_styles_and_spanner_match_r():
    g = (gt.GT(SRC)
         .tab_spanner("Treatment", columns=["Drug A (N=60)", "2024 total"])
         .tab_style(style.fill(color="#FFFF00"), loc.body(columns="2024 total", rows=[0]))
         .tab_style(style.text(weight="bold"), loc.body(columns="Characteristic", rows=[1])))
    assert _rtf(rr.as_rtftables(g, drop_cols="Drug A (N=60)")) == _golden("drop_styles_spanner")


def test_stub_labels_and_styles_match_r():
    g = (gt.GT(AE)
         .cols_label(n="Count")
         .cols_align("center", columns="n")
         .tab_style(style.text(style="italic"), loc.body(columns="n", rows=[1])))
    pages = rr.as_rtftables(g, stub=rr.stub_spec(["SOC", "PT"]))
    assert _rtf(pages) == _golden("stub_labels_styles")


def test_stub_and_drop_cols_match_r():
    g = gt.GT(AE.assign(ord=["1", "2", "3"])).cols_align("right", columns="n")
    pages = rr.as_rtftables(g, stub=rr.stub_spec(["SOC", "PT"]), drop_cols="ord")
    assert _rtf(pages) == _golden("stub_and_drop")


def test_by_value_stub_keeps_gt_metadata_matches_r():
    g = (gt.GT(AE)
         .cols_label(n="Count")
         .cols_align("center", columns="n")
         .tab_style(style.text(style="italic"), loc.body(columns="n", rows=[1])))
    pages = rr.as_rtftables(g, split="by_value", group_col="SOC",
                            stub=rr.stub_spec(["SOC", "PT"]))
    assert _rtf(pages) == _golden("by_value_stub")
