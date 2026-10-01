"""Post-hoc styling verbs for :class:`~rtfreporter.table.RtfTable`.

Ported from ``R/style_verbs.R``.  Each verb returns a **modified copy** of the
table, leaving the original untouched, so they compose cleanly::

    tbl2 = style_header(style_body(tbl, bold=True), align="center")

Borders **merge side by side**: a second call adds to the first instead of
replacing it, which is where layering happens now that
``rtf_border_with()`` is deprecated (R #348).
"""

from __future__ import annotations

import warnings
from dataclasses import replace

from .borders import (
    TABLE_BORDER_ZONES,
    Border,
    TableBorder,
    merge_border,
    warn_old_edge_reading,
)
from .table import HeaderRow, RtfTable, SpanCell

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


def style_cols(x: RtfTable, cols=None, **fields) -> RtfTable:
    """Return a copy with per-column *body* and/or *header* fields updated.

    Args:
        x: The source table.
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
    out = x.copy()
    for idx in _col_indices(x, cols):
        new = {k: v for k, v in fields.items() if v is not None}
        if "border" in new:
            new["border"] = merge_border(out.col_spec[idx].border, new["border"])
        out.col_spec[idx] = replace(out.col_spec[idx], **new)
    return out


def _check_flag(v, arg: str, verb: str):
    if not isinstance(v, bool):
        raise ValueError(f"`{verb}({arg}=)` must be True or False.")
    return v


def _check_align(a, verb: str):
    if a not in ("left", "center", "right"):
        raise ValueError(f'`{verb}(align=)` must be "left", "center", or "right".')
    return a


def _resolve_rows(tbl: RtfTable, rows, verb: str) -> list[int]:
    """``rows`` of :func:`style_body`: ``None`` = every body row; 0-based
    positions; a list of bools over the rows; or a predicate called with each
    row as a dict ``{column: value}`` (R's predicate / formula)."""
    n = tbl.nrows
    if rows is None:
        return list(range(n))
    if callable(rows):
        out = []
        for i, r in enumerate(tbl.rows):
            v = rows(dict(zip(tbl.column_names, r, strict=False)))
            if not isinstance(v, bool):
                raise ValueError(f"`{verb}(rows=)` predicate must return True or False; "
                                 f"got {type(v).__name__}.")
            if v:
                out.append(i)
        return out
    seq = [rows] if isinstance(rows, (bool, int)) else list(rows)
    if seq and all(isinstance(v, bool) for v in seq):
        if len(seq) != n:
            raise ValueError(f"`{verb}(rows=)` list of bools must have length {n} "
                             f"(the number of body rows); got {len(seq)}.")
        return [i for i, v in enumerate(seq) if v]
    if all(isinstance(v, int) and not isinstance(v, bool) for v in seq):
        if any(v < 0 or v >= n for v in seq):
            raise ValueError(f"`{verb}(rows=)` positions must be in 0..{n - 1}.")
        return [int(v) for v in seq]
    raise ValueError(f"`{verb}(rows=)` must be None, 0-based row positions, a list of "
                     "bools, or a predicate function(row).")


def style_body(x, rows=None, cols=None, bold=None, italic=None, underline=None,
               indent_twips=None, color=None, background=None, align=None, border=None):
    """Style body cells, by row and column (R ``style_body()``).

    Written per cell (into the table's ``cell_styles``), so a row can be
    picked out -- a subtotal in bold, one statistic shaded -- without touching
    the rest of its column.

    Args:
        x: An :class:`RtfTable`, or a list of pages.
        rows: ``None`` (every body row), 0-based row positions, a list of bools
            over the rows, or a predicate called with each row as a dict
            ``{column: value}``, e.g. ``lambda r: r["Statistic"] == "Mean"``.
            On a list of pages only ``None`` or a predicate: row positions are
            ambiguous across pages.
        cols: Column index / name, a list of them, or ``None`` for every column.
        bold, italic, underline: Text decoration.
        indent_twips: Left indent added to the cell.
        color: Text colour, ``"#RRGGBB"``.
        background: Cell fill, ``"#RRGGBB"``.
        align: ``"left"``, ``"center"`` or ``"right"``.
        border: An :func:`~rtfreporter.rtf_border`, merged side by side onto the
            cell's own.
    """
    kw = dict(bold=bold, italic=italic, underline=underline, indent_twips=indent_twips,
              color=color, background=background, align=align, border=border)
    if isinstance(x, (list, tuple)):
        if rows is not None and not callable(rows):
            raise ValueError(
                "`style_body()` on a page list cannot take row positions or bools -- "
                "page-local row numbers are ambiguous across pages.  Use a predicate "
                "function (evaluated per page), or style a single page directly.")
        return [style_body(p, rows=rows, cols=cols, **kw) for p in x]
    for arg in ("bold", "italic", "underline"):
        if kw[arg] is not None:
            _check_flag(kw[arg], arg, "style_body")
    if align is not None:
        _check_align(align, "style_body")
    _check_border(border, "style_body")
    rows_idx = _resolve_rows(x, rows, "style_body")
    cols_idx = _col_indices(x, cols)
    if not rows_idx:
        return x

    out = x.copy()
    nc = out.ncols
    cs_all = list(out.cell_styles) if out.cell_styles else [None] * out.nrows
    for r in rows_idx:
        cs = dict(cs_all[r]) if isinstance(cs_all[r], dict) else {}
        for key in ("bold", "italic", "underline", "indent_twips", "color",
                    "background", "align"):
            val = kw[key]
            if val is None:
                continue
            v = list(cs.get(key) or [None] * nc)
            for j in cols_idx:
                v[j] = int(val) if key == "indent_twips" else val
            cs[key] = v
        if border is not None:
            v = list(cs.get("border") or [None] * nc)
            for j in cols_idx:
                v[j] = merge_border(v[j], border)
            cs["border"] = v
        cs_all[r] = cs
    out.cell_styles = cs_all
    return out


def _promote_labels_row(labels, col_spec) -> HeaderRow:
    """A labels row as one cell per column, so a cell can carry its own border."""
    return HeaderRow(kind="spanning", spans=[
        SpanCell(start=j, end=j, label=labels[j] if j < len(labels) else "",
                 align=spec.header_align or "center", bold=bool(spec.header_bold),
                 italic=bool(spec.header_italic))
        for j, spec in enumerate(col_spec)])


def _patch_header_cells(row: HeaderRow, cols_idx, label, border, align, bold,
                        italic, underline) -> HeaderRow:
    targeted = [k for k, sp in enumerate(row.spans)
                if any(sp.start <= j <= sp.end for j in cols_idx)]
    if not targeted:
        warnings.warn("`style_header()`: no header cells intersect the requested "
                      "columns; nothing changed.", stacklevel=3)
        return row
    labels = None
    if label is not None:
        base = [label] if isinstance(label, str) else list(label)
        labels = [base[k % len(base)] for k in range(len(targeted))]
    spans = list(row.spans)
    for k, t in enumerate(targeted):
        sp = spans[t]
        new = {}
        if labels is not None:
            new["label"] = str(labels[k])
        if border is not None:
            new["border"] = merge_border(sp.border, border)
        if align is not None:
            new["align"] = align
        if bold is not None:
            new["bold"] = bold
        if italic is not None:
            new["italic"] = italic
        if underline is not None:
            new["underline"] = underline
        spans[t] = replace(sp, **new)
    return HeaderRow(kind="spanning", spans=spans)


def style_header(x, row=None, cols=None, label=None, border=None, align=None,
                 bold=None, italic=None, underline=None):
    """Style column-header cells, by header row and column (R ``style_header()``).

    Args:
        x: An :class:`RtfTable`, or a list of pages.
        row: 0-based header row(s), top first; ``None`` for every header row.
        cols: Column index / name, a list of them, or ``None`` for every column.
        label: New text for the selected cells (recycled across them).
        border: An :func:`~rtfreporter.rtf_border` for the selected cells only,
            merged side by side onto the cell's own.
        align, bold, italic, underline: Cell text styling.

    On a row of plain labels, ``bold`` / ``italic`` / ``align`` are stored per
    column and so shared by every label row (a warning says so when there are
    several); a ``border`` or ``underline`` turns that row into one cell per
    column first, so it can apply to the selected cells alone.  On a row of
    spanning cells every cell that covers a selected column is changed.
    """
    kw = dict(row=row, cols=cols, label=label, border=border, align=align, bold=bold,
              italic=italic, underline=underline)
    if isinstance(x, (list, tuple)):
        return [style_header(p, **kw) for p in x]
    if not x.col_header:
        raise ValueError("`style_header()`: this rtftable has no column header.")
    _check_border(border, "style_header")
    if align is not None:
        _check_align(align, "style_header")
    for arg, v in (("bold", bold), ("italic", italic), ("underline", underline)):
        if v is not None:
            _check_flag(v, arg, "style_header")
    hdrs = list(x.col_header)
    idx = list(range(len(hdrs))) if row is None else (
        [row] if isinstance(row, int) else list(row))
    if any(not isinstance(i, int) or i < 0 or i >= len(hdrs) for i in idx):
        raise ValueError(f"`style_header(row=)` must be in 0..{len(hdrs) - 1} "
                         "(the header rows, top first).")
    cols_idx = _col_indices(x, cols)
    out = x.copy()
    n_label_rows = sum(1 for h in hdrs if h.kind == "labels")
    for ri in idx:
        r = hdrs[ri]
        if r.kind == "labels":
            if border is not None or underline is not None:
                hdrs[ri] = _patch_header_cells(
                    _promote_labels_row(r.labels, out.col_spec), cols_idx, label,
                    border, align, bold, italic, underline)
            else:
                if label is not None:
                    labels = list(r.labels)
                    base = [label] if isinstance(label, str) else list(label)
                    for k, j in enumerate(cols_idx):
                        labels[j] = str(base[k % len(base)])
                    hdrs[ri] = HeaderRow(kind="labels", labels=labels)
                if (bold is not None or italic is not None or align is not None) \
                        and n_label_rows > 1:
                    warnings.warn("`style_header()`: header text styling "
                                  "(bold/italic/align) is stored per column and shared "
                                  "by ALL label rows.", stacklevel=2)
                for j in cols_idx:
                    new = {}
                    if bold is not None:
                        new["header_bold"] = bold
                    if italic is not None:
                        new["header_italic"] = italic
                    if align is not None:
                        new["header_align"] = align
                    if new:
                        out.col_spec[j] = replace(out.col_spec[j], **new)
        else:
            hdrs[ri] = _patch_header_cells(r, cols_idx, label, border, align, bold,
                                           italic, underline)
    out.col_header = hdrs
    return out


def style_zone(
    x: RtfTable,
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
        return x
    for b in zones.values():
        _check_border(b, "style_zone")
    warn_old_edge_reading(TableBorder(**zones), ncols=x.ncols, nrows=x.nrows)
    out = x.copy()
    base = out.border or TableBorder()
    merged = {z: merge_border(getattr(base, z), zones[z]) if z in zones else getattr(base, z)
              for z in TABLE_BORDER_ZONES}
    out.border = replace(base, **merged)
    return out


_COLS_MISSING = object()


def set_decimal_split(x, cols=_COLS_MISSING, ratio=None, decimal_mark: str = ".",
                      pad_chars=(1, 1), min_chars=(4, 6), max_chars=10,
                      include_compound: bool = False):
    """Line the decimal points of the given columns up (R ``set_decimal_split()``).

    Each data cell of the columns renders as two cells -- the integer part,
    right-aligned, and the decimal mark plus the rest, left-aligned -- so the
    points line up whatever the font; a cell that is not a number (free text,
    and by default a compound value such as ``"12.3 (4.56)"``) spans the pair
    as it would without this.  The header keeps the original columns.

    Args:
        x: An :class:`RtfTable`, or a list of pages.
        cols: The columns (0-based positions or names).  Required; pass
            ``cols=None`` explicitly to clear a previous setting.
        ratio: The integer half's share of the column, strictly between 0
            and 1; ``None`` measures it from the cells.
        decimal_mark: The separator (default ``"."``).
        pad_chars, min_chars: Per half (integer, decimal), in characters: the
            room added to what was measured, and the floor.
        max_chars: Past this many measured characters the allowance is
            dropped and the raw proportions are used (``math.inf``: never).
        include_compound: Split values with a companion (``"12.3 (4.56)"``)
            too.
    """
    if isinstance(x, (list, tuple)):
        return [set_decimal_split(p, cols=cols, ratio=ratio, decimal_mark=decimal_mark,
                                  pad_chars=pad_chars, min_chars=min_chars,
                                  max_chars=max_chars, include_compound=include_compound)
                for p in x]
    if cols is _COLS_MISSING:
        raise ValueError("`set_decimal_split()`: `cols` is required. To clear a previously "
                         "set split, pass `cols=None` explicitly.")
    out = x.copy()
    if cols is None:
        out.decimal_split = None
        return out
    cols_idx = _col_indices(x, cols)
    if not isinstance(decimal_mark, str) or not decimal_mark:
        raise ValueError("`decimal_mark` must be a single non-empty string.")
    if ratio is not None:
        try:
            ratio = float(ratio)
        except (TypeError, ValueError):
            ratio = None
        if ratio is None or not 0 < ratio < 1:
            raise ValueError("`ratio` must be a single number strictly between 0 and 1.")

    def widths(v, arg):
        if v is None:
            return None
        v = [float(z) for z in v]
        if len(v) != 2 or any(z < 0 for z in v):
            raise ValueError(f"`{arg}` must be two non-negative numbers "
                             "(integer half, decimal half).")
        return v

    if max_chars is not None and not float(max_chars) > 0:
        raise ValueError("`max_chars` must be a single positive number (or inf).")
    out.decimal_split = {
        "cols": [int(c) for c in cols_idx], "ratio": ratio, "decimal_mark": decimal_mark,
        "pad_chars": widths(pad_chars, "pad_chars"), "min_chars": widths(min_chars, "min_chars"),
        "max_chars": None if max_chars is None else float(max_chars),
        "include_compound": bool(include_compound),
    }
    return out
