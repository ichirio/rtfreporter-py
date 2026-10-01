"""paginate_cols() -- horizontal (column-wise) pagination.

Ported from ``R/paginate_cols.R``.  ``as_rtftables(split=)`` cuts ROWS; a
table wider than the page needs the other axis: cut COLUMNS and continue on
the next page, repeating the row-heading column(s) so each page stays
readable.  It works on BUILT tables, so the column positions mean the FINAL
printed columns (after ``drop_cols`` / a stub / a header of your own).

``page_order`` says which axis the page number advances along first:
``"across"`` (the column block advances, the row pages run inside it) or
``"down"``; in general, the axes ``"group"`` / ``"rows"`` / ``"cols"``
outermost first.

Relative widths are kept consistent across pages by scaling each page's
table width by ``share(page) / share(reference)`` -- page 1's share under
``width="fill"`` (the default), the whole table's under ``"keep"``.
"""

from __future__ import annotations

import warnings
from dataclasses import replace

from .table import HeaderRow, RtfTable, _normalize_col_header, _resolve_col

_PAGE_AXES = ("group", "rows", "cols")


def _resolve_page_axes(page_order) -> list[str]:
    if page_order is None or page_order == "across":
        return ["group", "cols", "rows"]
    if page_order == "down":
        return ["group", "rows", "cols"]
    ax = [page_order] if isinstance(page_order, str) else list(page_order)
    bad = [a for a in ax if a not in _PAGE_AXES]
    if bad:
        raise ValueError(f'`page_order`: "{bad[0]}" is not an axis.  Give the axes outermost '
                         'first, from "group", "rows", "cols" -- or "across" / "down" for '
                         "the two usual orders.")
    if len(set(ax)) != len(ax):
        raise ValueError("`page_order`: each axis may appear once.")
    return ax + [a for a in _PAGE_AXES if a not in ax]


def _page_row_keys(pages):
    """Each row page's group (a run of one page_group) and its place in it."""
    key = [p.page_group for p in pages]
    if all(k is None for k in key):
        runs = [list(range(len(pages)))]
    else:
        key = ["" if k is None else k for k in key]
        runs, start = [], 0
        for i in range(1, len(pages) + 1):
            if i == len(pages) or key[i] != key[start]:
                runs.append(list(range(start, i)))
                start = i
    g, r = [0] * len(pages), [0] * len(pages)
    for k, run in enumerate(runs, start=1):
        for pos, i in enumerate(run, start=1):
            g[i], r[i] = k, pos
    return g, r


def _indices(refs, names, arg) -> list[int]:
    if isinstance(refs, (str, int)):
        refs = [refs]
    out = []
    for ref in refs:
        try:
            out.append(_resolve_col(ref, names))
        except ValueError as exc:
            raise ValueError(f"`{arg}`: {exc}") from None
    return out


def _resolve_blocks(at, cols, by, names, carry) -> list[list[int]]:
    n0 = len(names)
    given = [k for k, v in (("at", at), ("cols", cols), ("by", by)) if v is not None]
    if len(given) > 1:
        raise ValueError(f"Give one of `at`, `cols` or `by`, not {' and '.join(given)}.")
    if by is not None:
        if isinstance(by, str):
            key = [n.split(by)[0] for n in names]
        elif len(by) == n0 and n0 != 1:
            key = [str(k) for k in by]
        else:
            raise ValueError("`by` must be a single separator found in the column names, "
                             f"or one key per column ({n0}).")
        key = [None if j in carry else k for j, k in enumerate(key)]
        keep = [j for j, k in enumerate(key) if k]
        if not keep:
            raise ValueError("`by` left no columns to split: every column is a carry column.")
        blocks, cur = [], [keep[0]]
        for a in keep[1:]:
            if key[a] != key[cur[-1]]:
                blocks.append(cur)
                cur = [a]
            else:
                cur.append(a)
        blocks.append(cur)
    elif cols is not None:
        if not isinstance(cols, (list, tuple)):
            raise ValueError("`cols` must be a list of column blocks (names or positions).")
        blocks = [sorted(set(_indices(b, names, "paginate_cols(cols)"))) for b in cols]
    else:
        if at is None or (isinstance(at, (list, tuple)) and not at):
            raise ValueError("One of `at` (the columns to cut before), `cols` or `by` is required.")
        idx = sorted(set(_indices(at, names, "paginate_cols(at)")))
        if any(i < 1 for i in idx):
            raise ValueError("`at` must name columns 1..ncol-1 (0-based) -- there is "
                             "nothing before column 0.")
        bounds = [0] + idx + [n0]
        blocks = [list(range(bounds[i], bounds[i + 1])) for i in range(len(bounds) - 1)]
    blocks = [[j for j in b if j not in carry] for b in blocks]
    blocks = [b for b in blocks if b]
    if not blocks:
        raise ValueError("`paginate_cols()` produced no column blocks: every column is a "
                         "carry (row-heading) column.")
    return blocks


def _reindex_header(header, keep):
    """A header on the kept columns: label rows sliced, spanning cells clipped,
    a row that loses every cell dropped (R ``.reindex_col_header()``)."""
    remap = {old: new for new, old in enumerate(keep)}
    out = []
    for row in header:
        if row.kind == "labels":
            out.append(HeaderRow(kind="labels", labels=[row.labels[j] for j in keep]))
            continue
        spans = []
        for sp in row.spans:
            covered = [remap[j] for j in range(sp.start, sp.end + 1) if j in remap]
            if covered:
                spans.append(replace(sp, start=min(covered), end=max(covered)))
        if spans:
            out.append(HeaderRow(kind="spanning", spans=spans))
    return out


def _share(tbl, keep, n0):
    if tbl.column_widths_twips is not None:
        return None
    rel = tbl.col_rel_width
    if rel is not None and len(rel) == n0 and sum(rel) > 0:
        return float(sum(rel[j] for j in keep))
    return float(len(keep))


def _reference(tbl, keeps, n0, width):
    if tbl.column_widths_twips is not None:
        return None
    if width == "fill":
        return _share(tbl, keeps[0], n0)
    rel = tbl.col_rel_width
    if rel is not None and len(rel) == n0 and sum(rel) > 0:
        return float(sum(rel))
    return float(n0)


def _keep_cols(tbl: RtfTable, keep, scale) -> RtfTable:
    n0 = tbl.ncols
    t = tbl.copy()
    t.column_names = [tbl.column_names[j] for j in keep]
    t.rows = [[r[j] if j < len(r) else None for j in keep] for r in tbl.rows]
    n_span_before = tbl.spanning_rows
    head = _reindex_header(tbl.col_header[:n_span_before], keep)
    t.col_header = head + _reindex_header(tbl.col_header[n_span_before:], keep)
    t.spanning_rows = len(head)
    t.col_spec = [tbl.col_spec[j] for j in keep]
    if tbl.col_rel_width is not None and len(tbl.col_rel_width) == n0:
        t.col_rel_width = [tbl.col_rel_width[j] for j in keep]
    if tbl.column_widths_twips is not None and len(tbl.column_widths_twips) == n0:
        t.column_widths_twips = [tbl.column_widths_twips[j] for j in keep]
    rt = [keep.index(j) for j in (tbl.row_title or [0]) if j in keep]
    t.row_title = rt or [0]
    if tbl.decimal_split:
        dc = [keep.index(j) for j in tbl.decimal_split["cols"] if j in keep]
        t.decimal_split = {**tbl.decimal_split, "cols": dc} if dc else None
    if tbl.cell_styles is not None:
        t.cell_styles = [
            None if cs is None else {
                k: [v[j] for j in keep] if isinstance(v, list) and len(v) == n0 else v
                for k, v in cs.items()}
            for cs in tbl.cell_styles]
    if scale is not None and abs(scale - 1) > 1.5e-8:
        if tbl.table_width_twips is not None:
            t.table_width_twips = int(round(tbl.table_width_twips * scale))
        else:
            pct = tbl.table_width_pct_of_writable if tbl.table_width_pct_of_writable is not None else 1
            t.table_width_pct_of_writable = float(pct) * scale
    return t


def _two_level_header(names, sep, carry_pos):
    """``col_header="names"``: the ``by`` key above, the rest below; a carry
    column keeps its own name under no spanning cell."""
    from .table import col_cell

    parts = [n.split(sep) for n in names]
    top = [p[0] for p in parts]
    bot = [n if j in carry_pos else p[-1] for j, (n, p) in enumerate(zip(names, parts, strict=True))]
    data_pos = [j for j in range(len(names)) if j not in carry_pos]
    cells = []
    run = []
    for j in data_pos:
        if run and top[j] != top[run[-1]]:
            cells.append(col_cell((min(run), max(run)), top[run[0]]))
            run = []
        run.append(j)
    if run:
        cells.append(col_cell((min(run), max(run)), top[run[0]]))
    return cells, bot


def paginate_cols(x, at=None, cols=None, by=None, carry=None, col_header=None,
                  allow_span_break: bool = True, width: str = "fill", page_order="across"):
    """Split a table (or its pages) by columns, repeating the row headings.

    Args:
        x: An :class:`RtfTable`, or a list of pages (from
            :func:`~rtfreporter.as_rtftables`); every page must have the same
            columns.
        at: The columns to cut BEFORE (0-based positions or names).
        cols: Explicit column blocks, a list of lists.
        by: A separator in the column names (a block per run of the part
            before it, e.g. ``"____"``), or one key per column.  Give one of
            ``at`` / ``cols`` / ``by``.
        carry: The columns repeated on every page; ``None`` = the table's
            row-title columns.
        col_header: A header written for the WHOLE table, sliced per page -- or
            ``"names"``, the two-level header the column names carry (needs
            ``by`` to be the separator).
        allow_span_break: ``False`` refuses a cut inside a spanning header cell.
        width: ``"fill"`` (default): page 1 fills the sheet and a column keeps
            its width on every page; ``"keep"``: every column keeps the width
            it had in the whole table.
        page_order: ``"across"`` (default), ``"down"``, or the axes
            ``"group"`` / ``"rows"`` / ``"cols"`` outermost first.

    Returns:
        A list of :class:`RtfTable` pages.
    """
    if width not in ("fill", "keep"):
        raise ValueError('`width` must be "fill" or "keep".')
    axes = _resolve_page_axes(page_order)
    pages = [x] if isinstance(x, RtfTable) else list(x)
    if not pages:
        return []
    bad = [i for i, p in enumerate(pages) if not isinstance(p, RtfTable)]
    if bad:
        raise TypeError("`paginate_cols()` on a list expects every element to be an RtfTable "
                        f"(as returned by as_rtftables()); element {bad[0]} is "
                        f"'{type(pages[bad[0]]).__name__}'.")
    names = pages[0].column_names
    n0 = len(names)
    for i, p in enumerate(pages):
        if p.ncols != n0:
            raise ValueError(f"`paginate_cols()` needs every page to have the same columns; "
                             f"page 0 has {n0} and page {i} has {p.ncols}.")

    carry_idx = (sorted(set(pages[0].row_title or [0])) if carry is None
                 else sorted(set(_indices(carry, names, "paginate_cols(carry)"))))
    blocks = _resolve_blocks(at, cols, by, names, set(carry_idx))

    hdr_names = isinstance(col_header, str) and col_header == "names"
    if hdr_names:
        if not isinstance(by, str):
            raise ValueError('`col_header="names"` needs `by` to be the separator in the '
                             'column names (e.g. by="____").')
    elif col_header is not None:
        from .table import check_col_header_width

        check_col_header_width(col_header, n0, "paginate_cols(col_header)")
        col_header = _normalize_col_header(col_header, n0, names)

    if not allow_span_break:
        bounds = [min(b) for b in blocks[1:]]
        for p in pages:
            for row in p.col_header:
                if row.kind != "spanning":
                    continue
                for sp in row.spans:
                    hit = [b for b in bounds if sp.start < b <= sp.end]
                    if hit:
                        raise ValueError(
                            f"`paginate_cols()` would break the spanning header cell "
                            f"'{sp.label}' (columns {sp.start}..{sp.end}) at column "
                            f"{hit[0]}. Move the cut to a group boundary, or pass "
                            "allow_span_break=True.")

    keeps = [sorted(set(carry_idx) | set(b)) for b in blocks]
    ref_sh = _reference(pages[0], keeps, n0, width)
    scales = ([None] * len(keeps) if ref_sh is None or ref_sh <= 0
              else [_share(pages[0], k, n0) / ref_sh for k in keeps])
    over = [i + 1 for i, s in enumerate(scales) if s is not None and s > 1 + 1e-9]
    if over and width == "fill":
        one = len(over) == 1
        warnings.warn(
            f"`paginate_cols()`: column block{'' if one else 's'} "
            f"{', '.join(str(o) for o in over)} total{'s' if one else ''} more than block 1, "
            f"so {'its' if one else 'their'} page{' is' if one else 's are'} wider than the "
            'sheet. Put the widest block first, or use width="keep".', stacklevel=2)

    g, r = _page_row_keys(pages)
    pairs = [(bi, i) for i in range(len(pages)) for bi in range(len(keeps))]
    key = {"group": lambda p: g[p[1]], "rows": lambda p: r[p[1]], "cols": lambda p: p[0]}
    order = sorted(range(len(pairs)),
                   key=lambda n: (*[key[a](pairs[n]) for a in axes], n))
    out = []
    for n in order:
        bi, i = pairs[n]
        page = _keep_cols(pages[i], keeps[bi], scales[bi])
        if hdr_names:
            from .post_hoc import set_col_header

            pos = [keeps[bi].index(j) for j in keeps[bi] if j in carry_idx]
            cells, bot = _two_level_header([names[j] for j in keeps[bi]], by, pos)
            page = set_col_header(page, cells, bot)
        elif col_header is not None:
            page.col_header = _reindex_header(col_header, keeps[bi])
            page.spanning_rows = 0
        out.append(page)
    return out
