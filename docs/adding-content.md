# Adding tables and figures

How content gets onto pages: the content calls, per-page titles and footnotes,
and the one-item-per-page rule that shapes the whole model.

## One content item per page

A page holds **exactly one** table or figure, plus an optional title block above
it and footnote block below. That constraint comes from the R package and it is
what makes pagination predictable: a list of *n* content items becomes *n*
pages, in order.

```python
from rtfreporter import rtf_document, rtf_tables, generate_rtfreport

doc = rtf_tables(rtf_document(), [table_one, table_two, table_three])
# -> a three-page report
generate_rtfreport(doc, "report.rtf", overwrite=True)
```

Because `as_rtftables()` already returns one table per page, the two compose
directly:

```python
pages = as_rtftables(df, split="group_force", max_rows=20, group_col=0)
doc = rtf_tables(rtf_document(), pages)
```

## Tables

`rtf_tables()` accepts a finished `RtfTable`, or anything `rtftable()` can build
— a DataFrame, a dict of columns, a list of row dicts — and forwards any extra
keywords to `rtftable()`:

```python
doc = rtf_tables(
    rtf_document(),
    {"Subject": ["001", "002"], "Age": [34, 45]},
    col_rel_width=[60, 40],
    border="tfl",
)
```

Building the table first gives you the full surface (headers, spanners, styling)
before it reaches the page:

```python
from rtfreporter import rtftable, rtf_col_header, col_cell, style_header

table = rtftable(
    df,
    col_header=rtf_col_header(
        [col_cell(cols=(1, 2), label="Treatment Group", align="center")],
        ["Characteristic", "Placebo", "Active"],
    ),
    col_rel_width=[50, 25, 25],
)
table = style_header(table, bold=True, align="center")
doc = rtf_tables(rtf_document(), [table])
```

See [Importing tables](importing-tables.md) for the adapter route and
[Post-hoc styling](styling.md) for the style verbs.

## Figures

`rtf_figures()` takes `Figure` objects from `rtfplot()`, or plain paths:

```python
from rtfreporter import rtf_figures, rtfplot

doc = rtf_figures(rtf_document(), ["km_curve.png", "forest.png"])

# or with explicit sizing
fig = rtfplot("km_curve.png", width_twips=9000, align="center")
doc = rtf_figures(rtf_document(), [fig])
```

With no explicit size an image is embedded at its **native** size — the pixel
dimensions divided by the DPI recorded in the file. See [Figures](figures.md)
for how the DPI is read and what happens when the file does not record one.

## Titles and footnotes

Both content calls take `titles` and `footnotes`, each accepting either **one
block per page** or **a single block shared by every page**:

```python
doc = rtf_tables(
    rtf_document(),
    pages,
    titles=["Table 14.3.1", "", "Adverse Events"],   # shared by all pages
    footnotes=["Source: ADAE", "Generated 2026-08-23"],
)
```

A block is a list of lines. A line may be a plain string, or a dict for
per-line control:

```python
titles=[
    {"text": "Table 14.3.1", "bold": True, "align": "center"},
    "",
    {"text": "Adverse Events", "align": "center"},
]
```

Titles and footnotes render as a **single-column table the same width as the
content**, which is what keeps them aligned with the table rules above and
below. An empty string is a blank line.

To set them after the content is in place, use `rtf_titles()` / `rtf_footnotes()`:

```python
from rtfreporter import rtf_titles, rtf_footnotes

doc = rtf_titles(doc, [["Page one title"], ["Page two title"]])
doc = rtf_footnotes(doc, ["Common footnote"])
```

Both need content to already exist — they assign to pages, so calling them on an
empty document raises.

## Mixing tables and figures

Content calls append, so a report can interleave them:

```python
doc = rtf_document(page=page)
doc = rtf_tables(doc, [summary_table], titles=["Table 14.1"])
doc = rtf_figures(doc, ["km_curve.png"], titles=["Figure 14.1"])
doc = rtf_tables(doc, listing_pages, titles=["Listing 16.1"])
```

Every call returns a **new** document and leaves the one passed in unchanged, so
a configured base document can seed several reports safely:

```python
base = rtf_document(page=house_page, default_format=house_format)

report_a = rtf_tables(base, pages_a)   # base stays empty
report_b = rtf_tables(base, pages_b)   # independent of report_a
```

## Where to next

- [Headers and footers](headers-footers.md) — the running band and page numbers.
- [Paginating](pagination.md) — turning a long table into pages.
- [Rendering and post-processing](output.md) — writing the file.
