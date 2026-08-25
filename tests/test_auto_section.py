"""``rtf_tables(auto_section=)`` -- one RTF section per named page.

Checked against the R package: with a running header plus
``combine_sections(Demographics=, Adverse_Events=)`` and
``auto_section = TRUE``, R emits **two** sections whose header bands read
"Protocol ABC Page Demographics" and "Protocol ABC Page Adverse_Events" --
each is the base header plus its *own* label, never the previous one's.
"""

from __future__ import annotations

import re

import pytest

import rtfreporter as rr

BS = chr(92)


@pytest.fixture
def named_pages():
    dm = rr.as_rtftables({"a": [1, 2]}, col_rel_width=[100])
    ae = rr.as_rtftables({"b": [3]}, col_rel_width=[100])
    return rr.combine_sections(Demographics=dm, Adverse_Events=ae)


@pytest.fixture
def running():
    return rr.rtf_header([{"l": "Protocol ABC", "r": "Page {AUTO_PAGE}"}])


def _header_bands(rtf: str) -> list[str]:
    """Visible text of each emitted header band."""
    out = []
    for band in re.findall(re.escape(BS + "header") + r"(.*?)(?=\n)", rtf):
        text = re.sub(re.escape(BS) + r"[a-zA-Z]+-?\d*[ ]?", " ", band)
        text = " ".join(re.sub(r"[{}]", " ", text).split())
        if text and not text.startswith("y"):  # skip the \headeryNNN distance
            out.append(text)
    return out


def test_named_pages_each_open_a_section(named_pages, running):
    doc = rr.rtf_tables(
        rr.rtf_section(rr.rtf_document(), header=running), named_pages, auto_section=True
    )
    assert [s["from_page"] for s in doc._sections] == [1, 2]


def test_each_section_gets_the_base_plus_only_its_own_label(named_pages, running):
    """The regression this guards: section 2 used to inherit section 1's label."""
    doc = rr.rtf_tables(
        rr.rtf_section(rr.rtf_document(), header=running), named_pages, auto_section=True
    )
    rows = [[list(r.values()) for r in s["header"].rows] for s in doc._sections]
    assert rows[0] == [["Protocol ABC", "Page {AUTO_PAGE}"], ["Demographics"]]
    assert rows[1] == [["Protocol ABC", "Page {AUTO_PAGE}"], ["Adverse_Events"]]


def test_rendered_output_matches_r(named_pages, running):
    doc = rr.rtf_tables(
        rr.rtf_section(rr.rtf_document(), header=running), named_pages, auto_section=True
    )
    rtf = rr.to_rtf(doc)
    assert _header_bands(rtf) == [
        "Protocol ABC Page Demographics",
        "Protocol ABC Page Adverse_Events",
    ]
    # R emits exactly two sections here; an empty base section must not add one.
    assert rtf.count(BS + "sectd") == 2


def test_off_by_default_emits_no_extra_sections(named_pages, running):
    doc = rr.rtf_tables(
        rr.rtf_section(rr.rtf_document(), header=running), named_pages
    )
    assert len(doc._sections) == 1


def test_unnamed_pages_fall_through(running):
    """A multi-page table stays ONE section: only its first page is named."""
    multi = rr.as_rtftables(
        {"v": list(range(6))}, split="rows", split_rows=2, col_rel_width=[100]
    )
    assert len(multi) == 3
    pages = rr.combine_sections(Listing=multi)
    assert [p.name for p in pages] == ["Listing", None, None]

    doc = rr.rtf_tables(
        rr.rtf_section(rr.rtf_document(), header=running), pages, auto_section=True
    )
    assert len(doc._sections) == 1
    assert doc._sections[0]["from_page"] == 1


@pytest.mark.parametrize(
    ("align", "slot"), [("left", "l"), ("center", "c"), ("right", "r")]
)
def test_section_label_align(named_pages, running, align, slot):
    doc = rr.rtf_tables(
        rr.rtf_section(rr.rtf_document(), header=running),
        named_pages,
        auto_section=True,
        section_label_align=align,
    )
    assert doc._sections[0]["header"].rows[-1] == {slot: "Demographics"}


def test_bad_section_label_align_is_rejected(named_pages, running):
    with pytest.raises(ValueError, match="section_label_align"):
        rr.rtf_tables(
            rr.rtf_section(rr.rtf_document(), header=running),
            named_pages,
            auto_section=True,
            section_label_align="middle",
        )


def test_works_without_a_base_header(named_pages):
    """With no running header the label becomes the whole band."""
    doc = rr.rtf_tables(rr.rtf_document(), named_pages, auto_section=True)
    assert [list(s["header"].rows[-1].values()) for s in doc._sections] == [
        ["Demographics"],
        ["Adverse_Events"],
    ]


def test_by_value_pages_are_named_and_section(running):
    """``split="by_value"`` names pages, so auto_section sections per group."""
    pages = rr.as_rtftables(
        {"PARAMCD": ["ALT", "ALT", "AST"], "V": [1, 2, 3]},
        split="by_value",
        group_col="PARAMCD",
    )
    doc = rr.rtf_tables(
        rr.rtf_section(rr.rtf_document(), header=running), pages, auto_section=True
    )
    assert [list(s["header"].rows[-1].values())[0] for s in doc._sections] == ["ALT", "AST"]


def test_fluent_add_tables_supports_auto_section(named_pages, running):
    doc = (
        rr.RtfDocument()
        .add_section(header=running)
        .add_tables(named_pages, auto_section=True)
    )
    assert len(doc._sections) == 2


def test_auto_section_does_not_mutate_the_input(named_pages, running):
    base = rr.rtf_section(rr.rtf_document(), header=running)
    rr.rtf_tables(base, named_pages, auto_section=True)
    assert len(base._sections) == 1
    assert len(base._pages) == 0
