# Getting started

## Install

`rtfreporter` has **no required runtime dependencies** — the core renderer is
pure Python. Data-frame adapters are optional extras:

```bash
pip install rtfreporter              # core only
pip install "rtfreporter[pandas]"    # + pandas
pip install "rtfreporter[polars]"    # + polars
pip install "rtfreporter[gt]"        # + great_tables
pip install "rtfreporter[all]"       # all of the above
```

## The mental model

A document is a **flat sequence of content pages**. Each page holds exactly one
content item — a table or a figure — plus an optional title and footnote.
Running headers and footers are defined by **sections**, which overlay a
header/footer band onto a range of pages.

```
RtfDocument
├── section  (header + footer, from page N)
└── pages
    ├── page 1   title · table/figure · footnote
    ├── page 2   …
    └── page 3   …
```

Two output layers are available and interchangeable:

- a **fluent builder** — `RtfDocument().add_section(...).add_table(...).save(...)`, and
- a **functional layer** — `to_rtf(doc)` / `save(doc, path)`.

## A first table

The quickest path is to hand a dict of columns (or a DataFrame) straight to
`add_table`:

```python
from rtfreporter import RtfDocument

doc = RtfDocument().add_table(
    {"Subject": ["001", "002", "003"], "Age": [34, 45, 28]},
    title=["Table 14.1", "", "Demographics"],
    footnote=["Source: ADSL"],
)
rtf = doc.to_rtf()          # -> an RTF string
doc.save("demographics.rtf")  # -> writes the file
```

`add_table` accepts either a ready-made `RtfTable` or any input that
[`rtftable`](reference.md#rtfreporter.table.rtftable) understands: a dict of
columns, a `(column_names, rows)` pair, a list of row dicts, or a pandas /
polars DataFrame. Extra keyword arguments are forwarded to `rtftable`.

## Building the table explicitly

Use [`rtftable`](reference.md#rtfreporter.table.rtftable) when you want control
over headers, borders, column formatting, or blank rows:

```python
from rtfreporter import rtftable, RtfDocument

tbl = rtftable(
    {"Parameter": ["Age", "Weight"], "Placebo": ["54.3", "72.1"], "Active": ["52.8", "70.4"]},
    col_spec=[{"col": 1, "align": "right"}, {"col": 2, "align": "right"}],
    border="tfl",
)
RtfDocument().add_table(tbl).save("summary.rtf")
```

## Running headers and footers

Add a section before the pages it should cover. Page-number **tokens** are
substituted at render time:

```python
from rtfreporter import RtfDocument, header, footer

doc = (
    RtfDocument()
    .add_section(
        header=rtf_header([{"l": "Protocol XYZ", "r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"}]),
        footer=rtf_footer([{"c": "CONFIDENTIAL"}]),
    )
    .add_table({"A": [1, 2, 3]})
)
```

See [Headers and footers](headers-footers.md) for the full token vocabulary.

## From a DataFrame, with pagination

[`as_rtftables`](reference.md#rtfreporter.adapters.as_rtftables) reads a table
object and splits it into one `RtfTable` per page:

```python
import pandas as pd
from rtfreporter import RtfDocument, as_rtftables

df = pd.DataFrame({"Arm": ["A"] * 40 + ["B"] * 40, "Subject": range(80)})
pages = as_rtftables(df, split="group_force", group_col="Arm", max_rows=25)

doc = RtfDocument()
for page in pages:
    doc.add_table(page, title=["Listing 16.1"])
doc.save("listing.rtf")
```

Continue with [Importing tables](importing-tables.md) and
[Pagination](pagination.md).
