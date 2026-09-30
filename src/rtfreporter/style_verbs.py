"""Post-hoc styling verbs for :class:`~rtfreporter.table.RtfTable`.

Ported from ``R/style_verbs.R``.  Each verb returns a **modified copy** of the
table, leaving the original untouched, so they compose cleanly::

    tbl2 = style_header(style_body(tbl, bold=True), align="center")

Borders **merge side by side**: a second call adds to the first instead of
replacing it, which is where layering happens now that
``rtf_border_with()`` is deprecated (R #348).
"""

from __future__ import annotations

from dataclasses import replace

from .borders import (
    TABLE_BORDER_ZONES,
    Border,
    TableBorder,
    merge_border,
    warn_old_edge_reading,
)
from .table import RtfTable

_BODY_FIELDS = ("align", "bold", "italic", "underline", "indent_twips", "color",
                "background", "border")
_HEADER_FIELDS = ("header_align", "header_bold", "header_italic", "header_background")


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


def _check_border(b, verb: str) -> None:
    if b is not None and not isinstance(b, Border):
        raise TypeError(f"`{verb}(border=)` must be None or an rtf_border() object.")


def style_cols(tbl: RtfTable, cols=None, **fields) -> RtfTable:
    """Return a copy with per-column *body* and/or *header* fields updated.

    Args:
        tbl: The source table.
        cols: Column index/name, a list of them, or ``None`` for every column.
        **fields: Any of the body fields (``align``, ``bold``, ``italic``,
            ``underline``, ``indent_twips``, ``color``, ``background`` -- the
            cell fill, ``border``) or header fields (``header_align``,
            ``header_bold``, ``header_italic``, ``header_background``).  A
            ``border`` merges side by side onto the column's existing one.
    """
    unknown = set(fields) - set(_BODY_FIELDS) - set(_HEADER_FIELDS)
    if unknown:
        raise ValueError(f"Unknown style field(s): {sorted(unknown)}.")
    _check_border(fields.get("border"), "style_cols")
    out = tbl.copy()
    for idx in _col_indices(tbl, cols):
        new = {k: v for k, v in fields.items() if v is not None}
        if "border" in new:
            new["border"] = merge_border(out.col_spec[idx].border, new["border"])
        out.col_spec[idx] = replace(out.col_spec[idx], **new)
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
        border: Per-column header border, merged side by side onto the
            column's existing one.
    """
    fields = {}
    if align is not None:
        fields["header_align"] = align
    if bold is not None:
        fields["header_bold"] = bold
    if italic is not None:
        fields["header_italic"] = italic
    if border is not None:
        _check_border(border, "style_header")
        fields["border"] = border
    return style_cols(tbl, cols, **fields)


def style_zone(
    tbl: RtfTable,
    header: Border | None = None,
    spanning: Border | None = None,
    body: Border | None = None,
    first_row: Border | None = None,
    last_row: Border | None = None,
) -> RtfTable:
    """Return a copy with table-zone borders merged in (mirrors R ``style_zone()``).

    Each argument names one kind of row -- ``header``, ``spanning``, ``body``,
    ``first_row``, ``last_row`` -- and takes an :func:`~rtfreporter.rtf_border`
    whose ``top`` / ``bottom`` / ``left`` / ``right`` are that zone's **outer**
    edges and whose ``inside_h`` / ``inside_v`` are the rules inside it.  A
    zone's border merges side by side onto what the table already has, so a
    second call adds to the first.
    """
    zones = {
        "header": header, "spanning": spanning, "body": body,
        "first_row": first_row, "last_row": last_row,
    }
    zones = {z: b for z, b in zones.items() if b is not None}
    if not zones:
        return tbl
    for b in zones.values():
        _check_border(b, "style_zone")
    warn_old_edge_reading(TableBorder(**zones), ncols=tbl.ncols, nrows=tbl.nrows)
    out = tbl.copy()
    base = out.border or TableBorder()
    merged = {z: merge_border(getattr(base, z), zones[z]) if z in zones else getattr(base, z)
              for z in TABLE_BORDER_ZONES}
    out.border = replace(base, **merged)
    return out
