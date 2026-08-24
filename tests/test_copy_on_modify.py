"""Document builders must not mutate their input (R copy-on-modify semantics).

Checked against the R package: after ``docA <- rtf_tables(base, pagesA)``,
``base$contents`` is still empty, so a base document can safely seed several
reports.  The Python port must behave the same way, or reusing shared page
setup silently leaks content from one report into another.
"""

from __future__ import annotations

import pytest

import rtfreporter as rr


@pytest.fixture
def pages_a():
    return rr.as_rtftables({"v": [1]}, col_rel_width=[100])


@pytest.fixture
def pages_b():
    return rr.as_rtftables({"v": [2]}, col_rel_width=[100])


def test_a_base_document_can_seed_two_reports(pages_a, pages_b):
    """The regression this guards: docB used to inherit docA's pages."""
    base = rr.rtf_document()
    doc_a = rr.rtf_tables(base, pages_a)
    doc_b = rr.rtf_tables(base, pages_b)

    assert len(base._pages) == 0, "the base document must stay empty"
    assert len(doc_a._pages) == 1
    assert len(doc_b._pages) == 1
    assert doc_a is not base and doc_b is not base and doc_a is not doc_b


def test_rtf_tables_returns_a_new_document(pages_a):
    base = rr.rtf_document()
    assert rr.rtf_tables(base, pages_a) is not base


def test_rtf_section_does_not_touch_the_input(pages_a):
    doc = rr.rtf_tables(rr.rtf_document(), pages_a)
    sectioned = rr.rtf_section(doc, header=rr.rtf_header([{"l": "H"}]))
    assert len(doc._sections) == 0
    assert len(sectioned._sections) == 1


def test_rtf_titles_and_footnotes_do_not_touch_the_input(pages_a):
    doc = rr.rtf_tables(rr.rtf_document(), pages_a)
    titled = rr.rtf_titles(doc, [["T"]])
    noted = rr.rtf_footnotes(doc, [["F"]])
    assert doc._pages[0]["title"] is None
    assert doc._pages[0]["footnote"] is None
    assert titled._pages[0]["title"] == ["T"]
    assert noted._pages[0]["footnote"] == ["F"]


def test_rtf_config_does_not_touch_the_input():
    base = rr.rtf_document()
    portrait = rr.rtf_config(base, page={"orientation": "portrait"})
    assert base.page.orientation == "landscape"
    assert portrait.page.orientation == "portrait"


def test_fluent_methods_also_copy(pages_a):
    base = rr.RtfDocument()
    chained = base.add_tables(pages_a)
    assert len(base._pages) == 0
    assert len(chained._pages) == 1


def test_fluent_chain_still_accumulates(pages_a):
    doc = (
        rr.RtfDocument()
        .add_section(header=rr.rtf_header([{"l": "H"}]))
        .add_tables(pages_a)
        .titles([["T"]])
    )
    assert len(doc._sections) == 1
    assert len(doc._pages) == 1
    assert doc._pages[0]["title"] == ["T"]


def test_functional_and_fluent_render_identically(pages_a):
    header = rr.rtf_header([{"l": "X", "r": "{AUTO_PAGE}"}])

    doc = rr.rtf_document()
    doc = rr.rtf_tables(doc, pages_a)
    doc = rr.rtf_section(doc, header=header)

    fluent = rr.RtfDocument().add_tables(pages_a).add_section(header=header)
    assert rr.to_rtf(doc) == fluent.to_rtf()


def test_copies_do_not_share_page_dicts(pages_a):
    """A later edit on the copy must not reach back into the original."""
    doc = rr.rtf_tables(rr.rtf_document(), pages_a)
    titled = rr.rtf_titles(doc, [["T"]])
    titled._pages[0]["title"] = ["CHANGED"]
    assert doc._pages[0]["title"] is None
