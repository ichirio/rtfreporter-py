"""Listings, compared with the R package: the RTF of as_rtftables(listing=),
build_listing()'s body, fit_listing_widths()'s widths and listing_wrap()'s
lines (``data-raw/xcheck/listing_r.R`` writes ``tests/xcheck_golden/listing/``)."""

import json
from pathlib import Path

import pytest

import rtfreporter as rr

ROOT = Path(__file__).parent
GOLDEN = ROOT / "xcheck_golden" / "listing"
AE = json.loads((ROOT.parent / "data-raw" / "xcheck" / "listing_data.json")
                .read_text(encoding="utf-8"))
EXP = json.loads((GOLDEN / "listing.json").read_text(encoding="utf-8"))


def _rtf(pages):
    return rr.rtf_tables(rr.rtf_document(), pages).to_rtf()


def _golden(name):
    return (GOLDEN / f"{name}.rtf").read_text(encoding="ascii").replace("\r\n", "\n")


def _spec1():
    return rr.listing_spec([
        rr.listing_col("USUBJID", width=11, collapse_repeats=True, label="Subject"),
        rr.listing_col(["AETERM", "AEDECOD"], width=20),
        rr.listing_col(["ASTDT", "AENDT"], width=10, label=["Start /", "End"]),
        rr.listing_col("AESEV", width=8, align="center")])


def test_multiline_listing_matches_r():
    assert _rtf(rr.as_rtftables(AE, listing=_spec1(), max_rows=12)) == _golden("multiline")


def test_flow_listing_without_spacers_matches_r():
    spec = rr.listing_spec([
        rr.listing_col(["USUBJID", "AGE", "SEX"], width=16, sep=" / "),
        rr.listing_col(["AETERM", "AEDECOD"], width=24, layout="flow"),
        "AESEV"], spacer=False, blank_row=False, record=False, align="right")
    assert _rtf(rr.as_rtftables(AE, listing=spec)) == _golden("flow_no_spacer")


def test_build_listing_body_matches_r():
    body = rr.build_listing(AE, _spec1())
    assert body.column_names == EXP["body_names"]
    for j, name in enumerate(body.column_names):
        exp = EXP["body"][name]
        assert [r[j] for r in body.rows] == exp, name


def test_fit_listing_widths_matches_r():
    spec = rr.fit_listing_widths(AE, rr.listing_spec([
        rr.listing_col("USUBJID"), rr.listing_col(["AETERM", "AEDECOD"]),
        rr.listing_col(["ASTDT", "AENDT"], width=12), "AESEV"]),
        labels={"AETERM": "Reported Term", "AEDECOD": "Preferred Term"})
    got = [{"name": c.name, "width": c.width, "rel_width": c.rel_width, "label": c.label}
           for c in spec.cols]
    assert got == EXP["fit"]
    code = rr.listing_code(spec, name="spec")
    assert code.startswith("spec = listing_spec([") and "width=12" in code


@pytest.mark.parametrize("k, width", [(0, 6), (1, 10), (2, 15)])
def test_listing_wrap_matches_r(k, width):
    corpus = ["Headache/Mild/Resolved after two weeks of treatment",
              "Supercalifragilisticexpialidocious-term, long", "", "a/b/c",
              "Line one\nLine two/three",
              "頭痛/軽度の頭痛が続く"]
    for layout in ("stack", "flow"):
        got = [rr.listing_wrap(t, width, sep="/", layout=layout) for t in corpus]
        exp = [[e] if isinstance(e, str) else e for e in EXP["wraps"][k][layout]]
        assert got == exp, layout


def test_listing_wrap_code_is_runnable():
    src = rr.listing_wrap_code("my_wrap")
    ns: dict = {}
    exec(compile(src, "<wrap>", "exec"), ns)
    assert ns["my_wrap"]("a/b/c", 2, "/", "stack") == rr.listing_wrap("a/b/c", 2)
