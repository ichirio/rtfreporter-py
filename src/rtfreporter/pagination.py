"""Pagination strategy factories and the custom ``split=`` hook.

Ported from ``R/paginate.R``.  The built-in page-splitting strategies are
exposed as reusable *factory functions* (:func:`page_split_none`,
:func:`page_split_rows`, :func:`page_split_by_value`,
:func:`page_split_group_safe`, :func:`page_split_group_force`) on the same
footing as a hand-written custom splitter, plus a standalone :func:`paginate`
that returns per-page frames.

The ``split=`` contract
-----------------------

A *split function* takes a single :class:`Frame` and returns a **list of
:class:`Frame`** -- one per page.  A page's :attr:`Frame.name` becomes the page
name (a group value, used e.g. for section naming).  ``as_rtftables(split=...)``
accepts either a built-in string (``"none"``, ``"rows"``, ``"by_value"``,
``"group_safe"``, ``"group_force"``) or such a callable.  A callable that
returns something other than a list of :class:`Frame` raises
:class:`PaginationError`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class PaginationError(ValueError):
    """Raised when a custom ``split=`` callable returns an invalid value."""


@dataclass
class Frame:
    """One rectangular page of data passed through the pagination hook.

    Args:
        column_names: Column names.
        rows: A list of rows (each a list of cell values).
        name: Optional page name (a group value, for ``page_split_by_value``).
        blank_rows: Optional blank-row positions (as attached by
            :func:`set_blank_rows`), consumed by :func:`~rtfreporter.rtftable`.
    """

    column_names: list[str]
    rows: list[list] = field(default_factory=list)
    name: str | None = None
    blank_rows: list | None = None


def as_frame(x) -> Frame:
    """Coerce a supported input to a :class:`Frame`.

    Accepts a :class:`Frame`, a ``(column_names, rows)`` pair, a dict of
    columns, a list of row dicts, or a pandas/polars DataFrame.
    """
    if isinstance(x, Frame):
        return x
    from .table import _coerce_data

    names, rows = _coerce_data(x)
    return Frame(column_names=names, rows=[list(r) for r in rows])


def _resolve_group(group_col, names: list[str]) -> int:
    """Resolve a group column (name / 0-based index / ``None`` = column 0)."""
    if group_col is None:
        return 0
    from .table import _resolve_col

    return _resolve_col(group_col, names)


def _frames_from_pages(frame: Frame, pages) -> list[Frame]:
    return [Frame(frame.column_names, rows, name) for rows, name in pages]


# -- Pagination strategy factories -------------------------------------------


def page_split_none() -> Callable[[Frame], list[Frame]]:
    """Return a split function that keeps the whole frame on one page."""

    def f(frame: Frame) -> list[Frame]:
        return [Frame(frame.column_names, list(frame.rows), frame.name)]

    return f


def page_split_rows(split_rows=None) -> Callable[[Frame], list[Frame]]:
    """Return a split function cutting at fixed row positions or a page size.

    Args:
        split_rows: An int page size, or explicit 0-based cut positions.
    """

    def f(frame: Frame) -> list[Frame]:
        if split_rows is None:
            raise PaginationError(
                "`split_rows` is required for row-position pagination."
            )
        from .adapters import _paginate

        pages = _paginate(
            frame.rows, [None] * len(frame.rows), "rows", split_rows, None, 2,
            " (Cont.)", None,
        )
        return _frames_from_pages(frame, pages)

    return f


def page_split_by_value(
    group_col=None,
    max_rows: int | None = None,
    min_group_rows: int = 2,
    cont_label: str = " (Cont.)",
    group_by: str = "auto",
) -> Callable[[Frame], list[Frame]]:
    """Return a split function that puts each distinct ``group_col`` value on its own page."""

    def f(frame: Frame) -> list[Frame]:
        _check_group_by(group_by)
        gidx = _resolve_group(group_col, frame.column_names)
        gkeys = [r[gidx] for r in frame.rows]
        from .adapters import _paginate

        pages = _paginate(
            frame.rows, gkeys, "by_value", None, max_rows, min_group_rows,
            cont_label, gidx,
        )
        return _frames_from_pages(frame, pages)

    return f


def page_split_group_safe(
    max_rows: int | None = None,
    group_col=None,
    min_group_rows: int = 2,
    cont_label: str = " (Cont.)",
    group_by: str = "auto",
) -> Callable[[Frame], list[Frame]]:
    """Return a split function that packs whole groups per page without splitting one."""
    return _group_factory(max_rows, group_col, min_group_rows, cont_label, group_by,
                          "group_safe")


def page_split_group_force(
    max_rows: int | None = None,
    group_col=None,
    min_group_rows: int = 2,
    cont_label: str = " (Cont.)",
    group_by: str = "auto",
) -> Callable[[Frame], list[Frame]]:
    """Return a split function that packs groups per page, force-splitting an oversized one."""
    return _group_factory(max_rows, group_col, min_group_rows, cont_label, group_by,
                          "group_force")


def _group_factory(max_rows, group_col, min_group_rows, cont_label, group_by, split):
    def f(frame: Frame) -> list[Frame]:
        _check_group_by(group_by)
        if max_rows is None:
            raise PaginationError(f"`max_rows` is required for {split} pagination.")
        gidx = _resolve_group(group_col, frame.column_names)
        gkeys = [r[gidx] for r in frame.rows]
        from .adapters import _paginate

        pages = _paginate(
            frame.rows, gkeys, split, None, max_rows, min_group_rows, cont_label, gidx,
        )
        return _frames_from_pages(frame, pages)

    return f


def _check_group_by(group_by: str) -> None:
    if group_by != "auto":
        raise NotImplementedError(
            f"group_by={group_by!r} is not implemented; only 'auto' is supported."
        )


_STRING_FACTORIES = {
    "none": lambda **kw: page_split_none(),
    "rows": lambda split_rows=None, **kw: page_split_rows(split_rows=split_rows),
    "by_value": lambda group_col=None, max_rows=None, min_group_rows=2,
    cont_label=" (Cont.)", group_by="auto", **kw: page_split_by_value(
        group_col=group_col, max_rows=max_rows, min_group_rows=min_group_rows,
        cont_label=cont_label, group_by=group_by),
    "group_safe": lambda max_rows=None, group_col=None, min_group_rows=2,
    cont_label=" (Cont.)", group_by="auto", **kw: page_split_group_safe(
        max_rows=max_rows, group_col=group_col, min_group_rows=min_group_rows,
        cont_label=cont_label, group_by=group_by),
    "group_force": lambda max_rows=None, group_col=None, min_group_rows=2,
    cont_label=" (Cont.)", group_by="auto", **kw: page_split_group_force(
        max_rows=max_rows, group_col=group_col, min_group_rows=min_group_rows,
        cont_label=cont_label, group_by=group_by),
}


def resolve_split(split, **ctx) -> Callable[[Frame], list[Frame]]:
    """Resolve a ``split=`` value (a string or a callable) to a split function.

    Strings map to the matching built-in factory, seeded with the ``ctx``
    call-time defaults (``max_rows`` / ``group_col`` / ...).  A callable is
    returned unchanged (the custom-split hook).
    """
    if callable(split):
        return split
    if isinstance(split, str):
        try:
            factory = _STRING_FACTORIES[split]
        except KeyError:
            raise ValueError(f"Unknown split strategy {split!r}.") from None
        return factory(**ctx)
    raise TypeError("`split` must be a strategy name or a split callable.")


def run_split(split, frame: Frame, **ctx) -> list[Frame]:
    """Resolve and apply a split, validating a custom callable's return value."""
    fn = resolve_split(split, **ctx)
    result = fn(frame)
    if not isinstance(result, (list, tuple)):
        raise PaginationError(
            "A split function must return a list of Frame objects; got "
            f"{type(result).__name__}."
        )
    out: list[Frame] = []
    for item in result:
        if not isinstance(item, Frame):
            raise PaginationError(
                "A split function must return Frame objects; got a "
                f"{type(item).__name__}."
            )
        out.append(item)
    return out


# -- Continuation-label helper -----------------------------------------------


def add_cont_label(frame: Frame, label: str, cont_label: str = " (Cont.)", col=0) -> Frame:
    """Prepend a continuation-label row to ``frame`` (mirrors R ``add_cont_label()``).

    Args:
        frame: The :class:`Frame` (or any :func:`as_frame` input) to prepend to.
        label: The group label; the inserted cell reads ``label + cont_label``.
        cont_label: The continuation suffix (default ``" (Cont.)"``).
        col: The 0-based column (or name) that carries the label (default 0).
    """
    frame = as_frame(frame)
    if not isinstance(label, str):
        raise TypeError("`label` must be a single string.")
    from .table import _resolve_col

    j = _resolve_col(col, frame.column_names)
    cont_row: list[Any] = ["" for _ in frame.column_names]
    cont_row[j] = f"{label}{cont_label}"
    return Frame(
        frame.column_names,
        [cont_row] + [list(r) for r in frame.rows],
        frame.name,
    )


# -- set_blank_rows() ---------------------------------------------------------


def set_blank_rows(
    data,
    blank_rows=None,
    blank_row_first: bool = False,
    blank_row_end: bool = False,
    group_col=None,
    group_by: str = "auto",
) -> Frame:
    """Resolve a blank-row spec and attach the positions to a frame.

    Mirrors R's ``set_blank_rows()``: resolves ``blank_rows`` (the same spec
    :func:`~rtfreporter.rtftable` accepts, plus the string ``"between_groups"``)
    into 0-based positions and stores them on the returned
    :class:`Frame`'s :attr:`~Frame.blank_rows`, so
    ``rtftable(set_blank_rows(df, ...))`` picks them up automatically.

    Args:
        data: A ``(column_names, rows)`` pair, dict, list of row dicts, DataFrame,
            or :class:`Frame`.
        blank_rows: ``None``; a 0-based ``int`` / sentinel / list of them;
            ``"between_groups"`` (a blank at every group-value change); or a
            :func:`~rtfreporter.blank_rows_by_change` /
            :func:`~rtfreporter.blank_rows_by_rule` spec.
        blank_row_first, blank_row_end: Also add a blank at the top / bottom.
        group_col: Group column (name / 0-based index) for ``"between_groups"``;
            ``None`` uses column 0.
        group_by: Group detection: ``"auto"`` / ``"value"`` (implemented);
            ``"indent"`` / ``"filled"`` raise :class:`NotImplementedError`.

    Returns:
        A :class:`Frame` with :attr:`~Frame.blank_rows` set (``None`` when the
        resolved position set is empty).
    """
    from .blank_rows import AFTER_LAST, BEFORE_FIRST, BlankRowsByChange, BlankRowsByRule
    from .table import _resolve_blank_rows

    frame = as_frame(data)
    names, rows = frame.column_names, frame.rows
    nrows = len(rows)

    def is_spec_obj(s):
        return isinstance(s, (BlankRowsByChange, BlankRowsByRule))

    items = list(blank_rows) if isinstance(blank_rows, (list, tuple)) else [blank_rows]
    internal: set[int] = set()
    for it in items:
        if it is None:
            continue
        if isinstance(it, str):
            if it != "between_groups":
                raise ValueError(f"Unrecognised blank_rows string {it!r}.")
            if group_by not in ("auto", "value"):
                raise NotImplementedError(
                    f"set_blank_rows(group_by={group_by!r}) is not implemented; "
                    "only 'auto' / 'value' (value-change detection) is supported."
                )
            gidx = _resolve_group(group_col, names)
            from .blank_rows import blank_rows_by_change

            internal.update(blank_rows_by_change(gidx).positions(names, rows))
        elif is_spec_obj(it) or isinstance(it, (int,)) or it is BEFORE_FIRST or it is AFTER_LAST:
            internal.update(_resolve_blank_rows(it, names, rows))
        else:
            internal.update(_resolve_blank_rows(it, names, rows))
    if blank_row_first:
        internal.add(0)
    if blank_row_end:
        internal.add(nrows)

    pos = sorted(p for p in internal if 0 <= p <= nrows)
    # Convert internal positions (p = before data row p) back to the public
    # convention rtftable() understands: BEFORE_FIRST for the top, else i-1.
    public = [BEFORE_FIRST if p == 0 else p - 1 for p in pos]
    frame.blank_rows = public or None
    return frame


# -- Standalone paginate() ----------------------------------------------------


def paginate(
    data,
    split="none",
    split_rows=None,
    max_rows: int | None = None,
    group_col=None,
    group_by: str = "auto",
    sort_by=None,
    sort_desc=None,
    cont_label: str = " (Cont.)",
    min_group_rows: int = 2,
    align_count_pct: bool = False,
    cell_format=None,
) -> list[Frame]:
    """Paginate ``data`` into a list of per-page :class:`Frame` objects.

    Mirrors R's ``paginate()``: applies an optional sort and cell-format pass,
    then the ``split`` strategy (a built-in name or a custom callable).  Returns
    the per-page frames (use :func:`~rtfreporter.as_rtftables` to also build
    :class:`~rtfreporter.RtfTable` pages).

    Args:
        data: A ``(column_names, rows)`` pair, dict of columns, list of row
            dicts, DataFrame, or :class:`Frame`.
        split: A strategy name or a custom split callable (see module docs).
        split_rows, max_rows, group_col, group_by, sort_by, sort_desc,
        cont_label, min_group_rows: As in :func:`~rtfreporter.as_rtftables`.
        align_count_pct, cell_format: Optional pre-split cell-format pass.
    """
    frame = as_frame(data)
    names = frame.column_names
    rows = [list(r) for r in frame.rows]

    from .adapters import _resolve_indices, _sort_rows

    sort_idx = _resolve_indices(sort_by, names)
    if sort_idx:
        rows = _sort_rows(rows, sort_idx, sort_desc)

    if cell_format is not None or align_count_pct:
        from .format_count_pct import (
            apply_cell_format,
            realign_count_pct_df,
            resolve_cell_format,
        )

        if cell_format is not None:
            fl = resolve_cell_format(cell_format, len(names))
            if fl is not None:
                apply_cell_format(rows, names, fl)
        elif align_count_pct:
            realign_count_pct_df(rows, names)

    ctx = dict(
        split_rows=split_rows,
        max_rows=max_rows,
        group_col=group_col,
        group_by=group_by,
        cont_label=cont_label,
        min_group_rows=min_group_rows,
    )
    return run_split(split, Frame(names, rows), **ctx)
