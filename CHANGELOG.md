# Changelog

All notable changes to this project are documented here.  The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
