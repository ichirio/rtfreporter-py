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
    """Insert a blank row wherever the value of ``cols`` changes."""

    cols: list
    include_before_first: bool = False
    include_after_last: bool = False

    def positions(self, column_names: list[str], rows: list[list]) -> set[int]:
        idxs = [_col_index(c, column_names) for c in _as_list(self.cols)]
        out: set[int] = set()
        prev = None
        for i, row in enumerate(rows, start=1):
            key = tuple(row[c] for c in idxs)
            if i > 1 and key != prev:
                out.add(i - 1)
            prev = key
        if self.include_before_first:
            out.add(0)
        if self.include_after_last:
            out.add(len(rows))
        return out


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
    cols, include_before_first: bool = False, include_after_last: bool = False
) -> BlankRowsByChange:
    """Build a spec that inserts a blank row when ``cols`` change value."""
    return BlankRowsByChange(cols, include_before_first, include_after_last)


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
