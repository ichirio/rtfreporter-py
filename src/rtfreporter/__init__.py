"""rtfreporter -- a Python toolkit for clinical RTF Tables, Listings and Figures.

A faithful, Pythonic port of the R package ``rtfreporter``.  Compose an RTF
document from tables (with multi-row spanning column headers, per-column
formatting, clinical borders), running headers/footers with automatic
page-number fields, titles/footnotes, and embedded PNG/JPEG figures -- with no
third-party RTF engine.

The **module-level functions mirror the R API** (``rtf_document``,
``rtf_tables``, ``rtf_header``, ``rtf_border``, ``generate_rtfreport`` ...); the
fluent :class:`RtfDocument` methods are an equivalent convenience.  Two
deliberate divergences from R: **all index-taking arguments are 0-based**, and
the ``blank_rows`` sentinels are the named constants :data:`BEFORE_FIRST` /
:data:`AFTER_LAST` (not bare integers).

Example (module-level / R-style pipe):
    >>> from rtfreporter import rtf_document, rtf_tables, rtf_header, generate_rtfreport
    >>> doc = rtf_document()
    >>> doc = rtf_tables(doc, {"Subject": ["001", "002"], "Age": [34, 45]},
    ...                  titles=["Table 14.1", "", "Demographics"])
    >>> doc = rtf_section(doc, header=rtf_header([{"l": "Protocol XYZ", "r": "Page {AUTO_PAGE}"}]))
    >>> _ = generate_rtfreport(doc, "demographics.rtf", overwrite=True)
"""

from __future__ import annotations

from ._escape import resolve_markup
from .adapters import as_rtftable, as_rtftables
from .assemble import (
    assemble_files,
    assemble_folder,
    assemble_from_spec,
    assemble_rtf,
    assemble_spec,
    assemble_toc,
    toc_entry,
    toc_heading,
)
from .blank_rows import (
    AFTER_LAST,
    BEFORE_FIRST,
    BlankRowsByChange,
    BlankRowsByRule,
    blank_rows_by_change,
    blank_rows_by_rule,
)
from .borders import (
    Border,
    BorderSide,
    TableBorder,
    rtf_border,
    rtf_border_bottom,
    rtf_border_box,
    rtf_border_none,
    rtf_border_side,
    rtf_border_tfl,
    rtf_border_top,
    rtf_border_with,
    rtf_table_border,
)
from .config import rtfreporter_options, rtfreporter_reset_defaults
from .document import (
    RtfDocument,
    generate_rtfreport,
    rtf_config,
    rtf_document,
    rtf_figures,
    rtf_footnotes,
    rtf_section,
    rtf_tables,
    rtf_titles,
    save,
    to_rtf,
)
from .figure import Figure, rtfplot
from .format_count_pct import (
    fmt_count_paren,
    fmt_count_paren_bare,
    fmt_right_align,
    format_count_pct,
    realign_count_pct,
)
from .header_footer import (
    HeaderFooter,
    rtf_footer,
    rtf_header,
    update_footer_row,
    update_header_row,
)
from .page import DefaultFormat, Page, rtf_default_format, rtf_page
from .pagination import (
    Frame,
    PaginationError,
    add_cont_label,
    page_split_by_value,
    page_split_group_force,
    page_split_group_safe,
    page_split_none,
    page_split_rows,
    paginate,
    set_blank_rows,
)
from .post_hoc import (
    add_col_header_row,
    add_header_row,
    col_header_from_names,
    collapse_repeats,
    combine_sections,
    rtf_columns,
    rtf_header_source,
    set_col_header,
    set_header_cell,
)
from .rtf_replace_text import rtf_replace_text
from .rtf_table_style import (
    TableStyle,
    rtf_table_style,
    rtf_table_style_tfl,
    rtf_table_style_with,
)
from .stub import stub_cols
from .style_verbs import style_body, style_cols, style_header, style_zone
from .table import (
    ColSpec,
    HeaderRow,
    RtfTable,
    SpanCell,
    col_cell,
    rtf_col_header,
    rtftable,
)
from .text_width import auto_col_widths, text_width_in

__version__ = "0.2.0"

__all__ = [
    "__version__",
    # document + pipe API
    "RtfDocument",
    "rtf_document",
    "rtf_tables",
    "rtf_figures",
    "rtf_titles",
    "rtf_footnotes",
    "rtf_section",
    "generate_rtfreport",
    "to_rtf",
    "save",
    # table model
    "RtfTable",
    "rtftable",
    "ColSpec",
    "SpanCell",
    "HeaderRow",
    "col_cell",
    "rtf_col_header",
    # adapters
    "as_rtftable",
    "as_rtftables",
    # header / footer
    "HeaderFooter",
    "rtf_header",
    "rtf_footer",
    "update_header_row",
    "update_footer_row",
    # page / format / config
    "Page",
    "rtf_page",
    "DefaultFormat",
    "rtf_default_format",
    "rtf_config",
    "rtfreporter_options",
    "rtfreporter_reset_defaults",
    # borders
    "Border",
    "BorderSide",
    "TableBorder",
    "rtf_border",
    "rtf_border_side",
    "rtf_border_none",
    "rtf_border_top",
    "rtf_border_bottom",
    "rtf_border_box",
    "rtf_border_tfl",
    "rtf_border_with",
    "rtf_table_border",
    # table style
    "TableStyle",
    "rtf_table_style",
    "rtf_table_style_tfl",
    "rtf_table_style_with",
    # post-hoc verbs / helpers
    "set_col_header",
    "set_header_cell",
    "add_header_row",
    "add_col_header_row",
    "col_header_from_names",
    "rtf_columns",
    "rtf_header_source",
    "collapse_repeats",
    "combine_sections",
    "stub_cols",
    "set_blank_rows",
    "auto_col_widths",
    "text_width_in",
    "rtf_replace_text",
    # assemble family
    "assemble_rtf",
    "assemble_files",
    "assemble_spec",
    "assemble_toc",
    "assemble_from_spec",
    "assemble_folder",
    "toc_heading",
    "toc_entry",
    # figures
    "Figure",
    "rtfplot",
    # blank rows
    "BEFORE_FIRST",
    "AFTER_LAST",
    "BlankRowsByChange",
    "BlankRowsByRule",
    "blank_rows_by_change",
    "blank_rows_by_rule",
    # count / percent formatters
    "format_count_pct",
    "realign_count_pct",
    "fmt_count_paren",
    "fmt_count_paren_bare",
    "fmt_right_align",
    # pagination
    "Frame",
    "PaginationError",
    "paginate",
    "add_cont_label",
    "page_split_none",
    "page_split_rows",
    "page_split_by_value",
    "page_split_group_safe",
    "page_split_group_force",
    # style verbs
    "style_body",
    "style_cols",
    "style_header",
    "style_zone",
    # misc
    "resolve_markup",
]
