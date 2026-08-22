# rtfreporter (Python) — Build Report

**Version:** 0.2.0
**Date:** 2026-08-22
**Scope:** Python port of the R package `rtfreporter` (clinical RTF Tables,
Listings and Figures). This report states plainly what is implemented, where the
Python port deliberately diverges from R, how the test suite compares to the R
original, and what remains before a first PyPI upload.

> Guiding principle for this report: **honesty over optimism.** Where a feature
> is partial or an R capability was not ported, it is called out as such rather
> than glossed over.

---

## 1. Headline results

| Check | Result |
|-------|--------|
| `pytest -q` | **795 passed**, 0 failed |
| Coverage (`pytest --cov`, branch on) | **94.02% line** (3764 stmts, 225 missed); 91.66% line+branch combined; enforced at `--cov-fail-under=90` |
| `ruff check .` | **All checks passed!** |
| `mkdocs build --strict` | **exit 0** |
| Packaging | `python -m build` → sdist + wheel; `twine check` **PASSED**; wheel installs into a clean venv and imports |

Pasted results:

```
$ pytest -q
TOTAL                                  3764    225   1800    189    92%
Required test coverage of 90% reached. Total coverage: 91.66%
795 passed in 8.05s

$ ruff check .
All checks passed!

$ mkdocs build --strict
exit=0 (strict build OK)

$ twine check dist/*
Checking dist/rtfreporter-0.2.0-py3-none-any.whl: PASSED
Checking dist/rtfreporter-0.2.0.tar.gz: PASSED
```

(Line coverage — statements only — is 94.02%; the 91.66% figure the gate reports
is the combined line+branch number, which is what `--cov-fail-under` measures.)

---

## 2. R-to-Python API mapping

Every `export(...)` in `/workspace/rtfreporter/NAMESPACE` (74 functions) with its
Python status. Legend: ✅ implemented · 🟡 partial · ❌ not ported.

**All 74 R-exported functions exist in the Python public API** (`rtfreporter.__all__`).
Six are partial (an advanced argument path or a simplified output); none are missing.

### Defaults / configuration

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `rtfreporter_options` | `rtfreporter_options` | ✅ | snapshot + setter returning prior values |
| `rtfreporter_reset_defaults` | `rtfreporter_reset_defaults` | ✅ | |

### Pipe composition API

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `rtf_document` | `rtf_document` | ✅ | |
| `rtf_config` | `rtf_config` | 🟡 | `font_table=` raises `NotImplementedError` (single built-in font table) |
| `rtf_page` | `rtf_page` | ✅ | |
| `rtf_default_format` | `rtf_default_format` | ✅ | |
| `rtf_tables` | `rtf_tables` | ✅ | |
| `rtf_figures` | `rtf_figures` | ✅ | |
| `rtf_section` | `rtf_section` | ✅ | |
| `rtf_titles` | `rtf_titles` | ✅ | |
| `rtf_footnotes` | `rtf_footnotes` | ✅ | |
| `generate_rtfreport` | `generate_rtfreport` | ✅ | |

### Content constructors

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `rtftable` | `rtftable` | ✅ | dict / `(names, rows)` / records / pandas / polars |
| `rtfplot` | `rtfplot` | ✅ | PNG/JPEG native DPI (pHYs / JFIF) |

### Table-object adapters

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `as_rtftable` | `as_rtftable` | 🟡 | Among table objects, only `great_tables` is read (R also does gt/gtsummary/flextable/huxtable/rtables) |
| `as_rtftables` | `as_rtftables` | 🟡 | `great_tables` only; `group_by≠"auto"`, `count_blank_rows`, `auto_width`, `stub_group_summary="parent"` raise `NotImplementedError` |
| `combine_sections` | `combine_sections` | ✅ | |

### DataFrame finishing

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `stub_cols` | `stub_cols` | ✅ | indented clinical stub, `group_summary` empty/parent |
| `collapse_repeats` | `collapse_repeats` | ✅ | table + page-list (per-page restart) |

### Header / footer

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `rtf_header` | `rtf_header` | ✅ | |
| `rtf_footer` | `rtf_footer` | ✅ | |
| `update_header_row` | `update_header_row` | ✅ | 0-based row index |
| `update_footer_row` | `update_footer_row` | ✅ | |

### Column-header API

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `col_cell` | `col_cell` | ✅ | index / name / range refs |
| `rtf_col_header` | `rtf_col_header` | ✅ | |
| `add_col_header_row` | `add_col_header_row` | ✅ | |
| `col_header_from_names` | `col_header_from_names` | ✅ | delimited-name spanner reconstruction |

### Post-hoc styling / header verbs

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `style_header` | `style_header` | ✅ | table + list dispatch (Python `_map_pages`) |
| `style_cols` | `style_cols` | ✅ | |
| `style_body` | `style_body` | ✅ | |
| `style_zone` | `style_zone` | ✅ | |
| `add_header_row` | `add_header_row` | ✅ | |
| `set_col_header` | `set_col_header` | ✅ | |
| `set_header_cell` | `set_header_cell` | ✅ | boundary-aligned merge |
| `rtf_columns` | `rtf_columns` | ✅ | |
| `rtf_header_source` | `rtf_header_source` | 🟡 | Emits Python source (a simplified port of R's reproducer) |

### Pagination

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `paginate` | `paginate` | 🟡 | default/DataFrame/list/`gt_tbl`; `group_by` only `"auto"` |
| `set_blank_rows` | `set_blank_rows` | 🟡 | `group_by` `"indent"`/`"filled"` raise `NotImplementedError` |
| `add_cont_label` | `add_cont_label` | ✅ | |
| `page_split_none` | `page_split_none` | ✅ | |
| `page_split_rows` | `page_split_rows` | ✅ | |
| `page_split_group_safe` | `page_split_group_safe` | ✅ | |
| `page_split_group_force` | `page_split_group_force` | ✅ | |
| `page_split_by_value` | `page_split_by_value` | ✅ | |

### Count / percent formatters

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `fmt_count_paren` | `fmt_count_paren` | ✅ | |
| `fmt_count_paren_bare` | `fmt_count_paren_bare` | ✅ | |
| `fmt_right_align` | `fmt_right_align` | ✅ | |
| `format_count_pct` | `format_count_pct` | ✅ | |
| `realign_count_pct` | `realign_count_pct` | ✅ | |

### Blank-row spec constructors

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `blank_rows_by_change` | `blank_rows_by_change` | ✅ | |
| `blank_rows_by_rule` | `blank_rows_by_rule` | ✅ | |

### Borders

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `rtf_border_side` | `rtf_border_side` | ✅ | |
| `rtf_border` | `rtf_border` | ✅ | |
| `rtf_border_none` | `rtf_border_none` | ✅ | |
| `rtf_border_top` | `rtf_border_top` | ✅ | |
| `rtf_border_bottom` | `rtf_border_bottom` | ✅ | |
| `rtf_border_box` | `rtf_border_box` | ✅ | |
| `rtf_table_border` | `rtf_table_border` | ✅ | |
| `rtf_border_tfl` | `rtf_border_tfl` | ✅ | |
| `rtf_border_with` | `rtf_border_with` | ✅ | |

### Shared style

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `rtf_table_style` | `rtf_table_style` | ✅ | |
| `rtf_table_style_with` | `rtf_table_style_with` | ✅ | |
| `rtf_table_style_tfl` | `rtf_table_style_tfl` | ✅ | |

### Report generation / assembly

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `assemble_rtf` | `assemble_rtf` | ✅ | cover + clickable TOC + bookmarks |
| `assemble_files` | `assemble_files` | ✅ | natural sort |
| `assemble_toc` | `assemble_toc` | ✅ | |
| `assemble_spec` | `assemble_spec` | ✅ | |
| `assemble_from_spec` | `assemble_from_spec` | ✅ | + CSV round-trip |
| `assemble_folder` | `assemble_folder` | ✅ | |
| `toc_heading` | `toc_heading` | ✅ | |
| `toc_entry` | `toc_entry` | ✅ | |

### Column-width / post-processing utilities

| R export | Python | Status | Notes |
|----------|--------|:------:|-------|
| `text_width_in` | `text_width_in` | ✅ | Courier exact, Arial approx |
| `auto_col_widths` | `auto_col_widths` | ✅ | protect-cols scaling |
| `rtf_replace_text` | `rtf_replace_text` | ✅ | in-place (with `.bak`) or new file |

### S3 methods (R idiom) — Python equivalents

| R S3 method | Python | Status | Notes |
|-------------|--------|:------:|-------|
| `print.*` (document/page/table/border/style) | dataclass `__repr__` | 🟡 | Structural repr, not R's formatted pretty-printer |
| `format.rtftable` | `to_rtf` / `save` | ✅ | RTF string / write to file |
| `summary.rtftable` | — | ❌ | No summary method ported |
| `plot.*` (border/table/document visual preview) | — | ❌ | Visual preview not ported (out of scope; no plotting dependency) |

---

## 3. Deliberate divergences from R

These are intentional, documented design choices — not gaps:

1. **0-based indices everywhere.** Every index-taking argument (columns, header
   rows, blank-row positions, `col_cell` refs) is 0-based, the Pythonic choice,
   versus R's 1-based. Names are accepted anywhere an index is.
2. **`blank_rows` sentinels are named constants, not magic integers.** R uses
   `0` (before the first row) and `-1` (after the last row). Python replaces
   these with the importable, distinct sentinels **`BEFORE_FIRST`** and
   **`AFTER_LAST`**. A bare integer `k` means "after data row `k`", and a bare
   negative integer raises a clear error pointing at `AFTER_LAST`, so a stray
   `-1` cannot be silently misread.
3. **Python class names with no R counterpart.** The model is exposed as real
   classes: `RtfDocument`, `RtfTable`, `ColSpec`, `SpanCell`, `HeaderRow`,
   `Border`, `BorderSide`, `TableBorder`, `TableStyle`, `HeaderFooter`, `Page`,
   `DefaultFormat`, `Figure`, `Frame`, `BlankRowsByChange`, `BlankRowsByRule`,
   `PaginationError`. R has no equivalent exported symbols (it uses S3 tags).
4. **Fluent `RtfDocument` methods alongside the R-named functions.** The
   module-level functions mirror the R API (`rtf_document(...)`,
   `rtf_tables(doc, ...)`, `generate_rtfreport(...)`); the same operations are
   also available as chainable methods (`.add_table()`, `.add_section()`,
   `.titles()`, `.footnotes()`, `.to_rtf()`, `.save()`). Both are supported;
   `to_rtf` / `save` are Python-only conveniences with no R export.
5. **`stub_cols=` → `stub_vars=`.** In `as_rtftable()`/`as_rtftables()` the
   stub-hierarchy argument is `stub_vars=` (matching R, where `stub_cols()` is a
   separate function), avoiding the name clash.
6. **Default column alignment follows R's `row_title` rule** (first column left,
   the rest centred, header following body alignment).

---

## 4. Test parity vs R

| Metric | R (`rtfreporter`) | Python port | Ratio |
|--------|-------------------|-------------|-------|
| Test files | 71 | 41 | — |
| Test LOC | 10,811 | 5,959 | ~0.55× |
| `test_that` blocks / `def test_` | 893 | 795 | ~0.89× |

The suite grew from **599 → 795 tests** in this phase, organised into per-area
files that assert on RTF structure/tokens and model state (never brittle
whole-file string equality). Because much of the R–Python LOC gap is unported
adapter breadth (below), tests-per-implemented-feature is close to parity.

### R test areas covered by the Python suite

Construction/validation, col-header + `set_col_header` + `set_header_cell` +
`col_header_from_names` + header-source, header borders/alignment,
spanning-align, border colours, cell format/colour/padding, blank rows
(+ normalize + `set_blank_rows`), pagination (+ factories + custom split +
`paginate` names/blanks), group-by / drop-cols / sort-by / collapse-repeats /
stub-cols, style verbs + styles + table-style, title/footnote, document
rendering + style defaults, rtf-page + orientation + text-width, default row
height + defaults (options), markup + escaping + page tokens, rtfplot,
great_tables adapter, borders/render helpers, `assemble_*` (+ spec CSV),
`combine_sections`, `rtf_replace_text`, `rtf_header_source`.

### R test areas that remain UNCOVERED in Python (feature absent → no tests)

- **`flextable-adapter`, `huxtable-adapter`, `rtables-adapter`,
  `gtsummary-adapter`, `gtsummary-split`** — those source adapters are not
  implemented (Python reads `great_tables` only among table objects). This is
  the single biggest gap vs R.
- **`gt-group`, `gt-styles`, `df-label-attrs`, `adapter-option-robustness`,
  `as-rtftables-internals`** — deeper GT-metadata / attribute edge cases beyond
  the ported adapter's scope are only partially mirrored.
- **`blank-rows-group-by` (`indent`/`filled`), `group-by`** — non-`"auto"`
  grouping paths raise `NotImplementedError`; only the change-detection path is
  tested.
- **`count-blank-rows`, `coverage-fillins`** — R-internal helpers with no direct
  Python analogue.
- **`plot`, `print-methods`** — R's visual `plot.*` previews are not ported, and
  `print.*` is a structural dataclass repr rather than R's formatted output, so
  the R formatting expectations are not mirrored 1:1.

---

## 5. PyPI readiness checklist

**Done**

- [x] `src/` layout, hatchling build backend.
- [x] `python -m build` produces both sdist and wheel.
- [x] `twine check dist/*` passes for both artifacts.
- [x] sdist contains the package source (and tests/docs/metadata).
- [x] Wheel installs into a clean virtualenv and imports
      (`import rtfreporter; rtfreporter.__version__` → `0.2.0`).
- [x] PEP 561 `py.typed` marker shipped in the wheel (force-included).
- [x] Complete metadata: `keywords`, classifiers (Intended Audience, Topic,
      Development Status = Beta, `Typing :: Typed`), and `project.urls`
      (Homepage, Documentation, Repository, Issues, Changelog).
- [x] `LICENSE` (Apache-2.0), `README.md`, `CHANGELOG.md` present.
- [x] Version bumped to **0.2.0** in `pyproject.toml` and `__init__.py`.
- [x] CI builds + `twine check`s the distributions on every push/PR (no publish
      step, no tokens — publishing is the user's decision).
- [x] `dist/` git-ignored; no build artifacts committed.

**Remaining before a first upload (user decisions)**

- [ ] Confirm the PyPI project **name** `rtfreporter` is available / desired
      (it may collide; a `-py` or namespaced name may be needed).
- [ ] Verify the `project.urls` point at the real repository/docs locations
      (currently `github.com/ichirio/rtfreporter-py`).
- [ ] Decide the publishing mechanism: a **Trusted Publisher** (OIDC) release
      job vs an API-token upload; add that workflow when ready.
- [ ] Tag `v0.2.0` and cut a GitHub release.
- [ ] Optional: a `TestPyPI` dry-run upload before the real one.

---

## 6. Open questions for the user

1. **Adapter breadth.** Should the flextable / huxtable / rtables / gtsummary
   adapters be ported, or is pandas / polars / great_tables the intended Python
   surface? This drives the largest remaining test-parity gap.
2. **Advanced pagination paths.** Port `group_by` modes other than `"auto"`
   (and `set_blank_rows(group_by="indent"/"filled")`), or leave them as
   explicit `NotImplementedError`s?
3. **`rtf_config(font_table=...)`.** Is a configurable multi-font table needed,
   or is the single built-in font table sufficient for clinical TFLs?
4. **`plot.*` previews / `summary.rtftable`.** Are the R visual-preview and
   summary methods wanted in Python (would add a plotting dependency), or is
   rendering-to-RTF the only intended output?
5. **Publishing.** Confirm the PyPI name, repo URLs, and preferred release
   mechanism (Trusted Publisher vs token) so a publish job can be added.
6. **`Development Status`.** Is **Beta** the right signal for 0.2.0, or should it
   stay Alpha until adapter breadth lands?
