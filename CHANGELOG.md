# Changelog

All notable changes to this project are documented here.  The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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
