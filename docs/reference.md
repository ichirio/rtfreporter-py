# API reference

Every symbol below is importable directly from the top-level `rtfreporter`
package, and follows the R package's name, arguments and defaults.

!!! note "Two deliberate divergences from R"

    **All index-taking arguments are 0-based** (R is 1-based), and the
    `blank_rows` sentinels are the named constants `BEFORE_FIRST` /
    `AFTER_LAST` rather than the magic integers `0` and `-1`.
    See [Differences from the R package](r-differences.md).

**Start here:** [four complete recipes](recipes.md) -- DM, AE, PK and LB,
each a program that ends in a rendered RTF.

## Contents

| Group | Symbols |
|---|---|
| [Document and rendering](#document-and-rendering) | `RtfDocument`, `rtf_document`, `rtf_config`, `rtf_page`, `DefaultFormat`, `rtf_default_format`, `Page`, `rtf_watermark`, `Watermark`, `generate_rtfreport`, `to_rtf`, `save` |
| [Package defaults](#package-defaults) | `rtfreporter_options`, `rtfreporter_reset_defaults` |
| [Sections: headers and footers](#sections-headers-and-footers) | `rtf_section`, `rtf_header`, `rtf_footer`, `HeaderFooter`, `update_header_row`, `update_footer_row` |
| [Page content: tables and figures](#page-content-tables-and-figures) | `rtf_tables`, `rtf_figures`, `rtf_titles`, `rtf_footnotes`, `rtftable`, `RtfTable`, `ColSpec`, `rtfplot`, `Figure` |
| [Importing tables](#importing-tables) | `as_rtftables`, `as_rtftable`, `combine_sections`, `stub_cols`, `stub_spec`, `StubSpec` |
| [Listings](#listings) | `listing_col`, `ListingCol`, `listing_spec`, `ListingSpec`, `build_listing`, `fit_listing_widths`, `listing_code`, `listing_wrap`, `listing_wrap_code`, `listing_disp_width`, `listing_take`, `listing_split_after`, `catx` |
| [Column headers](#column-headers) | `rtf_col_header`, `col_cell`, `col_key`, `header_map`, `SpanCell`, `HeaderRow`, `col_header_from_names`, `add_col_header_row`, `set_col_header`, `set_header_cell`, `rtf_columns`, `rtf_header_source` |
| [Post-hoc styling verbs](#post-hoc-styling-verbs) | `style_header`, `style_body`, `style_cols`, `style_zone`, `add_header_row`, `collapse_repeats`, `set_decimal_split` |
| [Cell-format functions](#cell-format-functions) | `format_count_pct`, `realign_count_pct`, `fmt_count_paren`, `fmt_count_paren_bare`, `fmt_value_paren`, `fmt_right_align` |
| [Numeric display formatters](#numeric-display-formatters) | `fmt_signif`, `fmt_round`, `fmt_numeric` |
| [Utilities](#utilities) | `round_num` |
| [Blank rows](#blank-rows) | `set_blank_rows`, `blank_rows_by_change`, `blank_rows_by_rule`, `BlankRowsByChange`, `BlankRowsByRule`, `BEFORE_FIRST`, `AFTER_LAST` |
| [Pagination strategies and helpers](#pagination-strategies-and-helpers) | `paginate_cols`, `paginate`, `Frame`, `PaginationError`, `add_cont_label` |
| [Borders](#borders) | `rtf_border_side`, `rtf_border`, `rtf_border_none`, `rtf_border_top`, `rtf_border_bottom`, `rtf_border_box`, `Border`, `BorderSide`, `TableBorder` |
| [Shared table styles](#shared-table-styles) | `rtf_table_style`, `rtf_table_style_with`, `rtf_table_style_tfl`, `TableStyle` |
| [Column-width utilities](#column-width-utilities) | `text_width_in`, `auto_col_widths` |
| [Assembling multiple RTF files](#assembling-multiple-rtf-files) | `assemble_rtf`, `assemble_files`, `assemble_folder`, `assemble_spec`, `assemble_from_spec`, `assemble_toc`, `toc_heading`, `toc_entry` |
| [Post-processing](#post-processing) | `rtf_replace_text` |
| [Markup](#markup) | `resolve_markup` |
| [Deprecated -- scheduled for removal](#deprecated----scheduled-for-removal) | `rtf_border_with`, `rtf_table_border`, `rtf_border_tfl` |


## Document and rendering

The entry point and the final render call.  Build a document by passing `rtf_document()` through the section and content calls below, then render it with `generate_rtfreport()`.  Every builder returns a **new** document; the one passed in is left unchanged, as in R.

::: rtfreporter.document.RtfDocument

::: rtfreporter.document.rtf_document

::: rtfreporter.document.rtf_config

::: rtfreporter.page.rtf_page

::: rtfreporter.page.DefaultFormat

::: rtfreporter.page.rtf_default_format

::: rtfreporter.page.Page

::: rtfreporter.watermark.rtf_watermark

::: rtfreporter.watermark.Watermark

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

Convert a pandas or polars DataFrame, a `great_tables` GT object, or a plain dict/records structure into `RtfTable` pages, reading the source's metadata and paginating in one call.  `as_rtftables()` returns one table **per page**; `as_rtftable()` is the single-page form.  `stub_cols()` merges hierarchy columns into one indented stub; `stub_spec()` asks `as_rtftables(stub=)` to do it inside the pipeline.

::: rtfreporter.adapters.as_rtftables

::: rtfreporter.adapters.as_rtftable

::: rtfreporter.post_hoc.combine_sections

::: rtfreporter.stub.stub_cols

::: rtfreporter.stub.stub_spec

::: rtfreporter.stub.StubSpec


## Listings

Turn source data into a listing body: declare the columns with `listing_col()` / `listing_spec()`, build the body with `build_listing()` (or pass the spec to `as_rtftables(listing=)`), and fit the widths to the page.  The wrapping rule is exposed so you can reproduce it.

::: rtfreporter.listing.listing_col

::: rtfreporter.listing.ListingCol

::: rtfreporter.listing.listing_spec

::: rtfreporter.listing.ListingSpec

::: rtfreporter.listing.build_listing

::: rtfreporter.listing.fit_listing_widths

::: rtfreporter.listing.listing_code

::: rtfreporter.listing.listing_wrap

::: rtfreporter.listing.listing_wrap_code

::: rtfreporter.listing.listing_disp_width

::: rtfreporter.listing.listing_take

::: rtfreporter.listing.listing_split_after

::: rtfreporter.catx.catx


## Column headers

Multi-row column headers with optional spanning cells, addressed by position (`pos=1`, `pos=(1, 3)`) or by column name.  Ranges are **inclusive and 0-based**.  `set_col_header()` configures the header of a finished table against its final printed columns; `rtf_columns()` lists those columns; `rtf_header_source()` deparses the current header back to editable source.

::: rtfreporter.table.rtf_col_header

::: rtfreporter.table.col_cell

::: rtfreporter.table.col_key

::: rtfreporter.post_hoc.header_map

::: rtfreporter.table.SpanCell

::: rtfreporter.table.HeaderRow

::: rtfreporter.post_hoc.col_header_from_names

::: rtfreporter.post_hoc.add_col_header_row

::: rtfreporter.post_hoc.set_col_header

::: rtfreporter.post_hoc.set_header_cell

::: rtfreporter.post_hoc.rtf_columns

::: rtfreporter.post_hoc.rtf_header_source


## Post-hoc styling verbs

Restyle an already-built table -- or every page of an `as_rtftables()` list at once -- addressing header rows, body rows and columns by position. Each verb returns a modified copy; last writer wins, per side and per field.  `collapse_repeats()` blanks repeated group values; `set_decimal_split()` aligns numbers on the decimal mark.

::: rtfreporter.style_verbs.style_header

::: rtfreporter.style_verbs.style_body

::: rtfreporter.style_verbs.style_cols

::: rtfreporter.style_verbs.style_zone

::: rtfreporter.post_hoc.add_header_row

::: rtfreporter.post_hoc.collapse_repeats

::: rtfreporter.style_verbs.set_decimal_split


## Cell-format functions

Ready-made cell re-formatters for the `cell_format` argument of `rtftable()` / `as_rtftables()`, notably monospaced count/percent alignment.  You can also write your own, following the same one-column-in / one-column-out contract.

::: rtfreporter.format_count_pct.format_count_pct

::: rtfreporter.format_count_pct.realign_count_pct

::: rtfreporter.format_count_pct.fmt_count_paren

::: rtfreporter.format_count_pct.fmt_count_paren_bare

::: rtfreporter.format_count_pct.fmt_value_paren

::: rtfreporter.format_count_pct.fmt_right_align


## Numeric display formatters

Format numbers for display -- significant digits, fixed decimals, or a per-value rule -- with the package's one rounding rule.

::: rtfreporter.num_format.fmt_signif

::: rtfreporter.num_format.fmt_round

::: rtfreporter.num_format.fmt_numeric


## Utilities

The rounding rule itself (`rtfreporter_options(rounding=)`).

::: rtfreporter.num_format.round_num


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

The standalone paginator and the helpers for writing your own split function (the `split=<callable>` hook of `as_rtftables()`).  The built-in strategies are named by string: `group_force` cuts on every `max_rows` and repeats the group header with a continuation label; `group_safe` never splits a group.  `paginate_cols()` splits a wide table across pages by columns.

::: rtfreporter.paginate_cols.paginate_cols

::: rtfreporter.pagination.paginate

::: rtfreporter.pagination.Frame

::: rtfreporter.pagination.PaginationError

::: rtfreporter.pagination.add_cont_label


## Borders

Border specifications.  Borders apply to content-table zones, to header and footer rows, and to individual columns and cells, so the same builders are reused throughout a report.

::: rtfreporter.borders.rtf_border_side

::: rtfreporter.borders.rtf_border

::: rtfreporter.borders.rtf_border_none

::: rtfreporter.borders.rtf_border_top

::: rtfreporter.borders.rtf_border_bottom

::: rtfreporter.borders.rtf_border_box

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


## Deprecated -- scheduled for removal

The constructors of the old border model.  Each warns once per session and names its replacement; build borders with `rtf_border()` and apply them with `style_zone()` or the `border=` arguments instead.

::: rtfreporter.borders.rtf_border_with

::: rtfreporter.borders.rtf_table_border

::: rtfreporter.borders.rtf_border_tfl

