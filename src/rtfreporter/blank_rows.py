"""Blank separator-row specifications.

Ported from ``R/blank_rows.R``.  Blank-row positions are 1-based "insert after
data row *p*" markers, with ``0`` meaning "before the first row" and ``-1`` /
``nrows`` meaning "after the last row".  Specs are resolved against the table
body at construction time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


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
