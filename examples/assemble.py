"""End-to-end example: assemble several RTF tables into one TOC deliverable.

Generates two individual clinical tables with :func:`generate_rtfreport`, then
combines them into a single deliverable with an auto-generated, clickable Table
of Contents (one bookmarked entry per source file) via :func:`assemble_rtf`.

Run::

    python examples/assemble.py
"""

from __future__ import annotations

import os
import tempfile

from rtfreporter import (
    assemble_rtf,
    generate_rtfreport,
    rtf_document,
    rtf_header,
    rtf_section,
    rtf_tables,
)


def _make_table(path: str, table_number: str, title: str, data: dict) -> str:
    """Render one clinical table to ``path`` and return the path."""
    doc = rtf_document()
    doc = rtf_tables(doc, data, titles=[f"Table {table_number}", "", title])
    doc = rtf_section(
        doc, header=rtf_header([{"l": "Protocol XYZ-001", "r": "Page {AUTO_PAGE}"}])
    )
    return generate_rtfreport(doc, path, overwrite=True)


def main() -> str:
    workdir = tempfile.mkdtemp(prefix="rtf_assemble_")

    demographics = _make_table(
        os.path.join(workdir, "t14_1_1.rtf"),
        "14.1.1",
        "Demographic Characteristics",
        {"Characteristic": ["Age, mean", "Sex, n (%) Female"],
         "Placebo": ["45.2", "12 (40.0%)"],
         "Active": ["46.1", "15 (50.0%)"]},
    )
    adverse = _make_table(
        os.path.join(workdir, "t14_2_1.rtf"),
        "14.2.1",
        "Adverse Events by System Organ Class",
        {"System Organ Class": ["Cardiac disorders", "GI disorders"],
         "Placebo": ["3 (10.0%)", "5 (16.7%)"],
         "Active": ["4 (13.3%)", "6 (20.0%)"]},
    )

    out_path = os.path.join(workdir, "deliverable.rtf")
    assemble_rtf(
        [demographics, adverse],
        out_path,
        toc="auto",  # extract each file's title for the TOC entry
        toc_title="Table of Contents",
        toc_page_numbering="roman",  # TOC pages i, ii; body restarts at 1
        overwrite=True,
    )

    rtf = open(out_path, encoding="utf-8").read()
    assert rtf.startswith("{\\rtf1"), "assembled output must start with {\\rtf1"
    assert "Table of Contents" in rtf
    assert rtf.count("HYPERLINK") == 2, "one clickable TOC entry per source file"
    assert "{\\fldrslt Table 14.1.1}" in rtf

    print(f"Wrote {out_path} ({len(rtf):,} bytes, 2 tables, auto TOC)")
    return out_path


if __name__ == "__main__":
    main()
