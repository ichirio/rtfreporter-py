# Assembling multi-file deliverables

A clinical submission is usually **many** RTF tables, listings and figures that
have to ship as one navigable document. The assemble family concatenates
files produced by [`generate_rtfreport`][rtfreporter.document.generate_rtfreport]
into a single deliverable — taking the fonts, colours and page geometry from the
first file — and optionally prepends a cover page and a clickable **Table of
Contents** with per-file bookmarks.

## The quick path

```python
from rtfreporter import assemble_rtf

assemble_rtf(
    ["t14_1_1.rtf", "t14_2_1.rtf", "l16_1.rtf"],
    "deliverable.rtf",
    toc="auto",                    # one TOC entry per file, title auto-extracted
    toc_page_numbering="roman",    # TOC pages i, ii; body restarts at 1
    overwrite=True,
)
```

`toc="auto"` reads each file's **rendered title** (the first centred-bold
paragraph of the page) and uses it as a level-1 TOC entry, falling back to the
file's base name when no title is found. Every entry is an RTF `HYPERLINK`
field pointing at a per-file bookmark, plus a `PAGEREF` field so the page number
next to it is filled in by the viewer.

!!! note "Auto titles track the renderer"
    Because `"auto"` parses the rendered title format, it stays in lock-step
    with how [`rtftable`][rtfreporter.table.rtftable] titles are emitted
    (`\pard\qc\li0\ri0 \b TITLE\b0 \par`). If you render titles as a title
    *table* instead of text, the same centred-bold cell is matched.

## Multi-level TOC and a cover page

A multi-level (chapter / table) table of contents is a **table**: one row per
file, in order -- a list of dicts or a pandas / polars DataFrame -- with
`file` and `label`, and optionally `heading` (printed above the row's entry
whenever it changes; `None` = none), `level` (the entry's indent, default 2)
and `order`.  `input_files` can then be left out: the table's `file` column
is used.

```python
from rtfreporter import assemble_rtf

assemble_rtf(
    toc=[
        {"file": "t14_1_1.rtf", "heading": "EFFICACY ANALYSES",
         "label": "Table 14.1.1 Demographics"},
        {"file": "t14_2_1.rtf", "heading": "SAFETY ANALYSES",
         "label": "Table 14.2.1 Adverse Events"},
        {"file": "l16_1.rtf", "heading": "LISTINGS",
         "label": "Listing 16.1 Disposition"},
    ],
    output_file="deliverable.rtf",
    cover={"title": "Study XYZ-001", "subtitle": "Final Report",
           "date": "2026-05-28", "version": "v1.0",
           "meta": ["Confidential"]},
    overwrite=True,
)
```

## Folder → table of contents → deliverable

For a whole output folder, [`assemble_folder`][rtfreporter.assemble.assemble_folder]
reads each file's table number and title into that table (natural-sorted, so
`t2` precedes `t10`).  Without an `output_file` it only returns the table, to
edit and hand to `assemble_rtf(toc=)`:

```python
from rtfreporter import assemble_folder, assemble_rtf

# One editable dict per file: order / file / table / heading / label / level / pages
toc = assemble_folder("output/tfl")
toc[0]["heading"] = "Demographics"   # group entries under a TOC heading
assemble_rtf(toc=toc, output_file="deliverable.rtf", overwrite=True)

# Or do all of it in one call (optionally saving the table to a .csv, which
# assemble_rtf(toc="toc.csv") reads back after you edit it):
assemble_folder("output/tfl", "deliverable.rtf", spec_file="toc.csv", overwrite=True)
```

!!! warning "Deprecated in 0.5.0 (as in R 0.8.2.9014)"
    `assemble_files()`, `assemble_spec()`, `assemble_toc()`,
    `assemble_from_spec()`, `toc_heading()` and `toc_entry()` still work and
    warn once a session; they are removed in 0.9.0.  `assemble_spec(dir)` is
    `assemble_folder(dir)`, `assemble_from_spec(spec, out)` is
    `assemble_rtf(toc=spec, output_file=out)`, and a list of `toc_heading()` /
    `toc_entry()` is a table whose `heading` column is filled.

See the runnable [`examples/assemble.py`](https://github.com/ichirio/rtfreporter-py/blob/main/examples/assemble.py).
