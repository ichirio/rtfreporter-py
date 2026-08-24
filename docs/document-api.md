# Document API guide

A report is built by starting from an empty document, adding content and
sections to it, and rendering the result. There are **two equivalent ways** to
write that, and you can mix them freely.

## Two spellings of the same thing

The R package composes a document with the native pipe:

```r
# R
rtf_document() |>
  rtf_tables(pages) |>
  rtf_section(header = hdr, footer = ftr) |>
  generate_rtfreport("report.rtf")
```

Python has no pipe operator, so the port offers both a **functional** form that
mirrors R line for line, and a **fluent** form that reads more naturally to
Python users.

=== "Functional (mirrors R)"

    ```python
    from rtfreporter import rtf_document, rtf_tables, rtf_section, generate_rtfreport

    doc = rtf_document(page=page)
    doc = rtf_tables(doc, pages)
    doc = rtf_section(doc, header=hdr, footer=ftr)
    generate_rtfreport(doc, "report.rtf", overwrite=True)
    ```

=== "Fluent (method chain)"

    ```python
    from rtfreporter import RtfDocument

    (
        RtfDocument(page=page)
        .add_tables(pages)
        .add_section(header=hdr, footer=ftr)
        .save("report.rtf")
    )
    ```

Both produce **byte-identical** output. Use whichever suits the surrounding
code: the functional form when translating R, the fluent form when writing
fresh Python.

!!! tip "Every call returns a new document"

    Documents are treated as immutable. `rtf_tables(doc, ...)` returns a *new*
    document rather than mutating `doc`, exactly as the R version does, so
    rebinding (`doc = rtf_tables(doc, ...)`) is required in the functional form.

## The building blocks

| Functional | Fluent method | Adds |
|---|---|---|
| `rtf_document(page=, default_format=, color_table=)` | `RtfDocument(...)` | the document itself |
| `rtf_tables(doc, tables, titles=, footnotes=)` | `.add_tables(...)` / `.add_table(...)` | one table page per list element |
| `rtf_figures(doc, figures, titles=, footnotes=)` | `.add_figure(...)` | one figure per page |
| `rtf_titles(doc, titles)` | `.titles(...)` | titles for the pages added so far |
| `rtf_footnotes(doc, footnotes)` | `.footnotes(...)` | footnotes likewise |
| `rtf_section(doc, page=, header=, footer=)` | `.add_section(...)` | a header/footer band over a page range |
| `generate_rtfreport(doc, path, overwrite=)` | `.save(path)` | writes the file |
| `to_rtf(doc)` | `.to_rtf()` | returns the RTF as a string |

## One content item per page

This is the model the R package uses and the port keeps: **each element of the
list you hand to `rtf_tables()` becomes one page.** `as_rtftables()` already
returns exactly that — a list of pages — so the two fit together:

```python
from rtfreporter import as_rtftables, rtf_document, rtf_tables, generate_rtfreport

pages = as_rtftables(df, split="group_force", max_rows=20, group_col=0)
doc = rtf_tables(rtf_document(), pages)
generate_rtfreport(doc, "listing.rtf", overwrite=True)
```

Titles and footnotes accept either **one value per page** or **a single value
shared by every page**:

```python
doc = rtf_tables(
    rtf_document(),
    pages,
    titles=["Table 14.1", "", "Demographic Characteristics"],   # same on every page
    footnotes=["Source: ADSL"],
)
```

## Rendering

`generate_rtfreport()` requires a path and, like R, refuses to clobber an
existing file unless you say so:

```python
generate_rtfreport(doc, "report.rtf")                  # errors if the file exists
generate_rtfreport(doc, "report.rtf", overwrite=True)  # replaces it
```

`to_rtf(doc)` returns the same bytes as a string if you would rather write them
yourself. See [Rendering and post-processing](output.md).

## A complete example

```python
import pandas as pd
from rtfreporter import (
    as_rtftables, generate_rtfreport, rtf_document, rtf_footer,
    rtf_header, rtf_page, rtf_section, rtf_tables,
)

df = pd.DataFrame({
    "Characteristic": ["Age (years)", "Age (years)", "Sex", "Sex"],
    "Statistic": ["Mean (SD)", "Median", "Male", "Female"],
    "Placebo (N=86)": ["75.2 (8.59)", "76.0", "33 (38.4%)", "53 (61.6%)"],
    "Active (N=96)":  ["76.0 (8.11)", "78.0", "41 (42.7%)", "55 (57.3%)"],
})

pages = as_rtftables(
    df,
    stub_vars=["Characteristic", "Statistic"],
    stub_label="",
    col_rel_width=[40, 30, 30],
    blank_rows="between_groups",
)

doc = rtf_document(page=rtf_page(paper_size="letter", orientation="landscape"))
doc = rtf_tables(doc, pages, titles=["Table 14.1.1", "", "Demographics"])
doc = rtf_section(
    doc,
    header=rtf_header([{"l": "Protocol ABC-2026-001",
                        "r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"}]),
    footer=rtf_footer([{"c": "CONFIDENTIAL"}]),
)
generate_rtfreport(doc, "demographics.rtf", overwrite=True)
```

## Where to next

- [Page and document setup](page-setup.md) — geometry, fonts and defaults.
- [Adding tables and figures](adding-content.md) — the content calls in detail.
- [Headers and footers](headers-footers.md) — sections and page-number fields.
