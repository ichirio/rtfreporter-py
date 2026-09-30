"""col_cell(<selector>) / col_key(), set_col_header(values=) and named label
rows, compared byte-for-byte with the R package; header_map() against R's.

The expected files are what R v0.8.2 wrote for the same calls
(``data-raw/xcheck/header_r.R`` writes ``tests/xcheck_golden/header/``).
"""

import json
from pathlib import Path

import pytest

import rtfreporter as rr

GOLDEN = Path(__file__).parent / "xcheck_golden" / "header"

WIDE = {"Param": ["Hgb", "ALT"],
        "Placebo____Day 1": ["13", "30"], "Placebo____Day 7": ["12", "31"],
        "Drug____Day 1": ["14", "29"], "Drug____Day 7": ["15", "28"]}
LONG = {"Period": ["P1", "P1", "P2", "P2"], "Param": ["Hgb", "ALT", "Hgb", "ALT"],
        "Placebo": ["13", "30", "12", "31"], "Drug": ["14", "29", "15", "28"]}
VALS = {"group": ["P1", "P2"], "n_pbo": [120, 118], "n_drug": [121, 117]}


def _rtf(pages):
    return rr.rtf_tables(rr.rtf_document(), pages, auto_title=True).to_rtf()


def _golden(name):
    return (GOLDEN / f"{name}.rtf").read_text(encoding="ascii").replace("\r\n", "\n")


def _values_pages():
    pages = rr.as_rtftables(LONG, split="by_value", group_col="Period", drop_cols="Period")
    return rr.set_col_header(
        pages, ["Parameter", "Placebo\n(N={n_pbo})", "Drug\n(N={n_drug}) {{x}}"], values=VALS)


def test_col_key_spanning_matches_r():
    pages = rr.set_col_header(
        rr.as_rtftables(WIDE, header_sep=None),
        [rr.col_cell(0, ""), rr.col_cell(rr.col_key("Placebo"), "Placebo"),
         rr.col_cell(rr.col_key("Drug"), "Drug")],
        ["Param", "Day 1", "Day 7", "Day 1", "Day 7"])
    assert _rtf(pages) == _golden("col_key")


def test_values_fill_each_page_matches_r():
    assert _rtf(_values_pages()) == _golden("values")


def test_header_map_matches_r():
    exp = json.loads((GOLDEN / "header_map.json").read_text(encoding="utf-8"))
    got = rr.header_map(_values_pages())
    # R counts from 1; the port from 0.  R drops a missing `rows` key.
    exp = [{**e, "page": e["page"] - 1, "row": e["row"] - 1, "cell": e["cell"] - 1,
            "from": e["from"] - 1, "to": e["to"] - 1, "rows": e.get("rows")} for e in exp]
    assert got == exp


def test_named_label_row_matches_r():
    data = {k: v for k, v in LONG.items() if k != "Period"}
    pages = rr.set_col_header(rr.as_rtftables(data), {"Placebo": "PBO", "Drug": "Active"})
    assert _rtf(pages) == _golden("named_row")


def test_values_errors():
    pages = rr.as_rtftables(LONG, split="by_value", group_col="Period")
    with pytest.raises(ValueError, match="no row for page"):
        rr.set_col_header(pages, ["a", "{n}", "b", "c"], values={"group": ["P1"], "n": [1]})
    with pytest.raises(ValueError, match="matched no page"):
        rr.set_col_header(pages, ["a", "{n}", "b", "c"],
                          values={"group": ["P1", "P2", "P3"], "n": [1, 2, 3]})
    with pytest.raises(ValueError, match="no value for"):
        rr.set_col_header(pages, ["a", "{m}", "b", "c"], values={"group": ["P1", "P2"], "n": [1, 2]})
    with pytest.raises(ValueError, match="no key column"):
        rr.set_col_header(pages, ["a", "{n}", "b", "c"], values={"g": ["P1", "P2"], "n": [1, 2]})
    # the render-time tokens are left for the renderer
    out = rr.set_col_header(pages, ["{PAGE}", "{n}", "b", "c"],
                            values={"group": ["P1", "P2"], "n": [1, 2]})
    assert out[0].col_header[0].labels[0] == "{PAGE}"


def test_page_by_key_and_a_combination():
    pages = rr.as_rtftables(LONG, page_by="Period")
    assert [p.page_by for p in pages] == ["P1", "P2"]
    out = rr.set_col_header(pages, ["{n}", "b", "c", "d"],
                            values={"rows": ["P2", "P1"], "n": ["two", "one"]}, by="rows")
    assert [p.col_header[0].labels[0] for p in out] == ["one", "two"]


def test_selector_errors_and_forms():
    names = ["a____x", "b____x", "a____y"]
    with pytest.raises(ValueError, match="non-adjacent"):
        rr.rtftable({n: ["1"] for n in names},
                    col_header=[rr.col_cell(rr.col_key("a"), "A")])
    with pytest.raises(ValueError, match="matched no data columns"):
        rr.rtftable({n: ["1"] for n in names}, col_header=[rr.col_cell(rr.col_key("zz"), "Z")])
    t = rr.rtftable({n: ["1"] for n in names},
                    col_header=[rr.col_cell(lambda nm: ["b____x", "a____y"], "BY")])
    assert (t.col_header[0].spans[0].start, t.col_header[0].spans[0].end) == (1, 2)
    t = rr.rtftable({n: ["1"] for n in names},
                    col_header=[rr.col_cell(rr.col_key("y", sep="____", part=-1), "Y")])
    assert t.col_header[0].spans[0].start == 2


def test_unnamed_label_row_must_fit():
    with pytest.raises(ValueError, match="label row has 2 labels"):
        rr.set_col_header(rr.rtftable({"a": ["1"], "b": ["2"], "c": ["3"]}), ["x", "y"])
    with pytest.raises(ValueError, match="unknown column"):
        rr.set_col_header(rr.rtftable({"a": ["1"]}), {"zz": "x"})
