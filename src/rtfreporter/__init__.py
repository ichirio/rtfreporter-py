"""rtfreporter -- a Python toolkit for clinical RTF Tables, Listings and Figures.

A faithful, Pythonic port of the R package ``rtfreporter``.  Compose an RTF
document from tables (with multi-row spanning column headers, per-column
formatting, clinical borders), running headers/footers with automatic
page-number fields, titles/footnotes, and embedded PNG/JPEG figures -- with no
third-party RTF engine.

Example:
    >>> from rtfreporter import RtfDocument, header, footer, rtftable
    >>> doc = (
    ...     RtfDocument()
    ...     .add_section(header=header([{"l": "Protocol XYZ", "r": "Page {AUTO_PAGE}"}]))
    ...     .add_table({"Subject": ["001", "002"], "Age": [34, 45]},
    ...                title=["Table 14.1", "", "Demographics"])
    ... )
    >>> _ = doc.save("demographics.rtf")
"""

from __future__ import annotations

from ._escape import resolve_markup
from .adapters import as_rtftable, as_rtftables
from .blank_rows import (
    BlankRowsByChange,
    BlankRowsByRule,
    blank_rows_by_change,
    blank_rows_by_rule,
)
from .borders import (
    Border,
    BorderSide,
    TableBorder,
    border,
    border_bottom,
    border_box,
    border_none,
    border_side,
    border_tfl,
    border_top,
)
from .document import RtfDocument, document, save, to_rtf
from .figure import Figure, rtfplot
from .header_footer import HeaderFooter, footer, header
from .page import DefaultFormat, Page
from .style_verbs import style_body, style_cols, style_header, style_zone
from .table import ColSpec, HeaderRow, RtfTable, SpanCell, col_cell, rtftable

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # document
    "RtfDocument",
    "document",
    "to_rtf",
    "save",
    # table model
    "RtfTable",
    "rtftable",
    "ColSpec",
    "SpanCell",
    "HeaderRow",
    "col_cell",
    # adapters
    "as_rtftable",
    "as_rtftables",
    # header / footer
    "HeaderFooter",
    "header",
    "footer",
    # page / format
    "Page",
    "DefaultFormat",
    # borders
    "Border",
    "BorderSide",
    "TableBorder",
    "border",
    "border_side",
    "border_none",
    "border_top",
    "border_bottom",
    "border_box",
    "border_tfl",
    # figures
    "Figure",
    "rtfplot",
    # blank rows
    "BlankRowsByChange",
    "BlankRowsByRule",
    "blank_rows_by_change",
    "blank_rows_by_rule",
    # style verbs
    "style_body",
    "style_cols",
    "style_header",
    "style_zone",
    # misc
    "resolve_markup",
]
