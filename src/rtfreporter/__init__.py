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
    rtf_table_border,
)
from .document import (
    RtfDocument,
    generate_rtfreport,
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
from .header_footer import HeaderFooter, rtf_footer, rtf_header
from .page import DefaultFormat, Page, rtf_page
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

__version__ = "0.1.0"

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
    # page / format
    "Page",
    "rtf_page",
    "DefaultFormat",
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
    "rtf_table_border",
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
    # style verbs
    "style_body",
    "style_cols",
    "style_header",
    "style_zone",
    # misc
    "resolve_markup",
]
