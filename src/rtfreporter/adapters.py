"""Input adapters and pagination: ``as_rtftable`` / ``as_rtftables``.

Ported (Pythonically, MVP scope) from ``R/as_rtftable.R``, ``R/as_rtftables.R``
and ``R/paginate.R``.  Turns a pandas DataFrame (core), a polars DataFrame, a
``great_tables`` GT object, or a plain dict/records into one or more
:class:`~rtfreporter.table.RtfTable` page objects, applying:

* spanning column headers reconstructed from delimited column names,
* an indented clinical *stub* built from hierarchy columns,
* row sorting, dropped carrier columns, repeat-value collapsing,
* pagination (by rows, by group, or one page per value) with ``(Cont.)``
  continuation markers, and blank separator rows between groups.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from . import gt_adapter
from .blank_rows import blank_rows_by_change
from .table import HeaderRow, RtfTable, SpanCell, rtftable

_DEFAULT_HEADER_SEPS = ("____", "___tlang_delim___")


# ============================================================================
#  Input coercion
# ============================================================================


@dataclass
class _Coerced:
    """Normalised input: a body plus any metadata channels an adapter read."""

    column_names: list[str]
    rows: list[list[Any]]
    auto_header: list[HeaderRow] | None = None
    titles: list[str] | None = None
    footnotes: list[str] | None = None
    col_spec: list[dict] | None = None
    cell_styles: list | None = None
    col_rel_width: list[float] | None = None
    column_widths_twips: list[int] | None = None


def _coerce_input(x, read_meta, header_sep) -> _Coerced:
    """Normalise a supported input to a :class:`_Coerced` record.

    ``auto_header`` is a list of :class:`HeaderRow` reconstructed from delimited
    names (or read from a GT object), or ``None`` when a flat header suffices.
    """
    if gt_adapter.is_gt(x):
        res = gt_adapter.gt_to_result(x, read_meta)
        return _Coerced(
            column_names=res.column_names,
            rows=res.rows,
            auto_header=res.col_header,
            titles=res.titles,
            footnotes=res.footnotes,
            col_spec=res.col_spec,
            cell_styles=res.cell_styles,
            col_rel_width=res.col_rel_width,
            column_widths_twips=res.column_widths_twips,
        )

    if type(x).__module__.split(".")[0] == "polars":  # polars (no pyarrow needed)
        data = x.to_dict(as_series=False)
        column_names = list(data.keys())
        n = max((len(v) for v in data.values()), default=0)
        rows = [[data[c][i] if i < len(data[c]) else None for c in column_names]
                for i in range(n)]
        rows = [[_clean(v) for v in r] for r in rows]
        auto_header = _split_names_to_col_header(column_names, header_sep)
        return _Coerced(column_names, rows, auto_header)

    if hasattr(x, "columns") and hasattr(x, "itertuples"):  # pandas
        column_names, rows = _pandas_to_rows(x)
    elif isinstance(x, dict):
        column_names = list(x.keys())
        cols = [list(v) for v in x.values()]
        n = max((len(c) for c in cols), default=0)
        rows = [[cols[j][i] if i < len(cols[j]) else None for j in range(len(column_names))]
                for i in range(n)]
    elif isinstance(x, (list, tuple)) and x and isinstance(x[0], dict):
        column_names = []
        for rec in x:
            for k in rec:
                if k not in column_names:
                    column_names.append(k)
        rows = [[rec.get(k) for k in column_names] for rec in x]
    else:
        raise TypeError(
            "as_rtftables() supports pandas/polars DataFrames, great_tables GT "
            "objects, dicts of columns, or lists of row dicts."
        )

    auto_header = _split_names_to_col_header(column_names, header_sep)
    return _Coerced(column_names, rows, auto_header)


def _clean(v):
    import math

    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return v


def _pandas_to_rows(df):
    names = [str(c) for c in df.columns]
    rows = [[_clean(v) for v in rec] for rec in df.itertuples(index=False, name=None)]
    return names, rows


# ============================================================================
#  Spanning header from delimited names
# ============================================================================


def _split_names_to_col_header(names: list[str], seps) -> list[HeaderRow] | None:
    if not seps or not names:
        return None
    seps = [s for s in ([seps] if isinstance(seps, str) else list(seps)) if s]
    if not seps:
        return None
    seps = sorted(seps, key=len, reverse=True)

    import re

    pattern = "|".join(re.escape(s) for s in seps)
    segs = [re.split(pattern, name) for name in names]
    depth = max(len(s) for s in segs)
    if depth <= 1:
        return None

    ncol = len(names)
    # Bottom-align each column's segments; None = "no cell", "" = blank label.
    M = [[None] * ncol for _ in range(depth)]
    for j, s in enumerate(segs):
        for r, seg in enumerate(s):
            M[depth - len(s) + r][j] = seg

    def same(a, b):
        return (a is None and b is None) or (a is not None and b is not None and a == b)

    header_rows: list[HeaderRow] = []
    for r in range(depth - 1):
        spans = []
        j = 0
        while j < ncol:
            k = j
            while (
                k + 1 < ncol
                and same(M[r][k + 1], M[r][j])
                and [M[x][k + 1] for x in range(r)] == [M[x][j] for x in range(r)]
            ):
                k += 1
            label = "" if M[r][j] is None else M[r][j]
            spans.append(SpanCell(start=j, end=k, label=label))
            j = k + 1
        header_rows.append(HeaderRow(kind="spanning", spans=spans))

    bottom = ["" if M[depth - 1][j] is None else M[depth - 1][j] for j in range(ncol)]
    header_rows.append(HeaderRow(kind="labels", labels=bottom))
    return header_rows


# ============================================================================
#  Column resolution helpers
# ============================================================================


def _resolve_index(ref, names: list[str]) -> int:
    if isinstance(ref, str):
        if ref not in names:
            raise ValueError(f"Unknown column name {ref!r}.")
        return names.index(ref)
    idx = int(ref)
    if idx < 0 or idx >= len(names):
        raise ValueError(f"Column index {idx} out of range.")
    return idx


def _resolve_indices(refs, names) -> list[int]:
    if refs is None:
        return []
    if isinstance(refs, (str, int)):
        refs = [refs]
    return [_resolve_index(r, names) for r in refs]


# ============================================================================
#  Stub (indented hierarchy column)
# ============================================================================


def _apply_stub(column_names, rows, stub_cols, stub_label, stub_indent):
    """Merge ``stub_cols`` (outer->inner) into one indented leading stub column.

    Each non-leaf level emits its own un-indented label row when its value
    changes; the leaf level becomes the indented stub of each data row.
    Returns ``(new_names, new_rows)``.
    """
    idxs = _resolve_indices(stub_cols, column_names)
    if not idxs:
        return column_names, rows
    keep = [j for j in range(len(column_names)) if j not in idxs]
    new_names = [stub_label or ""] + [column_names[j] for j in keep]
    n_levels = len(idxs)

    new_rows = []
    prev = [None] * n_levels
    for row in rows:
        levels = [row[j] for j in idxs]
        # Emit header rows for changed non-leaf levels.
        for lv in range(n_levels - 1):
            if levels[lv] != prev[lv] or any(
                levels[x] != prev[x] for x in range(lv)
            ):
                stub_text = _indent(levels[lv], lv, stub_indent)
                new_rows.append([stub_text] + [None] * len(keep))
        leaf_indent = (n_levels - 1) if n_levels > 1 else 0
        stub_text = _indent(levels[-1], leaf_indent, stub_indent)
        new_rows.append([stub_text] + [row[j] for j in keep])
        prev = levels
    return new_names, new_rows


def _indent(value, level: int, stub_indent: int) -> str:
    text = "" if value is None else str(value)
    if level <= 0:
        return text
    return " " * (level * stub_indent) + text


# ============================================================================
#  Sorting / collapse
# ============================================================================


def _sort_rows(rows, sort_idx, sort_desc):
    if not sort_idx:
        return rows
    order = list(range(len(rows)))
    for k in reversed(range(len(sort_idx))):
        col = sort_idx[k]
        desc = sort_desc[k] if sort_desc and k < len(sort_desc) else False
        order.sort(key=lambda i: _sort_key(rows[i][col]), reverse=desc)
    return [rows[i] for i in order]


def _sort_key(v):
    if v is None:
        return (1, "")
    if isinstance(v, (int, float)):
        return (0, v)
    return (0, str(v))


def _collapse_repeats(rows, collapse_idx):
    if not collapse_idx:
        return rows
    out = [list(r) for r in rows]
    prev = {c: object() for c in collapse_idx}
    for row in out:
        for c in collapse_idx:
            if row[c] == prev[c]:
                row[c] = ""
            else:
                prev[c] = row[c]
    return out


# ============================================================================
#  Pagination
# ============================================================================


def _paginate(rows, group_keys, split, split_rows, max_rows, min_group_rows, cont_label,
              group_idx=None):
    """Return a list of ``(page_rows, page_name)`` tuples."""
    n = len(rows)
    cont_col = group_idx if group_idx is not None else 0
    if split == "none":
        return [(rows, None)]

    if split == "rows":
        cuts = _row_cut_points(split_rows, max_rows, n)
        pages = []
        start = 0
        for cut in cuts + [n]:
            if cut > start:
                pages.append((rows[start:cut], None))
                start = cut
        return pages or [(rows, None)]

    if split == "by_value":
        pages = []
        seen_order = []
        buckets: dict[Any, list] = {}
        for i, key in enumerate(group_keys):
            if key not in buckets:
                buckets[key] = []
                seen_order.append(key)
            buckets[key].append(rows[i])
        for key in seen_order:
            grp = buckets[key]
            name = "" if key is None else str(key)
            if max_rows and len(grp) > max_rows:
                pages.extend(_split_group_rows(grp, max_rows, name, cont_label, group_col=cont_col))
            else:
                pages.append((grp, name))
        return pages

    if split in ("group_safe", "group_force"):
        if not max_rows:
            raise ValueError(f'`max_rows` is required for split="{split}".')
        return _paginate_groups(
            rows, group_keys, max_rows, split == "group_force", cont_label, cont_col
        )

    raise ValueError(f"Unknown split strategy {split!r}.")


def _row_cut_points(split_rows, max_rows, n):
    if split_rows is not None:
        if isinstance(split_rows, int):
            step = split_rows
            return list(range(step, n, step))
        return sorted(int(c) for c in split_rows if 0 < int(c) < n)
    if max_rows:
        return list(range(max_rows, n, max_rows))
    return []


def _group_runs(group_keys):
    runs = []
    start = 0
    for i in range(1, len(group_keys) + 1):
        if i == len(group_keys) or group_keys[i] != group_keys[start]:
            runs.append((start, i))  # [start, end)
            start = i
    return runs


def _paginate_groups(rows, group_keys, max_rows, force, cont_label, cont_col):
    runs = _group_runs(group_keys)
    pages = []
    current: list = []
    for (s, e) in runs:
        grp = rows[s:e]
        if len(grp) > max_rows and force:
            if current:
                pages.append((current, None))
                current = []
            name = str(group_keys[s]) if group_keys[s] is not None else ""
            pages.extend(_split_group_rows(grp, max_rows, name, cont_label, group_col=cont_col))
            continue
        if current and len(current) + len(grp) > max_rows:
            pages.append((current, None))
            current = []
        current.extend(grp)
    if current:
        pages.append((current, None))
    return pages


def _split_group_rows(grp, max_rows, name, cont_label, group_col):
    """Split one oversized group across pages, marking continuations."""
    pages = []
    start = 0
    first = True
    while start < len(grp):
        chunk = [list(r) for r in grp[start : start + max_rows]]
        if not first and group_col is not None and chunk:
            cell = chunk[0][group_col]
            chunk[0][group_col] = (str(cell) if cell not in (None, "") else name) + cont_label
        page_name = name if first else (name + cont_label if name else None)
        pages.append((chunk, page_name))
        start += max_rows
        first = False
    return pages


# ============================================================================
#  Public entry points
# ============================================================================


def as_rtftables(
    x,
    *,
    read_meta=True,
    split="none",
    split_rows=None,
    max_rows: int | None = None,
    group_col=None,
    group_by: str = "auto",
    sort_by=None,
    sort_desc=None,
    cont_label: str = " (Cont.)",
    min_group_rows: int = 2,
    blank_rows=None,
    blank_row_first: bool = False,
    blank_row_end: bool = False,
    count_blank_rows: bool = False,
    align_count_pct: bool = False,
    cell_format=None,
    collapse_repeats=None,
    drop_cols=None,
    stub_vars=None,
    stub_label=None,
    stub_indent: int = 4,
    stub_group_summary: str = "empty",
    header_sep=_DEFAULT_HEADER_SEPS,
    auto_width: bool = False,
    table_width_twips=None,
    border="tfl",
    style=None,
    **table_kwargs,
) -> list[RtfTable]:
    """Convert tabular input into a list of paginated :class:`RtfTable` pages.

    Args:
        x: A pandas/polars DataFrame, a ``great_tables`` GT object, a dict of
            columns, or a list of row dicts.
        read_meta: For a great_tables ``GT`` object, which metadata channels to
            read: ``True`` (all), ``False`` (none -- clean body only), or a list
            of :data:`~rtfreporter.gt_adapter.GT_META_TOKENS`
            (``"col_header"``, ``"alignment"``, ``"spanning"``, ``"widths"``,
            ``"titles"``, ``"footnotes"``, ``"styles"``).  Ignored for
            plain-frame input.
        split: ``"none"`` (default), ``"rows"``, ``"by_value"``,
            ``"group_safe"``, or ``"group_force"`` -- or a custom split
            **callable** (the R ``split=<function>`` hook, see
            :mod:`rtfreporter.pagination`): a function taking a single
            :class:`~rtfreporter.pagination.Frame` and returning a list of
            :class:`~rtfreporter.pagination.Frame` (one per page).  The
            ``page_split_*`` factory functions return such callables.
        split_rows: For ``split="rows"`` -- an int page size or explicit cut
            positions.
        max_rows: Max data rows per page (required by the group splits).
        group_col: The grouping column (index or name) for group/value splits,
            ``collapse_repeats`` grouping, and between-group blank rows.
        group_by: How a group boundary is detected on ``group_col`` -- one of
            ``"auto"`` (default), ``"indent"``, ``"value"``, ``"filled"``.  Only
            ``"auto"`` (value-change detection) is implemented; the others raise
            ``NotImplementedError``.
        sort_by, sort_desc: Column(s) to sort rows by, and per-column descending
            flags, applied before pagination.
        count_blank_rows: When ``True``, blank separator rows count toward
            ``max_rows`` during pagination.  Not yet implemented (raises).
        align_count_pct: When ``True``, realign ``count (pct)`` cells to a
            uniform width in every column except the first (see
            :func:`~rtfreporter.realign_count_pct`).  Applied before pagination;
            superseded by ``cell_format`` when both are given.
        cell_format: An optional per-column re-formatter -- a single callable
            (applied to columns ``1..n-1``) or a list of callables taken
            positionally.  Each takes one column (a list) and returns a list of
            the same length; see :func:`~rtfreporter.fmt_count_paren`.
        stub_group_summary: Forwarded to the stub builder -- ``"empty"`` (default)
            or ``"parent"``.  Only ``"empty"`` is implemented.
        auto_width: When ``True``, size columns to their widest content.  Not yet
            implemented (raises).
        table_width_twips: Total table width in twips, forwarded to
            :func:`~rtfreporter.rtftable`.
        style: A shared table style forwarded to :func:`~rtfreporter.rtftable`.
        cont_label: Continuation marker appended to a group that spills over.
        blank_rows: Blank-row spec applied per page (int positions or a
            :mod:`~rtfreporter.blank_rows` spec).  If ``None`` and ``group_col``
            is set, blanks are inserted where the group value changes.
        blank_row_first, blank_row_end: Add a blank row at the top/bottom of
            each page.
        collapse_repeats: Column(s) whose repeated consecutive values are
            blanked (per page).
        drop_cols: Carrier column(s) used for grouping/sorting but not printed.
        stub_vars: Hierarchy columns (outer->inner) merged into one indented
            clinical stub column (the R ``stub_vars`` argument; the standalone
            :func:`~rtfreporter.stub_cols` helper is a separate function).
        stub_label, stub_indent: Stub column header, and per-level indent (spaces).
        header_sep: Delimiters used to reconstruct spanning headers from names.
        border: Passed to :func:`~rtfreporter.rtftable`.
        **table_kwargs: Extra keyword arguments forwarded to
            :func:`~rtfreporter.rtftable` for every page.

    Returns:
        A list of :class:`RtfTable` objects, one per page.  When a page carries
        a name (group value), it is stored on the table's ``name`` attribute.
    """
    # Guard the not-yet-implemented R argument paths with a clear error rather
    # than silently ignoring them.
    if group_by != "auto":
        raise NotImplementedError(
            f"as_rtftables(group_by={group_by!r}) is not implemented; only "
            "'auto' (value-change detection) is supported."
        )
    if count_blank_rows:
        raise NotImplementedError(
            "as_rtftables(count_blank_rows=True) is not implemented."
        )
    if auto_width:
        raise NotImplementedError("as_rtftables(auto_width=True) is not implemented.")
    if stub_group_summary != "empty":
        raise NotImplementedError(
            f"as_rtftables(stub_group_summary={stub_group_summary!r}) is not "
            "implemented; only 'empty' is supported."
        )
    if table_width_twips is not None:
        table_kwargs = {**table_kwargs, "table_width_twips": table_width_twips}
    if style is not None:
        table_kwargs = {**table_kwargs, "style": style}

    if isinstance(x, (list, tuple)) and not (x and isinstance(x[0], dict)):
        # A plain list of frames -> concatenate the conversions.
        out: list[RtfTable] = []
        for item in x:
            out.extend(
                as_rtftables(
                    item, read_meta=read_meta, split=split, split_rows=split_rows,
                    max_rows=max_rows, group_col=group_col, sort_by=sort_by,
                    sort_desc=sort_desc, cont_label=cont_label,
                    min_group_rows=min_group_rows, blank_rows=blank_rows,
                    blank_row_first=blank_row_first, blank_row_end=blank_row_end,
                    align_count_pct=align_count_pct,
                    collapse_repeats=collapse_repeats, drop_cols=drop_cols,
                    stub_vars=stub_vars, stub_label=stub_label,
                    stub_indent=stub_indent, header_sep=header_sep,
                    border=border, **table_kwargs,
                )
            )
        return out

    coerced = _coerce_input(x, read_meta, header_sep)
    column_names = coerced.column_names
    rows = coerced.rows
    auto_header = coerced.auto_header
    titles = coerced.titles
    footnotes = coerced.footnotes

    # A metadata-rich source (great_tables) may bring per-cell styles + column
    # specs the plain-frame path never produces.  cell_styles are carried
    # *with* their row (appended as a trailing element) so sorting and
    # pagination keep every style aligned to its cell; they are split back off
    # per page below.
    carry_styles = coerced.cell_styles is not None
    if carry_styles:
        if stub_vars is not None or drop_cols is not None:
            raise ValueError(
                "`stub_vars` / `drop_cols` are not supported for great_tables "
                "input; the GT adapter already reshapes the body (row groups "
                "become an indented stub and hidden columns are dropped)."
            )
        rows = [list(r) + [coerced.cell_styles[i]] for i, r in enumerate(rows)]

    # Stub: reshape BEFORE any index-based resolution below.
    if stub_vars is not None:
        column_names, rows = _apply_stub(column_names, rows, stub_vars, stub_label, stub_indent)
        auto_header = None  # names changed; a flat header is used

    # Resolve carrier / grouping / sort columns on the (possibly reshaped) body.
    drop_idx = _resolve_indices(drop_cols, column_names)
    group_idx = _resolve_index(group_col, column_names) if group_col is not None else None
    sort_idx = _resolve_indices(sort_by, column_names)
    collapse_idx = _resolve_indices(collapse_repeats, column_names)

    if sort_idx:
        rows = _sort_rows(rows, sort_idx, sort_desc)

    # Optional cell-format pass BEFORE pagination, column-by-column, so every
    # page inherits the cleaned-up cells.  `cell_format` takes precedence;
    # `align_count_pct=True` is the shorthand for the built-in "n (xx.x)"
    # realigner (see R paginate()).
    if cell_format is not None or align_count_pct:
        from .format_count_pct import (
            apply_cell_format,
            realign_count_pct_df,
            resolve_cell_format,
        )

        rows = [list(r) for r in rows]
        if cell_format is not None:
            fl = resolve_cell_format(cell_format, len(column_names))
            if fl is not None:
                apply_cell_format(rows, column_names, fl)
        elif align_count_pct:
            realign_count_pct_df(rows, column_names)

    group_keys = [row[group_idx] for row in rows] if group_idx is not None else [None] * len(rows)

    if callable(split):
        # Custom split hook (or a page_split_* factory passed directly): build a
        # Frame, run the split, and normalise the returned frames to the same
        # ``(rows, page_name)`` shape the string strategies produce.
        from .pagination import Frame, run_split

        frames = run_split(
            split,
            Frame(column_names, rows),
            split_rows=split_rows,
            max_rows=max_rows,
            group_col=group_col,
            group_by=group_by,
            cont_label=cont_label,
            min_group_rows=min_group_rows,
        )
        pages = [(f.rows, f.name) for f in frames]
    else:
        pages = _paginate(
            rows, group_keys, split, split_rows, max_rows, min_group_rows, cont_label, group_idx
        )

    # Per-page blank spec: explicit blank_rows wins; else derive from group_col.
    page_blank = blank_rows
    if page_blank is None and group_idx is not None and not callable(split) and split not in ("by_value",):
        page_blank = blank_rows_by_change(group_idx)

    from .table import _resolve_blank_rows

    out: list[RtfTable] = []
    for page_rows, page_name in pages:
        prows = _collapse_repeats(page_rows, collapse_idx) if collapse_idx else [list(r) for r in page_rows]

        # Resolve blank positions on the FULL page body (index-stable even when
        # the grouping column is later dropped) into plain integer positions.
        blank_positions = _resolve_blank_rows(page_blank, column_names, page_rows)
        if blank_row_first:
            blank_positions = sorted(set(blank_positions) | {0})
        if blank_row_end:
            blank_positions = sorted(set(blank_positions) | {len(page_rows)})

        # Split the trailing cell-style element back off each row.
        page_cell_styles = None
        if carry_styles:
            page_cell_styles = [r[-1] for r in prows]
            prows = [r[:-1] for r in prows]

        # Drop carrier columns from the printed body + reindex the header.
        if drop_idx:
            prows, printed_names, printed_header = _drop_columns(
                prows, column_names, auto_header, drop_idx
            )
        else:
            printed_names, printed_header = column_names, auto_header

        col_header = printed_header if printed_header is not None else None
        kwargs = dict(table_kwargs)
        if col_header is not None and "col_header" not in kwargs:
            kwargs["col_header"] = col_header
        if coerced.col_spec is not None and "col_spec" not in kwargs:
            kwargs["col_spec"] = coerced.col_spec
        if coerced.col_rel_width is not None and "col_rel_width" not in kwargs:
            kwargs["col_rel_width"] = coerced.col_rel_width
        if coerced.column_widths_twips is not None and "column_widths_twips" not in kwargs:
            kwargs["column_widths_twips"] = coerced.column_widths_twips
        if page_cell_styles is not None:
            kwargs["cell_styles"] = page_cell_styles

        tbl = rtftable(
            (printed_names, prows),
            border=border,
            _blank_positions=blank_positions or None,
            **kwargs,
        )
        if titles is not None:
            tbl.titles = titles
        if footnotes is not None:
            tbl.footnotes = footnotes
        if page_name:
            tbl.name = page_name
        out.append(tbl)
    return out


def _drop_columns(rows, names, header, drop_idx):
    keep = [j for j in range(len(names)) if j not in drop_idx]
    new_names = [names[j] for j in keep]
    new_rows = [[r[j] for j in keep] for r in rows]
    new_header = _reindex_header(header, keep) if header is not None else None
    return new_rows, new_names, new_header


def _reindex_header(header, keep):
    remap = {old: new for new, old in enumerate(keep)}
    out = []
    for row in header:
        if row.kind == "labels":
            out.append(HeaderRow(kind="labels", labels=[row.labels[j] for j in keep]))
        else:
            spans = []
            for sp in row.spans:
                covered = [j for j in range(sp.start, sp.end + 1) if j in remap]
                if covered:
                    spans.append(
                        replace(sp, start=remap[covered[0]], end=remap[covered[-1]])
                    )
            out.append(HeaderRow(kind="spanning", spans=spans))
    return out


def as_rtftable(x, *, read_meta=True, border="tfl", **kwargs) -> RtfTable:
    """Convert a single table input to one :class:`RtfTable` (no pagination).

    A convenience wrapper over :func:`as_rtftables` with ``split="none"`` that
    returns the single page.
    """
    pages = as_rtftables(x, read_meta=read_meta, split="none", border=border, **kwargs)
    if len(pages) != 1:
        raise ValueError(
            f"as_rtftable() produced {len(pages)} pages; use as_rtftables()."
        )
    return pages[0]
