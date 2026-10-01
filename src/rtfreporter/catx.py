"""``catx()``: join values with a separator, skipping the missing ones.

Ported from ``R/catx.R`` (R #360).  The SAS ``CATX`` rule: the separator goes
between the values, and a missing or empty value is dropped rather than
printed as a doubled separator.
"""

from __future__ import annotations

import math


def _as_text(v) -> str:
    """A value as R's ``as.character()`` writes it: missing is ``""``, a
    whole number has no decimals, others use up to 15 significant digits."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        if math.isinf(v):
            return "Inf" if v > 0 else "-Inf"
        if v.is_integer() and abs(v) < 1e15:
            return str(int(v))
        return f"{v:.15g}"
    return str(v)


def catx(sep: str, *args) -> list[str]:
    """Join values with ``sep``, skipping the missing and empty ones.

    Each argument is a scalar or a vector (list / tuple / Series); vectors must
    share one length, and a scalar is recycled.  Values are trimmed first, so
    a blank value counts as empty::

        >>> catx(" / ", ["Headache", "Nausea"], ["Mild", None])
        ['Headache / Mild', 'Nausea']

    Returns:
        A list of strings, one per element.
    """
    if not isinstance(sep, str):
        raise ValueError("`sep` must be a single string.")
    if not args:
        return []
    vals = []
    for a in args:
        if isinstance(a, (str, int, float)) or a is None:
            items = [a]
        elif hasattr(a, "tolist"):
            items = list(a.tolist())
        else:
            items = list(a)
        vals.append([_as_text(v).strip() for v in items])
    lens = [len(v) for v in vals]
    n = max(lens)
    if n == 0:
        return []
    if any(ln not in (n, 1) for ln in lens):
        raise ValueError(
            "All arguments must be the same length, or length 1: got "
            + ", ".join(str(ln) for ln in lens) + "."
        )
    vals = [v * n if len(v) == 1 else v for v in vals]
    return [sep.join(p for p in (v[i] for v in vals) if p) for i in range(n)]
