# Splitting a report into sections

A *section* is a run of pages sharing one running header and footer. Splitting a
report into sections is how you give each table in a deliverable its own title
band, or restart a header per treatment group.

This page covers the two routes: letting the **data** drive the split, and
naming the sections **yourself**.

## What a section is

`rtf_section()` opens a section that applies from a page onward. Everything
added afterwards inherits that band until the next section:

```python
from rtfreporter import rtf_document, rtf_tables, rtf_section, rtf_header, rtf_footer

doc = rtf_document()
doc = rtf_section(doc, header=rtf_header([{"c": "Table 14.1 — Demographics"}]))
doc = rtf_tables(doc, dm_pages)

doc = rtf_section(doc, header=rtf_header([{"c": "Table 14.3 — Adverse Events"}]))
doc = rtf_tables(doc, ae_pages)
```

`page=` pins the section to an explicit 1-based page number instead of "the next
page added". Passing `None` for `header` or `footer` inherits the previous
section's band, so you can change only one of them.

## Route A — one section per group, from a column

When the thing you want to section by is a **real column** of the body, let
pagination name the pages for you. `split="by_value"` makes one page per
distinct value of `group_col` and names each page after that value:

```python
from rtfreporter import as_rtftables

pages = as_rtftables(
    lab_df,
    split="by_value",
    group_col="PARAMCD",     # one page per lab parameter
)
```

Each returned page carries its group value as its name, ready to become a
section heading.

This route needs the grouping key to still be a column. If you only want it for
grouping and not for display, keep it in the body for pagination and drop it
from the printed page:

```python
pages = as_rtftables(lab_df, split="by_value", group_col="PARAMCD", drop_cols=["PARAMCD"])
```

!!! warning "Do not drop the column you group on under `group_force`"

    Under `split="group_force"` the `(Cont.)` continuation label is written
    **into the grouping column's cell**. Hiding that column with `drop_cols`
    takes the marker with it. Group on a column that stays visible — see
    [Paginating](pagination.md).

## Route B — one section per table, with `combine_sections()`

Route A does not apply when the grouping is baked into *stub label rows* rather
than a column — which is what row-grouped sources produce. It also does not
apply to the commonest case of all: **several separate tables, each wanting its
own section**.

`combine_sections()` handles both. Each keyword argument is a group of pages;
its **first page** takes the argument's name and the rest are left blank, then
everything is concatenated into one flat list:

```python
from rtfreporter import combine_sections

pages = combine_sections(
    Demographics=dm_pages,
    Disposition=disp_pages,
    Adverse_Events=ae_pages,
)
```

The result is a single list you can hand straight to `rtf_tables()`. Only the
first page of each group is named, so a multi-page table is marked as **one**
group rather than one per page.

`combine_sections()` is format-agnostic — it only touches the names of the
tables in the list, so it works whatever produced them.

### Letting `auto_section` do the cutting

Those page names are consumed by `rtf_tables(auto_section=True)`, which opens a
section at each **named** page and appends the name as a heading row on the
running header:

```python
doc = rtf_document()
doc = rtf_section(doc, header=rtf_header([
    {"l": "Protocol ABC-2026-001", "r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"},
]))
doc = rtf_tables(doc, pages, auto_section=True)
```

Each section's header is the running header **plus its own label** — never the
previous section's as well. Unnamed pages fall through, so a multi-page table
stays one section. `section_label_align` places the label (`"left"` by default,
or `"center"` / `"right"`).

`split="by_value"` names its pages too, so the same call gives one section per
group without `combine_sections()`.

## Which route to use

| Situation | Route |
|---|---|
| Section per value of a body column | A — `split="by_value"`, `group_col=` |
| Several distinct tables in one deliverable | B — `combine_sections()` |
| Row-grouped source (group is a stub label row, not a column) | B |
| A single table that simply spans pages | Neither — one section is fine |

!!! note "One section per page is harmless"

    If you do nothing, a multi-page table is still rendered correctly; the
    header and footer repeat on every page. Sectioning is about the tidier
    one-section-per-table structure, not about fixing broken output.

## A worked example

```python
import pandas as pd
from rtfreporter import (
    as_rtftables, combine_sections, generate_rtfreport,
    rtf_document, rtf_header, rtf_section, rtf_tables,
)

dm = as_rtftables(dm_df, col_rel_width=[40, 30, 30])
ae = as_rtftables(ae_df, split="group_force", max_rows=16,
                  group_col=0, group_by="indent")

# Name each group's first page, then let auto_section cut the sections.
pages = combine_sections(Demographics=dm, Adverse_Events=ae)

doc = rtf_document()
doc = rtf_section(doc, header=rtf_header([
    {"l": "Protocol ABC-2026-001", "r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"},
]))
doc = rtf_tables(doc, pages, auto_section=True)
generate_rtfreport(doc, "deliverable.rtf", overwrite=True)
```

To combine reports that were rendered as **separate files**, with a table of
contents, see [Assembling deliverables](assembling.md) instead — that works on
finished RTF files rather than on in-memory pages.

## Where to next

- [Headers and footers](headers-footers.md) — what the band can contain.
- [Paginating](pagination.md) — the split strategies in detail.
- [Assembling deliverables](assembling.md) — combining rendered files.
