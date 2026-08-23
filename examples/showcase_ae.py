"""Showcase: Adverse events by system organ class and preferred term.

Mirrors the R package's ``showcase-ae`` article.  Subjects with at least one
treatment-emergent adverse event, summarised by SOC and PT from the bundled
ADaM ``adae`` (see :mod:`adam_data`).  The figures reproduce
``data-raw/R_reference_numbers.txt``.

Table rules (identical to the R article):

* an "Subjects with any adverse event" row on top;
* **each SOC row carries its own independent distinct-subject count** -- it is
  *not* the sum of its preferred terms, because one subject may report several
  PTs within the same SOC;
* a preferred term is shown only if it reaches **>= 3% in any arm**;
* SOCs are ordered alphabetically; PTs within a SOC by total distinct-subject
  count descending, ties A to Z;
* zero cells render as an aligned ``0 (0.0%)`` so the column stays flush;
* PTs are indented under their SOC, and that indent is what drives group-aware
  pagination and the ``(Cont.)`` continuation marker.

Run::

    python examples/showcase_ae.py
"""

from __future__ import annotations

import os

import pandas as pd

from rtfreporter import (
    col_cell,
    generate_rtfreport,
    rtf_col_header,
    rtf_document,
    rtf_footer,
    rtf_header,
    rtf_page,
    rtf_section,
    rtf_tables,
)

try:
    from adam_data import ANY_AE, ARM_LEVELS, arm_counts, arm_labels, load_adae, load_adsl
except ImportError:  # pragma: no cover - import-path shim
    from examples.adam_data import (
        ANY_AE,
        ARM_LEVELS,
        arm_counts,
        arm_labels,
        load_adae,
        load_adsl,
    )

HERE = os.path.dirname(os.path.abspath(__file__))

NBSP = chr(0xA0)  # U+00A0 NO-BREAK SPACE (kept ASCII in source)
#: Four non-breaking spaces: the indent that marks a PT as a child of its SOC.
INDENT = NBSP * 4
#: Preferred terms are kept when they reach this percentage in any arm.
PT_THRESHOLD_PCT = 3.0
#: Rows per page.  Matches the R article's limit: group_force cuts on this
#: limit and repeats the SOC header with ``(Cont.)`` when a group spans the
#: break, so the table reads as a realistic multi-page listing.
AE_MAX_ROWS = 16


# --------------------------------------------------------------------------
# Cell formatting
# --------------------------------------------------------------------------
def fmt_ae(n: int, denom: int) -> str:
    """Format ``n`` and its percentage as an aligned ``n (xx.x%)`` cell.

    Unlike :func:`~rtfreporter.format_count_pct`, a **zero is expanded** to
    ``0 (0.0%)`` rather than collapsed to a bare padded ``0``.  The R article
    does the same: the built-in aligner only pads paren-bearing cells, so
    expanding the zeros is what keeps a column of counts flush.  Every branch
    is 11 characters wide, so the closing paren lines up.
    """
    pct = 100.0 * n / denom if denom else 0.0
    if n == 0:
        body = f"{n:>3}{NBSP * 2}(0.0%)"
    elif pct >= 100:
        body = f"{n:>3}{NBSP * 2}({round(pct):>3}%)"
    elif pct < 10:
        body = f"{n:>3}{NBSP * 2}({pct:>3.1f}%)"
    else:
        body = f"{n:>3}{NBSP}({pct:>4.1f}%)"
    return body.replace(" ", NBSP)


# --------------------------------------------------------------------------
# Body assembly
# --------------------------------------------------------------------------
def _distinct_counts(frame: pd.DataFrame, *keys: str) -> pd.DataFrame:
    """Distinct-subject counts per arm for the given grouping keys."""
    return (
        frame.drop_duplicates(["USUBJID", "TRT01A", *keys])
        .groupby(["TRT01A", *keys], observed=True)
        .size()
        .rename("n")
        .reset_index()
    )


def kept_preferred_terms(adae: pd.DataFrame, denom: pd.Series) -> list[str]:
    """Preferred terms reaching ``PT_THRESHOLD_PCT`` in at least one arm."""
    counts = _distinct_counts(adae, "AEDECOD")
    counts["pct"] = [
        100.0 * row.n / int(denom[row.TRT01A]) for row in counts.itertuples()
    ]
    peak = counts.groupby("AEDECOD", observed=True)["pct"].max()
    return sorted(peak[peak >= PT_THRESHOLD_PCT].index.tolist())


def preferred_term_order(adae: pd.DataFrame) -> list[str]:
    """Canonical PT order: total distinct subjects descending, ties A to Z."""
    totals = (
        adae.drop_duplicates(["USUBJID", "AEDECOD"])
        .groupby("AEDECOD", observed=True)
        .size()
        .rename("tot")
        .reset_index()
        .sort_values(["tot", "AEDECOD"], ascending=[False, True])
    )
    return totals["AEDECOD"].tolist()


def build_body(adsl: pd.DataFrame, adae: pd.DataFrame) -> pd.DataFrame:
    """Assemble the AE body: any-AE row, then SOC rows with indented PTs."""
    denom = arm_counts(adsl)
    keep = set(kept_preferred_terms(adae, denom))
    pt_rank = {pt: i for i, pt in enumerate(preferred_term_order(adae))}

    def cells(frame: pd.DataFrame) -> list[str]:
        subjects = frame.drop_duplicates(["USUBJID", "TRT01A"])
        per_arm = subjects.groupby("TRT01A", observed=False).size()
        return [fmt_ae(int(per_arm.get(arm, 0)), int(denom[arm])) for arm in ARM_LEVELS]

    rows: list[dict[str, str]] = []

    def add(label: str, frame: pd.DataFrame) -> None:
        row = {"Adverse Event": label}
        row.update(dict(zip(ARM_LEVELS, cells(frame), strict=True)))
        rows.append(row)

    # Any adverse event -- a flush-left row of its own.
    add(ANY_AE, adae)

    # SOCs alphabetically; the SOC row is an INDEPENDENT distinct-subject count
    # over all its events, never the sum of the PTs printed beneath it.
    for soc in sorted(adae["AESOC"].dropna().unique()):
        soc_events = adae[adae["AESOC"] == soc]
        pts = [pt for pt in soc_events["AEDECOD"].dropna().unique() if pt in keep]
        if not pts:
            continue
        add(str(soc).title(), soc_events)
        for pt in sorted(pts, key=lambda p: (pt_rank.get(p, 10**6), p)):
            add(INDENT + str(pt).title(), soc_events[soc_events["AEDECOD"] == pt])

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Shared rtfreporter furniture
# --------------------------------------------------------------------------
AE_HEADER = rtf_header(
    rows=[
        {"l": "Acme Biopharma, Inc.", "r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"},
        {"l": "Protocol ABC-2026-001", "r": "Status: Draft"},
        {"c": "Table 14.3.1"},
        {"c": "Subjects With Treatment-Emergent Adverse Events by System Organ Class and Preferred Term"},
        {"c": "Safety Population"},
        {"c": ""},
    ]
)

AE_FOOTER = rtf_footer(
    rows=[
        {"l": "Note: A subject is counted once within each system organ class and preferred term."},
        {"l": "Preferred terms are shown when reported by at least 3% of subjects in any treatment group."},
        {"l": "Program: /prod/abc/tfl/t_14_3_1_ae.py", "r": "Generated: 2026-08-23 09:14"},
    ]
)

AE_PAGE = rtf_page(paper_size="letter", orientation="landscape")
AE_WIDTHS = [46, 18, 18, 18]


def ae_col_header(adsl: pd.DataFrame):
    """Two-row header: a spanning ``Treatment Group`` over the three arms."""
    return rtf_col_header(
        [col_cell(cols=(1, 3), label="Treatment Group", align="center")],
        ["System Organ Class / Preferred Term", *arm_labels(adsl)],
    )


def build_document(adsl: pd.DataFrame, body: pd.DataFrame):
    """Paginate group-aware and wrap the body in the shared furniture."""
    from rtfreporter import as_rtftables

    pages = as_rtftables(
        body,
        # Group on the VISIBLE label column and detect groups by indentation:
        # a flush-left row starts a group, indented rows belong to it.  Under
        # group_force the "(Cont.)" marker is written into this column, so it
        # must be a column that is actually printed.
        group_col=0,
        group_by="indent",
        split="group_force",
        max_rows=AE_MAX_ROWS,
        min_group_rows=2,
        cont_label=" (Cont.)",
        col_header=ae_col_header(adsl),
        col_spec=[
            {"col": 0, "align": "left"},
            {"col": 1, "align": "center"},
            {"col": 2, "align": "center"},
            {"col": 3, "align": "center"},
        ],
        col_rel_width=AE_WIDTHS,
    )
    doc = rtf_document(page=AE_PAGE)
    doc = rtf_tables(doc, pages)
    doc = rtf_section(doc, header=AE_HEADER, footer=AE_FOOTER)
    return doc, pages


def main() -> str:
    adsl = load_adsl()
    adae = load_adae()
    body = build_body(adsl, adae)
    doc, pages = build_document(adsl, body)
    out = os.path.join(HERE, "showcase_ae.rtf")
    generate_rtfreport(doc, out, overwrite=True)
    print(f"wrote {out}  ({len(pages)} pages, {len(body)} body rows)")
    print(body.to_string(index=False).replace(NBSP, "."))
    return out


if __name__ == "__main__":
    main()
