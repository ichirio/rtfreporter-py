"""Post-hoc table verbs that operate on a finished :class:`RtfTable`.

Ported from ``R/style_verbs.R`` / ``R/col_header.R`` / ``R/collapse_repeats.R``
/ ``R/header_source.R`` / ``R/as_rtftables.R``.  Every verb returns a modified
**copy** (or, for a list of pages, a new list of copies) leaving the input
untouched, so they compose cleanly on an :func:`~rtfreporter.as_rtftables`
result.  All column references are 0-based indices or names against the
**final, printed** table (see :func:`rtf_columns`).
"""

from __future__ import annotations

from dataclasses import replace

from .adapters import _collapse_repeats, _resolve_indices
from .table import (
    HeaderRow,
    RtfTable,
    SpanCell,
    _ColCellSpec,
    _normalize_col_header,
    _resolve_col,
    rtf_col_header,
)

_ALIGN = ("left", "center", "right")


def _require_table(x, verb: str) -> None:
    if not isinstance(x, RtfTable):
        raise TypeError(
            f"`{verb}()` expects an RtfTable or a list of RtfTable pages "
            "(as returned by as_rtftables() / as_rtftable())."
        )


def _map_pages(x, fn, verb: str, **kwargs):
    """Apply ``fn`` to a single table or to every page of a list."""
    if isinstance(x, RtfTable):
        return fn(x, **kwargs)
    if isinstance(x, (list, tuple)):
        for p in x:
            _require_table(p, verb)
        return [fn(p, **kwargs) for p in x]
    _require_table(x, verb)


# -- rtf_columns() ------------------------------------------------------------


def rtf_columns(x) -> list[str]:
    """Return the final body column names of a table (or a list's first page).

    Use it to see exactly which names/positions :func:`set_col_header`,
    :func:`~rtfreporter.style_cols`, etc. address before writing a header.
    """
    if isinstance(x, RtfTable):
        return list(x.column_names)
    if isinstance(x, (list, tuple)):
        if not x:
            return []
        _require_table(x[0], "rtf_columns")
        return list(x[0].column_names)
    _require_table(x, "rtf_columns")


# -- col_header_from_names() / add_col_header_row() ---------------------------


def col_header_from_names(names, sep=None) -> list:
    """Reconstruct spanning header rows from delimited column names.

    Mirrors R's ``col_header_from_names()``.  Splits each name on ``sep`` (the
    longest match wins); adjacent columns sharing a label and ancestor path are
    merged into one spanning cell.  Returns a list of header rows suitable for
    :func:`set_col_header` or ``rtftable(col_header=...)``; when no name splits,
    a single flat label row.

    Args:
        names: A list of column names (or anything with a ``column_names`` /
            ``columns`` attribute, whose names are used).
        sep: Separator(s) to split on.  ``None`` uses the package defaults
            (``"____"`` and ``"___tlang_delim___"``).
    """
    from .adapters import _DEFAULT_HEADER_SEPS, _split_names_to_col_header

    if hasattr(names, "column_names"):
        names = list(names.column_names)
    elif hasattr(names, "columns"):
        names = list(names.columns)
    names = [str(n) for n in names]
    if not names:
        raise ValueError("`names` must be a non-empty sequence of column names.")
    seps = _DEFAULT_HEADER_SEPS if sep is None else sep
    rows = _split_names_to_col_header(names, seps)
    if rows is None:
        return [HeaderRow(kind="labels", labels=list(names))]
    return rows


def add_col_header_row(hdr, row, position: str = "bottom") -> list:
    """Add one header row to a ``col_header`` spec (mirrors ``add_col_header_row()``).

    Args:
        hdr: An existing ``col_header`` spec (a list of rows) or any value
            ``rtftable(col_header=...)`` accepts (promoted automatically).
        row: One header row -- a list of labels or a list of
            :func:`~rtfreporter.col_cell` cells.
        position: ``"bottom"`` (default) appends below; ``"top"`` prepends above.

    Returns:
        A new list of header rows.
    """
    if position not in ("top", "bottom"):
        raise ValueError('`position` must be "top" or "bottom".')
    current = list(rtf_col_header(hdr)) if not isinstance(hdr, list) else list(hdr)
    return [row, *current] if position == "top" else [*current, row]


# -- add_header_row() ---------------------------------------------------------


def add_header_row(x, row, position: str = "top"):
    """Prepend/append one column-header row to a finished table (or list of pages).

    Args:
        x: An :class:`RtfTable` or a list of pages.
        row: One header row (labels or :func:`~rtfreporter.col_cell` cells),
            normalised against the final columns.
        position: ``"top"`` (default) prepends above the existing header rows;
            ``"bottom"`` appends below.
    """
    if position not in ("top", "bottom"):
        raise ValueError('`position` must be "top" or "bottom".')

    def one(tbl: RtfTable) -> RtfTable:
        new_rows = _normalize_col_header([row], tbl.ncols, tbl.column_names)
        out = tbl.copy()
        out.col_header = new_rows + list(out.col_header) if position == "top" else list(out.col_header) + new_rows
        return out

    return _map_pages(x, one, "add_header_row")


# -- set_col_header() ---------------------------------------------------------


def set_col_header(x, *rows, align=None):
    """Replace the whole column header of a finished table (final-table coords).

    Args:
        x: An :class:`RtfTable` or a list of pages.
        *rows: The header rows, top first -- each a list of labels or of
            :func:`~rtfreporter.col_cell` cells, resolved against the final
            columns.  A single pre-built ``rtf_col_header`` is accepted.  Passing
            nothing clears the header (renders the column names).
        align: Optional column-header alignment for the final columns -- a single
            value or one per column.

    Returns:
        An object of the same shape as ``x``.
    """
    if len(rows) == 0:
        header = None
    elif len(rows) == 1:
        header = rows[0]
    else:
        header = list(rows)

    def one(tbl: RtfTable) -> RtfTable:
        out = tbl.copy()
        nc = out.ncols
        out.col_header = _normalize_col_header(header, nc, out.column_names)
        if align is not None:
            a = [align] * nc if isinstance(align, str) else list(align)
            if len(a) != nc:
                raise ValueError(
                    f"`align` must have length 1 or {nc} (one per printed column)."
                )
            if not all(v in _ALIGN for v in a):
                raise ValueError('`align` values must be "left", "center", or "right".')
            out.col_spec = [replace(out.col_spec[j], header_align=a[j]) for j in range(nc)]
        return out

    return _map_pages(x, one, "set_col_header")


# -- set_header_cell() --------------------------------------------------------


def _row_to_spans(row: HeaderRow, ncols: int) -> list[SpanCell]:
    """Represent any header row as a gap-free list of :class:`SpanCell`."""
    if row.kind == "spanning":
        return [replace(s) for s in row.spans]
    labels = row.labels or []
    return [
        SpanCell(start=j, end=j, label=(labels[j] if j < len(labels) else ""))
        for j in range(ncols)
    ]


def set_header_cell(x, *cells, row: int):
    """Merge individual :func:`~rtfreporter.col_cell` cells into one header row.

    Places one or more cells (by name/position, spanning via a ``(a, b)`` range)
    into header row ``row`` (0-based), keeping the other cells of that row
    intact.  Each target span must align to existing cell boundaries in that row
    (it cannot split an existing spanning cell) and the requested cells must not
    overlap one another.

    Args:
        x: An :class:`RtfTable` or a list of pages.
        *cells: :func:`~rtfreporter.col_cell` objects to place.
        row: The 0-based header row to edit (top = 0).  Add a new row with
            :func:`add_header_row`.
    """
    if len(cells) == 0:
        raise ValueError("Provide at least one col_cell() to place.")

    def one(tbl: RtfTable) -> RtfTable:
        hdrs = list(tbl.col_header)
        if not hdrs:
            raise ValueError(
                "This table has no column header; use set_col_header() first."
            )
        if not isinstance(row, int) or row < 0 or row >= len(hdrs):
            raise ValueError(
                f"`row` must be in 0..{len(hdrs) - 1} (the header rows, top first). "
                "To add a new row use add_header_row()."
            )
        nc = tbl.ncols
        new_cells: list[SpanCell] = []
        for cc in cells:
            if not isinstance(cc, _ColCellSpec):
                raise TypeError("set_header_cell() takes col_cell() objects.")
            sc = _resolve_col_cell(cc, tbl.column_names)
            if sc.start < 0 or sc.end >= nc:
                raise ValueError(
                    f"col_cell() covers columns {sc.start}-{sc.end}, outside 0..{nc - 1}."
                )
            new_cells.append(sc)

        cur = _row_to_spans(hdrs[row], nc)
        starts = {c.start for c in cur}
        ends = {c.end for c in cur}
        nc2 = sorted(new_cells, key=lambda c: c.start)
        for i, cell in enumerate(nc2):
            if i > 0 and cell.start <= nc2[i - 1].end:
                raise ValueError(
                    f"Requested header cells overlap (columns "
                    f"{nc2[i - 1].start}-{nc2[i - 1].end} and {cell.start}-{cell.end})."
                )
            if cell.start not in starts or cell.end not in ends:
                raise ValueError(
                    f"Target columns {cell.start}-{cell.end} do not align to existing "
                    "header-cell boundaries in that row (would split a spanning cell); "
                    "adjust the span."
                )

        def covered(c: SpanCell) -> bool:
            return any(n.start <= c.start and c.end <= n.end for n in new_cells)

        merged = [c for c in cur if not covered(c)] + new_cells
        merged.sort(key=lambda c: c.start)
        out = tbl.copy()
        hdrs[row] = HeaderRow(kind="spanning", spans=merged)
        out.col_header = hdrs
        return out

    return _map_pages(x, one, "set_header_cell")


def _resolve_col_cell(cc: _ColCellSpec, names: list[str]) -> SpanCell:
    """Resolve a :func:`col_cell` spec to a :class:`SpanCell` (final coords)."""
    pos = cc.pos
    if isinstance(pos, (list, tuple)):
        idxs = [_resolve_col(p, names) for p in pos]
        start, end = min(idxs), max(idxs)
    else:
        start = end = _resolve_col(pos, names)
    return SpanCell(
        start=start,
        end=end,
        label=cc.label or "",
        align=cc.align,
        bold=cc.bold,
        italic=cc.italic,
        underline=cc.underline,
        border=cc.border,
    )


# -- collapse_repeats() -------------------------------------------------------


def collapse_repeats(x, cols):
    """Blank consecutive repeated values in ``cols`` of a finished table.

    Keeps only the first row of each run; suppressed cells become ``""``.  On a
    list of pages each page is collapsed independently (a run restarts at every
    page break), matching ``as_rtftables(collapse_repeats=cols)``.

    Args:
        x: An :class:`RtfTable` or a list of pages.
        cols: Columns to collapse -- 0-based indices and/or names, in the final
            body columns, processed in the given order.
    """

    def one(tbl: RtfTable) -> RtfTable:
        idx = _resolve_indices(cols, tbl.column_names)
        out = tbl.copy()
        out.rows = _collapse_repeats(out.rows, idx)
        return out

    return _map_pages(x, one, "collapse_repeats")


# -- combine_sections() -------------------------------------------------------


def combine_sections(**groups) -> list[RtfTable]:
    """Flatten named tables/page-lists into one list ready for auto-sectioning.

    Mirrors R's ``combine_sections()``: each keyword argument's **name** is
    placed on its group's **first** page (``.name``) and the remaining pages are
    blanked (``None``), so one logical (possibly paginated) table renders as one
    section.  Each value is an :class:`RtfTable` or a list of them (e.g. an
    :func:`~rtfreporter.as_rtftables` result).

    Returns:
        A single flat list of :class:`RtfTable` pages (copies).
    """
    out: list[RtfTable] = []
    for label, g in groups.items():
        if isinstance(g, RtfTable):
            g = [g]
        if not isinstance(g, (list, tuple)):
            raise TypeError(
                f"`combine_sections()` argument '{label}' must be an RtfTable or a "
                "list of RtfTables."
            )
        if len(g) == 0:
            continue
        if not all(isinstance(p, RtfTable) for p in g):
            raise TypeError(
                f"`combine_sections()` argument '{label}' must contain only RtfTable "
                "objects."
            )
        for i, p in enumerate(g):
            c = p.copy()
            c.name = label if i == 0 else None
            out.append(c)
    return out


# -- rtf_header_source() ------------------------------------------------------


def rtf_header_source(x, snippet: bool = True) -> str:
    """Preview a finished table's column header as reusable source.

    A simplified port of R's ``rtf_header_source()``: introspects the header of
    a finished table (or the first page of a list) and returns Python source
    that reproduces it.  With ``snippet=True`` (default) a ready-to-run
    ``set_col_header(tbl, ...)`` call; with ``snippet=False`` just the row
    expressions.  Pair with :func:`rtf_columns` to see the exact column names.
    """
    tbl = x[0] if isinstance(x, (list, tuple)) and x else x
    _require_table(tbl, "rtf_header_source")
    rows = tbl.col_header or [HeaderRow(kind="labels", labels=list(tbl.column_names))]

    parts: list[str] = []
    for r in rows:
        if r.kind == "labels":
            parts.append(repr(list(r.labels or [])))
        else:
            cells = []
            for s in r.spans:
                pos = s.start if s.start == s.end else (s.start, s.end)
                cells.append(f"col_cell({pos!r}, {s.label!r})")
            parts.append("[" + ", ".join(cells) + "]")
    body = ",\n  ".join(parts)
    if not snippet:
        return body
    return f"set_col_header(\n  tbl,\n  {body},\n)"
