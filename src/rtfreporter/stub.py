"""Clinical indented-stub construction (the R ``stub_cols()`` verb).

Ported from ``R/stub.R``.  Merges a hierarchy of columns (parent-first,
leaf-last) into a single indented "stub" column: each parent level emits its own
un-indented label row when its value changes, and every data row becomes an
indented leaf under it.  A *group-summary* row (an empty or parent-repeating
leaf) folds its statistics onto the group's label row instead of an indented
leaf row.  Non-breaking spaces are used for the indent so viewers preserve it.
"""

from __future__ import annotations

from dataclasses import dataclass

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
    layout: str = "merged",
    label_span: bool = False,
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
        layout: ``"merged"`` (default) replaces the hierarchy columns with one
            indented stub column; ``"columns"`` keeps them where they were --
            a group value moves onto its own row, blank on its member rows,
            whose leaf is indented in the leaf column.
        label_span: Render each group label row as one cell spanning the table
            (``layout="merged"`` only).  A group-summary row folded onto a
            label row is never spanned: it carries statistics.

    Returns:
        A :class:`~rtfreporter.pagination.Frame`: under ``"merged"`` the stub
        column first, then every non-``vars`` column of ``data`` in order;
        under ``"columns"`` every column in its place.  Label rows hold
        ``None`` in the other columns.  ``stub_src`` gives each row's source
        row (``None`` for an inserted label row) and ``label_rows`` the rows
        to span, which :func:`~rtfreporter.rtftable` reads.
    """
    from .adapters import _resolve_indices
    from .table import _coerce_data

    if layout not in ("merged", "columns"):
        raise ValueError('`layout` must be "merged" or "columns".')
    if not isinstance(label_span, bool):
        raise ValueError("`label_span` must be True or False.")
    if layout == "columns":
        if label_span:
            raise ValueError('`label_span` applies to layout="merged" only; with '
                             'layout="columns" the group value stays in its own column.')
        if label is not None:
            raise ValueError('`label` names the merged stub column, which '
                             'layout="columns" does not create.')

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
        from .catx import _as_text

        return _as_text(v)

    parents = [[as_chr(r[j]) for r in rows] for j in par_i]
    leafv = [as_chr(r[leaf_i]) for r in rows]

    stub: list[str] = []
    src: list[int | None] = []
    lvl_of: list[int | None] = []   # the parent level of a label row, None for a leaf
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
                lvl_of.append(lvl)
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
            lvl_of.append(None)
        prev = cur

    keep = [j for j in range(len(names)) if j not in idx]
    out_rows: list[list] = []
    if layout == "columns":
        # Keep the hierarchy columns: a label row carries its own value in its
        # own column and nothing else; a leaf row blanks every parent and holds
        # the indented leaf.
        out_names = list(names)
        for k, s in enumerate(src):
            row = [None] * len(names) if s is None else list(rows[s])
            for j in idx:
                row[j] = None
            target = idx[-1] if lvl_of[k] is None else idx[lvl_of[k]]
            row[target] = stub[k]
            out_rows.append(row)
    else:
        if label is None:
            label = " / ".join(str(names[j]) for j in idx)
        out_names = [label] + [names[j] for j in keep]
        for k, s in enumerate(src):
            rest = [None] * len(keep) if s is None else [rows[s][j] for j in keep]
            out_rows.append([stub[k]] + rest)

    label_rows = [k for k, s in enumerate(src) if s is None] if label_span else None
    return Frame(column_names=out_names, rows=out_rows, stub_src=src,
                 label_rows=label_rows or None)


@dataclass(frozen=True)
class StubSpec:
    """Every stub setting in one object, built by :func:`stub_spec`."""

    vars: object
    label: str | None = None
    indent: int = 4
    group_summary: object = ("empty", "parent")
    layout: str = "merged"
    label_span: bool = False


def stub_spec(vars, label: str | None = None, indent: int = 4,
              group_summary=("empty", "parent"), layout: str = "merged",
              label_span: bool = False) -> StubSpec:
    """Every stub setting in one object, for ``as_rtftables(stub=)`` (R
    ``stub_spec()``, #314).

    The arguments are :func:`stub_cols`'s.  A bare list of columns
    (``stub=["SOC", "PT"]``) is the common case and needs no spec.
    """
    if vars is None:
        raise ValueError("`vars` is required: the hierarchy columns, parent first.")
    if layout not in ("merged", "columns"):
        raise ValueError('`layout` must be "merged" or "columns".')
    return StubSpec(vars=vars, label=label, indent=indent, group_summary=group_summary,
                    layout=layout, label_span=label_span)
