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
| `{BOOK_PAGE}` | An empty slot that [`assemble_rtf(book_page=)`](assembling.md) fills with the assembled book's page number. |
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

(`{SECTION_PAGES}` was removed: it raises an error naming `{TOTAL_PAGES}` /
`{AUTO_TOTAL_PAGES}` instead.)

## Run tokens: which program, and when

A header, footer, title or footnote can also say which program wrote the file
and when.  These are filled **as the file is written**, the same on every page:

| Token | Becomes |
|-------|---------|
| `{PROGRAM}` | The program's path, as given. |
| `{PROGRAM_FULL}` | The same path made absolute (from the working folder when the file is written), with the system's separator. |
| `{PROGRAM_NAME}` / `{PROGRAM_DIR}` | Its file name / its folder. |
| `{DATETIME}` | The time of the render, `%d%b%Y  %H:%M` by default (`rtfreporter_options(datetime_format=)`); `{DATETIME:%Y-%m-%d}` takes a format of its own. Month and day names are English whatever the locale. |

Say the program **once, where the document is made**:

```python
doc = rtf_document(program="programs/t_dm.py")
footer = rtf_footer([{"l": "{PROGRAM_FULL}", "r": "Generated on: {DATETIME}"}])
```

`generate_rtfreport(program=)` overrides it for one call, and
`rtfreporter_options(program=)` sets one for the session.  When none is said
and a `{PROGRAM...}` token is used, the program is **found**, in this order:

1. the script Python runs (`__main__.__file__`, else `sys.argv[0]`);
2. the notebook a Jupyter kernel runs, when the kernel knows it (VS Code's
   `__vsc_ipynb_file__`, Jupyter Server 2's `JPY_SESSION_NAME`);
3. `rtf_document(program_fallback=)` (or `generate_rtfreport(program_fallback=)`)
   -- the last resort, so a program's own file name always wins.

A program found (or the fallback) is said in a one-line message on stderr; a
program said is not, and a file with no `{PROGRAM...}` token looks for
nothing.  The file name is completed to the one on disk: a file that is there
gets its real case; a name with no extension becomes the program of that name
in its folder (`.py`, `.ipynb`), else gets `.py`.  No program at all is an
error.  For a validated production run, say the program: a relative path
found this way is joined to the working folder.

For reproducible output (tests, golden files) fix the time with
`rtfreporter_options(render_time="2026-10-04 10:05:00")`.

## Tokens of one's own

A study's own values -- `{STUDY}`, `{CUTOFF}`, `{POPULATION}` -- come from
`rtf_document(tokens=)`, or `rtfreporter_options(tokens=)` for a session (the
document's value wins), and are filled like the run tokens, RTF-escaped:

```python
doc = rtf_document(tokens={"STUDY": "ABC-123", "CUTOFF": "01JUN2026"})
hdr = rtf_header([{"l": "Study {STUDY}", "r": "Data cut-off: {CUTOFF}"}])
```

A name is upper case -- a letter, then letters, digits or `_` -- and not one of
rtfreporter's own; a value is one string or number.  A column header takes its
values from `set_col_header(values=)` instead.

[`rtf_text_tokens()`](reference.md#rtfreporter.text_tokens.rtf_text_tokens)
lists every token a page's text may carry -- the page and run tokens, then a
document's (and the session's) own -- with when each is filled and an example
value, for a program that offers them in an "insert" menu or a preview.

## Leaving out empty rows

One header can serve every report of a study when a report with no value for
a line goes without it.  With `drop_empty_rows=True`, a band row whose tokens
of one's own are **all empty** when the file is written, and which says
nothing else but blanks and brackets, is left out:

```python
hdr = rtf_header([
    {"l": "Study {STUDY}", "r": "Page {PAGE} of {TOTAL_PAGES}"},
    {"l": "<{POPULATION}>"},          # left out when POPULATION is ""
], drop_empty_rows=True)
```

A row with no token, one of rtfreporter's own (`{PAGE}`) or an unknown one is
always written; a band whose every row is left out is no band.  The default,
`False`, writes every row.

## Band options

Both [`rtf_header()`](reference.md#rtfreporter.header_footer.rtf_header) and
[`rtf_footer()`](reference.md#rtfreporter.header_footer.rtf_footer) accept a
`border` (applied to the first row), `row_height_twips`, per-side cell
padding, a `width` (or the absolute `width_twips`), a `font` and
`font_size_half_points`, `markup` and `drop_empty_rows`.
