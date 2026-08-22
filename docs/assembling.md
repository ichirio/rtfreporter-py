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

```python
from rtfreporter import assemble_rtf, toc_heading, toc_entry

assemble_rtf(
    ["t14_1_1.rtf", "t14_2_1.rtf", "l16_1.rtf"],
    "deliverable.rtf",
    cover={"title": "Study XYZ-001", "subtitle": "Final Report",
           "date": "2026-05-28", "version": "v1.0",
           "meta": ["Confidential"]},
    toc=[
        toc_heading("EFFICACY ANALYSES"),
        toc_entry("Table 14.1.1 Demographics", file="t14_1_1.rtf"),
        toc_heading("SAFETY ANALYSES"),
        toc_entry("Table 14.2.1 Adverse Events", file="t14_2_1.rtf"),
        toc_heading("LISTINGS"),
        toc_entry("Listing 16.1 Disposition"),   # bound to the next unused file
    ],
    overwrite=True,
)
```

## Folder → spec → deliverable

For a whole output folder, build an editable **assembly spec** (one row per
file, with the table number and title read from each file), tweak it, and
assemble:

```python
from rtfreporter import assemble_spec, assemble_from_spec, assemble_folder

# One editable dict per file: order / file / table / heading / label / level / pages
spec = assemble_spec("output/tfl")
spec[0]["heading"] = "Demographics"   # group entries under a TOC heading
assemble_from_spec(spec, "deliverable.rtf", overwrite=True)

# Or do all of it in one call (optionally saving the spec to a .csv):
assemble_folder("output/tfl", "deliverable.rtf", spec_file="spec.csv", overwrite=True)
```

[`assemble_files`][rtfreporter.assemble.assemble_files] lists a folder's `.rtf`
files in natural-sorted order (so `t2` precedes `t10`);
[`assemble_toc`][rtfreporter.assemble.assemble_toc] turns files (or a spec) into
the `toc=` list directly.

See the runnable [`examples/assemble.py`](https://github.com/ichirio/rtfreporter-py/blob/main/examples/assemble.py).
