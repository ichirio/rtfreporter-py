"""Clinical indented-stub construction (the R ``stub_cols()`` verb).

Ported from ``R/stub.R``.  Merges a hierarchy of columns (parent-first,
leaf-last) into a single indented "stub" column: each parent level emits its own
un-indented label row when its value changes, and every data row becomes an
indented leaf under it.  A *group-summary* row (an empty or parent-repeating
leaf) folds its statistics onto the group's label row instead of an indented
leaf row.  Non-breaking spaces are used for the indent so viewers preserve it.
"""

from __future__ import annotations

from .pagination import Frame

_NBSP = " "


def _resolve_group_summary(group_summary) -> set[str]:
    """Resolve the ``group_summary`` argument to a set of active modes."""
    if group_summary is None:
        return set()
    if isinstance(group_summary, str):
        group_summary = [group_summary]
    modes = set(group_summary)
    if "all" in modes:
        return {"empty", "parent"}
    if "none" in modes:
        return set()
    unknown = modes - {"empty", "parent"}
    if unknown:
        raise ValueError(
            f"`group_summary` values must be a subset of "
            f"{{'empty', 'parent', 'all', 'none'}}; got {sorted(unknown)}."
        )
    return modes


def stub_cols(
    data,
    vars,
    label: str | None = None,
    indent: int = 4,
    group_summary=("empty", "parent"),
) -> Frame:
    """Merge hierarchy columns into one indented clinical stub column.

    Args:
        data: A ``(column_names, rows)`` pair, dict of columns, list of row
            dicts, or a pandas/polars DataFrame.
        vars: The hierarchy columns to merge, **parent first, leaf last** -- at
            least two, as 0-based indices and/or names.
        label: Name for the merged stub column.  ``None`` (default) joins the
            merged column names with ``" / "``.
        indent: Non-breaking spaces prepended per nesting level (default 4).
        group_summary: Which leaf values mark a row as its group's summary
            (folded onto the label row): a subset of ``("empty", "parent")`` --
            ``"empty"`` for an empty leaf, ``"parent"`` for a leaf equal to its
            deepest non-empty parent.  Also accepts ``"all"`` / ``"none"`` /
            ``None``.

    Returns:
        A :class:`~rtfreporter.pagination.Frame`: the stub column first, then
        every non-``vars`` column of ``data`` in order.  Label rows hold ``None``
        in the non-stub columns.
    """
    from .adapters import _resolve_indices
    from .table import _coerce_data

    names, rows = _coerce_data(data)
    idx = _resolve_indices(vars, names)
    if len(set(idx)) != len(idx):
        raise ValueError("`vars` must name distinct columns.")
    if len(idx) < 2:
        raise ValueError("`vars` needs at least two columns (parent, then leaf) to merge.")
    if label is not None and not isinstance(label, str):
        raise ValueError("`label` must be None or a single string.")
    indent = int(indent)
    if indent < 0:
        raise ValueError("`indent` must be a single non-negative integer.")

    modes = _resolve_group_summary(group_summary)
    empty_mode = "empty" in modes
    parent_mode = "parent" in modes

    leaf_i = idx[-1]
    par_i = idx[:-1]
    n_par = len(par_i)
    pad = _NBSP * indent

    def as_chr(v) -> str:
        return "" if v is None else str(v)

    parents = [[as_chr(r[j]) for r in rows] for j in par_i]
    leafv = [as_chr(r[leaf_i]) for r in rows]

    stub: list[str] = []
    src: list[int | None] = []
    prev: list[str] | None = None
    label_pos: list[int | None] = [None] * n_par

    for i in range(len(rows)):
        cur = [parents[lvl][i] for lvl in range(n_par)]
        if prev is None:
            restart: int | None = 0
        else:
            changed = [lvl for lvl in range(n_par) if cur[lvl] != prev[lvl]]
            restart = changed[0] if changed else None
        if restart is not None:
            for lvl in range(restart, n_par):
                if not cur[lvl]:
                    label_pos[lvl] = None
                    continue
                depth_l = sum(1 for v in cur[:lvl] if v)
                stub.append(pad * depth_l + cur[lvl])
                src.append(None)
                label_pos[lvl] = len(stub) - 1

        nz = [lvl for lvl in range(n_par) if cur[lvl]]
        d_idx = nz[-1] if nz else None

        is_summary = d_idx is not None and (
            (empty_mode and not leafv[i])
            or (parent_mode and leafv[i] and leafv[i] == cur[d_idx])
        )

        if is_summary and label_pos[d_idx] is not None and src[label_pos[d_idx]] is None:
            src[label_pos[d_idx]] = i
        else:
            depth = sum(1 for v in cur if v)
            stub.append(pad * depth + leafv[i])
            src.append(i)
        prev = cur

    keep = [j for j in range(len(names)) if j not in idx]
    if label is None:
        label = " / ".join(names[j] for j in idx)
    out_names = [label] + [names[j] for j in keep]

    out_rows: list[list] = []
    for k, s in enumerate(src):
        rest = [None] * len(keep) if s is None else [rows[s][j] for j in keep]
        out_rows.append([stub[k]] + rest)

    return Frame(column_names=out_names, rows=out_rows)
