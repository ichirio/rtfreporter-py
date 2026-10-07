"""Post-hoc table verbs that operate on a finished :class:`RtfTable`.

Ported from ``R/style_verbs.R`` / ``R/col_header.R`` / ``R/collapse_repeats.R``
/ ``R/header_source.R`` / ``R/as_rtftables.R``.  Every verb returns a modified
**copy** (or, for a list of pages, a new list of copies) leaving the input
untouched, so they compose cleanly on an :func:`~rtfreporter.as_rtftables`
result.  All column references are 0-based indices or names against the
**final, printed** table (see :func:`rtf_columns`).
"""

from __future__ import annotations

import json
from dataclasses import replace

from ._run_tokens import RENDER_TOKENS
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
    """Reconstruct spanning header rows from delimited column names (deprecated).

    **Deprecated** (warns once a session, still works; removed in 0.9.0, as in
    R): :func:`~rtfreporter.as_rtftables` builds this header from a frame's
    names (``header_sep=``).

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
    from .borders import _deprecate_once

    _deprecate_once(
        "col_header_from_names",
        "`col_header_from_names()` is deprecated: `as_rtftables()` builds this "
        "header from a frame's names (`header_sep=`).\n  Removed in 0.9.0.",
    )
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
    """Add one header row to a ``col_header`` spec (deprecated; mirrors ``add_col_header_row()``).

    **Deprecated** (warns once a session, still works; removed in 0.9.0, as in
    R): write the row in :func:`~rtfreporter.rtf_col_header` itself (its rows,
    top first).

    Args:
        hdr: An existing ``col_header`` spec (a list of rows) or any value
            ``rtftable(col_header=...)`` accepts (promoted automatically).
        row: One header row -- a list of labels or a list of
            :func:`~rtfreporter.col_cell` cells.
        position: ``"bottom"`` (default) appends below; ``"top"`` prepends above.

    Returns:
        A new list of header rows.
    """
    from .borders import _deprecate_once

    _deprecate_once(
        "add_col_header_row",
        "`add_col_header_row()` is deprecated: write the row in "
        "`rtf_col_header()` itself (its rows, top first).\n  Removed in 0.9.0.",
    )
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


def set_col_header(x, *rows, align=None, values=None, by=None):
    """Replace the whole column header of a finished table (final-table coords).

    Args:
        x: An :class:`RtfTable` or a list of pages.
        *rows: The header rows, top first -- each a list of labels, a dict
            ``{column: label}`` (a named row: it may be shorter than the table,
            the columns it leaves out keep their own name), or a list of
            :func:`~rtfreporter.col_cell` cells, resolved against the final
            columns.  A single pre-built ``rtf_col_header`` is accepted.  Passing
            nothing clears the header (renders the column names).  An unnamed
            label row must carry one label per printed column.
        align: Optional column-header alignment for the final columns -- a single
            value or one per column.
        values: Optional per-page values for the ``{tokens}`` in the header: a
            table (DataFrame or dict of columns) with one row per page key and
            one column per token, e.g. ``"Placebo\\n(N={n_pbo})"`` filled from
            ``{"group": [...], "n_pbo": [...]}``.  ``{{`` / ``}}`` are literal
            braces; the render-time tokens (``{PAGE}``, ``{AUTO_PAGE}``, ...)
            are left for the renderer; any other unfilled token, a page with no
            row and a row no page uses are errors.  :func:`header_map` shows
            the result.
        by: The page key ``values`` is matched on, which is also the name of
            its key column: ``"group"`` (default; the value a ``by_value`` split
            cut the page for, else the page's name), ``"rows"`` (its
            ``page_by`` value) or ``"name"``; several for a combination.

    Returns:
        An object of the same shape as ``x``.
    """
    from .table import check_col_header_width

    if len(rows) == 0:
        header = None
    elif len(rows) == 1:
        header = rows[0]
    else:
        header = list(rows)

    if values is not None:
        pages = [x] if isinstance(x, RtfTable) else list(x)
        idx, keys, records = _match_value_rows(pages, values, by)
        filled = []
        for p, i in zip(pages, idx, strict=True):
            vals = {k: v for k, v in records[i].items() if k not in keys}
            h = _fill_header_tokens(header, vals, "set_col_header(values = )")
            filled.append(set_col_header(p, *([] if h is None else [h]), align=align))
        return filled[0] if isinstance(x, RtfTable) else filled

    def one(tbl: RtfTable) -> RtfTable:
        out = tbl.copy()
        nc = out.ncols
        check_col_header_width(header, nc, "set_col_header")
        out.col_header = _normalize_col_header(header, nc, out.column_names)
        # the whole header is replaced, spanning rows included
        out.spanning_rows = 0
        out.col_header_given = header is not None
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


# -- set_col_header(values=) / header_map() -----------------------------------
#
# A column header is usually one shape with a few values that change page to
# page -- "(N=120)" for one period, "(N=118)" for the next.  It is written ONCE
# with `{token}` where a value belongs, and the values arrive as a table keyed
# by the page's own key -- its group, its page_by value or its name -- never
# its position (R col_header_values.R).

#: Tokens the RENDERER fills later: left alone here.
#: ``{DATE}`` is not one (R #532): nothing ever filled it.
_RENDER_TOKENS = frozenset(RENDER_TOKENS)
_TOKEN_RX = r"[{]([A-Za-z._][A-Za-z0-9._]*)[}]"


def _fill_text_tokens(txt, vals: dict, where: str):
    import re

    from .catx import _as_text

    if not isinstance(txt, str) or "{" not in txt:
        return txt
    s = txt.replace("{{", "\x01").replace("}}", "\x02")
    for nm, v in vals.items():
        s = s.replace("{" + nm + "}", _as_text(v))
    left = [t for t in dict.fromkeys(re.findall(_TOKEN_RX, s)) if t not in _RENDER_TOKENS]
    if left:
        raise ValueError(
            f"{where}: no value for " + ", ".join(f"`{{{t}}}`" for t in left)
            + ".\n  Supply it in `values`, or write `{{` for a literal brace.\n"
            "  values has: " + (", ".join(vals) if vals else "(nothing)")
        )
    return s.replace("\x01", "{").replace("\x02", "}")


def _fill_header_tokens(spec, vals: dict, where: str):
    """Fill every label a header spec carries, whatever shape it was written in."""
    from dataclasses import replace as dc_replace

    from .table import _ColCellSpec

    if spec is None:
        return spec
    if isinstance(spec, _ColCellSpec):
        return dc_replace(spec, label=_fill_text_tokens(spec.label, vals, where))
    if isinstance(spec, str):
        return _fill_text_tokens(spec, vals, where)
    if isinstance(spec, dict):
        return {k: _fill_header_tokens(v, vals, where) for k, v in spec.items()}
    if isinstance(spec, (list, tuple)):
        return [_fill_header_tokens(v, vals, where) for v in spec]
    return spec


def _page_key(tbl: RtfTable, axis: str):
    if axis == "group":
        return tbl.page_group if tbl.page_group else tbl.name
    if axis == "rows":
        return tbl.page_by if tbl.page_by else None
    if axis == "name":
        return tbl.name
    raise ValueError(f'`by`: "{axis}" is not a page axis (group, rows, name).')


def _match_value_rows(pages, values, by):
    """Match each page to one row of ``values`` (R ``.match_value_rows()``);
    returns ``(row index per page, key columns, the value records)``."""
    import sys

    from .catx import _as_text
    from .table import _coerce_data

    try:
        names, rows = _coerce_data(values)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("`values` must be a table (a DataFrame or a dict of columns): "
                         "one row per page key, one column per token.") from exc
    records = [dict(zip(names, r, strict=True)) for r in rows]
    by = ["group"] if by is None else ([by] if isinstance(by, str) else list(by))
    missing = [b for b in by if b not in names]
    if missing:
        raise ValueError(
            "`values` has no key column " + ", ".join(f"`{m}`" for m in missing)
            + ".  Name the key column after the axis it matches: `group`, `rows`, `name`."
        )
    if by == ["group"] and not any(p.page_group for p in pages):
        print('set_col_header(values = ): no group axis, so `by = "group"` '
              "matches on the page name instead.", file=sys.stderr)

    def key_of_page(p):
        return " + ".join(str(_page_key(p, a)) for a in by)

    want = [" + ".join(_as_text(r[a]) for a in by) for r in records]
    rowmap = {}
    for i, w in enumerate(want):
        rowmap.setdefault(w, i)
    out = []
    for i, p in enumerate(pages):
        k = key_of_page(p)
        if k not in rowmap:
            raise ValueError(
                f"`values` has no row for page {i} "
                f"({'unnamed' if p.name is None else repr(p.name)}).\n"
                f"  looked for {' + '.join(by)} = \"{k}\"\n"
                "  values has: " + " | ".join(dict.fromkeys(want))
            )
        out.append(rowmap[k])
    unused = [i for i in range(len(records)) if i not in set(out)]
    if unused:
        raise ValueError(
            f"`values` row{'s' if len(unused) > 1 else ''} "
            + ", ".join(str(i) for i in unused) + " matched no page: "
            + " | ".join(dict.fromkeys(want[i] for i in unused))
            + ".\n  Every row must be used -- a row left over is usually a label "
            "that does not match the data."
        )
    return out, by, records


def header_map(x) -> list[dict]:
    """What every page's column header ended up with (R ``header_map()``).

    One record per header cell: the page (0-based), its ``name``, ``group``
    and ``rows`` (``page_by``) keys, the header ``row`` and ``cell`` (0-based),
    the columns it covers (``from`` / ``to``, 0-based inclusive) and its
    ``text``.  ``pandas.DataFrame(header_map(pages))`` makes it a table.
    """
    pages = [x] if isinstance(x, RtfTable) else list(x)
    out = []
    for i, p in enumerate(pages):
        for r, row in enumerate(p.col_header):
            cells = ([(k, k, k, lab) for k, lab in enumerate(row.labels or [])]
                     if row.kind == "labels"
                     else [(k, sp.start, sp.end, sp.label) for k, sp in enumerate(row.spans or [])])
            for k, frm, to, text in cells:
                out.append({"page": i, "name": p.name, "group": _page_key(p, "group"),
                            "rows": _page_key(p, "rows"), "row": r, "cell": k,
                            "from": frm, "to": to, "text": text})
    return out


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
    """Merge individual :func:`~rtfreporter.col_cell` cells into one header row (deprecated).

    **Deprecated** (warns once a session, still works; removed in 0.9.0, as in
    R): write the spanning cell in the header (:func:`~rtfreporter.rtf_col_header`
    / :func:`set_col_header`, a new row with :func:`add_header_row`) and
    restyle cells with :func:`~rtfreporter.style_header`.

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
    from .borders import _deprecate_once

    _deprecate_once(
        "set_header_cell",
        "`set_header_cell()` is deprecated: write the spanning cell in the header "
        "(`rtf_col_header()` / `set_col_header()`, a new row with "
        "`add_header_row()`) and restyle cells with `style_header()`.\n  "
        "Removed in 0.9.0.",
    )
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


def _hs_str(s) -> str:
    """A string as a Python literal (double-quoted, escaped)."""
    return json.dumps(str(s), ensure_ascii=False)


def _hs_side(sd, level: str) -> str:
    # A default single rule is just True and a style name stands alone;
    # anything carrying a weight or a colour needs the full value.
    plain_w = (sd.width or 15) == 15 and level not in ("default", "all")
    if sd.color is None and plain_w:
        return "True" if sd.style == "single" else _hs_str(sd.style)
    args = [_hs_str(sd.style)]
    if not plain_w:
        args.append(str(sd.width or 15))
    if sd.color is not None:
        args.append(f"color={_hs_str(sd.color)}")
    return f"rtf_border_line({', '.join(args)})"


def _hs_border(b, level: str) -> str:
    parts = [f"{s}={_hs_side(getattr(b, s), level)}"
             for s in ("top", "bottom", "left", "right") if getattr(b, s) is not None]
    return f"rtf_border({', '.join(parts)})"


def _hs_cell(cell: SpanCell, cn: list[str], col_spec, level: str) -> str:
    pos = (_hs_str(cn[cell.start]) if cell.start == cell.end
           else f"({_hs_str(cn[cell.start])}, {_hs_str(cn[cell.end])})")
    args = [pos, _hs_str(cell.label or "")]
    eff_align = col_spec[cell.start].header_align if col_spec and cell.start < len(col_spec) else None
    if cell.align is not None:
        args.append(f"align={_hs_str(cell.align)}")
    elif level in ("default", "all") and eff_align is not None:
        args.append(f"align={_hs_str(eff_align)}")
    for f in ("bold", "italic", "underline"):
        if getattr(cell, f):
            args.append(f"{f}=True")
        elif level == "all":
            args.append(f"{f}=False")
    if cell.border is not None:
        args.append(f"border={_hs_border(cell.border, level)}")
    return f"col_cell({', '.join(args)})"


def _hs_label_row(labels, cn: list[str]) -> str:
    n = min(len(labels), len(cn))
    return "{" + ", ".join(f"{_hs_str(cn[i])}: {_hs_str(labels[i])}" for i in range(n)) + "}"


def _hs_scaffold_row(ncol: int, stub_idx: list[int]) -> HeaderRow:
    # The stub columns stay single empty cells; the rest are bundled under one
    # empty spanning cell whose label the caller fills in.
    ns = [j for j in range(ncol) if j not in stub_idx]
    cells = [SpanCell(j, j, "") for j in stub_idx]
    if ns:
        cells.append(SpanCell(min(ns), max(ns), ""))
    return HeaderRow(kind="spanning", spans=sorted(cells, key=lambda c: c.start))


def _hs_col_header(rows, cn, col_spec, level: str, ind: str = "") -> str:
    parts = []
    for r in rows:
        if r.kind == "labels":
            parts.append(_hs_label_row(r.labels or [], cn))
        else:
            parts.append("[" + ", ".join(_hs_cell(c, cn, col_spec, level) for c in r.spans) + "]")
    inner = ind + "    "
    return ("rtf_col_header(\n" + inner + f",\n{inner}".join(parts) + ",\n" + ind + ")")


def _hs_align_line(col_spec, level: str) -> str | None:
    ha = [s.header_align or "" for s in col_spec]
    da = [s.align or "" for s in col_spec]
    if level == "explicit" and ha == da:
        return None
    return "align=[" + ", ".join(_hs_str(a) for a in ha) + "]"


def _hs_zone_line(border, level: str) -> str | None:
    if border is None:
        return None
    parts = [f"{z}={_hs_border(getattr(border, z), level)}"
             for z in ("header", "spanning") if getattr(border, z, None) is not None]
    if not parts:
        return None
    return f"tbl = style_zone(tbl, {', '.join(parts)})"


def rtf_header_source(x, level: str = "explicit", snippet: bool = True,
                      add_span_level: bool = False, stub=0) -> str:
    """Deparse a table's column header back to editable ``rtf_col_header()`` source.

    Renders the **current** column header of a finished :func:`rtftable` (or
    the first page of an :func:`as_rtftables` list) as Python source, addressed
    by **column name**, so you can copy it, edit the labels / spans, and
    re-apply it with :func:`set_col_header`.  It pairs with
    :func:`rtf_columns`, which lists the final column names.

    The output is name-based (cell positions are written as column names,
    which survive reordering), keeps the header's empty gap cells, and
    reproduces per-cell text decorations and borders.

    ``add_span_level=True`` previews **adding a second hierarchy level**: the
    ``stub`` column(s) stay as single (empty) cells and every other column is
    bundled under one empty spanning cell whose label you fill in -- a quick
    scaffold for turning a one-row header into a grouped, two-row header.

    Args:
        x: An :class:`RtfTable`, or a list of them (the first page is used).
        level: Verbosity of the emitted cells: ``"explicit"`` (default -- only
            fields that differ from the defaults), ``"default"`` (also each
            cell's effective ``align`` and the default border widths, but not
            the ``False`` decoration flags), or ``"all"`` (everything).
        snippet: When ``True`` (default), return statements that re-apply the
            header to a table named ``tbl``: a ``set_col_header()`` call that
            also reproduces the header text alignment (from ``col_spec``), and
            a ``style_zone()`` call for the header-related zone borders
            (``header`` / ``spanning``).  When ``False``, return the bare
            ``rtf_col_header(...)`` value.
        add_span_level: When ``True``, prepend a scaffold spanning row
            grouping the non-``stub`` columns.
        stub: Column(s) to keep un-spanned when ``add_span_level=True``:
            0-based position(s) and/or column name(s).  Default ``0`` (the
            first column, where ``as_rtftables(stub=)`` places the stub).

    Returns:
        The source, as one string (``print()`` it to see the line breaks).
    """
    if level not in ("explicit", "default", "all"):
        raise ValueError('`level` must be one of "explicit", "default", "all".')
    tbl = x[0] if isinstance(x, (list, tuple)) and x else x
    if not isinstance(tbl, RtfTable):
        raise TypeError("`rtf_header_source()` expects an RtfTable or a list of RtfTable "
                        "pages (as returned by as_rtftables()).")
    cn = list(tbl.column_names)
    col_spec = tbl.col_spec
    rows = list(tbl.col_header or []) or [HeaderRow(kind="labels", labels=cn)]

    if add_span_level:
        refs = stub if isinstance(stub, (list, tuple)) else [stub]
        stub_idx = []
        for r in refs:
            j = cn.index(r) if isinstance(r, str) and r in cn else r
            if isinstance(j, str) or not isinstance(j, int) or not 0 <= j < len(cn):
                raise ValueError(f"`stub` must be valid column name(s) or position(s) "
                                 f"in 0..{len(cn) - 1}.")
            stub_idx.append(j)
        rows = [_hs_scaffold_row(len(cn), stub_idx)] + rows

    if not snippet:
        return _hs_col_header(rows, cn, col_spec, level)
    hdr = _hs_col_header(rows, cn, col_spec, level, ind="    ")
    al = _hs_align_line(col_spec, level)
    out = "tbl = set_col_header(\n    tbl,\n    " + hdr + ",\n"
    if al is not None:
        out += "    " + al + ",\n"
    out += ")"
    zl = _hs_zone_line(tbl.border, level)
    if zl is not None:
        out += "\n" + zl
    return out
