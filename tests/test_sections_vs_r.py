"""Sections opened by ``rtf_tables(auto_section=True)``, compared byte-for-byte
with the R package -- with and without an explicit section on the page an auto
section starts.

R (#548, v0.8.2.9017): the explicit ``rtf_section(page = n)`` wins that page;
the auto sections build on the running header (R's ``page = NULL`` template),
one RTF section per page.  ``data-raw/xcheck/sections_r.R`` writes
``tests/xcheck_golden/sections/``.
"""

from pathlib import Path

import pytest

import rtfreporter as rr

GOLDEN = Path(__file__).parent / "xcheck_golden" / "sections"
DATA = {"a": ["x", "y"], "b": [1, 2]}


def _pages():
    return rr.combine_sections(
        T1=rr.as_rtftables(DATA, col_rel_width=[50, 50]),
        T2=rr.as_rtftables(DATA, col_rel_width=[50, 50]))


def _hdr(text):
    return rr.rtf_header(rows=[{"l": text}])


def _golden(name):
    return (GOLDEN / f"{name}.rtf").read_text(encoding="ascii").replace("\r\n", "\n")


def _doc(explicit_page=None):
    doc = rr.rtf_section(rr.rtf_document(), header=_hdr("Study"))
    if explicit_page is not None:
        doc = rr.rtf_section(doc, page=explicit_page, header=_hdr("Explicit"))
    return rr.rtf_tables(doc, _pages(), auto_section=True)


def test_auto_sections_alone_match_r():
    assert _doc().to_rtf() == _golden("auto_only")


@pytest.mark.parametrize("page", [1, 2])
def test_an_explicit_section_wins_its_page_as_in_r(page):
    assert _doc(page).to_rtf() == _golden(f"explicit_page{page}")
