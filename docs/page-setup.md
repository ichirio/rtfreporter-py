# Page and document setup

Everything about the sheet the report is printed on: paper size, orientation,
margins, where the running header and footer sit, the base font, and the
package-wide defaults behind all of it.

## The defaults

Out of the box a document is **US Letter, landscape, with uniform 0.75-inch
margins** — the geometry clinical TFLs normally use, and the same defaults as
the R package:

```python
>>> import rtfreporter as rr
>>> rr.rtfreporter_options()
{'page.paper_size': 'letter',
 'page.orientation': 'landscape',
 'page.margin_top_in': 0.75,
 'page.margin_bottom_in': 0.75,
 'page.margin_left_in': 0.75,
 'page.margin_right_in': 0.75,
 'font': 'Courier',
 'font_size_half_points': 18,
 'markup': 'script',
 'title_format': 'text',
 'footnote_format': 'table',
 'figure.default_dpi': 96,
 ...}
```

!!! note "Why 0.75 inches on every side"

    These are the FDA's PDF-submission minimums: at least 0.75 in for the
    left/binding edge and for a landscape top margin, and text kept at least
    0.375 in from any edge. A uniform 0.75 in clears all of them, so a
    default-geometry report is submission-safe without tuning.

    For an unusually wide table, narrowing the left/right margins to 0.5 in
    still clears the 0.375 in floor.

## Setting the page

`rtf_page()` builds the geometry; hand it to `rtf_document()`:

```python
from rtfreporter import rtf_document, rtf_page

page = rtf_page(
    paper_size="letter",     # "letter", "legal", "a3", "a4", "a5"
    orientation="landscape", # or "portrait"
    margin_left_in=0.5,      # widen the writable area for a wide table
    margin_right_in=0.5,
)
doc = rtf_document(page=page)
```

Explicit dimensions win over `paper_size` and are used exactly as given — they
are never swapped to match `orientation`:

```python
page = rtf_page(width_in=14, height_in=8.5)   # a custom wide sheet
```

### The header/footer band

The running header and footer sit **at the margin boundary** by default: the
band distance equals the full top/bottom margin. Override it per document when
you need the band closer to the paper edge:

```python
page = rtf_page(header_dist_in=0.5, footer_dist_in=0.5)
```

## Reconfiguring an existing document

`rtf_config()` returns a **copy** with overrides applied — whole objects
replace, dicts merge field by field:

```python
from rtfreporter import rtf_config

portrait = rtf_config(doc, page={"orientation": "portrait"})
# `doc` is unchanged
```

This is the copy-on-modify behaviour the R package has; see
[Document API guide](document-api.md).

## Fonts, row height and padding

`rtf_default_format()` carries the document-wide typographic defaults:

```python
from rtfreporter import rtf_default_format, rtf_document

fmt = rtf_default_format(
    font_size_half_points=18,        # 9 pt (half-points, as RTF counts them)
    row_height_twips=240,
    cell_padding_left_twips=72,
    cell_padding_right_twips=72,
    title_format="text",             # or "table"
    footnote_format="table",
)
doc = rtf_document(default_format=fmt)
```

Sizes are in **half-points** for fonts and **twips** (1/1440 inch) for
everything else — RTF's own units, kept rather than converted so values map
one-to-one onto the emitted control words.

A per-table setting always beats the document default, which in turn beats the
`rtfreporter.*` option, which beats the factory value.

## Site-wide defaults

`rtfreporter_options()` reads the resolved defaults, and sets them when called
with keywords — handy in a `sitecustomize.py` or at the top of a reporting run
so every table in a study inherits house style:

```python
import rtfreporter as rr

rr.rtfreporter_options(
    **{"page.paper_size": "a4", "page.orientation": "portrait", "font": "Times New Roman"}
)

rr.rtfreporter_reset_defaults()      # back to the factory values
```

Resolution order, highest first:

1. an explicit argument (`rtf_page(paper_size="a4")`),
2. an `rtfreporter.*` option set via `rtfreporter_options()`,
3. the factory default.

## Column widths

Three ways to size columns, in increasing specificity:

```python
as_rtftables(df, col_rel_width=[40, 20, 20, 20])       # proportions
as_rtftables(df, column_widths_twips=[5760, 2880])     # absolute twips
as_rtftables(df, table_width_pct=80)                   # % of the writable width
```

`auto_col_widths()` measures the rendered text and proposes widths, and
`text_width_in()` measures single strings:

```python
from rtfreporter import auto_col_widths, text_width_in

widths = auto_col_widths(df, table_width_twips=13680)
text_width_in(["Xanomeline High Dose"], font="courier_new", size_half_points=18)
```

`13680` twips is the writable width of default-geometry Letter landscape
(11 in − 2 × 0.75 in). `col_rel_width` and the auto width helpers track the
writable width for you.

## Where to next

- [Adding tables and figures](adding-content.md) — putting content on the page.
- [Headers and footers](headers-footers.md) — what goes in the band.
- [Borders and rules](borders.md) — the TFL rule convention.
