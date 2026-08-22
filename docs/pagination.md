# Paginating tables with `as_rtftables()`

[`as_rtftables`](reference.md#rtfreporter.adapters.as_rtftables) turns a table
into a **list of `RtfTable` page objects** — one per RTF page. Pagination has
three pillars: how rows are split, which column the page-shaping operations act
on, and how blank separator rows are inserted.

```python
import pandas as pd
from rtfreporter import as_rtftables

df = pd.DataFrame({"ID": list(range(10))})
```

## Split strategies

The `split` argument selects the strategy:

| `split` | Behaviour |
|---------|-----------|
| `"none"` | One page (the default). |
| `"rows"` | Fixed page size via `split_rows` (an int) or explicit cut positions. |
| `"by_value"` | One page per distinct `group_col` value. |
| `"group_safe"` | Fill pages up to `max_rows`, never splitting a group. |
| `"group_force"` | Like `group_safe`, but split an oversized group across pages. |

### By fixed row count

```python
pages = as_rtftables(df, split="rows", split_rows=4)
[p.nrows for p in pages]   # [4, 4, 2]
```

`split_rows` may also be an explicit list of cut positions.

### One page per group value

```python
df = pd.DataFrame({"grp": ["A", "A", "B"], "v": [1, 2, 3]})
pages = as_rtftables(df, split="by_value", group_col="grp")
[getattr(p, "name", None) for p in pages]   # ["A", "B"]
```

The group value is stored on each page's `name` attribute, handy for a title.

### Group-aware packing

`group_safe` and `group_force` both require `max_rows`. `group_safe` keeps every
group intact; `group_force` will split a single group larger than `max_rows`
across pages and mark the continuation:

```python
df = pd.DataFrame({"grp": ["A"] * 5, "v": list(range(5))})
pages = as_rtftables(df, split="group_force", group_col="grp", max_rows=3)
len(pages)                                   # 2
any("(Cont.)" in str(c) for c in pages[1].rows[0])   # True
```

The continuation label is configurable with `cont_label` (default `" (Cont.)"`).

## Shared column knobs

`sort_by`, `collapse_repeats`, `drop_cols` and `group_col` all select a column
by name or 0-based index and are applied **before** pagination, so they compose
predictably with any split:

```python
pages = as_rtftables(
    df,
    split="group_safe",
    group_col="grp",
    max_rows=10,
    sort_by="v",
    collapse_repeats="grp",   # blank repeated group labels within a page
    drop_cols=None,           # keep everything printed
)
```

## Blank separator rows

Blank rows visually separate groups. When `group_col` is set (and the split is
not `by_value`), a blank row is inserted **per page** wherever the group value
changes. You can also request blanks explicitly:

```python
# Explicit blank-row spec (see the blank_rows module):
from rtfreporter import blank_rows_by_change

pages = as_rtftables(df, blank_rows=blank_rows_by_change("grp"))

# Or a blank at the top / bottom of every page:
pages = as_rtftables(df, split="rows", split_rows=4,
                     blank_row_first=True, blank_row_end=True)
```

Blank positions are resolved on the *full* page body — so they stay correct even
when a grouping column is later removed with `drop_cols`.

## Custom split hooks

The built-in strategies are exposed as **factory functions** that return a
callable, on the same footing as a hand-written splitter. Pass either the
string name or the callable to `split=`:

```python
from rtfreporter import as_rtftables, page_split_group_safe

# These two calls are equivalent:
pages = as_rtftables(df, split="group_safe", max_rows=20, group_col="visit")
pages = as_rtftables(df, split=page_split_group_safe(max_rows=20, group_col="visit"))
```

A **custom split function** takes a single
[`Frame`][rtfreporter.pagination.Frame] and returns a list of `Frame` — one per
page. A page's `name` becomes the page/section name. This is the R
`split=<function>` hook:

```python
from rtfreporter import Frame, as_rtftables

def first_row_alone(frame: Frame) -> list[Frame]:
    """Put the first row on its own page, the rest on a second page."""
    head = Frame(frame.column_names, frame.rows[:1])
    tail = Frame(frame.column_names, frame.rows[1:])
    return [head, tail]

pages = as_rtftables(df, split=first_row_alone)
```

A split function that returns anything other than a list of `Frame` raises
[`PaginationError`][rtfreporter.pagination.PaginationError].
[`add_cont_label()`][rtfreporter.pagination.add_cont_label] helps you prepend a
`" (Cont.)"` label row when a group carries onto the next page.

The standalone [`paginate()`][rtfreporter.pagination.paginate] applies the same
machinery and returns the per-page `Frame` objects directly (use
`as_rtftables()` to also build the `RtfTable` pages).

## Assembling the document

Each page is an ordinary `RtfTable`; feed them to a document in order:

```python
from rtfreporter import RtfDocument, header

doc = RtfDocument().add_section(
    header=rtf_header([{"r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"}])
)
for page in pages:
    doc.add_table(page, title=["Listing 16.2.1"])
doc.save("listing.rtf")
```

See the runnable [`examples/pagination.py`](https://github.com/ichirio/rtfreporter-py/blob/main/examples/pagination.py).
