# Cross-check against the R package

Same data, same options → the same RTF commands. This directory holds a
differential test harness that renders a set of cases with **both** the R
package and this port and requires the output to be **byte-identical** (line
endings aside).

That makes the R implementation the oracle for the whole renderer at once,
instead of hand-written expectations one behaviour at a time. It has already
caught real port defects that unit tests missed — a stub indented with plain
spaces instead of non-breaking spaces, `split_rows` treated as a page size
rather than as cut positions, and separator rows inserted where R inserts none.

## Layout

| Path | Role |
|------|------|
| `cases.json` | The case definitions — data, options, expected-to-match |
| `render_r.R` | Renders every case with **R**, writing `tests/xcheck_golden/*.rtf` |
| `../../tests/xcheck_golden/` | R's output, **committed** so CI needs no R |
| `../../tests/test_xcheck_vs_r.py` | Renders the same cases in Python and diffs |

Committing R's output is what lets the comparison run on every push: the CI
machine has no R, but it still enforces R parity.

## Running it

The Python side needs nothing special — it is part of the normal suite:

```bash
pytest tests/test_xcheck_vs_r.py -v
```

Regenerating the golden files needs R, the `rtfreporter` R package checked out,
and `jsonlite`:

```bash
Rscript data-raw/xcheck/render_r.R                 # assumes C:/Yrepo/rtfreporter
Rscript data-raw/xcheck/render_r.R /path/to/rtfreporter
```

Then re-run the tests and **read the diff before committing**: a change in the
golden files means the R package's output moved, which is either a deliberate
upstream change to follow or a regression to report upstream.

## Adding a case

Append to `cases.json`:

```json
{
  "id": "my_case",
  "why": "One line on what this pins down — shown when the test fails.",
  "data": {"A": ["x", "y"], "B": [1, 2]},
  "as_rtftables": {"split": "group_safe", "group_col": "A", "max_rows": 4}
}
```

Then regenerate the golden file and run the suite. Two guards keep the set
honest: a case with no golden file fails, and a golden file with no case fails.

### Conventions

* **Prefer column names to indices.** Both implementations accept names
  identically, which sidesteps the 0-based/1-based divergence entirely.
* **When an index is unavoidable**, give both dialects and each renderer picks
  its own:

  ```json
  "as_rtftables": {"split_rows": {"r": 3, "py": 2}}
  ```

* **Keep cases deterministic.** No dates, no random data, no locale-dependent
  formatting — the comparison is exact.
* **Say why.** The `why` field is printed on failure and is often the fastest
  way to see what broke.

## What is compared

The whole rendered document: preamble, font and colour tables, page geometry,
section breaks, header/footer bands, column headers and spanners, every row and
cell, borders, blank rows, continuation markers and titles/footnotes.

Only the line-ending style is normalised (R writes CRLF, Python writes LF).
Everything else must match exactly.

## Which R the golden files come from

Since 0.5.0 the port follows **R `main` at 0.8.2.9026** (ichirio/rtfreporter
2385a6b), the development version after the v0.8.2 release, minus the ARD /
plan layer.  Every golden file was re-rendered from that commit with R 4.3.3;
all the files rendered by v0.8.2 (and the two #509 files rendered at
0.8.2.9003) came out **byte-identical**, so the R changes since v0.8.2 move no
output these cases cover.  New cases for the features ported from it:

| Golden files | What they pin |
|---|---|
| `own_tokens_program_full.rtf` | `{PROGRAM_FULL}` (#560) and tokens of one's own, `rtf_document(tokens=)` (#564) |
| `drop_empty_rows.rtf`, `drop_empty_rows_whole_band.rtf` | `rtf_header()` / `rtf_footer(drop_empty_rows=)` (#571) |
| `table_style_align_default.rtf`, `table_style_align_set.rtf` | `rtf_table_style(align=)` defaulting to each column's own (#522) |
| `assemble/toc_table.rtf` | `assemble_rtf(toc=<table>)` with no `input_files` (0.8.2.9014) |

`gt/` was not re-rendered (the `gt` R package was not installed); it is
still R v0.8.2's, and no R change since touches the gt reader.

Earlier history: `decimal/styles_size.rtf` and `decimal/font_fill.rtf` were
first rendered at the #509 fix (0e05ce5, 0.8.2.9003), and
`listing/wrap_key.rtf` after the #505/#506 fix (0.8.2.9001), while the rest
came from the v0.8.2 tag.

### Running the scripts without devtools

Each script loads the R package from the checkout with
`devtools::load_all(<path>)`; when devtools is not installed it falls back to
the **installed** package, so install the checkout first:

```bash
R CMD INSTALL /path/to/rtfreporter
Rscript data-raw/xcheck/render_r.R /path/to/rtfreporter
```
