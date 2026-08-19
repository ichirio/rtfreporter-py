# rtfreporter

**A Python toolkit for clinical RTF Tables, Listings and Figures (TLFs).**

`rtfreporter` composes a Rich Text Format (RTF) document — the format regulators
and medical writers still expect — directly from tabular data, with **no
third-party RTF engine**. It is a faithful, Pythonic port of the R package
[`rtfreporter`](https://github.com/ichirio/rtfreporter).

- Build tables with multi-row **spanning column headers**, per-column
  formatting, and the clinical **TFL border** convention.
- Turn a **pandas** / **polars** DataFrame or a **great_tables** `GT` object
  into paginated pages with one call (`as_rtftables`).
- Running **headers / footers** with automatic page-number fields
  (`{AUTO_PAGE}`, `{AUTO_TOTAL_PAGES}`).
- **Titles / footnotes**, blank separator rows, `(Cont.)` continuation markers.
- Embed **PNG / JPEG figures** at their native DPI.
- A fluent, chainable document builder plus a plain functional layer.

## Install

```bash
pip install rtfreporter          # core (no hard dependencies)
pip install "rtfreporter[all]"   # + pandas, polars, great_tables
```

## Quickstart

```python
from rtfreporter import RtfDocument, header, footer

doc = (
    RtfDocument()
    .add_section(
        header=header([{"l": "Protocol XYZ", "r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"}]),
        footer=footer([{"c": "CONFIDENTIAL"}]),
    )
    .add_table(
        {"Subject": ["001", "002", "003"], "Age": [34, 45, 28], "Sex": ["M", "F", "M"]},
        title=["Table 14.1", "", "Demographic Characteristics"],
        footnote=["Source: ADSL"],
    )
)

doc.save("demographics.rtf")
```

## Where to next

<div class="grid cards" markdown>

- **[Getting started](getting-started.md)** — install and a five-minute tour.
- **[Importing tables](importing-tables.md)** — `as_rtftable` / `as_rtftables`.
- **[Pagination](pagination.md)** — split strategies and `(Cont.)` markers.
- **[Borders and rules](borders.md)** — presets, zones, and per-cell control.
- **[Headers and footers](headers-footers.md)** — sections and page tokens.
- **[Figures](figures.md)** — embed PNG / JPEG.
- **[Styling](styling.md)** — the post-hoc style verbs.
- **[API reference](reference.md)** — every public symbol.

</div>
