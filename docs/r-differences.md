# Differences from the R package

`rtfreporter` (Python) follows the R package's function names, argument names,
argument order, and defaults as closely as possible.  There are **two
deliberate divergences**, both chosen for Pythonic ergonomics.

## 1. Indices are 0-based

Every index-taking argument is **0-based** (R is 1-based).  A column *name* may
be used anywhere an index is accepted.  This applies to, among others:

- `drop_cols`, `sort_by`, `group_col`, `collapse_repeats`, `stub_vars`
- `col_cell(pos=...)` — the R **inclusive** two-element range semantics are
  kept, just 0-based: `col_cell((1, 3), "Treatment")` spans columns 1, 2, and 3.
  Validation requires `start >= 0` and `start <= end`.
- `row_title`
- `cell_styles` row keys

For example, R's `col_cell(pos = c(2, 5), "Treatment")` becomes
`col_cell((1, 4), "Treatment")` in Python.

## 2. `blank_rows` sentinels are named constants

R uses magic integers for the two special blank-row positions: `0` = *before
the first row* and `-1` = *after the last row*.  Python replaces these with two
**distinct, importable sentinel objects** so a stray `-1` cannot be silently
misread:

```python
from rtfreporter import rtftable, BEFORE_FIRST, AFTER_LAST

rtftable(data, blank_rows=[BEFORE_FIRST, 2, AFTER_LAST])
```

A bare integer position is **0-based** and means "insert a blank row *after*
data row `i`".  A bare negative integer raises an error pointing at
`AFTER_LAST`.

### R → Python mapping

| R `blank_rows`          | Python `blank_rows`      |
| ----------------------- | ------------------------ |
| `0`                     | `BEFORE_FIRST`           |
| `k` (1-based, after row `k`) | `k - 1` (0-based int) |
| `-1`                    | `AFTER_LAST`             |

So R's `blank_rows = c(0, 2, -1)` (before first; after data row 2; after last)
becomes Python `blank_rows=[BEFORE_FIRST, 1, AFTER_LAST]`.

## Everything else matches R

The module-level functions (`rtf_document`, `rtf_tables`, `rtf_header`,
`rtf_border`, `generate_rtfreport`, ...) mirror the R exports.  The Python class
names (`RtfTable`, `RtfDocument`, `ColSpec`, ...) are Python-only types — R has
no exposed classes (it is pure S3), so there is nothing to match — and the
fluent `RtfDocument` methods are an additional convenience layer over the
R-named functions.
