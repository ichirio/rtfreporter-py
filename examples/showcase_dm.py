"""Showcase: Table 14.1.1 -- Summary of Demographic and Baseline Characteristics.

A production-style demographics table built from the bundled ADaM ``adsl``
(see :mod:`adam_data`), mirroring the R package's ``showcase-dm`` article.  The
numbers reproduce ``data-raw/R_reference_numbers.txt`` exactly.

The table is produced **two ways** so both input paths are exercised:

* from a plain :class:`pandas.DataFrame`, and
* from a ``great_tables`` ``GT`` object handed to :func:`as_rtftables`.

Both routes share the same rtfreporter *furniture* -- running header, footer,
page geometry, column header and widths -- which is built once below.  Every
rtfreporter call is written out in full rather than hidden behind a wrapper, so
the example doubles as documentation.

Run::

    python examples/showcase_dm.py
"""

from __future__ import annotations

import os

import pandas as pd

from rtfreporter import (
    col_cell,
    format_count_pct,
    generate_rtfreport,
    rtf_col_header,
    rtf_document,
    rtf_footer,
    rtf_header,
    rtf_page,
    rtf_section,
    rtf_tables,
)

try:  # allow both `python examples/showcase_dm.py` and `import examples.showcase_dm`
    from adam_data import ARM_LEVELS, arm_counts, arm_labels, load_adsl
except ImportError:  # pragma: no cover - import-path shim
    from examples.adam_data import ARM_LEVELS, arm_counts, arm_labels, load_adsl

HERE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------
# Body: one row per (Characteristic, Statistic), one column per arm.
# --------------------------------------------------------------------------
def _count_row(adsl: pd.DataFrame, column: str, level: str, denom: pd.Series) -> list[str]:
    """A ``n (xx.x%)`` cell per arm for one category level.

    Uses :func:`format_count_pct`, so a zero count renders as a padded ``0``
    with no parenthetical -- identical to the R package's output.
    """
    cells = []
    for arm in ARM_LEVELS:
        n = int(((adsl[column] == level) & (adsl["TRT01A"] == arm)).sum())
        cells.append(format_count_pct(n, n / int(denom[arm]))[0])
    return cells


def build_body(adsl: pd.DataFrame) -> pd.DataFrame:
    """Assemble the demographics body as a tidy two-level frame."""
    denom = arm_counts(adsl)
    rows: list[dict[str, str]] = []

    def add(characteristic: str, statistic: str, cells: list[str]) -> None:
        row = {"Characteristic": characteristic, "Statistic": statistic}
        row.update(dict(zip(ARM_LEVELS, cells, strict=True)))
        rows.append(row)

    # -- Age (years): n, Mean (SD), Median, Min, Max ------------------------
    by_arm = {arm: adsl.loc[adsl["TRT01A"] == arm, "AGE"] for arm in ARM_LEVELS}
    add("Age (years)", "n", [f"{int(by_arm[a].notna().sum())}" for a in ARM_LEVELS])
    add(
        "Age (years)",
        "Mean (SD)",
        [f"{by_arm[a].mean():.1f} ({by_arm[a].std(ddof=1):.2f})" for a in ARM_LEVELS],
    )
    add("Age (years)", "Median", [f"{by_arm[a].median():.1f}" for a in ARM_LEVELS])
    add(
        "Age (years)",
        "Min, Max",
        [f"{int(by_arm[a].min())}, {int(by_arm[a].max())}" for a in ARM_LEVELS],
    )

    # -- Categorical blocks --------------------------------------------------
    for characteristic, column in (
        ("Age group, n (%)", "AGEGR"),
        ("Sex, n (%)", "SEX"),
        ("Race, n (%)", "RACE"),
    ):
        for level in list(adsl[column].cat.categories):
            add(characteristic, str(level), _count_row(adsl, column, level, denom))

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Shared rtfreporter furniture -- built once, used by both routes.
# --------------------------------------------------------------------------
DM_HEADER = rtf_header(
    rows=[
        {"l": "Acme Biopharma, Inc.", "r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"},
        {"l": "Protocol ABC-2026-001", "r": "Status: Draft"},
        {"c": "Table 14.1.1"},
        {"c": "Summary of Demographic and Baseline Characteristics"},
        {"c": "Safety Population"},
        {"c": ""},
    ]
)

DM_FOOTER = rtf_footer(
    rows=[
        {
            "l": "Note: Percentages are based on the number of non-missing "
            "subjects in each treatment group."
        },
        {"l": "Program: /prod/abc/tfl/t_14_1_1_dm.py", "r": "Generated: 2026-08-23 09:14"},
    ]
)

DM_PAGE = rtf_page(paper_size="letter", orientation="landscape")

#: 40 : 20 : 20 : 20 -- a wide stub, three equal arm columns.
DM_WIDTHS = [40, 20, 20, 20]


def dm_col_header(adsl: pd.DataFrame):
    """Two-row column header: a spanning ``Treatment Group`` over the three arms."""
    labels = arm_labels(adsl)
    return rtf_col_header(
        [col_cell(cols=(1, 3), label="Treatment Group", align="center")],
        ["", *labels],
    )


def _col_spec() -> list[dict[str, object]]:
    """Left-aligned stub, centred arm columns."""
    return [
        {"col": 0, "align": "left"},
        {"col": 1, "align": "center"},
        {"col": 2, "align": "center"},
        {"col": 3, "align": "center"},
    ]


def build_document(adsl: pd.DataFrame, body: pd.DataFrame):
    """Wrap the body in the shared furniture and return an ``RtfDocument``."""
    from rtfreporter import as_rtftables

    pages = as_rtftables(
        body,
        stub_vars=["Characteristic", "Statistic"],
        stub_label="",
        col_header=dm_col_header(adsl),
        col_spec=_col_spec(),
        col_rel_width=DM_WIDTHS,
        blank_rows="between_groups",
    )
    doc = rtf_document(page=DM_PAGE)
    doc = rtf_tables(doc, pages)
    doc = rtf_section(doc, header=DM_HEADER, footer=DM_FOOTER)
    return doc


def build_gt(adsl: pd.DataFrame, body: pd.DataFrame):
    """The same body as a ``great_tables`` GT object.

    Demonstrates the second input route: rtfreporter reads the GT object's own
    labels and spanners, so the column header does not have to be restated.
    """
    from great_tables import GT

    flat = body.copy()
    # Merge the two hierarchy columns here: a GT stub is read as a single
    # column, so the indent is baked into the label instead of via stub_vars.
    indent = chr(0xA0) * 4
    seen: set[str] = set()
    labels = []
    for characteristic, statistic in zip(
        flat["Characteristic"], flat["Statistic"], strict=True
    ):
        if characteristic not in seen:
            seen.add(characteristic)
            labels.append(characteristic)
        labels.append(indent + statistic)
    rows = []
    seen.clear()
    for i, (characteristic, statistic) in enumerate(
        zip(flat["Characteristic"], flat["Statistic"], strict=True)
    ):
        if characteristic not in seen:
            seen.add(characteristic)
            rows.append([characteristic] + [""] * len(ARM_LEVELS))
        rows.append([indent + statistic] + [flat.iloc[i][a] for a in ARM_LEVELS])
    gt_frame = pd.DataFrame(rows, columns=["Characteristic", *ARM_LEVELS])

    table = GT(gt_frame).tab_spanner(label="Treatment Group", columns=list(ARM_LEVELS))
    for arm, label in zip(ARM_LEVELS, arm_labels(adsl), strict=True):
        table = table.cols_label(**{arm: label})
    return table.cols_label(Characteristic="")


def build_document_via_gt(adsl: pd.DataFrame, body: pd.DataFrame):
    """Build the document from the GT object rather than the raw frame."""
    from rtfreporter import as_rtftables

    pages = as_rtftables(
        build_gt(adsl, body),
        read_meta=True,
        col_spec=_col_spec(),
        col_rel_width=DM_WIDTHS,
    )
    doc = rtf_document(page=DM_PAGE)
    doc = rtf_tables(doc, pages)
    doc = rtf_section(doc, header=DM_HEADER, footer=DM_FOOTER)
    return doc


def main() -> str:
    adsl = load_adsl()
    body = build_body(adsl)
    doc = build_document(adsl, body)
    out = os.path.join(HERE, "showcase_dm.rtf")
    generate_rtfreport(doc, out, overwrite=True)

    # Second route: the identical body handed over as a great_tables object.
    gt_out = os.path.join(HERE, "showcase_dm_gt.rtf")
    generate_rtfreport(build_document_via_gt(adsl, body), gt_out, overwrite=True)
    print(f"wrote {gt_out}")
    print(f"wrote {out}")
    # Replace the non-breaking padding with a dot so the body is readable on
    # consoles whose encoding cannot represent U+00A0 (e.g. Windows cp932).
    preview = body.to_string(index=False).replace(" ", ".")
    print(preview)
    return out


if __name__ == "__main__":
    main()
