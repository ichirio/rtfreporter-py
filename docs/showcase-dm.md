# Showcase: demographics (Table 14.1.1)

A production-style demographics table built from real ADaM data, rendered to
RTF. Every figure on this page is checked against the R implementation of
`rtfreporter` — see [Validation](#validation-against-r).

Run it:

```bash
python examples/showcase_dm.py
```

## The data

The bundled `examples/data/adsl.csv` is a subset of
[pharmaverseadam](https://pharmaverse.github.io/pharmaverseadam/)'s `adsl`
(Apache-2.0, derived from the CDISC pilot study), restricted to the three
randomised arms. `examples/adam_data.py` loads it and applies the derivations:

```python
from adam_data import load_adsl, arm_counts, arm_labels

adsl = load_adsl()
arm_counts(adsl)     # Placebo 86, Xanomeline Low Dose 96, Xanomeline High Dose 72
arm_labels(adsl)     # ['Placebo (N=86)', 'Xanomeline Low Dose (N=96)', ...]
```

Three details matter for a clinical table:

* `TRT01A`, `SEX` and `RACE` become **ordered categoricals**, so `groupby`
  keeps a stable clinical row order rather than an alphabetical one.
* `RACE` declares **all four levels**, including ones with no subjects. Asian
  has zero subjects in every arm and must still appear as a row — a category
  that silently vanishes is a reporting bug.
* `AGEGR` is cut at `[-inf, 65)`, `[65, 81)`, `[81, inf)` (`right=False`).

No R and no network are needed. If you would rather not use the bundled data,
`examples/adam_synthetic.py` generates seeded, reproducible data with the same
column contract and can be swapped in directly.

## The furniture, defined once

The running header, footer, page geometry, column header and widths are plain
rtfreporter objects, built once and shared by both routes below.

```python
from rtfreporter import rtf_header, rtf_footer, rtf_page, rtf_col_header, col_cell

DM_HEADER = rtf_header(rows=[
    {"l": "Acme Biopharma, Inc.", "r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"},
    {"l": "Protocol ABC-2026-001", "r": "Status: Draft"},
    {"c": "Table 14.1.1"},
    {"c": "Summary of Demographic and Baseline Characteristics"},
    {"c": "Safety Population"},
    {"c": ""},
])

DM_FOOTER = rtf_footer(rows=[
    {"l": "Note: Percentages are based on the number of non-missing subjects "
          "in each treatment group."},
    {"l": "Program: /prod/abc/tfl/t_14_1_1_dm.py", "r": "Generated: 2026-08-23 09:14"},
])

DM_PAGE = rtf_page(paper_size="letter", orientation="landscape")
DM_WIDTHS = [40, 20, 20, 20]        # a wide stub, three equal arm columns
```

`{AUTO_PAGE}` and `{AUTO_TOTAL_PAGES}` become live RTF fields, so Word
renumbers them itself.

The column header is two rows: a spanner over the three arms, then the arm
labels carrying their N.

```python
col_header = rtf_col_header(
    [col_cell(cols=(1, 3), label="Treatment Group", align="center")],
    ["", *arm_labels(adsl)],
)
```

`cols=(1, 3)` is an **inclusive, 0-based** range: columns 1 through 3. Indices
are 0-based throughout the Python port — this is the one deliberate departure
from the R package.

## Counts that line up

Percentages come from [`format_count_pct`][rtfreporter.format_count_pct.format_count_pct], which
pads each cell so the closing parenthesis aligns down the column:

```python
from rtfreporter import format_count_pct

format_count_pct(14, 14 / 86)   # ' 14 (16.3)'  (padded with U+00A0)
format_count_pct(0, 0.0)        # '  0       '  (a zero keeps its digit)
```

A zero renders as a padded `0` with no parenthetical, identical to R. The
adverse-events table wants zeros written out as `0 (0.0%)` instead — see
[that page](showcase-ae.md#zeros-that-align) for why, and how.

## Building the table

The body is a tidy frame: one row per (characteristic, statistic), one column
per arm. `stub_vars` folds the two hierarchy columns into a single indented
clinical stub.

```python
from rtfreporter import as_rtftables, rtf_document, rtf_tables, rtf_section, generate_rtfreport

pages = as_rtftables(
    body,
    stub_vars=["Characteristic", "Statistic"],
    stub_label="",
    col_header=col_header,
    col_spec=[{"col": 0, "align": "left"},
              {"col": 1, "align": "center"},
              {"col": 2, "align": "center"},
              {"col": 3, "align": "center"}],
    col_rel_width=DM_WIDTHS,
    blank_rows="between_groups",
)

doc = rtf_document(page=DM_PAGE)
doc = rtf_tables(doc, pages)
doc = rtf_section(doc, header=DM_HEADER, footer=DM_FOOTER)
generate_rtfreport(doc, "showcase_dm.rtf", overwrite=True)
```

`blank_rows="between_groups"` inserts a separator wherever the group changes.
The two other R sentinels are named constants here, because Python's `-1`
(“the last element”) means the opposite of R's `-1` (“after the last row”):

```python
from rtfreporter import BEFORE_FIRST, AFTER_LAST

blank_rows=[BEFORE_FIRST, 2, AFTER_LAST]   # positions are 0-based
```

A bare negative integer is rejected rather than silently misread.

## The same table from great_tables

rtfreporter reads a `great_tables` `GT` object directly, including its labels
and spanners, so the column header need not be restated:

```python
from great_tables import GT

table = (
    GT(gt_frame)
    .tab_spanner(label="Treatment Group", columns=list(ARM_LEVELS))
    .cols_label(**{arm: label for arm, label in zip(ARM_LEVELS, arm_labels(adsl))})
)

pages = as_rtftables(table, read_meta=True, col_spec=..., col_rel_width=DM_WIDTHS)
```

Both routes produce the same numbers. See
[Importing tables](importing-tables.md) for what the adapter does and does not
carry across.

## Validation against R

`tests/test_showcase.py` asserts the Python output against
`data-raw/R_reference_numbers.txt`, generated by running the equivalent
computation in R over the same data:

| Statistic | Placebo | Xanomeline Low Dose | Xanomeline High Dose |
|-----------|--------:|--------------------:|---------------------:|
| n | 86 | 96 | 72 |
| Mean (SD) | 75.2 (8.59) | 76.0 (8.11) | 73.8 (7.94) |
| Median | 76.0 | 78.0 | 75.5 |
| Min, Max | 52, 89 | 51, 88 | 56, 88 |
| Age `<65` | 14 | 8 | 11 |
| Age `65 - 80` | 42 | 53 | 49 |
| Age `>80` | 30 | 35 | 12 |
| Male | 33 | 41 | 37 |
| Female | 53 | 55 | 35 |
| White | 78 | 90 | 62 |
| Black or African American | 8 | 6 | 9 |
| Asian | 0 | 0 | 0 |
| American Indian or Alaska Native | 0 | 0 | 1 |

If one of these disagrees, the Python side is wrong — the expectations are not
free-floating.
