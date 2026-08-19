# Changelog

All notable changes to this project are documented here.  The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
