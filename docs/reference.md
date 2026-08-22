# API reference

Auto-generated from the source docstrings. Everything here is importable
directly from the top-level `rtfreporter` package.

The module-level functions mirror the R API (`rtf_document`, `rtf_tables`,
`rtf_header`, `rtf_border`, ...). Two deliberate divergences from R:
**all index-taking arguments are 0-based**, and the `blank_rows` sentinels are
the named constants `BEFORE_FIRST` / `AFTER_LAST`.

## Document and the pipe API

::: rtfreporter.document.RtfDocument

::: rtfreporter.document.rtf_document

::: rtfreporter.document.rtf_tables

::: rtfreporter.document.rtf_figures

::: rtfreporter.document.rtf_titles

::: rtfreporter.document.rtf_footnotes

::: rtfreporter.document.rtf_section

::: rtfreporter.document.generate_rtfreport

::: rtfreporter.document.to_rtf

::: rtfreporter.document.save

## Table model

::: rtfreporter.table.rtftable

::: rtfreporter.table.RtfTable

::: rtfreporter.table.ColSpec

::: rtfreporter.table.SpanCell

::: rtfreporter.table.HeaderRow

::: rtfreporter.table.col_cell

::: rtfreporter.table.rtf_col_header

## Adapters

::: rtfreporter.adapters.as_rtftable

::: rtfreporter.adapters.as_rtftables

### great_tables adapter

::: rtfreporter.gt_adapter.gt_to_result

::: rtfreporter.gt_adapter.resolve_meta_tokens

::: rtfreporter.gt_adapter.GT_META_TOKENS

## Headers and footers

::: rtfreporter.header_footer.rtf_header

::: rtfreporter.header_footer.rtf_footer

::: rtfreporter.header_footer.HeaderFooter

::: rtfreporter.header_footer.update_header_row

::: rtfreporter.header_footer.update_footer_row

## Page and defaults

::: rtfreporter.page.rtf_page

::: rtfreporter.page.Page

::: rtfreporter.page.DefaultFormat

::: rtfreporter.page.rtf_default_format

::: rtfreporter.document.rtf_config

::: rtfreporter.config.rtfreporter_options

::: rtfreporter.config.rtfreporter_reset_defaults

## Borders

::: rtfreporter.borders.BorderSide

::: rtfreporter.borders.Border

::: rtfreporter.borders.TableBorder

::: rtfreporter.borders.rtf_border_side

::: rtfreporter.borders.rtf_border

::: rtfreporter.borders.rtf_border_none

::: rtfreporter.borders.rtf_border_top

::: rtfreporter.borders.rtf_border_bottom

::: rtfreporter.borders.rtf_border_box

::: rtfreporter.borders.rtf_border_tfl

::: rtfreporter.borders.rtf_border_with

::: rtfreporter.borders.rtf_table_border

## Table style

::: rtfreporter.rtf_table_style.rtf_table_style

::: rtfreporter.rtf_table_style.rtf_table_style_tfl

::: rtfreporter.rtf_table_style.rtf_table_style_with

::: rtfreporter.rtf_table_style.TableStyle

## Figures

::: rtfreporter.figure.rtfplot

::: rtfreporter.figure.Figure

## Blank rows

::: rtfreporter.blank_rows.BEFORE_FIRST

::: rtfreporter.blank_rows.AFTER_LAST

::: rtfreporter.blank_rows.blank_rows_by_change

::: rtfreporter.blank_rows.blank_rows_by_rule

::: rtfreporter.blank_rows.BlankRowsByChange

::: rtfreporter.blank_rows.BlankRowsByRule

## Pagination

::: rtfreporter.pagination.paginate

::: rtfreporter.pagination.Frame

::: rtfreporter.pagination.add_cont_label

::: rtfreporter.pagination.page_split_none

::: rtfreporter.pagination.page_split_rows

::: rtfreporter.pagination.page_split_by_value

::: rtfreporter.pagination.page_split_group_safe

::: rtfreporter.pagination.page_split_group_force

::: rtfreporter.pagination.PaginationError

::: rtfreporter.pagination.set_blank_rows

## Post-hoc helpers

::: rtfreporter.post_hoc.rtf_columns

::: rtfreporter.post_hoc.set_col_header

::: rtfreporter.post_hoc.set_header_cell

::: rtfreporter.post_hoc.add_header_row

::: rtfreporter.post_hoc.add_col_header_row

::: rtfreporter.post_hoc.col_header_from_names

::: rtfreporter.post_hoc.collapse_repeats

::: rtfreporter.post_hoc.combine_sections

::: rtfreporter.post_hoc.rtf_header_source

## Stub and column widths

::: rtfreporter.stub.stub_cols

::: rtfreporter.text_width.auto_col_widths

::: rtfreporter.text_width.text_width_in

## Assemble (multi-file deliverables)

::: rtfreporter.assemble.assemble_rtf

::: rtfreporter.assemble.assemble_files

::: rtfreporter.assemble.assemble_spec

::: rtfreporter.assemble.assemble_toc

::: rtfreporter.assemble.assemble_from_spec

::: rtfreporter.assemble.assemble_folder

::: rtfreporter.assemble.toc_heading

::: rtfreporter.assemble.toc_entry

## Post-processing

::: rtfreporter.rtf_replace_text.rtf_replace_text

## Count / percent formatters

::: rtfreporter.format_count_pct.format_count_pct

::: rtfreporter.format_count_pct.realign_count_pct

::: rtfreporter.format_count_pct.fmt_count_paren

::: rtfreporter.format_count_pct.fmt_count_paren_bare

::: rtfreporter.format_count_pct.fmt_right_align

## Style verbs

::: rtfreporter.style_verbs.style_body

::: rtfreporter.style_verbs.style_cols

::: rtfreporter.style_verbs.style_header

::: rtfreporter.style_verbs.style_zone

## Markup

::: rtfreporter._escape.resolve_markup
