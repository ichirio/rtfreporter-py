"""assemble_rtf(), compared byte-for-byte with the R package.

The expected files are what R assembled from the same two deliverables -- R
v0.8.2, and 0.8.2.9026 for ``toc_table.rtf`` (``data-raw/xcheck/assemble_r.R``
writes ``tests/xcheck_golden/assemble/``).
The port renders its own inputs; the table xcheck already holds those equal.
"""

from pathlib import Path

import pytest

import rtfreporter as rr

GOLDEN = Path(__file__).parent / "xcheck_golden" / "assemble"


def _one(tmp_path, ident, rows):
    data = {"Item": [f"{ident}-{i + 1}" for i in range(rows)],
            "N": [str(i + 1) for i in range(rows)]}
    doc = rr.rtf_tables(rr.rtf_document(), rr.as_rtftables(data))
    doc = rr.rtf_titles(doc, [[f"Table {ident}"]])
    doc = rr.rtf_section(
        doc, page=1,
        header=rr.rtf_header([{"l": "Study X", "r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"}]),
        footer=rr.rtf_footer([{"c": "{BOOK_PAGE}"}]),
    )
    path = tmp_path / f"{ident}.rtf"
    rr.generate_rtfreport(doc, str(path))
    return str(path)


def _norm(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


@pytest.mark.parametrize("name, book_page", [
    ("book_page", "Book page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"),
    ("book_page_none", None),
])
def test_assemble_matches_r(tmp_path, name, book_page):
    inputs = [_one(tmp_path, "T1", 3), _one(tmp_path, "T2", 2)]
    out = tmp_path / f"{name}.rtf"
    rr.assemble_rtf(inputs, str(out), book_page=book_page)
    expected = _norm((GOLDEN / f"{name}.rtf").read_text(encoding="ascii"))
    assert _norm(out.read_text(encoding="utf-8")) == expected


def test_toc_table_matches_r(tmp_path):
    """``assemble_rtf(toc=<table>)`` with no ``input_files`` (R 0.8.2.9014)."""
    inputs = [_one(tmp_path, "T1", 3), _one(tmp_path, "T2", 2)]
    toc = [{"file": inputs[0], "heading": "EFFICACY", "label": "Table T1  First", "level": 2},
           {"file": inputs[1], "heading": None, "label": "Table T2  Second", "level": 1}]
    out = tmp_path / "toc_table.rtf"
    rr.assemble_rtf(toc=toc, output_file=str(out), toc_page_numbering="decimal")
    expected = _norm((GOLDEN / "toc_table.rtf").read_text(encoding="ascii"))
    assert _norm(out.read_text(encoding="utf-8")) == expected


def test_book_page_refuses_static_tokens(tmp_path):
    inputs = [_one(tmp_path, "T1", 1), _one(tmp_path, "T2", 1)]
    with pytest.raises(ValueError, match="static"):
        rr.assemble_rtf(inputs, str(tmp_path / "x.rtf"), book_page="Page {PAGE}")
