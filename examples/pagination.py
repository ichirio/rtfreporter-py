"""End-to-end example: a multi-page listing with ``(Cont.)`` markers.

Builds a subject-level adverse-event listing large enough to span several pages,
paginates it with :func:`rtfreporter.as_rtftables` so that no treatment group is
split awkwardly, and marks continued groups with a ``(Cont.)`` label.  The
running header carries a live page number.

Run::

    python examples/pagination.py
"""

from __future__ import annotations

import os

import pandas as pd

from rtfreporter import RtfDocument, rtf_footer, rtf_header


def make_data(n_per_group: int = 8) -> pd.DataFrame:
    groups = ["Placebo", "Low Dose", "High Dose"]
    rows = []
    for g in groups:
        for i in range(n_per_group):
            rows.append(
                {
                    "Treatment": g,
                    "Subject": f"{g[:3].upper()}-{i + 1:03d}",
                    "Preferred Term": ["Headache", "Nausea", "Fatigue", "Dizziness"][i % 4],
                    "Severity": ["Mild", "Moderate", "Severe"][i % 3],
                }
            )
    return pd.DataFrame(rows)


def build() -> RtfDocument:
    df = make_data()

    # group_force: keep each Treatment together where it fits, but split an
    # oversized group across pages with a "(Cont.)" continuation marker.
    pages = as_rtftables_pages(df)

    doc = RtfDocument().add_section(
        header=rtf_header([{"l": "Protocol XYZ-123", "r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"}]),
        footer=rtf_footer([{"c": "Confidential -- Draft"}]),
    )
    for page in pages:
        doc.add_table(
            page,
            title=["Table 14.3.1", "", "Listing of Adverse Events"],
            footnote=["Adverse events coded using MedDRA."],
        )
    return doc


def as_rtftables_pages(df: pd.DataFrame):
    from rtfreporter import as_rtftables

    return as_rtftables(
        df,
        split="group_force",
        group_col="Treatment",
        max_rows=6,
        collapse_repeats="Treatment",
        cont_label=" (Cont.)",
    )


def main() -> str:
    doc = build()
    rtf = doc.to_rtf()

    assert rtf.startswith("{\\rtf1"), "output must start with {\\rtf1"
    assert rtf.count("{") == rtf.count("}"), "RTF group braces must balance"
    assert "(Cont.)" in rtf, "a continued group should carry the (Cont.) marker"
    assert rtf.count("\\page") + rtf.count("\\sect") >= 1, "expected multiple pages"

    out_path = os.path.join(os.path.dirname(__file__), "pagination.rtf")
    doc.save(out_path)
    n_pages = rtf.count("\\page") + rtf.count("\\sbkpage")
    print(f"Wrote {out_path} ({len(rtf):,} bytes, ~{n_pages} page breaks/sections)")
    return out_path


if __name__ == "__main__":
    main()
