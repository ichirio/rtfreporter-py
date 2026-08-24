# Importing tables with `as_rtftable()` / `as_rtftables()`

[`as_rtftables`](reference.md#rtfreporter.adapters.as_rtftables) is the single
entry point for turning a **table object** into the `RtfTable` page objects a
document consumes. It does two jobs:

1. **Read** the source table — its rendered body plus metadata the RTF renderer
   can use (column labels, spanning headers, titles/footnotes from a `GT`); and
2. **Paginate** — split the body into one `RtfTable` per page.

This article covers the *reading / conversion* side. Pagination has its own
guide: [Pagination](pagination.md).

!!! note "How this differs from the R package"

    In R, reading table objects is the package's headline feature: it accepts
    `gt`, `gtsummary`, `rtables`/`tern`, `tfrmt`, `flextable` and `huxtable`
    objects, because that is the ecosystem R users already work in.

    **Python has no equivalents to most of those packages**, so the supported
    sources here are the ones that actually exist: **pandas**, **polars**, and
    **`great_tables`** (the Python port of `gt`, supported in full — spanners,
    `tab_style()` cell styling, row groups, summary rows and footnotes).

    The consequence is that the DataFrame route carries more weight in Python
    than in R: rather than handing over a finished framework object, you shape
    a tidy frame and let `as_rtftables()` finish it with `stub_vars`,
    `col_header`, `cell_format` and the pagination arguments. See
    [Relationship to R](relationship-to-r.md).

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
- a **great_tables** `GT` object (fully featured — see
  [Importing a great_tables `GT`](#importing-a-great_tables-gt) below),
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
tbl = as_rtftable(df, stub_vars=["Group", "Stat"], stub_label="", stub_indent=4)
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

## Importing a great_tables `GT`

The `GT` adapter is **full-featured**: it reads the rendered table and the
metadata channels the RTF renderer can reproduce.

```python
import pandas as pd
from great_tables import GT, style, loc
from rtfreporter import as_rtftable

df = pd.DataFrame({"grp": ["A", "A", "B"], "lbl": ["x", "y", "z"],
                   "n": [1, 2, 3], "pct": [0.1, 0.25, 1.0]})
gt = (
    GT(df, rowname_col="lbl", groupname_col="grp")
    .tab_header(title="Table 14.1", subtitle="Demographics")
    .tab_spanner(label="Statistics", columns=["n", "pct"])
    .cols_label(n="Count", pct="Percent")
    .fmt_percent("pct", decimals=1)
    .tab_style(style=style.text(weight="bold"), locations=loc.body("n", rows=[0]))
    .tab_source_note("Source: ADSL")
)
tbl = as_rtftable(gt)
```

### What **is** carried

| GT feature | Mapped to |
|------------|-----------|
| `fmt_*` formatted values | the **rendered/display** cell text (not the raw data) |
| hidden columns (`cols_hide`) | dropped |
| `cols_label` | column-header labels |
| `tab_spanner` (**multiple / nested levels**) | stacked spanning header rows |
| row groups (`groupname_col`) | full-width group-label rows with children indented into a leading stub (same convention as `stub_cols`) |
| `rowname_col` | the leading stub column |
| per-column alignment | `ColSpec.align` |
| `cols_width` (all `px`, or all `%`) | `column_widths_twips` / `col_rel_width` |
| `tab_style(style.text(...))` — bold / italic / underline / align / colour | the per-cell `cell_styles` channel (body) or `header_*` (labels) |
| `tab_style(style.borders(...))` — solid/double/dashed/dotted/hidden, px×15 / pt×20 twips | per-cell / per-header `Border` |
| `tab_header` title + subtitle | the title block |
| `tab_footnote` + `tab_source_note` text | the footnote block |
| grand-summary rows (where exposed) | best-effort labelled rows |

Border colour handling mirrors the R package: **black is omitted** (the RTF
default), and a **transparent or zero-alpha (`#RRGGBB00`) border yields *no*
border** — `tfrmt` overlays transparent borders to hide a theme's default rules,
and carrying them through would print spurious black lines.

### What is **not** carried

Cell **fills**, fonts and font sizes, Markdown, and great_tables' own *theme*
borders (`tab_options`) have no RTF counterpart and are ignored. In-cell
footnote **marks** (the superscript reference beside a value) are not injected;
the footnote *text* is still collected into the footnote block.

### Choosing what to read: `read_meta`

`read_meta` controls which metadata channels are read. The clean, reshaped body
(formatted values, hidden columns dropped, row groups interleaved) is **always**
produced; only the channels below are gated:

```python
as_rtftable(gt, read_meta=True)                 # everything (default)
as_rtftable(gt, read_meta=False)                # clean body only
as_rtftable(gt, read_meta=["titles", "styles"]) # just these channels
```

The tokens are `"col_header"`, `"alignment"`, `"spanning"`, `"widths"`,
`"titles"`, `"footnotes"`, and `"styles"`
(`rtfreporter.gt_adapter.GT_META_TOKENS`). An unknown token raises `ValueError`.

Because the `GT` adapter already reshapes the body, `stub_cols` / `drop_cols`
are rejected for `GT` input (row groups and hidden columns are handled for you).
Pagination (`split=`) and blank-row options still apply, and per-cell styles
stay aligned to their cells across page splits.
