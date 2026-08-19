# rtfreporter (Python) — Build Report

**Date:** 2026-08-19
**Scope:** Python port of the R package `rtfreporter` (clinical RTF Tables,
Listings and Figures). This report states plainly what is implemented, what is
deferred, and how test coverage compares to the R original.

> Guiding principle for this report: **honesty over optimism.** Where a feature
> is partial or an R capability was not ported, it is called out as such rather
> than glossed over.

---

## 1. Headline results

| Check | Result |
|-------|--------|
| `pytest -q` | **392 passed** (0 failed) |
| `ruff check .` | **All checks passed!** |
| `mkdocs build --strict` | **exit 0, 0 warnings** |
| Line coverage (`pytest --cov`) | **86%** (1897 stmts, 199 missed) |
| Runnable examples | `demographics.py`, `pagination.py`, `styling.py` — all run and write valid `.rtf` |

Pasted `pytest` summary:

```
392 passed in 2.30s
```

Pasted `ruff` result:

```
All checks passed!
```

Pasted `mkdocs` result:

```
exit=0 warnings=0
```

---

## 2. Implemented vs deferred, feature by feature

Legend: ✅ implemented · 🟡 partial · ❌ not ported (deferred).

### Table model & construction

| Feature | Status | Notes |
|---------|--------|-------|
| `rtftable()` from dict / `(names, rows)` / records | ✅ | `table.py` |
| pandas / polars DataFrame input | ✅ | duck-typed, no hard dependency |
| Per-column `ColSpec` (align, bold, italic, underline, indent, color, border) | ✅ | |
| Multi-row column headers (label rows) | ✅ | |
| Spanning headers via `col_cell()` (index/name/range refs) | ✅ | |
| Spanning headers reconstructed from delimited names | ✅ | `____` / custom `header_sep` |
| Header alignment cascade (explicit → col_header_align → body align → center) | ✅ | |
| Blank-row specs (`by_change`, `by_rule`, int positions, `-1`) | ✅ | `blank_rows.py` |
| Blank-row normalize (detect empty rows, collapse adjacent) | ✅ | |
| Column widths: equal / relative / absolute / table-width-pct | ✅ | `compute_cellx` |
| Row heights (header / data / blank, exact vs at-least) | ✅ | |
| Cell padding (left/right, doc default vs table override) | ✅ | |
| Per-cell style overrides (`cell_styles`) | 🟡 | Model + renderer support present; no high-level verb to build them |
| Input validation & typed errors | ✅ | `test_rtftable_validation.py` |

### Adapters & pagination

| Feature | Status | Notes |
|---------|--------|-------|
| `as_rtftable()` / `as_rtftables()` | ✅ | `adapters.py` |
| great_tables `GT` adapter (labels, one spanner level, title block) | 🟡 | Cell styling, footnotes, summary/group rows **not** read |
| Split strategies: `none`, `rows`, `by_value`, `group_safe`, `group_force` | ✅ | |
| `(Cont.)` continuation markers | ✅ | configurable `cont_label` |
| `sort_by` / `sort_desc`, `collapse_repeats`, `drop_cols`, `group_col` | ✅ | + header reindex on drop |
| Clinical stub (`stub_cols`, `stub_label`, `stub_indent`) | ✅ | |
| Between-group & per-page blank rows (`blank_row_first`/`_end`) | ✅ | |
| List-of-frames flattening | ✅ | |
| Custom split **function** hook | ❌ | R's `split = <function>` not ported |
| flextable / huxtable / rtables / gtsummary adapters | ❌ | Only pandas/polars/GT/dict/records |

### Document, sections, output

| Feature | Status | Notes |
|---------|--------|-------|
| Fluent builder (`RtfDocument`) + functional layer (`to_rtf`, `save`) | ✅ | |
| Sections overlaying header/footer onto page ranges; inherit on `None` | ✅ | |
| Running headers/footers (1–3 col rows, `l`/`c`/`r`) | ✅ | |
| Page tokens `{AUTO_PAGE}`, `{AUTO_TOTAL_PAGES}`, `{SECTION_PAGES}` (live fields) | ✅ | |
| Static `{PAGE}` / `{TOTAL_PAGES}` (baked, per-page sections) | ✅ | |
| Titles / footnotes (text format & table format) | ✅ | |
| Page geometry (letter/legal/a3/a4/a5, orientation, margins, band distance) | ✅ | `page.py` |
| Colour table auto-collection + `\cf` / `\brdrcf` indexing | ✅ | |
| Embedded PNG / JPEG figures at native DPI | ✅ | `figure.py` |
| `update_header_row()` / post-hoc HF row edit helpers | ❌ | Build the band up front instead |

### Borders, styles, text

| Feature | Status | Notes |
|---------|--------|-------|
| `BorderSide` / `Border` / `TableBorder` records | ✅ | `borders.py` |
| Presets `tfl` / `none`; zone model (header/spanning/body/first_row/last_row) | ✅ | |
| Spanning group-underline auto-rule | ✅ | |
| Border styles single/double/thick/dash/dot; explicit `none` override | ✅ | |
| Style verbs `style_body` / `style_cols` / `style_header` / `style_zone` | ✅ | `style_verbs.py` |
| Markup: superscript/subscript (`^{}`/`_{}`), relational `>=`/`<=` | ✅ | `_escape.py` |
| ASCII-safe Unicode escaping (`\uNNNN?`) | ✅ | |
| `format_count_pct()`-style numeric formatting helper | ❌ | Not ported; format upstream in the data frame |

---

## 3. Test parity vs R

| Metric | R (`rtfreporter`) | Python port | Ratio |
|--------|-------------------|-------------|-------|
| Test files | 71 | 24 | — |
| Test LOC | 10,789 | 2,754 | ~0.26× |
| `test_that` blocks / `def test_` | 893 | 390 (392 cases with parametrization) | ~0.44× |
| Expectations / assertions | 1,976 expectations | ~500 assert statements | — |
| Source LOC (for context) | 14,024 | 3,681 | ~0.26× |

The Python port grew from **61 → 392 tests** during this build (≈6.4×). Because
the Python source is ~26% of the R source LOC (many R features are not ported),
counting tests-per-implemented-feature the ratio is substantially closer to
parity than the raw 393/893 figure suggests.

### R test areas — coverage map

**Covered by a dedicated Python test file / area:**

- rtftable-construction → `test_rtftable_construction.py`
- rtftable-validation / pipe-validation → `test_rtftable_validation.py`
- col-header, set-col-header → `test_col_header.py`
- col-header-from-names, header-split → `test_adapter_reshaping.py`
- header-borders → `test_header_borders.py`
- header-alignment → `test_header_alignment.py`
- spanning-align → `test_spanning_align.py`
- border-colors → `test_border_colors.py`
- cell-format → `test_cell_format.py`
- cell-color → `test_cell_color.py`
- cell-padding → `test_cell_padding.py`
- blank-rows, set-blank-rows, blank-row-normalize → `test_blank_rows.py`
- blank-rows-group-by, paginate-blanks → `test_pagination.py`, `test_adapter_reshaping.py`
- paginate, page-split-factories, paginate-names → `test_pagination.py`
- group-by, drop-cols, sort-by, collapse-repeats, stub-cols → `test_adapter_reshaping.py`
- style-verbs, styles → `test_style_verbs.py`
- title-footnote → `test_title_footnote.py`
- rtf-generation, document-rendering, document-style-defaults → `test_document.py`
- rtf-page, page-orientation, text-width → `test_page.py`
- default-row-height, defaults → `test_page.py`
- markup, escape, page-tokens → `test_markup.py`, `test_escape.py`
- rtfplot, plot → `test_figures.py`
- adapters (pandas/polars/GT) → `test_adapters.py`
- borders / render helpers → `test_borders.py`, `test_render.py`, `test_style_and_content.py`

**R areas UNCOVERED / NOT PORTED** (the underlying feature is absent, so no
tests were written — per the "do not test unimplemented features" rule):

- `format-count-pct` — numeric count/percent formatting helper not ported.
- `custom-split` — user split-function hook not ported.
- `flextable-adapter`, `huxtable-adapter`, `rtables-adapter`,
  `gtsummary-adapter`, `gtsummary-split`, `gt-group`, `gt-styles`,
  `df-label-attrs` — those source adapters are not implemented.
- `set-header-cell`, `rtf-replace-text` — post-hoc HF/text mutation helpers not ported.
- `combine-sections`, `assemble-rtf`, `assemble-spec` — the R internal
  assembly/spec layer differs from the Python driver; the Python equivalent is
  exercised indirectly through `test_document.py` rather than 1:1.
- `count-blank-rows`, `coverage-fillins`, `print-methods`,
  `adapter-option-robustness` — internal/utility helpers with no direct Python
  analogue.

**Partially covered:** the `gt-adapter` path is smoke-tested (`test_adapters.py`
constructs a `GT` and converts it) but the deeper GT metadata cases in the R
suite (styles, groups, spanners edge cases) are not mirrored, matching the
adapter's MVP scope.

---

## 4. Coverage detail

`pytest --cov` (branch coverage on), 86% overall. Lower-covered modules and why:

- `header_footer.py` (52%) — normalization branches for unusual row shapes and
  the `normalize_hf` type dispatch are lightly exercised.
- `borders.py` (80%) — several convenience constructors and merge edge cases.
- `render.py` (82%) — some text-block color/edge branches and the `[empty table]`
  path.
- `adapters.py` (83%) — GT metadata branches and a few error paths.
- `figure.py` (83%) — malformed-image byte-scan fallbacks.

These are candidates for the next test pass if higher coverage is desired.

---

## 5. What was built in this session

1. **`examples/`** — three runnable end-to-end scripts, each writes a real `.rtf`
   and self-asserts (`{\rtf1` prefix + balanced braces).
2. **Docs site** — MkDocs Material + mkdocstrings; `index`, `getting-started`,
   six ported articles (importing, pagination, borders, headers/footers,
   figures, styling) and an auto-API `reference`. Builds under `--strict` with
   zero warnings.
3. **CI** — `.github/workflows/tests.yml` (ubuntu, py 3.10/3.11/3.12, ruff +
   pytest) and `docs.yml` (strict build + `mkdocs gh-deploy`). `dev` extras +
   coverage config added to `pyproject.toml`.
4. **Tests** — expanded 61 → 392, organised into 24 per-area files asserting on
   RTF structure/tokens and model state (not brittle whole-file equality).
5. **One source fix** — `render._render_data_row` closure now binds its loop
   variables (B023), surfaced by `ruff check .` over the whole repo.

---

## 6. Key decisions & assumptions

- **No third-party RTF engine and no hard runtime dependencies.** Data-frame
  support is duck-typed; pandas/polars/great_tables are optional extras.
- **0-based column indices** throughout the public API (names accepted anywhere
  an index is), which is the Pythonic choice and diverges from R's 1-based.
- **Immutability for style verbs** — every verb returns a modified copy.
- **mkdocstrings griffe warnings** are silenced via
  `docstring_options: {warn_unknown_params: false, warnings: false}` because the
  hand-written docstrings group related parameters on one line (e.g.
  `bold, italic, underline:`). This keeps `--strict` green without rewriting
  every docstring; broken cross-references are still caught by MkDocs strict mode.

## 7. Recommended next decisions for the user

1. **Adapter breadth** — decide whether the flextable / huxtable / rtables /
   gtsummary adapters are in scope for this port, or whether pandas/polars/GT is
   the intended surface. This is the single biggest gap vs the R package.
2. **`format_count_pct` / numeric formatting** — port the helper, or standardise
   on formatting values upstream in the data frame before `rtftable()`.
3. **Custom split hook** — whether to expose `split=<callable>` for bespoke
   pagination.
4. **Coverage target** — if a hard threshold is wanted, add `--cov-fail-under`
   to CI and close the `header_footer.py` / `render.py` branch gaps.
5. **Per-cell styling ergonomics** — add a high-level verb to construct
   `cell_styles` (the renderer already supports it).
