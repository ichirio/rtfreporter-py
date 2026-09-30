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


def _as_border(b: dict):
    """A border written as JSON -> :func:`rtfreporter.rtf_border`; a side is
    ``True`` / ``False`` / a style name, or ``{"style", "width", "color"}``."""
    return rr.rtf_border(**{
        k: rr.rtf_border_side(**v) if isinstance(v, dict) else v for k, v in b.items()
    })


def _as_style(st: dict | None) -> dict:
    st = dict(st or {})
    if "border" in st:
        st["border"] = _as_border(st["border"])
    return st


def render_case(case: dict) -> str:
    """Build the case with this port and return the RTF text."""
    kwargs = {key: _pick(v) for key, v in case.get("as_rtftables", {}).items()}

    watch = kwargs.pop("blank_rows_by_change", None)
    if watch is not None:
        kwargs["blank_rows"] = rr.blank_rows_by_change(watch)
    if isinstance(kwargs.get("border"), dict):
        kwargs["border"] = _as_border(kwargs["border"]["rtf_border"])

    pages = rr.as_rtftables(case["data"], **kwargs)

    if case.get("style_zone"):
        zones = {z: _as_border(b) for z, b in case["style_zone"].items()}
        pages = [rr.style_zone(p, **zones) for p in pages]

    page_spec = case.get("page")
    fmt_spec = case.get("default_format")
    doc = rr.rtf_document(
        page=rr.rtf_page(**{k: _pick(v) for k, v in page_spec.items()}) if page_spec else None,
        default_format=rr.rtf_default_format(**fmt_spec) if fmt_spec else None,
        font_table=case.get("font_table"),
        watermark=(rr.rtf_watermark(**case["watermark"])
                   if isinstance(case.get("watermark"), dict) else case.get("watermark")),
    )

    doc = rr.rtf_tables(doc, pages, **{k: _pick(v) for k, v in case.get("rtf_tables", {}).items()})
    if case.get("titles") is not None:
        doc = rr.rtf_titles(doc, [case["titles"]], **_as_style(case.get("titles_style")))
    if case.get("footnotes") is not None:
        doc = rr.rtf_footnotes(doc, [case["footnotes"]], **_as_style(case.get("footnotes_style")))

    if case.get("header") is not None or case.get("footer") is not None:
        header = rr.rtf_header(case["header"]) if case.get("header") else None
        footer = None
        if case.get("footer") is not None:
            border = None if case.get("footer_border") == "none" else rr.rtf_border(top=True)
            footer = rr.rtf_footer(case["footer"], border=border)
        doc = rr.rtf_section(doc, page=1, header=header, footer=footer)

    # The run tokens: a fixed program and time, so R and the port agree.
    run = case.get("run")
    if run is None:
        return rr.to_rtf(doc)
    old = rr.rtfreporter_options(render_time=run["render_time"])
    try:
        return doc.to_rtf(program=run["program"])
    finally:
        rr.rtfreporter_options(**old)


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
    if case.get("r_bug"):
        # The R output this case is checked against carries a known R defect
        # (the issue named in the case); the port deliberately renders the
        # intended output, so the byte comparison is expected to fail until the
        # R fix ships and the golden is regenerated from that release.
        pytest.xfail(f"known R defect: {case['r_bug']}")
    golden_path = os.path.join(GOLDEN_DIR, case["id"] + ".rtf")
    with open(golden_path, encoding="ascii") as fh:
        expected = _normalise(fh.read())
    actual = _normalise(render_case(case))

    assert actual == expected, (
        f"RTF differs from the R package for case {case['id']!r}.\n"
        f"Why this case exists: {case.get('why', '(unstated)')}\n"
        f"{_first_difference(expected, actual)}"
    )
