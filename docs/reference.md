# API reference

Every symbol below is importable directly from the top-level `rtfreporter`
package, and follows the R package's name, arguments and defaults.

!!! note "Two deliberate divergences from R"

    **All index-taking arguments are 0-based** (R is 1-based), and the
    `blank_rows` sentinels are the named constants `BEFORE_FIRST` /
    `AFTER_LAST` rather than the magic integers `0` and `-1`.
    See [Differences from the R package](r-differences.md).

## Contents

| Group | Symbols |
|---|---|
| [Document and rendering](#document-and-rendering) | `RtfDocument`, `rtf_document`, `rtf_config`, `rtf_page`, `DefaultFormat`, `rtf_default_format`, `Page`, `generate_rtfreport`, `to_rtf`, `save` |
| [Package defaults](#package-defaults) | `rtfreporter_options`, `rtfreporter_reset_defaults` |
| [Sections: headers and footers](#sections-headers-and-footers) | `rtf_section`, `rtf_header`, `rtf_footer`, `HeaderFooter`, `update_header_row`, `update_footer_row` |
| [Page content: tables and figures](#page-content-tables-and-figures) | `rtf_tables`, `rtf_figures`, `rtf_titles`, `rtf_footnotes`, `rtftable`, `RtfTable`, `ColSpec`, `rtfplot`, `Figure` |
| [Importing tables](#importing-tables) | `as_rtftables`, `as_rtftable`, `combine_sections`, `stub_cols` |
| [Column headers](#column-headers) | `rtf_col_header`, `col_cell`, `SpanCell`, `HeaderRow`, `col_header_from_names`, `add_col_header_row`, `set_col_header`, `set_header_cell`, `rtf_columns`, `rtf_header_source` |
| [Post-hoc styling verbs](#post-hoc-styling-verbs) | `style_header`, `style_body`, `style_cols`, `style_zone`, `add_header_row`, `collapse_repeats` |
| [Cell-format functions](#cell-format-functions) | `format_count_pct`, `realign_count_pct`, `fmt_count_paren`, `fmt_count_paren_bare`, `fmt_right_align` |
| [Blank rows](#blank-rows) | `set_blank_rows`, `blank_rows_by_change`, `blank_rows_by_rule`, `BlankRowsByChange`, `BlankRowsByRule`, `BEFORE_FIRST`, `AFTER_LAST` |
| [Pagination strategies and helpers](#pagination-strategies-and-helpers) | `paginate`, `Frame`, `PaginationError`, `add_cont_label`, `page_split_none`, `page_split_rows`, `page_split_by_value`, `page_split_group_safe`, `page_split_group_force` |
| [Borders](#borders) | `rtf_border_side`, `rtf_border`, `rtf_border_with`, `rtf_border_none`, `rtf_border_top`, `rtf_border_bottom`, `rtf_border_box`, `rtf_table_border`, `rtf_border_tfl`, `Border`, `BorderSide`, `TableBorder` |
| [Shared table styles](#shared-table-styles) | `rtf_table_style`, `rtf_table_style_with`, `rtf_table_style_tfl`, `TableStyle` |
| [Column-width utilities](#column-width-utilities) | `text_width_in`, `auto_col_widths` |
| [Assembling multiple RTF files](#assembling-multiple-rtf-files) | `assemble_rtf`, `assemble_files`, `assemble_folder`, `assemble_spec`, `assemble_from_spec`, `assemble_toc`, `toc_heading`, `toc_entry` |
| [Post-processing](#post-processing) | `rtf_replace_text` |
| [Markup](#markup) | `resolve_markup` |


## Document and rendering

The entry point and the final render call.  Build a document by passing `rtf_document()` through the section and content calls below, then render it with `generate_rtfreport()`.  Every builder returns a **new** document; the one passed in is left unchanged, as in R.

::: rtfreporter.document.RtfDocument

::: rtfreporter.document.rtf_document

::: rtfreporter.document.rtf_config

::: rtfreporter.page.rtf_page

::: rtfreporter.page.DefaultFormat

::: rtfreporter.page.rtf_default_format

::: rtfreporter.page.Page

::: rtfreporter.document.generate_rtfreport

::: rtfreporter.document.to_rtf

::: rtfreporter.document.save


## Package defaults

Inspect and reset the configurable `rtfreporter.*` defaults (paper size, orientation, margins, font, font size).  Resolution order: an explicit argument, then an option, then the factory value.

::: rtfreporter.config.rtfreporter_options

::: rtfreporter.config.rtfreporter_reset_defaults


## Sections: headers and footers

A section applies a running header and footer to a range of pages.  The bands are themselves small tables whose rows you build with `rtf_header()` / `rtf_footer()` and edit with the `update_*_row()` helpers.

::: rtfreporter.document.rtf_section

::: rtfreporter.header_footer.rtf_header

::: rtfreporter.header_footer.rtf_footer

::: rtfreporter.header_footer.HeaderFooter

::: rtfreporter.header_footer.update_header_row

::: rtfreporter.header_footer.update_footer_row


## Page content: tables and figures

Add one content item per page with `rtf_tables()` / `rtf_figures()`, and attach per-page titles and footnotes.  For finer control build the content object yourself with `rtftable()` / `rtfplot()` and pass it in.

::: rtfreporter.document.rtf_tables

::: rtfreporter.document.rtf_figures

::: rtfreporter.document.rtf_titles

::: rtfreporter.document.rtf_footnotes

::: rtfreporter.table.rtftable

::: rtfreporter.table.RtfTable

::: rtfreporter.table.ColSpec

::: rtfreporter.figure.rtfplot

::: rtfreporter.figure.Figure


## Importing tables

Convert a pandas or polars DataFrame, a `great_tables` GT object, or a plain dict/records structure into `RtfTable` pages, reading the source's metadata and paginating in one call.  `as_rtftables()` returns one table **per page**; `as_rtftable()` is the single-page form.  `stub_cols()` finishes a tidy frame beforehand by merging hierarchy columns into one indented stub.

::: rtfreporter.adapters.as_rtftables

::: rtfreporter.adapters.as_rtftable

::: rtfreporter.post_hoc.combine_sections

::: rtfreporter.stub.stub_cols


## Column headers

Multi-row column headers with optional spanning cells, addressed by position (`cols=1`, `cols=(1, 3)`) or by column name.  Ranges are **inclusive and 0-based**.  `set_col_header()` configures the header of a finished table against its final printed columns; `rtf_columns()` lists those columns; `rtf_header_source()` deparses the current header back to editable source.

::: rtfreporter.table.rtf_col_header

::: rtfreporter.table.col_cell

::: rtfreporter.table.SpanCell

::: rtfreporter.table.HeaderRow

::: rtfreporter.post_hoc.col_header_from_names

::: rtfreporter.post_hoc.add_col_header_row

::: rtfreporter.post_hoc.set_col_header

::: rtfreporter.post_hoc.set_header_cell

::: rtfreporter.post_hoc.rtf_columns

::: rtfreporter.post_hoc.rtf_header_source


## Post-hoc styling verbs

Restyle an already-built table -- or every page of an `as_rtftables()` list at once -- addressing header rows, body rows and columns by position. Each verb returns a modified copy; last writer wins, per side and per field.  `collapse_repeats()` blanks repeated group values.

::: rtfreporter.style_verbs.style_header

::: rtfreporter.style_verbs.style_body

::: rtfreporter.style_verbs.style_cols

::: rtfreporter.style_verbs.style_zone

::: rtfreporter.post_hoc.add_header_row

::: rtfreporter.post_hoc.collapse_repeats


## Cell-format functions

Ready-made cell re-formatters for the `cell_format` argument of `rtftable()` / `as_rtftables()`, notably monospaced count/percent alignment.  You can also write your own, following the same one-column-in / one-column-out contract.

::: rtfreporter.format_count_pct.format_count_pct

::: rtfreporter.format_count_pct.realign_count_pct

::: rtfreporter.format_count_pct.fmt_count_paren

::: rtfreporter.format_count_pct.fmt_count_paren_bare

::: rtfreporter.format_count_pct.fmt_right_align


## Blank rows

Insert blank separator rows by position, by value change, or by rule.  Positions are 0-based; the two R sentinels (`0` and `-1`) are the named constants `BEFORE_FIRST` and `AFTER_LAST`.

::: rtfreporter.pagination.set_blank_rows

::: rtfreporter.blank_rows.blank_rows_by_change

::: rtfreporter.blank_rows.blank_rows_by_rule

::: rtfreporter.blank_rows.BlankRowsByChange

::: rtfreporter.blank_rows.BlankRowsByRule

::: rtfreporter.blank_rows.BEFORE_FIRST

::: rtfreporter.blank_rows.AFTER_LAST


## Pagination strategies and helpers

Built-in page-split strategies as reusable callables for the `split=` argument of `as_rtftables()`, plus the helpers for writing your own.  `group_force` cuts on every `max_rows` and repeats the group header with a continuation label; `group_safe` never splits a group.

::: rtfreporter.pagination.paginate

::: rtfreporter.pagination.Frame

::: rtfreporter.pagination.PaginationError

::: rtfreporter.pagination.add_cont_label

::: rtfreporter.pagination.page_split_none

::: rtfreporter.pagination.page_split_rows

::: rtfreporter.pagination.page_split_by_value

::: rtfreporter.pagination.page_split_group_safe

::: rtfreporter.pagination.page_split_group_force


## Borders

Border specifications.  Borders apply to content-table zones, to header and footer rows, and to individual columns and cells, so the same builders are reused throughout a report.

::: rtfreporter.borders.rtf_border_side

::: rtfreporter.borders.rtf_border

::: rtfreporter.borders.rtf_border_with

::: rtfreporter.borders.rtf_border_none

::: rtfreporter.borders.rtf_border_top

::: rtfreporter.borders.rtf_border_bottom

::: rtfreporter.borders.rtf_border_box

::: rtfreporter.borders.rtf_table_border

::: rtfreporter.borders.rtf_border_tfl

::: rtfreporter.borders.Border

::: rtfreporter.borders.BorderSide

::: rtfreporter.borders.TableBorder


## Shared table styles

Bundle border, padding and row-height defaults into a reusable style and share it across many tables.  Snapshot semantics: a table captures the style's state at construction.

::: rtfreporter.rtf_table_style.rtf_table_style

::: rtfreporter.rtf_table_style.rtf_table_style_with

::: rtfreporter.rtf_table_style.rtf_table_style_tfl

::: rtfreporter.rtf_table_style.TableStyle


## Column-width utilities

Measure rendered text and propose column widths.

::: rtfreporter.text_width.text_width_in

::: rtfreporter.text_width.auto_col_widths


## Assembling multiple RTF files

Combine several rendered RTF files into one deliverable with a table of contents -- for example a TLF shell catalogue.

::: rtfreporter.assemble.assemble_rtf

::: rtfreporter.assemble.assemble_files

::: rtfreporter.assemble.assemble_folder

::: rtfreporter.assemble.assemble_spec

::: rtfreporter.assemble.assemble_from_spec

::: rtfreporter.assemble.assemble_toc

::: rtfreporter.assemble.toc_heading

::: rtfreporter.assemble.toc_entry


## Post-processing

Last-mile edits to an already-rendered RTF file, such as a one-off find-and-replace on the generated bytes.

::: rtfreporter.rtf_replace_text.rtf_replace_text


## Markup

Inline text markup: superscripts, subscripts and relational operators, resolved into RTF control words at render time.

::: rtfreporter._escape.resolve_markup

