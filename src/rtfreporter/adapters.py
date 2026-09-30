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

#: Writable width of the factory page (landscape Letter, 0.75in margins).
_DEFAULT_WRITABLE_TWIPS = (11 - 2 * 0.75) * 1440


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
    # No label: the stub's columns named outer to inner, as R's stub_cols().
    if stub_label is None:
        stub_label = " / ".join(str(column_names[j]) for j in idxs)
    new_names = [stub_label] + [column_names[j] for j in keep]
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


#: Stub indents use a NON-BREAKING space, as R does.  A plain space is a wrap
#: opportunity and may be collapsed by the viewer, so the indent would not
#: survive; U+00A0 does.  It is also what group_by="indent" detection expects.
_STUB_INDENT_CHAR = chr(0xA0)


def _indent(value, level: int, stub_indent: int) -> str:
    text = "" if value is None else str(value)
    if level <= 0:
        return text
    return _STUB_INDENT_CHAR * (level * stub_indent) + text


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
              group_idx=None, group_mode=None, edge_first=False, edge_end=False,
              blank_ignore=()):
    """Return a list of ``(page_rows, page_name)`` tuples.

    ``group_mode`` is the resolved ``group_by`` (``"value"`` / ``"indent"`` /
    ``"filled"``; ``None`` reads as ``"value"``).  A VALUE-based group is a
    key, so under ``split="by_value"`` its page gathers every row that has it,
    scattered or not, and those rows keep the order they were in (R #485).  An
    indent / filled group is a POSITION in the body -- there is no key to
    gather by -- so it stays a run.
    """
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
        # One page per group; a group longer than max_rows is force-split the
        # way group_force splits it, and every page keeps the group's name.
        if group_idx is not None:
            _, labels, headers = _group_info(rows, group_idx, group_mode)
        else:
            labels, headers = [""] * n, [i == 0 for i in range(n)]
        groups: list[tuple[Any, list[int]]] = []
        if group_mode in (None, "value"):
            buckets: dict[Any, list[int]] = {}
            for i, key in enumerate(group_keys):
                if key not in buckets:
                    buckets[key] = []
                    groups.append((key, buckets[key]))
                buckets[key].append(i)
        else:
            for s_, e_ in _group_runs(group_keys):
                groups.append((group_keys[s_], list(range(s_, e_))))
        pages = []
        for g, (key, idx) in enumerate(groups, start=1):
            name = str(key) if key not in (None, "") else f"group_{g}"
            grp = [rows[i] for i in idx]
            if max_rows and len(grp) > max_rows:
                sub = _split_group_force(
                    grp, ([g] * len(idx), [labels[i] for i in idx],
                          [headers[i] for i in idx]),
                    max_rows, cont_label, cont_col, min_group_rows,
                )
                pages.extend((p, name) for p in sub)
            else:
                pages.append((grp, name))
        return pages

    if split in ("group_safe", "group_force"):
        if not max_rows:
            raise ValueError(f'`max_rows` is required for split="{split}".')
        info = _group_info(rows, group_idx, group_mode)
        fn = _split_group_force if split == "group_force" else _split_group_safe
        pages = fn(rows, info, max_rows, cont_label, cont_col, min_group_rows,
                   edge_first=edge_first, edge_end=edge_end, blank_ignore=blank_ignore)
        return [(p, None) for p in pages]

    raise ValueError(f"Unknown split strategy {split!r}.")


def _row_cut_points(split_rows, max_rows, n):
    """Row indices at which a new page begins.

    ``split_rows`` is a list of explicit **cut positions**, or a single
    position -- NOT a page size.  This matches R: on 7 rows,
    ``split_rows = 3`` (R, 1-based) cuts once, giving pages of 2 and 5 rows.
    Positions are 0-based here, so the equivalent call is ``split_rows = 2``.
    Use ``max_rows`` when you want a fixed page size.
    """
    if split_rows is not None:
        positions = [split_rows] if isinstance(split_rows, int) else list(split_rows)
        return sorted({int(c) for c in positions if 0 < int(c) < n})
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


def _group_info(rows, group_idx, mode):
    """Per-row group id, label and header flag (R's ``.compute_group_info()``).

    ``group_idx`` is the column the groups are read from (``None`` -> column
    0, as in R).  ``mode`` is ``"value"``, ``"indent"`` or ``"filled"``
    (``None`` / ``"auto"`` reads the column).  A row before the first header
    (indent / filled) has id ``None``.  A materialised blank row
    (:class:`_BlankMarker`) never opens a group: under ``"value"`` it joins
    the group above it, so it does not break the run.
    """
    n = len(rows)
    idx = 0 if group_idx is None else group_idx
    col = [_as_text(r[idx]) if idx < len(r) else "" for r in rows]
    if mode in (None, "auto"):
        mode = _detect_group_mode(col)
    if mode == "value":
        keys = [r[idx] if idx < len(r) else None for r in rows]
        for i in range(n):
            if isinstance(rows[i], _BlankMarker) and i > 0:
                keys[i] = keys[i - 1]
                col[i] = col[i - 1]
        gid: list = []
        headers: list[bool] = []
        current = 0
        for i in range(n):
            head = i == 0 or keys[i] != keys[i - 1]
            if head:
                current += 1
            gid.append(current)
            headers.append(head)
        return gid, col, headers
    gid, labels, headers = [], [], []
    current_id, current_label = 0, ""
    for i, v in enumerate(col):
        nonempty = v != "" and not isinstance(rows[i], _BlankMarker)
        head = nonempty if mode == "filled" else (
            nonempty and v[:1] not in _GROUP_INDENT_CHARS)
        if head:
            current_id += 1
            current_label = v
        gid.append(current_id or None)
        labels.append(current_label)
        headers.append(head)
    return gid, labels, headers


def _continuation_row(row, cont_col, text):
    """A repeated group header: every cell blanked except ``cont_col``."""
    out = ["" if isinstance(cell, str) else None for cell in row]
    if 0 <= cont_col < len(out):
        out[cont_col] = text
    return out


def _same_group(a, b) -> bool:
    return a is not None and b is not None and a == b


def _split_group_force(rows, info, max_rows, cont_label, cont_col, min_group_rows,
                       edge_first=False, edge_end=False, blank_ignore=()):
    """Cut every ``max_rows`` rows, continuing a group across the break.

    A port of R's ``.split_group_force()``: when the cut falls inside a group,
    a ``(Cont.)`` row repeating the group's label opens the next page, and it
    is one of that page's ``max_rows``.  ``min_group_rows`` is widow / orphan
    control:

    * *orphan* -- the group starts on this page but would show fewer than
      ``min_group_rows`` children, so the whole group moves to the next page;
    * *widow* -- the cut would spill fewer than ``min_group_rows`` rows onto the
      next page, so the cut is pulled back.

    Under ``count_blank_rows=True`` the page-edge blanks print rows too (R
    #362): ``edge_first`` / ``edge_end`` take them off the page's budget unless
    they fall against a blank row.
    """
    rows = list(rows)
    n = len(rows)
    if n == 0:
        return [rows]
    gid, labels, headers = (list(v) for v in info)
    pages: list = []
    pos = 0
    while pos < n:
        budget = max_rows - (
            1 if edge_first and not _row_is_blank(rows[pos], blank_ignore) else 0
        ) - (1 if edge_end else 0)
        budget = max(budget, 1)
        end = min(pos + budget, n)  # exclusive
        if edge_end and end < n and _row_is_blank(rows[end], blank_ignore):
            end = min(end + 1, n)  # the trailing edge merges with it

        if min_group_rows > 0 and end < n and _same_group(gid[end - 1], gid[end]):
            last = end - 1
            end_gid = gid[last]
            h = last
            while h > pos and not headers[h]:
                h -= 1
            starts_here = h > pos and headers[h] and gid[h] == end_gid
            if starts_here and (last - h) < min_group_rows:
                end = h  # orphan: push the whole group to the next page
            else:
                tail = 0
                k = end
                while k < n and _same_group(gid[k], end_gid):
                    tail += 1
                    k += 1
                if 0 < tail < min_group_rows:
                    new_last = last - (min_group_rows - tail)
                    g = last
                    while g > pos and _same_group(gid[g - 1], end_gid):
                        g -= 1
                    if new_last > pos and (new_last - g + 1) >= min_group_rows:
                        end = new_last + 1

        pages.append(rows[pos:end])

        # Mid-group cut -> the next page opens with a "(Cont.)" row.
        if end < n and _same_group(gid[end - 1], gid[end]):
            label = labels[end - 1]
            text = ("" if label is None else str(label)) + cont_label
            rows.insert(end, _continuation_row(rows[end], cont_col, text))
            gid.insert(end, gid[end - 1])
            labels.insert(end, label)
            headers.insert(end, True)
            n += 1
        pos = end
    return pages


def _split_group_safe(rows, info, max_rows, cont_label, cont_col, min_group_rows,
                      edge_first=False, edge_end=False, blank_ignore=()):
    """Pack whole groups onto each page (R's ``.split_group_safe()``).

    A group that does not fit on a page by itself is force-split with
    :func:`_split_group_force`, and its tail stays open so the next groups can
    pack onto it.  What a page holds is what it would PRINT, the page-edge
    blanks included when they are counted (R #362).
    """
    if not rows:
        return [list(rows)]
    gid_all, labels, headers = info

    def printed(head, tail):
        first = head[0] if head else tail[0]
        return (len(head or []) + len(tail)
                + (1 if edge_first and not _row_is_blank(first, blank_ignore) else 0)
                + (1 if edge_end and not _row_is_blank(tail[-1], blank_ignore) else 0))

    # Rows before the first header form a synthetic "preamble" group (id 0).
    gid = [0 if g is None else g for g in gid_all]
    order: list = []
    members: dict = {}
    for i, g in enumerate(gid):
        if g not in members:
            members[g] = []
            order.append(g)
        members[g].append(i)

    pages: list = []
    buf: list | None = None
    for g in order:
        idx = members[g]
        grp = [rows[i] for i in idx]
        if printed(None, grp) > max_rows:
            if buf is not None:
                pages.append(buf)
                buf = None
            sub = _split_group_force(
                grp, ([gid_all[i] for i in idx], [labels[i] for i in idx],
                      [headers[i] for i in idx]),
                max_rows, cont_label, cont_col, min_group_rows,
                edge_first=edge_first, edge_end=edge_end, blank_ignore=blank_ignore,
            )
            pages.extend(sub[:-1])
            buf = sub[-1]
        elif buf is not None and printed(buf, grp) > max_rows:
            pages.append(buf)
            buf = grp
        else:
            buf = grp if buf is None else buf + grp
    if buf is not None:
        pages.append(buf)
    return pages


# -- count_blank_rows: materialise / collapse blank markers (R #362 / #330) --

#: What a materialised blank row stands for: a separator (subject to the
#: page-edge rule, R #332) or a position the caller named.
_MARK_SEP, _MARK_EXPLICIT = 1, 2


class _BlankMarker(list):
    """An empty row standing in for a blank row, so the split counts it.

    ``count_blank_rows=True`` inserts one wherever a blank row will print,
    before the split; each page turns them back into blank positions.
    """

    code = _MARK_SEP


def _row_is_blank(row, ignore=()) -> bool:
    """A materialised blank, or a row with nothing to print (every cell empty
    once the columns that will not be printed are left out)."""
    if isinstance(row, _BlankMarker):
        return True
    return all(
        _as_text(v).strip(" \t\r\n") == ""
        for j, v in enumerate(row) if j not in ignore
    )


def _materialize_blank_markers(rows, sep_pos, exp_pos):
    """Insert a :class:`_BlankMarker` before each 0-based row position (``n`` =
    after the last row).  Position 0 is left to ``blank_row_first``, as in R."""
    n = len(rows)
    code = {p: _MARK_SEP for p in sep_pos if 1 <= p <= n}
    for p in exp_pos:
        if 1 <= p <= n and p not in code:
            code[p] = _MARK_EXPLICIT
    if not code:
        return list(rows), False
    out: list = []
    for i in range(n + 1):
        if i in code:
            template = rows[i - 1]
            mk = _BlankMarker(_continuation_row(template, -1, ""))
            mk.code = code[i]
            out.append(mk)
        if i < n:
            out.append(rows[i])
    return out, True


def _collapse_blank_markers(page_rows, blank_row_first, blank_row_end):
    """Drop a page's markers and return ``(data_rows, blank_positions)``.

    A marker's position is the number of data rows above it.  A separator may
    only sit BETWEEN rows (R #332); a named position is honoured wherever it
    lands.  The page edges are ``blank_row_first`` / ``blank_row_end``.
    """
    data: list = []
    sep: list[int] = []
    exp: list[int] = []
    for r in page_rows:
        if isinstance(r, _BlankMarker):
            (sep if r.code == _MARK_SEP else exp).append(len(data))
        else:
            data.append(r)
    n = len(data)
    pos = set(_trim_page_edges(sep, n)) | set(exp)
    if blank_row_first:
        pos.add(0)
    if blank_row_end:
        pos.add(n)
    return data, sorted(p for p in pos if 0 <= p <= n)


# ============================================================================
#  Public entry points
# ============================================================================

#: Characters that mark a cell as indented, i.e. a group *member* (as in R).
_GROUP_INDENT_CHARS = (" ", "	", " ")


def _as_text(value) -> str:
    """Render a cell as text, treating None/NaN as the empty string."""
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN
        return ""
    return str(value)


def _detect_group_mode(values: list[str]) -> str:
    """Infer how group boundaries are marked, mirroring R's detection order.

    Indentation wins over sparseness, which wins over plain value changes.
    """
    nonempty = [v != "" for v in values]
    if any(ne and v[:1] in _GROUP_INDENT_CHARS for ne, v in zip(nonempty, values, strict=True)):
        return "indent"
    if any(not ne for ne in nonempty) and any(nonempty):
        return "filled"
    return "value"


def _resolve_group_mode(rows, group_idx, group_by: str) -> str:
    """The ``group_by`` a call resolves to: ``"auto"`` reads the column."""
    if group_idx is None or group_by != "auto":
        return group_by if group_by != "auto" else "value"
    return _detect_group_mode([_as_text(row[group_idx]) for row in rows])


def _compute_group_keys(rows, group_idx, group_by: str):
    """Per-row group keys for run-length grouping.

    Mirrors R's ``.compute_group_info()``.  ``"value"`` groups consecutive equal
    cells; ``"indent"`` treats a flush-left cell as a group header and indented
    cells as its members; ``"filled"`` treats any non-empty cell as a header.
    For the header-based modes the key is the header's own text, so it doubles
    as the page name for ``split="by_value"``.
    """
    if group_idx is None:
        return [None] * len(rows)
    values = [_as_text(row[group_idx]) for row in rows]
    mode = _detect_group_mode(values) if group_by == "auto" else group_by
    if mode == "value":
        return [row[group_idx] for row in rows]
    if mode not in ("indent", "filled"):
        raise ValueError(
            f"`group_by` must be one of 'auto', 'indent', 'value', 'filled'; got {group_by!r}."
        )
    keys: list[str] = []
    current = ""
    for value in values:
        nonempty = value != ""
        is_header = nonempty if mode == "filled" else (
            nonempty and value[:1] not in _GROUP_INDENT_CHARS
        )
        if is_header:
            current = value
        keys.append(current)
    return keys


def _table_width_pct_frac(x, arg: str = "table_width_pct") -> float:
    """A percentage in (0, 100] as a fraction; refused with rtftable()'s own
    message instead of quietly resolving to NaN (R #388)."""
    try:
        pct = float(x)
    except (TypeError, ValueError):
        pct = float("nan")
    if not (0 < pct <= 100):
        raise ValueError(f"`{arg}` must be a number in (0, 100].")
    return pct / 100


def _resolve_total_width_twips(twips, user_args: dict) -> int | None:
    """The table's total width in twips, resolved the way rtftable() resolves
    it (R #382): an absolute ``table_width_twips`` first, then a percentage of
    the writable width, then ``None`` for "whatever the page gives"."""
    if twips is not None:
        return int(twips)
    frac = user_args.get("table_width_pct_of_writable")
    if frac is None and user_args.get("table_width_pct") is not None:
        frac = _table_width_pct_frac(user_args["table_width_pct"])
    if frac is None:
        return None
    return int(round(_DEFAULT_WRITABLE_TWIPS * float(frac)))


#: Accepted string shorthand for ``blank_rows`` (mirrors the R package).
BETWEEN_GROUPS = "between_groups"


def _trim_page_edges(pos, n: int) -> list[int]:
    """A separator blank belongs BETWEEN rows.  Position 0 (before the first
    row) and ``n`` (after the last row) are the page's edges, and those are
    decided by ``blank_row_first`` / ``blank_row_end`` alone -- a group
    boundary that happens to coincide with a page boundary must not put one
    there, because on that page it separates nothing (R #332).

    Explicit integer positions are NOT separators and never come through here:
    ``blank_rows=2`` is a direct request for "after row 2 of each page" and is
    honoured even when the page has exactly three rows.
    """
    return [p for p in pos if 0 < p < n]


def _resolve_pagewise_blanks(spec, column_names, rows) -> list[int]:
    """Resolve a per-page ``blank_rows`` spec to internal positions, trimming
    the separator items (:class:`~rtfreporter.blank_rows.BlankRowsByChange` /
    :class:`~rtfreporter.blank_rows.BlankRowsByRule`, which is also what
    ``"between_groups"`` expands to) to the page's interior."""
    from .blank_rows import BlankRowsByChange, BlankRowsByRule
    from .table import _resolve_blank_rows

    if spec is None:
        return []
    items = list(spec) if isinstance(spec, (list, tuple)) else [spec]
    out: set[int] = set()
    for item in items:
        if item is None:
            continue
        pos = _resolve_blank_rows(item, column_names, rows)
        if isinstance(item, (BlankRowsByChange, BlankRowsByRule)):
            pos = _trim_page_edges(pos, len(rows))
        out.update(pos)
    return sorted(out)


def _page_by_runs(rows, by_idx):
    """The partitions ``page_by`` implies (R ``.page_by_runs()``): one per
    DISTINCT key, holding every row that has it, in the body's order.
    Returns ``[(row indices, label)]``.

    A row with no key of its own (a stub label row) takes the key of the row
    it introduces (the next real one), and at the foot of the body that of the
    row it follows.
    """
    from .catx import _as_text as r_text

    keys = []
    for j in by_idx:
        v = [r_text(r[j]) if j < len(r) else "" for r in rows]
        miss = [not x.strip() for x in v]
        nxt, prv = [None] * len(v), [None] * len(v)
        last = None
        for i in range(len(v) - 1, -1, -1):
            if not miss[i]:
                last = v[i]
            nxt[i] = last
        last = None
        for i in range(len(v)):
            if not miss[i]:
                last = v[i]
            prv[i] = last
        keys.append([v[i] if not miss[i] else (nxt[i] if nxt[i] is not None else (prv[i] or ""))
                     for i in range(len(v))])
    key = [tuple(k[i] for k in keys) for i in range(len(rows))]
    out: dict = {}
    for i, k in enumerate(key):
        out.setdefault(k, []).append(i)
    return [(idx, ", ".join(k)) for k, idx in out.items()]


def _order_and_name_pages(pages, grp, by):
    """Order and name the pages of a ``page_by`` split (R
    ``.order_and_name_pages()``): with a named inner split (``by_value``) the
    group is the outer axis and the name; otherwise the key's value is."""
    n = len(pages)
    has_grp = n > 0 and all(g is not None for g in grp)
    order = list(range(n))
    if has_grp:
        g_first = {g: i for i, g in reversed(list(enumerate(grp)))}
        b_first = {b: i for i, b in reversed(list(enumerate(by)))}
        order.sort(key=lambda i: (g_first[grp[i]], b_first[by[i]], i))
    names = grp if has_grp else by
    return [(pages[i][0], names[i], pages[i][2], pages[i][3],
             grp[i] if has_grp else None, by[i]) for i in order]


def _split_blank_positions(spec, column_names, rows):
    """Resolve a ``blank_rows`` spec on the whole body into ``(separators,
    explicit)`` internal positions, for :func:`_materialize_blank_markers`.

    Separator items (a change / rule spec, which is also what
    ``"between_groups"`` expands to) only sit between rows (R #332); an
    explicitly named position is taken as it is.
    """
    from .blank_rows import BlankRowsByChange, BlankRowsByRule
    from .table import _resolve_blank_rows

    if spec is None:
        return [], []
    items = list(spec) if isinstance(spec, (list, tuple)) else [spec]
    sep: set[int] = set()
    exp: set[int] = set()
    for item in items:
        if item is None:
            continue
        pos = _resolve_blank_rows(item, column_names, rows)
        if isinstance(item, (BlankRowsByChange, BlankRowsByRule)):
            sep.update(_trim_page_edges(pos, len(rows)))
        else:
            exp.update(pos)
    return sorted(sep), sorted(exp - sep)


def _expand_between_groups(blank_rows, group_idx, group_by="auto"):
    """Expand the ``"between_groups"`` shorthand into a change-based spec.

    ``blank_rows="between_groups"`` means "a blank row at every group
    transition on ``group_col``, **using this call's ``group_by`` detection**",
    matching the R package.  It may also appear inside a combining list, e.g.
    ``["between_groups", AFTER_LAST]``.  When no ``group_col`` was given the
    first column is used, as in R.

    Passing ``group_by`` through matters for an indented stub: every stub cell
    differs, so value-comparison would blank between *every* row, while the
    ``"auto"`` default detects indentation and blanks only at the group heads.
    """
    if blank_rows is None:
        return None
    if isinstance(blank_rows, str):
        if blank_rows != BETWEEN_GROUPS:
            raise ValueError(
                f"`blank_rows` string must be {BETWEEN_GROUPS!r}; got {blank_rows!r}."
            )
        # R's "between_groups" blanks only the transitions -- not before the
        # first row or after the last, which blank_rows_by_change() does by
        # default.  Verified against R: A,A,B,B -> [2].
        return blank_rows_by_change(
            group_idx if group_idx is not None else 0,
            group_by=group_by,
            include_before_first=False,
            include_after_last=False,
        )
    if isinstance(blank_rows, (list, tuple)):
        return [_expand_between_groups(item, group_idx, group_by) for item in blank_rows]
    return blank_rows


def as_rtftables(
    x,
    *,
    read_meta=True,
    split="none",
    split_rows=None,
    max_rows: int | None = None,
    group_col=None,
    group_by: str = "auto",
    page_by=None,
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
    na: str = "",
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
            The built-in strategies are named by string; a callable is the
            custom-split hook (R's ``split = <function>``).
        split_rows: For ``split="rows"`` -- an int page size or explicit cut
            positions.
        max_rows: Max data rows per page (required by the group splits).
        group_col: The grouping column (index or name) for group/value splits,
            ``collapse_repeats`` grouping, and between-group blank rows.
        group_by: How a group boundary is detected on ``group_col`` -- one of
            ``"auto"`` (default), ``"indent"``, ``"value"``, ``"filled"``.  Only
            ``"auto"`` (value-change detection) is implemented; the others raise
            ``NotImplementedError``.
        page_by: Column(s) whose value starts a page and names it (R
            ``page_by``), the OUTER level: every row of a value is gathered onto
            its pages, in the body's order, and the split, ``max_rows``, the
            groups and the blank rows then apply within it.  A row with no
            value of its own (a stub label row) belongs with the row it
            introduces.  With no ``group_col`` the groups are read from the
            first column the key does not occupy.  Under ``split="by_value"``
            the group is the outer axis and names the pages; otherwise the
            pages are named by the key's values (joined with ``", "``).
        sort_by, sort_desc: Column(s) to sort rows by, and per-column descending
            flags, applied before pagination.
        count_blank_rows: What ``max_rows`` counts.  ``False`` (default): the
            data rows only.  ``True``: the rows the page prints -- the blank
            rows from ``blank_rows`` are placed before the split so they count,
            and the ``blank_row_first`` / ``blank_row_end`` page edges count
            unless they fall against a blank row (R #362).
        align_count_pct: When ``True``, realign ``count (pct)`` cells to a
            uniform width in every column except the first (see
            :func:`~rtfreporter.realign_count_pct`).  Applied before pagination;
            superseded by ``cell_format`` when both are given.
        na: The text printed for a missing value (``None`` / ``nan``) in any
            column, e.g. ``"-"``; ``""`` (default) leaves the cell empty.
            Applied to the whole body before the split and before
            ``cell_format``, so the aligners pad it like any other value.
        cell_format: An optional per-column re-formatter -- a single callable
            (applied to columns ``1..n-1``) or a list of callables taken
            positionally.  Each takes one column (a list) and returns a list of
            the same length; see :func:`~rtfreporter.fmt_count_paren`.
        stub_group_summary: Forwarded to the stub builder -- ``"empty"`` (default)
            or ``"parent"``.  Only ``"empty"`` is implemented.
        auto_width: When ``True``, size each column to its widest content --
            column-header label or data cell -- via
            :func:`~rtfreporter.auto_col_widths`, so long labels do not wrap.
            Computed once on the whole table and applied to every page.
            Ignored when explicit ``column_widths_twips`` / ``col_rel_width``
            are given.  Legacy note: not yet
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
    # A `cell_styles` of your own, one element per body row, follows its rows
    # the same way (R #498) instead of being handed whole to every page,
    # where a second page could not take it.
    user_styles = table_kwargs.get("cell_styles")
    if (coerced.cell_styles is None and user_styles is not None
            and stub_vars is None and drop_cols is None
            and len(user_styles) == len(rows)):
        coerced.cell_styles = list(table_kwargs.pop("cell_styles"))
    carry_styles = coerced.cell_styles is not None
    if carry_styles:
        if stub_vars is not None or drop_cols is not None:
            raise ValueError(
                "`stub_vars` / `drop_cols` are not supported for great_tables "
                "input; the GT adapter already reshapes the body (row groups "
                "become an indented stub and hidden columns are dropped)."
            )
        rows = [list(r) + [coerced.cell_styles[i]] for i, r in enumerate(rows)]

    # by_value + stub_vars: each group is its own section, so the body is split
    # by the PRE-stub `group_col` first (every row of a value gathered, in
    # order) and the stub is built per group, one page each -- as R does.
    # Built on the whole body, a constant intermediate level would collapse
    # into one stub row spanning every group, and the groups would fragment.
    if split == "by_value" and stub_vars is not None:
        gi = _resolve_index(group_col, column_names) if group_col is not None else 0
        gval = [_as_text(r[gi]) for r in rows]
        tk = {k: v for k, v in table_kwargs.items()
              if k not in ("table_width_twips", "style")}
        user_cs = tk.get("cell_styles")
        out_pages: list[RtfTable] = []
        by_pre = _resolve_indices(page_by, column_names) if page_by is not None else []
        for k, value in enumerate(dict.fromkeys(gval), start=1):
            g_idx = [i for i, g in enumerate(gval) if g == value]
            # `page_by` stays the inner level: the group's rows are cut by it
            # first, on the pre-stub columns, and each part is one page.
            parts = ([[g_idx[i] for i in part] for part, _ in
                      _page_by_runs([rows[i] for i in g_idx], by_pre)]
                     if by_pre else [g_idx])
            for idx in parts:
                sub = {name: [rows[i][j] for i in idx] for j, name in enumerate(column_names)}
                if user_cs is not None and len(user_cs) == len(rows):
                    tk["cell_styles"] = [user_cs[i] for i in idx]
                pages_k = as_rtftables(
                    sub, read_meta=read_meta, split="none", group_by=group_by,
                    sort_by=sort_by, sort_desc=sort_desc, cont_label=cont_label,
                    min_group_rows=min_group_rows, blank_rows=blank_rows,
                    blank_row_first=blank_row_first, blank_row_end=blank_row_end,
                    count_blank_rows=count_blank_rows, align_count_pct=align_count_pct,
                    cell_format=cell_format, na=na, collapse_repeats=collapse_repeats,
                    drop_cols=drop_cols, stub_vars=stub_vars, stub_label=stub_label,
                    stub_indent=stub_indent, stub_group_summary=stub_group_summary,
                    header_sep=header_sep, auto_width=auto_width,
                    table_width_twips=table_width_twips, border=border, style=style, **tk,
                )
                label = (", ".join(_as_text(rows[idx[0]][j]) for j in by_pre)
                         if by_pre and idx else None)
                for tbl in pages_k:
                    tbl.name = value if value else f"group_{k}"
                    tbl.page_group = tbl.name
                    tbl.page_by = label
                out_pages.extend(pages_k)
        return out_pages

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

    # na: the text for a missing value, in every column, body-wide and before
    # the cell-format pass -- so the aligners see it as ordinary text -- and
    # before the split, so the blanks collapse_repeats writes per page stay
    # blank (R).
    if not isinstance(na, str):
        raise ValueError(
            "`na` must be a single string -- the text printed for a missing value "
            '(e.g. "-" or "NA").  "" (the default) leaves the cell empty.'
        )
    if na:
        ncol = len(column_names)
        rows = [[na if j < ncol and (v is None or (isinstance(v, float) and v != v)) else v
                 for j, v in enumerate(r)] for r in rows]

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
                apply_cell_format(rows, column_names, fl, na=na)
        elif align_count_pct:
            realign_count_pct_df(rows, column_names, na=na)

    def paginate_part(part_rows, g_idx):
        """Split one body (the whole one, or one page_by partition) into pages:
        ``(rows, name, materialised, blank spec)`` each."""
        # `group_by="auto"` is settled BEFORE any blank marker goes in: a
        # marker's empty cell would make a value-grouped column read as
        # "filled", every row its own group, and group_safe free to cut
        # anywhere (R #330).  With no group column the splits read column 0.
        split_mode = group_by
        if group_by == "auto":
            gcol = g_idx if g_idx is not None else 0
            split_mode = (_detect_group_mode([_as_text(r[gcol]) for r in part_rows])
                          if part_rows else "value")

        # count_blank_rows: every blank row that will print is materialised as
        # a marker row BEFORE the split, so it counts toward `max_rows`; each
        # page turns its markers back into blank positions (R #362).
        materialised = False
        if count_blank_rows:
            spec = _expand_between_groups(blank_rows, g_idx, split_mode)
            sep_pos, exp_pos = _split_blank_positions(spec, column_names, part_rows)
            part_rows, materialised = _materialize_blank_markers(part_rows, sep_pos, exp_pos)

        group_keys = _compute_group_keys(part_rows, g_idx, split_mode)
        if materialised and split_mode == "value":
            # A marker joins the group above it, so it does not break the run.
            for i in range(1, len(part_rows)):
                if isinstance(part_rows[i], _BlankMarker):
                    group_keys[i] = group_keys[i - 1]

        if callable(split):
            # Custom split hook: build a Frame, run the split, and normalise the
            # returned frames to the ``(rows, page_name)`` shape.
            from .pagination import Frame, run_split

            frames = run_split(
                split,
                Frame(column_names, part_rows),
                split_rows=split_rows,
                max_rows=max_rows,
                group_col=g_idx if group_col is None else group_col,
                group_by=group_by,
                cont_label=cont_label,
                min_group_rows=min_group_rows,
            )
            part_pages = [(f.rows, f.name) for f in frames]
        else:
            # Under count_blank_rows the page edges print rows too, so the group
            # splits count them (R #362).  A row with content only in a column
            # that is not printed (a drop_cols carrier) is blank on the page.
            ignore = set(drop_idx or ())
            if carry_styles:
                ignore.add(len(column_names))
            part_pages = _paginate(
                part_rows, group_keys, split, split_rows, max_rows, min_group_rows,
                cont_label, g_idx, group_mode=split_mode,
                edge_first=count_blank_rows and blank_row_first,
                edge_end=count_blank_rows and blank_row_end,
                blank_ignore=ignore,
            )
        # Per-page blank spec: R inserts NO blank rows unless `blank_rows` asks
        # for them -- setting `group_col` alone must not add separators.
        pblank = _expand_between_groups(blank_rows, g_idx, group_by)
        return [(r, nm, materialised, pblank, None, None) for r, nm in part_pages]

    if page_by is None:
        pages = paginate_part(rows, group_idx)
    else:
        # page_by: the OUTER level (R .paginate_by_page()).  Each partition goes
        # through the same split; the group column defaults to the first column
        # the key does not occupy (the BY column itself has no structure).
        by_idx = _resolve_indices(page_by, column_names)
        g_idx = group_idx
        if g_idx is None:
            g_idx = next((j for j in range(len(column_names)) if j not in by_idx), None)
        collected, grp, by = [], [], []
        for part_idx, label in _page_by_runs(rows, by_idx):
            for page in paginate_part([rows[i] for i in part_idx], g_idx):
                collected.append(page)
                grp.append(page[1] if page[1] else None)
                by.append(label)
        pages = _order_and_name_pages(collected, grp, by)

    # auto_width: measure the WHOLE table once (all pages share the widths, so
    # paginated pages line up).  Carrier columns are dropped from the printed
    # body, so measure the printed shape.
    auto_width_twips = None
    if auto_width and not (
        "column_widths_twips" in table_kwargs or "col_rel_width" in table_kwargs
    ):
        from .text_width import auto_col_widths

        measured_names, measured_rows = column_names, rows
        if drop_idx:
            keep = [i for i in range(len(column_names)) if i not in set(drop_idx)]
            measured_names = [column_names[i] for i in keep]
            measured_rows = [[r[i] for i in keep] for r in rows]
        header_labels = table_kwargs.get("col_header", coerced.auto_header)

        # The budget is the table's total width, resolved the way rtftable()
        # resolves it: absolute first, then a percentage of the writable width
        # (R #382).  Reading only `table_width_twips` here made auto_width deaf
        # to `table_width_pct`.
        width_budget = _resolve_total_width_twips(table_width_twips, table_kwargs)
        if width_budget is None:
            # No explicit budget: keep natural widths, but cap the total at the
            # default writable page width so a wide table still fits (as in R).
            natural = auto_col_widths(
                (measured_names, measured_rows), col_header=header_labels
            )
            if sum(natural) > _DEFAULT_WRITABLE_TWIPS:
                width_budget = _DEFAULT_WRITABLE_TWIPS
        # protect_cols=[0] keeps the stub / row-label column at its natural
        # width so only the data columns absorb the scaling, matching R's
        # `protect_cols = 1L`.
        auto_width_twips = auto_col_widths(
            (measured_names, measured_rows),
            col_header=header_labels,
            table_width_twips=width_budget,
            protect_cols=[0],
        )

    # An absolute total width is a table setting, not an auto-sizing one
    # (R #382): forward it so `as_rtftables(table_width_twips=)` means what
    # `rtftable(table_width_twips=)` means.
    if table_width_twips is not None and "table_width_twips" not in table_kwargs:
        table_kwargs = dict(table_kwargs, table_width_twips=int(table_width_twips))

    out: list[RtfTable] = []
    for page_rows, page_name, materialised, page_blank, page_group, page_by_key in pages:
        if materialised:
            # The blanks were counted by the split: read them off the markers.
            page_rows, blank_positions = _collapse_blank_markers(
                page_rows, blank_row_first, blank_row_end)
        else:
            # Resolve blank positions on the FULL page body (index-stable even
            # when the grouping column is later dropped) into plain positions.
            blank_positions = _resolve_pagewise_blanks(page_blank, column_names, page_rows)
            if blank_row_first:
                blank_positions = sorted(set(blank_positions) | {0})
            if blank_row_end:
                blank_positions = sorted(set(blank_positions) | {len(page_rows)})
        prows = _collapse_repeats(page_rows, collapse_idx) if collapse_idx else [list(r) for r in page_rows]

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

        # col_header: the AUTO (adapter-derived) header travels with the body
        # through the drop / stub reindexing.  A USER-supplied `col_header` is
        # instead applied AFTER the table is built, against the FINAL printed
        # columns (via set_col_header()), as R does -- which also means the
        # table is built without a header as far as its border is concerned.
        col_header = printed_header if printed_header is not None else None
        kwargs = dict(table_kwargs)
        user_col_header = kwargs.pop("col_header", None)
        if col_header is not None and user_col_header is None:
            kwargs["col_header"] = col_header
        if coerced.col_spec is not None and "col_spec" not in kwargs:
            kwargs["col_spec"] = coerced.col_spec
        if coerced.col_rel_width is not None and "col_rel_width" not in kwargs:
            kwargs["col_rel_width"] = coerced.col_rel_width
        if coerced.column_widths_twips is not None and "column_widths_twips" not in kwargs:
            kwargs["column_widths_twips"] = coerced.column_widths_twips
        if page_cell_styles is not None:
            kwargs["cell_styles"] = page_cell_styles

        # auto_width sizes columns to their widest content.  The widths are
        # computed once on the FULL table (below) and reused for every page, so
        # paginated pages stay aligned.  Explicit widths always win.
        if (
            auto_width_twips is not None
            and "column_widths_twips" not in kwargs
            and "col_rel_width" not in kwargs
        ):
            if len(auto_width_twips) == len(printed_names):
                kwargs["column_widths_twips"] = list(auto_width_twips)

        tbl = rtftable(
            (printed_names, prows),
            border=border,
            _blank_positions=blank_positions or None,
            **kwargs,
        )
        if user_col_header is not None:
            from .post_hoc import set_col_header

            tbl = set_col_header(tbl, user_col_header)
        if titles is not None:
            tbl.titles = titles
        if footnotes is not None:
            tbl.footnotes = footnotes
        if page_name:
            tbl.name = page_name
        tbl.page_group = page_group
        tbl.page_by = page_by_key
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
