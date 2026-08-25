"""Cross-check every rendered RTF against the R package's own output.

``tests/xcheck_golden/*.rtf`` are produced by the **R** implementation from
``data-raw/xcheck/cases.json`` (regenerate with
``Rscript data-raw/xcheck/render_r.R``).  This module renders the same cases
with this port and requires the results to be **byte-identical** once line
endings are normalised -- same data, same options, same RTF commands.

That makes R the oracle for the whole renderer at once, rather than one
hand-written expectation at a time, and it runs in CI without R installed.
"""

from __future__ import annotations

import json
import os

import pytest

import rtfreporter as rr

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CASES_PATH = os.path.join(REPO, "data-raw", "xcheck", "cases.json")
GOLDEN_DIR = os.path.join(HERE, "xcheck_golden")

with open(CASES_PATH, encoding="utf-8") as fh:
    CASES = json.load(fh)["cases"]


def _pick(value):
    """An index may be given as ``{"r": 1, "py": 0}``; take the Python side."""
    if isinstance(value, dict) and "py" in value:
        return value["py"]
    return value


def render_case(case: dict) -> str:
    """Build the case with this port and return the RTF text."""
    kwargs = {key: _pick(v) for key, v in case.get("as_rtftables", {}).items()}

    watch = kwargs.pop("blank_rows_by_change", None)
    if watch is not None:
        kwargs["blank_rows"] = rr.blank_rows_by_change(watch)

    pages = rr.as_rtftables(case["data"], **kwargs)

    page_spec = case.get("page")
    doc = rr.rtf_document(
        page=rr.rtf_page(**{k: _pick(v) for k, v in page_spec.items()})
        if page_spec
        else None
    )

    tbl_kwargs = {}
    if case.get("titles") is not None:
        tbl_kwargs["titles"] = case["titles"]
    if case.get("footnotes") is not None:
        tbl_kwargs["footnotes"] = case["footnotes"]
    doc = rr.rtf_tables(doc, pages, **tbl_kwargs)

    if case.get("header") is not None or case.get("footer") is not None:
        header = rr.rtf_header(case["header"]) if case.get("header") else None
        footer = None
        if case.get("footer") is not None:
            border = None if case.get("footer_border") == "none" else rr.rtf_border_top()
            footer = rr.rtf_footer(case["footer"], border=border)
        doc = rr.rtf_section(doc, page=1, header=header, footer=footer)

    return rr.to_rtf(doc)


def _normalise(text: str) -> str:
    """Ignore line-ending style only -- everything else must match."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _first_difference(expected: str, actual: str) -> str:
    """A readable report of where the two RTFs diverge."""
    exp_lines = expected.split("\n")
    act_lines = actual.split("\n")
    for i, (e, a) in enumerate(zip(exp_lines, act_lines, strict=False), start=1):
        if e != a:
            col = next(
                (j for j, (ec, ac) in enumerate(zip(e, a, strict=False)) if ec != ac),
                min(len(e), len(a)),
            )
            return (
                f"line {i}, column {col + 1}\n"
                f"  R : {e[max(0, col - 40):col + 60]!r}\n"
                f"  Py: {a[max(0, col - 40):col + 60]!r}"
            )
    if len(exp_lines) != len(act_lines):
        return f"line count differs: R has {len(exp_lines)}, Python has {len(act_lines)}"
    return "no textual difference found"


def test_every_case_has_a_golden_file():
    """A case without R output would silently pass; fail loudly instead."""
    missing = [
        c["id"] for c in CASES
        if not os.path.exists(os.path.join(GOLDEN_DIR, c["id"] + ".rtf"))
    ]
    assert not missing, (
        f"No R golden output for: {missing}. "
        "Regenerate with: Rscript data-raw/xcheck/render_r.R"
    )


def test_no_orphan_golden_files():
    """A golden file with no case is stale and must not linger."""
    known = {c["id"] + ".rtf" for c in CASES}
    present = {f for f in os.listdir(GOLDEN_DIR) if f.endswith(".rtf")}
    assert not (present - known), f"Stale golden files: {sorted(present - known)}"


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_matches_r_byte_for_byte(case):
    golden_path = os.path.join(GOLDEN_DIR, case["id"] + ".rtf")
    with open(golden_path, encoding="ascii") as fh:
        expected = _normalise(fh.read())
    actual = _normalise(render_case(case))

    assert actual == expected, (
        f"RTF differs from the R package for case {case['id']!r}.\n"
        f"Why this case exists: {case.get('why', '(unstated)')}\n"
        f"{_first_difference(expected, actual)}"
    )
