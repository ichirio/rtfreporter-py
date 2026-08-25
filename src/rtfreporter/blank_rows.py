"""Blank separator-row specifications.

Ported from ``R/blank_rows.R``.

**0-based position convention (a deliberate divergence from R).**  A bare
integer position ``i`` means *insert a blank row after data row* ``i`` (rows are
0-based, so ``0`` is the first data row).  The two R sentinels ``0`` (before the
first row) and ``-1`` (after the last row) are replaced by the named,
importable constants :data:`BEFORE_FIRST` and :data:`AFTER_LAST`.  They are
distinct sentinel objects -- **not** bare integers -- so a stray ``-1`` cannot
be silently misread as "after the last row"; passing a bare negative integer
raises a clear error pointing at :data:`AFTER_LAST`.

Example::

    rtftable(data, blank_rows=[BEFORE_FIRST, 2, AFTER_LAST])

inserts a blank row before the first data row, after data row ``2`` (the third
row), and after the last data row.

R-to-Python mapping:

===================  ==========================
R ``blank_rows``     Python ``blank_rows``
===================  ==========================
``0``                ``BEFORE_FIRST``
``k`` (1-based)      ``k - 1`` (0-based int)
``-1``               ``AFTER_LAST``
===================  ==========================

Specs are resolved against the table body at construction time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


class _BlankRowSentinel:
    """A distinct, importable blank-row position marker.

    Used for :data:`BEFORE_FIRST` and :data:`AFTER_LAST` so that positions like
    "before the first row" / "after the last row" are explicit named values
    rather than magic integers.
    """

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return self._name


#: Insert a blank row *before* the first data row (R's ``0`` sentinel).
BEFORE_FIRST = _BlankRowSentinel("BEFORE_FIRST")

#: Insert a blank row *after* the last data row (R's ``-1`` sentinel).
AFTER_LAST = _BlankRowSentinel("AFTER_LAST")


@dataclass
class BlankRowsByChange:
    """Insert a blank row wherever the group of ``cols`` changes.

    ``group_by`` chooses how a boundary is detected, exactly as in
    :func:`~rtfreporter.as_rtftables`: ``"value"`` (the default) compares the
    cell values, while ``"indent"`` / ``"filled"`` treat a flush-left or a
    non-empty cell as a group header.  ``"auto"`` infers the mode from the
    column's content.

    ``include_before_first`` and ``include_after_last`` default to ``True``, so
    the block of grouped rows is fenced top and bottom, matching R.
    """

    cols: list
    group_by: str = "value"
    include_before_first: bool = True
    include_after_last: bool = True

    def positions(self, column_names: list[str], rows: list[list]) -> set[int]:
        idxs = [_col_index(c, column_names) for c in _as_list(self.cols)]
        keys = self._keys(idxs, rows)
        out: set[int] = set()
        for i in range(1, len(keys)):
            if keys[i] != keys[i - 1]:
                out.add(i)
        if self.include_before_first:
            out.add(0)
        if self.include_after_last:
            out.add(len(rows))
        return out

    def _keys(self, idxs: list[int], rows: list[list]) -> list:
        """Per-row group keys, honouring ``group_by``."""
        if self.group_by == "value":
            return [tuple(row[c] for c in idxs) for row in rows]
        # Header-based detection reuses the adapter's shared implementation so
        # the two cannot drift apart.
        from .adapters import _compute_group_keys

        if len(idxs) != 1:
            raise ValueError(
                'blank_rows_by_change(group_by=) other than "value" needs exactly '
                "one column."
            )
        return _compute_group_keys(rows, idxs[0], self.group_by)


@dataclass
class BlankRowsByRule:
    """Insert a blank row before/after every row whose ``col`` matches ``pattern``."""

    col: object
    pattern: str
    where: str = "before"

    def positions(self, column_names: list[str], rows: list[list]) -> set[int]:
        if self.where not in ("before", "after"):
            raise ValueError('`where` must be "before" or "after".')
        idx = _col_index(self.col, column_names)
        rx = re.compile(self.pattern)
        out: set[int] = set()
        for i, row in enumerate(rows, start=1):
            val = row[idx]
            if val is not None and rx.search(str(val)):
                out.add(i - 1 if self.where == "before" else i)
        return out


def blank_rows_by_change(
    cols,
    group_by: str = "value",
    include_before_first: bool = True,
    include_after_last: bool = True,
) -> BlankRowsByChange:
    """Build a spec that inserts a blank row when the group of ``cols`` changes.

    Args:
        cols: Column name(s) or 0-based index/indices to watch.
        group_by: How a boundary is detected -- ``"value"`` (default),
            ``"indent"``, ``"filled"`` or ``"auto"``.
        include_before_first: Also blank before the first row (default ``True``).
        include_after_last: Also blank after the last row (default ``True``).
    """
    return BlankRowsByChange(cols, group_by, include_before_first, include_after_last)


def blank_rows_by_rule(col, pattern: str, where: str = "before") -> BlankRowsByRule:
    """Build a spec that inserts a blank row before/after regex matches in ``col``."""
    return BlankRowsByRule(col, pattern, where)


def _as_list(x):
    return list(x) if isinstance(x, (list, tuple)) else [x]


def _col_index(ref, names: list[str]) -> int:
    if isinstance(ref, str):
        if ref not in names:
            raise ValueError(f"Unknown column name {ref!r}.")
        return names.index(ref)
    return int(ref)
