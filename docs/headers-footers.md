# Headers and footers (sections)

An `rtfreporter` document is a flat sequence of content pages. The running
**header** and **footer** — the lines repeated at the top and bottom of every
page — are not attached to individual pages. They are defined by **sections**.

## The model: sections overlay page ranges

A **section** assigns a header and footer starting at a given page; that
header/footer applies to every page **from there until the next section**. There
is no separate per-page header mechanism. You create sections with
[`add_section`](reference.md#rtfreporter.document.RtfDocument.add_section):

```python
from rtfreporter import RtfDocument, header, footer

doc = (
    RtfDocument()
    .add_section(
        header=rtf_header([{"l": "Protocol XYZ-001", "r": "Confidential"}]),
        footer=rtf_footer([{"c": "ACME Pharma, Inc."}]),
    )
    .add_table({"A": [1, 2, 3]})
)
```

Two consequences worth remembering:

- Passing `header=None` (or `footer=None`) for a section means **inherit** the
  previous section's band — not "blank".
- Sections are an overlay on the flat page list; content order alone determines
  page numbers.

Start a second section at a later page with `from_page`:

```python
doc = (
    RtfDocument()
    .add_section(header=rtf_header([{"c": "Section 1"}]), from_page=1)
    .add_table({"A": [1]})
    .add_section(header=rtf_header([{"c": "Section 2"}]), from_page=2)
    .add_table({"A": [2]})
)
```

## Building a band

A band is a stack of rows; each row has one to three columns keyed by position:

- a plain **string** → a single centered column;
- a **dict** with `l` / `c` / `r` keys → left / center / right cells;
- a short **sequence** → `[c]`, `[l, r]`, or `[l, c, r]`.

```python
hdr = rtf_header([
    {"l": "Protocol XYZ-001", "r": "Confidential"},
    {"l": "Table 14.1.1",     "r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"},
])
ftr = rtf_footer(["ACME Pharma, Inc."])
```

## Page-number tokens

Cells may contain page tokens, substituted at render time:

| Token | Meaning |
|-------|---------|
| `{AUTO_PAGE}` | Current page number (a live field; updates in the viewer). |
| `{AUTO_TOTAL_PAGES}` | Total page count (a live `NUMPAGES` field). |
| `{SECTION_PAGES}` | Pages in the current section (a live field). |
| `{PAGE}` | Current page number, **baked in** statically at render time. |
| `{TOTAL_PAGES}` | Total page count, baked in statically. |

The `{AUTO_*}` tokens emit RTF *fields*, so a word processor keeps them correct
if pages reflow. The static `{PAGE}` / `{TOTAL_PAGES}` are resolved to literal
numbers during rendering; using `{PAGE}` causes each page to be emitted as its
own section so the number bakes in distinctly.

```python
rtf_header([{"r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"}])   # live field
rtf_header([{"r": "Page {PAGE}"}])                              # baked number
```

## Band options

Both [`header`](reference.md#rtfreporter.header_footer.header) and
[`footer`](reference.md#rtfreporter.header_footer.footer) accept a `border`
(applied to the first row), `row_height_twips`, per-side cell padding, and an
explicit `width_twips`.
