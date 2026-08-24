# Articles

Practical guides for producing clinical RTF deliverables. Start with
[Get started](getting-started.md), then work through the guides below in
roughly this order.

## For package users

<div class="grid cards" markdown>

- :material-file-document-edit: **[Document API guide](document-api.md)**

    The two equivalent ways to build a document — the R-style functional calls
    and the fluent method chain — and when each reads better.

- :material-page-layout-body: **[Page and document setup](page-setup.md)**

    Paper size, orientation, margins, the header/footer band, fonts, and the
    `rtfreporter.*` option defaults.

- :material-table-plus: **[Adding tables and figures](adding-content.md)**

    Putting content on pages: `rtf_tables()`, `rtf_figures()`, per-page titles
    and footnotes, one content item per page.

- :material-border-all: **[Borders and rules](borders.md)**

    The TFL border convention, the five zones, and per-column and per-cell
    overrides.

- :material-import: **[Importing tables](importing-tables.md)**

    `as_rtftable()` / `as_rtftables()` for pandas, polars and `great_tables`,
    and exactly what metadata is carried across.

- :material-file-multiple: **[Paginating](pagination.md)**

    Split strategies, group-aware breaks, `(Cont.)` continuation markers and
    widow/orphan control.

- :material-page-layout-header-footer: **[Headers and footers](headers-footers.md)**

    Sections, running headers and footers, and the automatic page-number
    fields.

- :material-content-cut: **[Splitting a report into sections](section-splitting.md)**

    One section per group or per table, and `combine_sections()`.

- :material-format-paint: **[Post-hoc styling](styling.md)**

    Restyling a finished table with `style_header()`, `style_body()`,
    `style_cols()` and `style_zone()`.

- :material-image: **[Figures](figures.md)**

    Embedding PNG and JPEG at native DPI.

- :material-printer: **[Rendering and post-processing](output.md)**

    `generate_rtfreport()`, what the bytes look like, and last-mile edits with
    `rtf_replace_text()`.

- :material-book-open-page-variant: **[Assembling deliverables](assembling.md)**

    Combining several RTF files into one document with a table of contents.

</div>

## Worked clinical examples

End-to-end recipes whose figures are checked against the R implementation.

<div class="grid cards" markdown>

- :material-account-group: **[Demographics (Table 14.1.1)](showcase-dm.md)**

    A production-style demographics table from real ADaM data, built both from
    a pandas DataFrame and from a `great_tables` object.

- :material-alert-circle: **[Adverse events by SOC/PT](showcase-ae.md)**

    Subjects with treatment-emergent adverse events by system organ class and
    preferred term: independent SOC counts, a 3% filter, and multi-page output
    with `(Cont.)`.

</div>

## Relationship to the R package

<div class="grid cards" markdown>

- :fontawesome-brands-r-project: **[Relationship to R](relationship-to-r.md)**

    How this port is developed — features land in R first — where to ask
    questions, and where the two packages necessarily differ.

- :material-compare: **[Differences from the R package](r-differences.md)**

    The two deliberate divergences: 0-based indices and the `blank_rows`
    sentinels.

</div>
