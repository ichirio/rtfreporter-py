# Importing tables with `as_rtftable()` / `as_rtftables()`

[`as_rtftables`](reference.md#rtfreporter.adapters.as_rtftables) is the single
entry point for turning a **table object** into the `RtfTable` page objects a
document consumes. It does two jobs:

1. **Read** the source table — its rendered body plus metadata the RTF renderer
   can use (column labels, spanning headers, titles/footnotes from a `GT`); and
2. **Paginate** — split the body into one `RtfTable` per page.

This article covers the *reading / conversion* side. Pagination has its own
guide: [Pagination](pagination.md).

```python
import pandas as pd
from rtfreporter import as_rtftables, as_rtftable

df = pd.DataFrame({
    "Parameter": ["Age (years)", "  Mean", "  SD"],
    "Placebo":   ["", "75.1", "8.2"],
    "Active":    ["", "74.4", "7.9"],
})

pages = as_rtftables(df)   # a list of RtfTable page objects
len(pages)                 # 1
single = as_rtftable(df)   # convenience: exactly one page, else an error
```

## Supported inputs

`as_rtftables()` accepts any of:

- a **pandas** `DataFrame`,
- a **polars** `DataFrame`,
- a **great_tables** `GT` object (column labels and one level of spanners are
  read into the header; titles/subtitles become the title block),
- a plain **dict** of columns,
- a **list of row dicts**, or
- a **list** of any of the above (flattened to one page set each).

`as_rtftable()` is a thin wrapper that runs with `split="none"` and returns the
single resulting page (raising if the input would produce more than one).

## Spanning headers from delimited names

Column names that encode a hierarchy with a delimiter are automatically
reconstructed into a spanning header. The default delimiters are `____` and
`___tlang_delim___` (configurable via `header_sep`):

```python
df = pd.DataFrame({
    "Item":          ["n", "Mean"],
    "Drug A____N":    [10, 11],
    "Drug A____Mean": [1.1, 2.2],
    "Drug B____N":    [20, 21],
    "Drug B____Mean": [3.3, 4.4],
})
tbl = as_rtftable(df)
# tbl.col_header -> a spanning row ("Drug A" over cols 1-2, "Drug B" over 3-4)
#                   above a label row ("Item", "N", "Mean", "N", "Mean")
```

## Building a clinical stub

`stub_cols` merges one or more hierarchy columns (outer → inner) into a single
indented leading **stub** column — the classic clinical row-label layout. Each
non-leaf level emits its own un-indented label row when its value changes; the
leaf level becomes the indented stub of each data row.

```python
df = pd.DataFrame({
    "Group": ["Age", "Age", "Sex"],
    "Stat":  ["n", "Mean", "Male"],
    "Value": [86, 75.1, 40],
})
tbl = as_rtftable(df, stub_cols=["Group", "Stat"], stub_label="", stub_indent=4)
# stub column -> "Age", "    n", "    Mean", "Sex", "    Male"
```

## Reshaping knobs

All of these act on a **column** selected by name or 0-based index:

| Argument | Effect |
|----------|--------|
| `sort_by` / `sort_desc` | Sort rows before pagination. |
| `collapse_repeats` | Blank out repeated consecutive values in a column. |
| `drop_cols` | Use a column for grouping/sorting but do not print it. |
| `group_col` | The grouping column for group splits and between-group blank rows. |

```python
df = pd.DataFrame({"grp": ["A", "A", "B"], "v": [1, 2, 3]})

as_rtftable(df, sort_by="v", sort_desc=[True])   # rows 3, 2, 1
as_rtftable(df, collapse_repeats="grp")          # second "A" blanked
as_rtftable(df, drop_cols="grp")                 # only column "v" printed
as_rtftable(df, group_col="grp")                 # blank row inserted at A→B change
```

## Missing values

`NaN` / `None` cells are normalised to blank cells during conversion, so a
pandas `float` column with gaps renders cleanly.

## What is *not* carried

The adapters are MVP-scoped. Cell-level styling from a `GT` object, footnotes,
summary rows and row groups are **not** read; only the data body, column labels,
one spanner level, and the title block are. Anything else can be reapplied with
the [style verbs](styling.md) or `rtftable()` arguments.
