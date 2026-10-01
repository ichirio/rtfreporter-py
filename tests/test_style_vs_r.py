"""style_body(rows=) and style_header(row=, cols=, label=, border=,
underline=), compared byte-for-byte with the R package
(``data-raw/xcheck/style_r.R`` writes ``tests/xcheck_golden/style/``)."""

import warnings
from pathlib import Path

import rtfreporter as rr

GOLDEN = Path(__file__).parent / "xcheck_golden" / "style"
DF = {"Stat": ["n", "Mean", "SD", "Median"], "A": ["10", "5.1", "1.2", "5.0"],
      "B": ["12", "5.4", "1.1", "5.3"]}


def _rtf(tbl):
    return rr.rtf_tables(rr.rtf_document(), [tbl]).to_rtf()


def _golden(name):
    return (GOLDEN / f"{name}.rtf").read_text(encoding="ascii").replace("\r\n", "\n")


def test_style_body_rows_matches_r():
    t = rr.rtftable(DF)
    t = rr.style_body(t, rows=lambda r: r["Stat"] == "Mean", bold=True, background="#FFFF00")
    t = rr.style_body(t, rows=[2, 3], cols="B", color="#FF0000", italic=True,
                      align="right", indent_twips=120)
    t = rr.style_body(t, rows=0, border=rr.rtf_border(bottom="double"))
    assert _rtf(t) == _golden("body_rows")


def test_style_header_cells_matches_r():
    t = rr.rtftable(DF, col_header=[["", "Arm A", "Arm B"], ["Statistic", "Value", "Value"]])
    t = rr.style_header(t, row=1, cols="B", label="Val.",
                        border=rr.rtf_border(bottom="double"), underline=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t = rr.style_header(t, row=0, cols=["A", "B"], align="right")
    assert _rtf(t) == _golden("header_cells")
