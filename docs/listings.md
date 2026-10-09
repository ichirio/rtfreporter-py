# Listings end to end

A table and a listing want different things from the same package. A table is
already a table by the time it reaches `rtfreporter`: something counted,
summarised and labelled it, and what is left is rendering. A listing is
different -- it is one row of source data per subject, and the work is
**shape**:

* several source variables belong in one printed column, joined by `/`;
* a long cell has to break over several physical rows so it fits a column that
  is only so many characters wide;
* narrow blank columns sit between the printed ones as gutters;
* one blank row separates one subject's block from the next; and
* **a page break must never land inside a subject's block.**

`listing_col()`, `listing_spec()` and `build_listing()` do the first four.
The fifth is `as_rtftables()`, which could already do it. This article runs the
whole thing, source data to `.rtf`.

## The source data

A small ADSL, one row per subject, shaped like an adverse-event
listing. Note the values that are longer than the column they will print in,
and the missing ones:

```python
import pandas as pd

adsl = pd.DataFrame({
    "USUBJID":  ["PILOT-204-1015", "PILOT-204-1023", "PILOT-205-100028",
                 "PILOT-206-1034", "PILOT-206-1045"],
    "DCDECOD":  ["COMPLETED", "COMPLETED", "DISCONTINUED", "ONGOING", "COMPLETED"],
    "AELOC":    ["UPPER", None, "LOWER", "UPPER", None],
    "AEDECOD":  ["HYPERGLYCAEMIA", "UPPER RESPIRATORY TRACT INFECTION",
                 "SKIN ULCER", "INJECTION SITE REACTION", "HYPERGLYCAEMIA"],
    "AETOXGR":  ["3", "4", "3", "4", "2"],
    "AESEV":    ["GRADE 3", "GRADE 2", "GRADE 3", "GRADE 1", None],
    "AESER":    ["Y", "N", "Y", "N", "Y"],
    "AEACN":    ["DOSE REDUCED", "DOSE NOT CHANGED", "DRUG INTERRUPTED",
                 "DRUG WITHDRAWN", "DOSE REDUCED"],
    "AEACNOTH": ["DOSE NOT CHANGED", "DRUG WITHDRAWN", "DOSE NOT CHANGED",
                 None, "DOSE NOT CHANGED"],
    "ECOGBL":   ["0", "1", "1", "0", "2"],
})
```

## Describing the columns

`listing_col()` describes **one printed column**: which source variables it is
built from, how wide it may be before its text wraps, and what its header says.

```python
from rtfreporter import listing_col

listing_col(["DCDECOD", "AELOC", "AEDECOD"], width=22,
            label="Disposition/\nLocation/\nPreferred Term")
```

Four things are worth reading twice.

**`vars` may name several columns.** Their values are joined with the
listing's separator (`/` by default), and **missing and empty values are
skipped** -- a subject with no `AELOC` prints `COMPLETED/UPPER RES...`, not
`COMPLETED//UPPER RES...`.

That join is `catx()`, which the package exports for the columns you build
yourself:

```python
>>> from rtfreporter import catx
>>> catx("/", "COMPLETED", None, "HYPERGLYCAEMIA")
['COMPLETED/HYPERGLYCAEMIA']
```

**`width` is a number of characters, not a rendered width.** It decides where
the text breaks onto another physical row, and therefore how tall the subject's
block is. What the column *measures* in the table is `rel_width`, which
defaults to `width`.

**The output column takes the first variable's name** -- `DCDECOD` above --
which is why the reshaped data below has a `DCDECOD` column holding the joined
text. It is an internal name, not a header; pass `name="COL01"` if you would
rather read the columns positionally.

**`label` may contain a line break**, which starts another header row -- the
same convention as everywhere else in rtfreporter, and what you write is used
exactly as written. Leave it out and the header is derived from the data: the
source column names, joined with the separator and wrapped to the column.
`label=""` asks for a deliberately empty one.

Two more per-column settings matter before the widths: `layout="flow"` fills
each line as far as `width` allows instead of breaking after every separator
-- for a column like `AGE/SEX`, which would otherwise spend two rows on four
characters -- and `collapse_repeats=True` marks a **key** column, printed once
per record and again at the top of the next page.

`listing_spec()` collects the columns, in the order they print, and the
settings that apply to all of them:

```python
from rtfreporter import listing_spec

spec = listing_spec([
    listing_col("USUBJID", width=15, label="Unique\nSubject ID"),
    listing_col(["DCDECOD", "AELOC", "AEDECOD"], width=22,
                label="Disposition/\nLocation/\nPreferred Term"),
    listing_col("AETOXGR", label="Grade at\nInitial\nDiagnosis"),
    listing_col(["AESEV", "AESER"], width=18,
                label="Severity/\nSerious\nEvent"),
    listing_col(["AEACN", "AEACNOTH"], width=20,
                label="Action Taken/\nOther Action\nTaken"),
    listing_col("ECOGBL", label="ECOG\nPerformance\nat Baseline"),
])
```

## Letting the page choose the widths

Every `width` above was picked by hand. That is the tedious part of writing a
listing -- too narrow and a cell wraps into a tall ragged block, too wide and
the listing runs off the sheet -- and it is not a matter of taste: the answer
follows from the paper, the margins, the font and the data.

`fit_listing_widths()` works it out. Describe the columns without widths:

```python
from rtfreporter import fit_listing_widths, rtf_page

bare = listing_spec([
    listing_col("USUBJID", collapse_repeats=True),
    listing_col(["DCDECOD", "AELOC", "AEDECOD"]),
    listing_col("AETOXGR"),
    listing_col(["AESEV", "AESER"]),
    listing_col(["AEACN", "AEACNOTH"]),
    listing_col("ECOGBL"),
])

fitted = fit_listing_widths(
    adsl, bare,
    page=rtf_page(paper_size="A4", orientation="landscape",
                  margin_left_in=0.5, margin_right_in=0.5),
    size_half_points=16,
)
```

The page's writable width, divided by the width of one character in the
listing's font, is how many characters there are to spend; the gutters come out
of it, because they print too.

Each column's **demand** is the 90th percentile of the display widths of its
cells -- a quantile rather than the maximum, so one unusually long value wraps
instead of pushing every other column narrow -- floored by the widest token
its header cannot break. That floor is why a label like `"Grade at Initial
Diagnosis"` asks for nine characters (`"Diagnosis"`) and not twenty-six: a
header wraps, so a long one should not claim a column the data does not need.

A `width` you set yourself is never touched. It comes out of the budget first
and the rest fit around it:

```python
>>> pinned = listing_spec([
...     listing_col("USUBJID", width=15),          # this one is a decision
...     listing_col(["DCDECOD", "AELOC", "AEDECOD"]),
...     listing_col("AETOXGR"),
... ])
>>> [c.width for c in fit_listing_widths(adsl, pinned, total_width=60).cols]
[15, 36, 7]
```

### Paste it back into the program

The measurement is a starting point, not a verdict, so it comes back as
source:

```python
>>> from rtfreporter import listing_code
>>> print(listing_code(fitted, name="listing"))
listing = listing_spec([
    listing_col('USUBJID', width=21, rel_width=21, collapse_repeats=True,
        label='USUBJID'),
    listing_col(['DCDECOD', 'AELOC', 'AEDECOD'], width=57, rel_width=57,
        label='DCDECOD/AELOC/AEDECOD'),
    listing_col('AETOXGR', width=10, rel_width=10,
        label='AETOXGR'),
    listing_col(['AESEV', 'AESER'], width=13, rel_width=13,
        label='AESEV/AESER'),
    listing_col(['AEACN', 'AEACNOTH'], width=45, rel_width=45,
        label='AEACN/AEACNOTH'),
    listing_col('ECOGBL', width=8, rel_width=8,
        label='ECOGBL'),
])
```

Paste that into the program and tune it there. A column whose header must not
break, or one you want roomy, is a judgement the program should record -- not
something recomputed on every run from data that may change. Only what differs
from the listing's defaults is written out.

## What `build_listing()` does

```python
from rtfreporter import build_listing

body = build_listing(adsl, spec)
pd.DataFrame(body.rows, columns=body.column_names)
```

```text
           USUBJID .sp1            DCDECOD .sp2 AETOXGR .sp3     AESEV .sp4              AEACN .sp5 ECOGBL  .rtf_record
0   PILOT-204-1015              COMPLETED/            3       GRADE 3/           DOSE REDUCED/           0            1
1                                   UPPER/                           Y        DOSE NOT CHANGED                        1
2                           HYPERGLYCAEMIA                                                                            1
3                                                                                                                     1
4   PILOT-204-1023              COMPLETED/            4       GRADE 2/       DOSE NOT CHANGED/           1            2
5                        UPPER RESPIRATORY                           N          DRUG WITHDRAWN                        2
6                          TRACT INFECTION                                                                            2
7                                                                                                                     2
8       PILOT-205-           DISCONTINUED/            3       GRADE 3/       DRUG INTERRUPTED/           1            3
9           100028                  LOWER/                           Y        DOSE NOT CHANGED                        3
10                              SKIN ULCER                                                                            3
11                                                                                                                    3
12  PILOT-206-1034                ONGOING/            4       GRADE 1/          DRUG WITHDRAWN           0            4
13                                  UPPER/                           N                                                4
14                          INJECTION SITE                                                                            4
15                                REACTION                                                                            4
16                                                                                                                    4
17  PILOT-206-1045              COMPLETED/            2              Y           DOSE REDUCED/           2            5
18                          HYPERGLYCAEMIA                                    DOSE NOT CHANGED                        5
19                                                                                                                    5
```

Read that against the source data:

* **`USUBJID` wrapped.** `PILOT-205-100028` is 16 characters and the column
  takes 15, so it breaks after a hyphen -- `build_listing()` breaks at word
  boundaries (a space, a comma, a hyphen) and takes the break *after* the
  character, so the reader can see why the line ended.
* **The joined column breaks at the separator first.** Each source variable
  starts its own line, which is what makes a listing of this shape readable at
  all. Only a piece that is *still* too long breaks again at a word boundary --
  `UPPER RESPIRATORY TRACT INFECTION` becomes two lines under a 22-character
  column.
* **Every column of one subject is padded to the tallest**, so the block stays
  aligned across columns, and **a blank row closes each block**.
* **`.sp1` … `.sp5` are the gutters**, the narrow blank columns between the
  printed ones.
* **`.rtf_record` is bookkeeping**, not a printed column: one id per source row.
  It is what keeps a subject whole across a page break, below.

A token that is *still* too wide -- one with nowhere to break -- is hard-split
at the column width. Cutting a subject id in half is ugly, but the alternative
is worse: the column's relative width follows `width`, so an overflowing token
is one Word wraps onto a second line, making the record a row taller than
`build_listing()` counted and the page taller than `max_rows` allowed for.

Widths are **display widths**: a full-width (CJK) glyph occupies two monospaced
columns and counts as two, so a Japanese listing wrapped to 20 really does fit
in twenty.

## Rendering it

`build_listing()` is preparation only -- it hands back an ordinary `Frame`, and
`as_rtftables()` renders. The body carries its spec, so the two compose:

```python
from rtfreporter import as_rtftables

pages = as_rtftables(body)
```

The **header, the relative widths and the left alignment all came from the
spec.** None of the three had to be written out: no list of header strings
with an empty entry for every gutter, no `col_rel_width=[15, 1, 22, 1, ...]`
to keep in step with the column list, no `col_spec` repeating `"align": "left"`
eleven times.

Usually you do not want the intermediate object at all, and pass the spec
straight to `as_rtftables()`:

```python
pages = as_rtftables(adsl, listing=spec)
```

The two forms produce the same tables. Reach for `build_listing()` when you
want to look at -- or patch -- the reshaped data before it is rendered; reach
for `listing=` the rest of the time.

## Keeping a subject whole across a page break

Give it a row budget and it paginates, **never splitting a subject's block**:

```python
>>> pages = as_rtftables(adsl, listing=spec, max_rows=8)
>>> [len(p.rows) for p in pages]
[8, 4, 8]
```

The second page holds one subject only: the next block is five rows, and four
plus five would not fit in eight.

Nothing new implements that. `build_listing()` emitted the `.rtf_record`
column, and the hook pointed the machinery that was already there at it:

```python
# what as_rtftables(listing=spec, max_rows=8) sets for you
as_rtftables(body, max_rows=8,
             group_col=".rtf_record",   # a group is one subject's block
             group_by="value",          # a new value starts a new group
             split="group_safe",        # fill the page, never split a group
             drop_cols=".rtf_record")   # ... and never print it
```

`drop_cols` columns are hidden **after** pagination, which is why a column can
decide the page breaks and still never appear. Every one of those is a
*default*: pass `split`, `group_col` or `drop_cols` yourself and the hook
leaves your choice alone.

## The whole report

Landscape, because a listing is wide; a title block, a footnote block, and the
file:

```python
from rtfreporter import (generate_rtfreport, rtf_default_format, rtf_document,
                         rtf_footer, rtf_header, rtf_section, rtf_tables)

pages = as_rtftables(adsl, listing=spec, max_rows=8)

doc = rtf_document(
    page=rtf_page(orientation="landscape", paper_size="A4",
                  margin_top_in=0.5, margin_bottom_in=0.5,
                  margin_left_in=0.5, margin_right_in=0.5),
    default_format=rtf_default_format(font_size_half_points=16),
)
doc = rtf_section(
    doc,
    header=rtf_header([["Listing 16.2.7.1"], ["Adverse Events"],
                       ["<Safety Analysis Set>"]]),
    footer=rtf_footer([{"l": "ECOG: Eastern Cooperative Oncology Group"}]),
)
doc = rtf_tables(doc, pages)
generate_rtfreport(doc, "listing-16-2-7-1.rtf", overwrite=True)
```

That is the whole pipeline: `adsl` in, one `.rtf` out, with the column
description as the only thing written by hand.

## Listing types

`listing_spec(type=)` names a template that supplies the defaults --
separator, gutters and their width, the blank row after each record, the
default alignment, and the wrapping rule itself. One ships:

| `type` | what it means |
|---|---|
| `"multiline"` | `/` separator, gutter columns, a blank row after each record and one at the top of every page, left aligned, and text wrapped at the separator first and at word boundaries only where a piece is still too long. |

Any argument you pass explicitly overrides the template, the same relationship
`rtftable(border="tfl")` has with its preset:

```python
listing_spec(["USUBJID", "AETOXGR"],
             sep=" | ",        # join with something else
             spacer=False,     # no gutter columns
             blank_row=False)  # no blank row between records
```

`record=False` drops the hidden record column too -- do that only if you
intend to paginate some other way, because it is what a page break is told to
respect.

### Changing how a cell breaks

`listing_spec(wrap=)` takes a function of `(text, width, sep, layout)` that
returns one element per line. There are two ways in, and they answer different
questions.

**Adjust the rule from outside.** `listing_wrap()` *is* the shipped rule, so
call it and fix up what comes back:

```python
>>> from rtfreporter import listing_wrap
>>> def cap_two(text, width, sep, layout):
...     out = listing_wrap(text, width, sep, layout)
...     if width is not None and len(out) > 2:
...         out = [out[0], out[1][: width - 1] + "…"]
...     return out
>>> cap_two("UPPER RESPIRATORY TRACT INFECTION", 12, "/", "stack")
['UPPER', 'RESPIRATORY…']
```

**Change the rule from inside.** When the break logic itself has to differ --
a different notion of a word, a byte budget rather than a display width --
`listing_wrap_code()` writes the shipped rule out as Python source to paste
into your program and edit. It is the real code, checked against the rule by
the test suite, so it cannot disagree with what the package runs. What it hands
you is the *policy*: the functions a fork rewrites. The measurements they are
built on -- `listing_disp_width()`, `listing_take()`, `listing_split_after()`
-- are imported and called, not copied, so a fix to those reaches every fork:

```python
>>> from rtfreporter import listing_wrap_code
>>> print(listing_wrap_code("my_wrap"))
# The "multiline" wrapping rule from rtfreporter, to edit.
#
#   listing_spec(cols, wrap=my_wrap)
#
# Keep the contract: called with (text, width, sep, layout); `width` may
# be None; `layout` is "stack" or "flow"; return a non-empty list of lines.
#
import re

from rtfreporter import listing_disp_width, listing_split_after, listing_take
...
```

Paste it, change what you need, and hand the entry function to
`listing_spec(wrap=my_wrap)`.

## Checked against R

The listing machinery is a port of the R package's, and its differential test
(`data-raw/xcheck/listing_r.R`) renders two listings with **both**
implementations and requires byte-identical RTF, and compares
`build_listing()`'s body, the fitted widths and `listing_wrap()` over a corpus
of awkward strings. The R package's own article, which also covers the
**rlistings** route (not available in Python), is
[Listings end to end](https://ichirio.github.io/rtfreporter/articles/listings.html).

## See also

* [Paginating](pagination.md) -- the split strategies, `group_col` /
  `group_by`, and `drop_cols` in general.
* [API reference: Listings](reference.md#listings) -- every setting, one entry
  each.
