"""Post-hoc styling verbs for :class:`~rtfreporter.table.RtfTable`.

Ported (Pythonically) from ``R/style_verbs.R``.  Each verb returns a **modified
copy** of the table, leaving the original untouched, so they compose cleanly::

    tbl2 = style_header(style_body(tbl, bold=True), align="center")
"""

from __future__ import annotations

from dataclasses import replace

from .borders import Border, TableBorder
from .table import RtfTable

_BODY_FIELDS = ("align", "bold", "italic", "underline", "indent_twips", "color", "border")
_HEADER_FIELDS = ("header_align", "header_bold", "header_italic")
_VALID_ZONES = ("header", "spanning", "body", "first_row", "last_row")


def _col_indices(tbl: RtfTable, cols) -> list[int]:
    if cols is None:
        return list(range(tbl.ncols))
    if isinstance(cols, (str, int)):
        cols = [cols]
    out = []
    for c in cols:
        if isinstance(c, str):
            if c not in tbl.column_names:
                raise ValueError(f"Unknown column name {c!r}.")
            out.append(tbl.column_names.index(c))
        else:
            idx = int(c)
            if idx < 0 or idx >= tbl.ncols:
                raise ValueError(f"Column index {idx} out of range.")
            out.append(idx)
    return out


def style_cols(tbl: RtfTable, cols=None, **fields) -> RtfTable:
    """Return a copy with per-column *body* and/or *header* fields updated.

    Args:
        tbl: The source table.
        cols: Column index/name, a list of them, or ``None`` for every column.
        **fields: Any of the body fields (``align``, ``bold``, ``italic``,
            ``underline``, ``indent_twips``, ``color``, ``border``) or header
            fields (``header_align``, ``header_bold``, ``header_italic``).
    """
    unknown = set(fields) - set(_BODY_FIELDS) - set(_HEADER_FIELDS)
    if unknown:
        raise ValueError(f"Unknown style field(s): {sorted(unknown)}.")
    out = tbl.copy()
    for idx in _col_indices(tbl, cols):
        out.col_spec[idx] = replace(
            out.col_spec[idx], **{k: v for k, v in fields.items() if v is not None}
        )
    return out


def style_body(tbl: RtfTable, cols=None, **fields) -> RtfTable:
    """Return a copy with per-column *body* styling updated (see :func:`style_cols`)."""
    unknown = set(fields) - set(_BODY_FIELDS)
    if unknown:
        raise ValueError(f"style_body accepts only body fields; got {sorted(unknown)}.")
    return style_cols(tbl, cols, **fields)


def style_header(tbl: RtfTable, cols=None, align=None, bold=None, italic=None, border=None) -> RtfTable:
    """Return a copy with column-header styling updated.

    Args:
        align: Header alignment (mapped to ``header_align``).
        bold, italic: Header decoration flags (mapped to ``header_*``).
        border: Per-column header border override.
    """
    fields = {}
    if align is not None:
        fields["header_align"] = align
    if bold is not None:
        fields["header_bold"] = bold
    if italic is not None:
        fields["header_italic"] = italic
    if border is not None:
        fields["border"] = border
    return style_cols(tbl, cols, **fields)


def style_zone(tbl: RtfTable, zone: str, border: Border | None) -> RtfTable:
    """Return a copy with one table :class:`~rtfreporter.borders.TableBorder` zone set.

    Args:
        zone: One of ``"header"``, ``"spanning"``, ``"body"``, ``"first_row"``,
            ``"last_row"``.
        border: A :class:`~rtfreporter.borders.Border` (or ``None`` to clear it).
    """
    if zone not in _VALID_ZONES:
        raise ValueError(f"`zone` must be one of {_VALID_ZONES}.")
    if border is not None and not isinstance(border, Border):
        raise TypeError("`border` must be a Border or None.")
    out = tbl.copy()
    base = out.border or TableBorder()
    out.border = replace(base, **{zone: border})
    return out
