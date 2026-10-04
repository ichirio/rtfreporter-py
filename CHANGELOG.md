# Changelog

All notable changes to this project are documented here.  The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Documentation

- **Citation and credits** (#8).  A `CITATION.cff` (GitHub's "Cite this
  repository"), and README sections on how to cite the package and what it
  builds on: the R rtfreporter it is ported from, pandas / polars /
  great_tables / matplotlib, and pharmaverseadam for the example data, whose
  copyright holders `examples/data/README.md` now names.

### Verified

- **R ichirio/rtfreporter#505/#506 ("a listing key prints once per record
  when a key to its left wraps") does not reproduce in the port.**  R's
  pre-fix bug was in `.collapse_repeats_chunk()`'s hierarchical key: a key
  column's repeat test was combined with the columns to its left, so a left
  key that wraps across lines ("Xanomeline" / "High Dose") changed that
  combined key from line to line and made the key to its right (e.g.
  `SUBJ`) reprint on the wrapped continuation line instead of staying
  blank.  The port's `_collapse_repeats()` (`src/rtfreporter/adapters.py`)
  blanks each `collapse_repeats` column against only its own previous
  value, independent of other columns, so it was never susceptible.
  Checked by rendering the trigger scenario (`TRT` wrapping over `SUBJ`,
  both `collapse_repeats` keys) with R pre-fix (c1dae2e), R `main` (post-fix,
  0.8.2.9001), and this port: the port's output is byte-identical to R
  `main` and differs from R pre-fix.  Pinned with
  `test_listing_key_wrap_matches_r` (`tests/test_listing_vs_r.py`) and its
  golden `tests/xcheck_golden/listing/wrap_key.rtf`, rendered by R `main`.

## [0.4.1] — 2026-10-01

### Fixed

- **A row split by `set_decimal_split()` lost the table's font size and the
  cell fill** (#5; the R package's ichirio/rtfreporter#509, fixed there in
  0.8.2.9003).  The split data rows were written without the table's own font
  switch (`rtftable(font_size_half_points=, font=)`), so their numbers fell
  back to the document's size and font, and without the `background` of their
  column or of `cell_styles`, so a shaded column had unshaded rows wherever a
  number was split.  0.4.0 reproduced this on purpose, for byte parity with R
  v0.8.2; it now matches R's fix (the two affected differential golden files
  are rendered by R `main` at the fix -- see `data-raw/xcheck/README.md`).
  Tables without `set_decimal_split()` are byte-identical.

## [0.4.0] — 2026-10-01

### Following R v0.8.2 (#3)

The port now matches the R package's **v0.8.2** release, outside the ARD /
table-plan engine (`normalize_ard()`, `widen_ard()`, `table_plan()`,
`plan_*()`), which stays out of scope for now.  Every change was checked
against R v0.8.2 byte for byte: the `data-raw/xcheck/` harness grew from 24
to 68 cases, plus differential scripts for the formatters, assembly, headers,
styles, figures, decimal alignment, column pagination, listings, great_tables
input and the four recipes.  Every R v0.8.2 export outside ARD / plan now
exists in Python except `rtfreporter_ai_manual()`.

#### Breaking changes

- **`page_split_*()` retired** (R #334): the split strategies are
  `as_rtftables(split=)` / `paginate(split=)` only.
- **The footer is drawn by the footnote band** (R #296); output of documents
  with footers changes accordingly (as R's did).
- **The border constructors of the old model** (`rtf_border_with()`,
  `rtf_table_border()`, `rtf_border_tfl()`) are deprecated and warn once per
  session (R #340-#348); build borders with `rtf_border()` / `style_zone()`.
- **`rounding="r"` rounds as R >= 4.0's `round()`** (it used Python's
  `round()`, which differs on values such as 23.445 and 0.05).
- **`rtfplot()`'s first argument is `x`** (was `path`), a file path or a plot
  object, as R.
- **Argument names follow R:** `col_cell(pos=)` (was `cols=`),
  `generate_rtfreport(report=)` (was `doc=`), `add_cont_label(chunk=)`,
  `set_blank_rows(df=)`, `paginate(x=)`, `style_body / style_cols /
  style_header / style_zone(x=)` (were `tbl=`).  Positional calls are
  unaffected.
- **`rtf_header_source()`** now writes name-based statements
  (`tbl = set_col_header(tbl, rtf_col_header(...), align=[...])`,
  `tbl = style_zone(tbl, ...)`); its arguments are R's
  `(x, level, snippet, add_span_level, stub)`.
- **Positional arguments with `drop_cols`** (`col_rel_width`,
  `column_widths_twips`, `col_spec`, `row_title`, `cell_styles`) address the
  columns **before** the drop and lose the dropped ones, as R.

#### Added

- **Pagination:** `count_blank_rows` (R #362 / #330), group splits cut as R
  cuts them, one-group page break (#408), page-edge separators (#332), gather
  by value (#485), page names as headings and `auto_section` on a name change
  (#433), `as_rtftables(page_by=, na=)`, `paginate_cols()` (column-wise
  pagination with `at` / `cols` / `by`, `carry`, `col_header`,
  `allow_span_break`, `width`, `page_order`).
- **Formatting:** `fmt_signif()`, `fmt_round()`, `fmt_numeric()`,
  `fmt_value_paren()`, `catx()`, `round_num()`, named cell formats, `na=` on
  the formatters (#476 / #350); `set_decimal_split()` (R #304).
- **Run tokens** `{PROGRAM}`, `{PROGRAM_NAME}`, `{PROGRAM_DIR}`,
  `{DATETIME[:fmt]}` with `program=`; the `{BOOK_PAGE}` slot and
  `assemble_rtf(book_page=)`; `{SECTION_PAGES}` error (#410); assembled page
  counts (#401 / #415).
- **`rtf_watermark()`** and `watermark=` on `rtf_document()` / `rtf_config()` /
  `rtf_section()`.
- **Fonts:** per-element fonts (`rtftable(font=, font_size_half_points=)`,
  `font=` on titles / footnotes / header / footer) and a variable-length font
  table (`rtf_document(font_table=)` / `rtf_config(font_table=)`, which raised
  `NotImplementedError` before).
- **Column headers:** `col_key()`, `col_cell(<selector>)`,
  `set_col_header(values=, by=)`, `header_map()`, named label rows (#453), the
  label-row width check (#435); `rtf_header_source(level=, add_span_level=,
  stub=)`.
- **Styling:** cell fill (`background` / `header_background`, `cell_styles`
  background); `style_body(rows=)` per cell; `style_header(row=, cols=,
  label=, border=, underline=)`; block styles for titles and footnotes
  (#291 / #292 / #398); `rtf_tables()` overrides of a pre-built table's
  formatting, `auto_title=` / `title_label_align=`.
- **Stub:** `stub_spec()` and `as_rtftables(stub=)` (the flat `stub_vars`
  family is superseded, R #314); `stub_cols(layout="columns",
  label_span=True)`.
- **Listings:** `listing_col()`, `listing_spec()`, `build_listing()`,
  `as_rtftables(listing=)`, `fit_listing_widths()`, `listing_code()`,
  `listing_wrap()`, `listing_wrap_code()`, `listing_disp_width()`,
  `listing_take()`, `listing_split_after()`.
- **Figures:** `rtfplot()` / `rtf_figures()` draw a plot object (a matplotlib
  figure, a plotnine plot, or a drawing function) at `render_width` x
  `render_height` inches and `render_dpi` (R #394);
  `rtf_figures(width_twips=, height_twips=, align=)`.  New extra
  `rtfreporter[plot]` (matplotlib).
- **great_tables input** takes `stub=` and `drop_cols=`: the table's labels,
  alignment and cell styles follow their columns, as R's gt input does.
- **Docs:** Listings, Figures and "Four recipes: DM, AE, PK, LB" articles;
  the reference index follows R's.

#### Fixed

- `as_rtftables(cell_styles=)` of your own follows its rows across pages
  (R #498); `by_value` + a stub splits on the pre-stub `group_col` and each
  group's page keeps the source's metadata.
- great_tables input with `drop_cols` / `stub` raised "Column index out of
  range"; the gt column names are kept verbatim (R #458).
- The `figure.default_dpi` option was ignored (a constant 96 was used).
- A `col_spec` of your own and a great_tables table's now merge per column
  (yours wins), as R.

### Added

- **Differential cross-check against the R package.** `data-raw/xcheck/cases.json`
  defines cases rendered by **both** implementations; `tests/test_xcheck_vs_r.py`
  requires the two RTF files to be **byte-identical** (line endings aside).
  R's output is committed under `tests/xcheck_golden/`, so CI enforces R parity
  without R installed. 24 cases cover geometry, borders, titles/footnotes,
  header/footer bands, every split strategy, blank rows, stubs, sorting,
  dropped columns, count/percent alignment, auto width, spanning headers and
  markup. See `data-raw/xcheck/README.md`.

- **`rtf_tables(auto_section=)` / `section_label_align=`** — ports R's automatic
  sectioning. A **named** page opens its own RTF section whose header is the
  running header plus a heading row carrying the name; unnamed pages fall
  through, so a multi-page table stays one section. This gives
  `combine_sections()` its consumer: it records the grouping, and
  `auto_section=True` acts on it. `split="by_value"` names pages too, so the
  same call yields one section per group. Verified against R: identical header
  bands and exactly two `\sectd` for the two-table case.
- **`group_by` across the pagination surface.** `page_split_by_value`,
  `page_split_group_safe`, `page_split_group_force` and `set_blank_rows()`
  accepted only `"auto"` and raised `NotImplementedError` otherwise; all four R
  modes (`auto` / `value` / `indent` / `filled`) now work everywhere, sharing
  one detection implementation.
- **`as_rtftables(auto_width=True)`** — sizes each column to its widest content
  via `auto_col_widths()`, computed once on the whole table so paginated pages
  stay aligned. Matches R exactly, including the two details that are easy to
  miss: the first column is protected at its natural width (R's
  `protect_cols = 1L`), and with no `table_width_twips` the total is capped at
  the default writable page width.

- **The R package's hex logo**, reused as the site logo, favicon and README
  mark. The design is identical (hexagon, navy frame, miniature clinical-TFL
  page, `rtfreporter` wordmark, `ichirio` family attribution); only the
  per-package tagline changes, from `CLINICAL · TFL · RTF` to
  `PYTHON · CLINICAL · TFL`, so the two sites read as one project while
  staying distinguishable in a browser tab.
- **Documentation site brought in line with the R package**: navy/Source Sans 3
  styling matching the pkgdown site, an Articles index, and five new user
  guides — Document API, Page and document setup, Adding tables and figures,
  Splitting a report into sections, and Rendering and post-processing.
- `docs/relationship-to-r.md` — states the **R-first development policy** (new
  features are designed and built in the R package, then ported here) and
  directs questions to the **shared Discussions forum on the R repository**.
- The API reference is regrouped into 16 described sections mirroring the R
  reference index, generated by `data-raw/gen_reference.py`, which fails if any
  public symbol is left unlisted.

### Fixed

- **Three divergences the cross-check caught immediately**, all confirmed
  against R before changing anything:
    - **The clinical stub was indented with plain spaces**, where R uses
      non-breaking spaces (U+00A0). A plain space is a wrap opportunity and can
      be collapsed by the viewer, so the indent did not reliably survive into
      Word.
    - **`split_rows` was treated as a page size**; in R it is a list of explicit
      **cut positions**. On 10 rows `split_rows=4` now yields pages of 4 and 6,
      as R does, not 4/4/2. Use `max_rows` for a fixed page size. Positions are
      0-based here, so R's `3` is Python's `2`.
    - **Setting `group_col` inserted separator rows by itself.** R adds none
      unless `blank_rows` asks; `blank_rows="between_groups"` is now required to
      get them.
- `page_split_rows()` accepts `max_rows`, matching what `as_rtftables(split="rows")`
  already allowed.
- **`blank_rows="between_groups"` blanked between every row of an indented
  stub.** It compared cell values instead of using the call's `group_by`, and
  a stub built by `stub_vars` has a different value on every line, so every row
  looked like a group transition. R's documented behaviour is to use "this
  call's `group_by` detection", whose `"auto"` default sees the indentation.
  Verified against R: the demographics body now blanks only at the group heads
  (`[5, 9]` for the reference frame), not after all 16 rows.
- **Three examples and docs snippets called document builders for effect**
  (`doc.add_table(...)` in a loop) and silently produced an empty document,
  since builders became copy-on-modify. They rebind now.
- **Three argument defaults did not match R**, found by diffing every R export's
  formals against the Python signatures:
    - `rtf_footer(border=)` defaulted to `None`; R defaults to
      `rtf_border_top()`, so a footer band now carries its top rule again
      (`\clbrdrtrdrsrdrw15`). `rtf_header` correctly stays borderless.
    - `blank_rows_by_change()` defaulted `include_before_first` /
      `include_after_last` to `False`; R defaults both to `True`. Checked in R:
      `A,A,B,B` yields `[0, 2, 4]`, and an unchanging column still yields
      `[0, 3]`.
    - `blank_rows_by_change()` was missing R's `group_by` argument; all four
      modes are now accepted and share the adapter's detection code.
  `blank_rows="between_groups"` is unaffected — it blanks transitions only
  (R: `[2]`), which is now pinned explicitly rather than relying on the
  defaults.
- **Document builders mutated their input.** `rtf_tables()`, `rtf_figures()`,
  `rtf_section()`, `rtf_titles()`, `rtf_footnotes()` and the fluent
  `RtfDocument` methods changed the document passed in and returned that same
  object, where R uses copy-on-modify. Reusing a configured base document to
  start two reports silently leaked the first report's pages into the second.
  All builders now return an independent copy, matching R
  (`docA`/`docB` from one base: 1 page each, base unchanged).
- The homepage quickstart imported `header` / `footer`, names that no longer
  exist after the 0.2.0 rename.
- The section-splitting guide implied `combine_sections()` produced sections
  on its own. It records the grouping, but R's `rtf_tables(auto_section=)`
  that consumes it is not ported yet; the page now says so and shows the
  explicit `rtf_section()` equivalent.

## [0.3.0] — 2026-08-23

Adds a clinical **showcase** built from real ADaM data, and fixes two
pagination/grouping gaps that building it exposed.

### Added

- **Bundled ADaM sample data** (`examples/data/adsl.csv`, `adae.csv`) — a
  subset of [pharmaverseadam](https://pharmaverse.github.io/pharmaverseadam/)
  (Apache-2.0, CDISC pilot study), so every example runs with no R and no
  network. Provenance and regeneration: `data-raw/export_pharmaverseadam.R`.
- `examples/adam_data.py` — loader applying the showcase derivations, and
  `examples/adam_synthetic.py` — a seeded synthetic generator with the same
  column contract, for users who would rather not vendor the data.
- `examples/showcase_dm.py` — Table 14.1.1 demographics, built both from a
  pandas DataFrame and from a `great_tables` GT object.
- `examples/showcase_ae.py` — adverse events by SOC and preferred term:
  independent SOC-level counts, a 3% preferred-term filter, indentation-driven
  grouping and multi-page output with `(Cont.)`.
- `docs/showcase-dm.md` and `docs/showcase-ae.md`.
- `tests/test_showcase.py` — asserts the output against
  `data-raw/R_reference_numbers.txt`, i.e. figures produced by the R package.

### Fixed

- **`split="group_force"` never produced a continuation.** It split a group
  only when that group alone exceeded `max_rows`, which is `group_safe`
  behaviour. It now ports R's `.split_group_force()`: cut on every `max_rows`,
  apply widow/orphan control via `min_group_rows`, and repeat the group header
  on the next page with `cont_label`. Verified against R, which returns
  identical pages for the same input.
- **`blank_rows="between_groups"` raised `ValueError`.** The R shorthand is now
  supported, including inside a combining list, and defaults to the first
  column when no `group_col` is given.

### Changed

- **`group_by` is implemented.** It previously raised `NotImplementedError` for
  anything but `"auto"`. All four R modes now work (`auto`, `indent`, `value`,
  `filled`), with R's detection order (indent → filled → value). Default blank
  separator rows are derived from the detected groups rather than raw cell
  values under the header-based modes.

## [0.2.0] — 2026-08-22

This release brings the public API into line with the R package, adds the
count/percent formatters, pagination factories and custom-split hook, the
post-hoc styling/header verbs, the options system, the `assemble_*` family with
a clickable Table of Contents, and PyPI-grade packaging (PEP 561 typing marker,
full metadata, a build + `twine check` CI job). The test suite grew to 795
tests at 94% line coverage, enforced in CI via `--cov-fail-under=90`.

### Breaking changes

- **The public API was renamed to match the R package (a clean break; no
  aliases were kept).**  The un-prefixed constructor names are gone; use the
  `rtf_`-prefixed R spellings instead:
  `border_side → rtf_border_side`, `border → rtf_border`,
  `border_none → rtf_border_none`, `border_top → rtf_border_top`,
  `border_bottom → rtf_border_bottom`, `border_box → rtf_border_box`,
  `border_tfl → rtf_border_tfl`, `header → rtf_header`, `footer → rtf_footer`,
  `document → rtf_document`.  The Python class names (`RtfTable`, `RtfDocument`,
  `ColSpec`, ...) and the fluent `RtfDocument` methods are unchanged.
- **`blank_rows` positions are now 0-based** (position `i` inserts a blank row
  *after* data row `i`) and the two R sentinels are the named, importable
  constants **`BEFORE_FIRST`** (R's `0`) and **`AFTER_LAST`** (R's `-1`).  A
  bare negative integer now raises an error pointing at `AFTER_LAST`.  Previous
  code passing `0` / `-1` must switch to `BEFORE_FIRST` / `AFTER_LAST`, and a
  bare integer `k` now means "after data row `k`" (one row later than before).
- **`as_rtftables()` / `as_rtftable()`: the `stub_cols=` argument was renamed to
  `stub_vars=`** (matching R, where `stub_vars` is the argument and `stub_cols()`
  is a separate function).
- **Default column alignment now follows R's `row_title` rule**: the first
  column (the row-title/stub column) defaults to left-aligned and every other
  column defaults to centre-aligned, with the column header following the body
  alignment.  Previously every column defaulted to left.

### Added

- **R-aligned module-level API (the primary documented surface).**  New
  constructors mirroring the R exports: `rtf_document`, `rtf_tables`,
  `rtf_figures`, `rtf_titles`, `rtf_footnotes`, `rtf_section`,
  `generate_rtfreport` (the R pipe API), plus `rtf_page`, `rtf_col_header`, and
  `rtf_table_border`.
- **New `rtftable()` arguments** matching R: `spanning_header`, `row_title`,
  `read_attributes`, `style`, and `table_width_pct_of_writable`.
- **New `as_rtftables()` arguments** matching R: `group_by`, `align_count_pct`,
  `cell_format`, `auto_width`, `table_width_twips`, `stub_group_summary`,
  `count_blank_rows`, and `style`.  The not-yet-ported paths (`group_by` other
  than `"auto"`, `count_blank_rows=True`, `cell_format`, `auto_width`,
  `stub_group_summary="parent"`) raise a clear `NotImplementedError`.
- **`BEFORE_FIRST` / `AFTER_LAST`** blank-row sentinel constants.
- **Count / percent display-width formatters** (`rtfreporter.format_count_pct`):
  `format_count_pct`, `realign_count_pct`, `fmt_count_paren`,
  `fmt_count_paren_bare`, and `fmt_right_align`, ported from R.  Wired into
  `as_rtftables()` via `align_count_pct=True` (the `"n (xx.x)"` realigner) and
  the general `cell_format=` per-column re-formatter.
- **Pagination factories and a custom-split hook** — `page_split_none`,
  `page_split_rows`, `page_split_group_safe`, `page_split_group_force`,
  `page_split_by_value`, `paginate`, and `add_cont_label` for bespoke
  `split=<callable>` strategies.
- **Post-hoc styling / header verbs** — `style_header`, `style_cols`,
  `style_body`, `style_zone`, `add_header_row`, `set_col_header`,
  `set_header_cell`, `rtf_columns`, `rtf_header_source`, `col_header_from_names`,
  `add_col_header_row`, `collapse_repeats`, and `combine_sections`.
- **Options system** — `rtfreporter_options()` / `rtfreporter_reset_defaults()`
  with the R resolution order (explicit argument → option → factory default).
- **`assemble_*` family** — `assemble_rtf`, `assemble_files`, `assemble_spec`,
  `assemble_from_spec`, `assemble_folder`, `assemble_toc`, `toc_heading`, and
  `toc_entry`: concatenate rendered RTF files into one deliverable with a cover
  page and a clickable, bookmarked Table of Contents.
- **Column-width utilities** (`text_width_in`, `auto_col_widths`), the clinical
  indented stub (`stub_cols`), and `rtf_replace_text` for post-render text
  substitution.
- **PEP 561 typing** — a `py.typed` marker shipped in the wheel, plus complete
  PyPI metadata (keywords, classifiers, and `project.urls`).
- **Full-featured `great_tables` (GT) adapter** (`rtfreporter.gt_adapter`).
  The GT path now reads the rendered/display body (`fmt_*` formatted values,
  hidden columns dropped), **multi-level / nested spanners**, **row groups**
  (rendered as full-width group-label rows with children indented into a
  leading stub), per-column **alignment** and **widths**, **title + subtitle**,
  **footnotes + source notes**, and per-cell **styles** from `tab_style()`
  (bold / italic / underline / align / text colour and cell borders) mapped to
  the model's `cell_styles` and header channels. Border mapping follows the R
  package (solid/double/dashed/dotted/hidden → single/double/dash/dot/none,
  px×15 / pt×20 twips, black omitted); a **transparent / zero-alpha border
  yields no border**. Best-effort grand-summary rows where great_tables exposes
  them.
- **`read_meta` token mechanism for GT** — `True` / `False` / a list of
  `GT_META_TOKENS` (`col_header`, `alignment`, `spanning`, `widths`, `titles`,
  `footnotes`, `styles`) to opt in/out of individual metadata channels; the
  clean reshaped body is always produced.
- `RtfTable.name` is now a real field (used for section naming).

## [0.1.0] — 2026-08-19

Initial release: a Pythonic port of the R package
[`rtfreporter`](https://github.com/ichirio/rtfreporter) covering the core
DataFrame → RTF path.

### Added

- **RTF renderer core** — valid RTF documents from a table model, in twips.
  Landscape US-Letter default geometry with uniform 0.75" margins, a
  header/footer band with automatic page-number fields (`{AUTO_PAGE}`,
  `{AUTO_TOTAL_PAGES}`, `{SECTION_PAGES}`, `{PAGE}`, `{TOTAL_PAGES}`),
  ASCII-safe text (non-ASCII emitted as `\uNNNN?`), and `"none"` borders that
  omit the RTF command.
- **`RtfDocument` builder** — a fluent, chainable API
  (`.add_section()`, `.add_table()`, `.add_figure()`, `.titles()`,
  `.footnotes()`, `.to_rtf()`, `.save()`) plus a module-level functional layer.
- **`RtfTable` table model** — multi-row / spanning column headers
  (`col_cell`), per-column `ColSpec`, per-cell styles, border zones, blank
  separator rows.
- **`as_rtftable` / `as_rtftables`** — pandas (core), polars, and
  `great_tables` (GT) adapters; pagination (by rows, by group, one page per
  value) with `(Cont.)` markers and blank rows between groups; spanning headers
  reconstructed from delimited column names; `sort_by`, `drop_cols`,
  `collapse_repeats`, and an indented clinical `stub_cols`.
- **Borders / zones + style verbs** — `border_side` / `border` / `border_tfl`,
  and `style_header` / `style_body` / `style_cols` / `style_zone`.
- **Titles / footnotes** rendered as width-matched blocks; **PNG/JPEG figures**
  embedded at native DPI (reads PNG `pHYs` / JPEG JFIF density).

### Deferred

See `BUILD_REPORT.md` for the list of R features not yet ported (multi-frame
tables, `assemble_rtf`, gtsummary/rtables/flextable/huxtable adapters, the full
options system).
