"""Count / percent display-width formatters.

Ported from ``R/format_count_pct.R`` and ``R/cell_format.R``.  Clinical TFL
cells of the form ``"n (xx.x)"`` need consistent display widths so columns line
up in a monospaced renderer.  The public functions are:

* :func:`format_count_pct` -- build padded ``"n (xx.x)"`` strings from numeric
  ``count`` / ``pct`` vectors (fixed 10-/11-character width branches).
* :func:`realign_count_pct` -- re-pad already-formatted ``"n (xx.x)"`` strings
  to the same fixed width; non-matching strings pass through unchanged.
* :func:`fmt_right_align` -- right-justify a column to its widest cell.
* :func:`fmt_count_paren` -- align ``count (parenthetical)`` cells to the
  column's actual digit widths; bare counts are left untouched.
* :func:`fmt_count_paren_bare` -- as above, but also pad bare integer counts
  into the same count field.

Padding uses a non-breaking space (U+00A0) by default so RTF / Word do not
collapse the alignment; pass ``nbsp=" "`` for plain-text output.
"""

from __future__ import annotations

import math
import re

NBSP = "\u00a0"


def _is_na(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def _as_str_na_empty(v) -> str:
    """``as.character`` with ``NA -> ""`` (R's ``x[is.na(x)] <- ""``)."""
    return "" if _is_na(v) else str(v)


def _fmt_int3(v) -> str:
    """Format an integer in a width-3 field; ``NA`` renders as ``" NA"``."""
    if _is_na(v):
        return "NA".rjust(3)
    return f"{int(v):3d}"


def _seq(x):
    """Coerce a scalar or iterable to a list (a str is treated as a scalar)."""
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def format_count_pct(
    count,
    pct,
    pct_unit: str = "fraction",
    nbsp: str = NBSP,
    pct_sign: bool = False,
) -> list[str]:
    """Format ``count`` + ``pct`` pairs to a uniform display width.

    Args:
        count: An integer/float, or a list of them.  ``NA`` (``None``/``nan``)
            and ``0`` produce the count-only branch (no parentheses).
        pct: A percentage value or list.  By default a *fraction* in ``[0, 1]``;
            pass ``pct_unit="percent"`` when values are already in ``[0, 100]``.
            Recycled against ``count`` when one argument is length 1.
        pct_unit: ``"fraction"`` (default, ``0..1``) or ``"percent"`` (``0..100``).
        nbsp: Character used to replace padding spaces (default U+00A0).  Pass
            ``" "`` for plain text.
        pct_sign: When ``True``, a literal ``%`` is placed before the closing
            parenthesis and every branch is one character wider so the ``)``
            still aligns.

    Returns:
        A list of strings the same length as the recycled inputs.
    """
    if pct_unit not in ("fraction", "percent"):
        raise ValueError('`pct_unit` must be "fraction" or "percent".')
    counts = _seq(count)
    pcts = _seq(pct)
    for name, vals in (("count", counts), ("pct", pcts)):
        for v in vals:
            if not (_is_na(v) or isinstance(v, (int, float))):
                raise TypeError(f"`{name}` must be numeric.")
    n_in = max(len(counts), len(pcts))
    if len(counts) == 1:
        counts = counts * n_in
    if len(pcts) == 1:
        pcts = pcts * n_in
    if len(counts) != len(pcts):
        raise ValueError(
            "`count` and `pct` must have the same length (or one be length 1)."
        )

    out: list[str] = []
    for c1, p in zip(counts, pcts, strict=True):
        if not _is_na(p) and pct_unit == "fraction":
            p = p * 100
        if _is_na(c1) or _is_na(p) or int(c1) == 0:
            raw = _fmt_int3(c1) + ("        " if pct_sign else "       ")
        elif p >= 100:
            paren = f"({round(p):3d}%)" if pct_sign else f"({round(p):3d})"
            raw = f"{_fmt_int3(c1)}  {paren}"
        elif p < 10:
            paren = f"({p:3.1f}%)" if pct_sign else f"({p:3.1f})"
            raw = f"{_fmt_int3(c1)}  {paren}"
        else:
            paren = f"({p:4.1f}%)" if pct_sign else f"({p:4.1f})"
            raw = f"{_fmt_int3(c1)} {paren}"
        if nbsp != " ":
            raw = raw.replace(" ", nbsp)
        out.append(raw)
    return out


_REALIGN_RE = re.compile(r"^\s*(\d+)\s*\((\d+(?:\.\d+)?)(%?)\)\s*$")


def realign_count_pct(x, nbsp: str = NBSP) -> list[str]:
    """Re-pad existing ``"n (xx.x)"`` strings to a uniform display width.

    Cells matching ``^\\d+ \\(\\d+(\\.\\d+)?%?\\)$`` are reformatted through
    :func:`format_count_pct`; all others are returned unchanged.  An optional
    trailing ``%`` inside the parentheses is preserved.

    Args:
        x: A string or list of strings.
        nbsp: Padding character (see :func:`format_count_pct`).

    Returns:
        A list of strings the same length as ``x``.
    """
    if x is None:
        return x
    items = _seq(x)
    out = [_as_str_na_empty(v) for v in items]
    for i, s in enumerate(out):
        m = _REALIGN_RE.match(s)
        if m:
            n = int(m.group(1))
            pct = float(m.group(2))
            pct_sign = bool(m.group(3))
            out[i] = format_count_pct(
                n, pct, pct_unit="percent", nbsp=nbsp, pct_sign=pct_sign
            )[0]
    return out


def fmt_right_align(x, nbsp: str = NBSP) -> list[str]:
    """Right-justify every non-empty cell of a column to its widest cell.

    Empty cells are left empty.  ``nbsp`` (default U+00A0) is used for padding.
    """
    items = _seq(x)
    out = [_as_str_na_empty(v) for v in items]
    nz = [i for i, s in enumerate(out) if s.strip()]
    if not nz:
        return out
    w = max(len(out[i]) for i in nz)
    for i in nz:
        val = out[i].rjust(w)
        if nbsp != " ":
            val = val.replace(" ", nbsp)
        out[i] = val
    return out


_COUNT_CORE_RE = re.compile(r"^\s*(\d+)\s*(\((.*)\))?\s*$")


def _fmt_count_core(x, nbsp: str, bare: bool) -> list[str]:
    """Shared core for :func:`fmt_count_paren` / :func:`fmt_count_paren_bare`."""
    items = _seq(x)
    out = [_as_str_na_empty(v) for v in items]
    counts: list[str | None] = [None] * len(out)
    inners: list[str] = [""] * len(out)
    haspar: list[bool] = [False] * len(out)
    for i, s in enumerate(out):
        m = _COUNT_CORE_RE.match(s)
        if m and m.group(1):
            counts[i] = m.group(1)
            if m.group(2) is not None:
                haspar[i] = True
                inners[i] = m.group(3) if m.group(3) is not None else ""
    do = [counts[i] is not None and (haspar[i] or bare) for i in range(len(out))]
    if not any(do):
        return out
    wc = max(len(counts[i]) for i in range(len(out)) if do[i])
    inner_ws = [len(inners[i]) for i in range(len(out)) if haspar[i] and do[i]]
    wi = max(inner_ws) if inner_ws else 0
    full = wc + (2 + wi + 1 if wi > 0 else 0)
    for i in range(len(out)):
        if not do[i]:
            continue
        cc = counts[i].rjust(wc)
        if haspar[i]:
            val = f"{cc} ({inners[i].rjust(wi)})"
        else:
            val = cc.ljust(max(full, wc))
        if nbsp != " ":
            val = val.replace(" ", nbsp)
        out[i] = val
    return out


def fmt_count_paren(x, nbsp: str = NBSP) -> list[str]:
    """Align ``count (parenthetical)`` cells to the column's digit widths.

    Only cells that have parentheses are touched; a lone count such as ``"0"``,
    a continuous statistic like ``"75.2 (8.6)"`` (count is not a bare integer),
    free text, and empty cells are returned unchanged.
    """
    return _fmt_count_core(x, nbsp=nbsp, bare=False)


def fmt_count_paren_bare(x, nbsp: str = NBSP) -> list[str]:
    """Like :func:`fmt_count_paren`, but also pad bare integer counts.

    A lone integer with no parentheses (e.g. ``"0"`` for a zero count, or a raw
    total) is padded into the same count field so it lines up under the
    parenthetical cells.
    """
    return _fmt_count_core(x, nbsp=nbsp, bare=True)


# -- cell_format machinery (R cell_format.R) ---------------------------------


def resolve_cell_format(cell_format, ncol: int):
    """Resolve ``cell_format`` into a per-column list of callables (length ``ncol``).

    A single callable applies to columns ``1..ncol-1`` (column ``0`` -- the row
    label -- is left alone, the clinical convention).  A list is taken
    positionally (``cell_format[j]`` for column ``j``; non-callable entries are
    skipped).  Returns ``None`` when nothing applies.
    """
    if cell_format is None or ncol < 1:
        return None
    fl: list = [None] * ncol
    if callable(cell_format):
        for j in range(1, ncol):
            fl[j] = cell_format
    elif isinstance(cell_format, (list, tuple)):
        for j in range(min(len(cell_format), ncol)):
            if callable(cell_format[j]):
                fl[j] = cell_format[j]
    else:
        raise TypeError("`cell_format` must be a callable or a list of callables.")
    return fl


def _is_character_column(rows, j: int) -> bool:
    """A column is "character" when every non-empty cell is a string (R dtype)."""
    for r in rows:
        v = r[j]
        if _is_na(v) or v == "":
            continue
        if not isinstance(v, str):
            return False
    return True


def apply_cell_format(rows, column_names, fl) -> None:
    """Apply a resolved per-column format list to ``rows`` in place.

    Only character columns are reformatted (mirroring R, which skips non-string
    columns).  Each callable must return a sequence the same length as the
    column.
    """
    n = len(rows)
    for j, f in enumerate(fl):
        if not callable(f):
            continue
        if j >= len(column_names) or not _is_character_column(rows, j):
            continue
        col = [r[j] for r in rows]
        formatted = list(f(col))
        if len(formatted) != n:
            raise ValueError(
                "A `cell_format` function must return a vector the same length "
                f"as the column (got {len(formatted)}, expected {n})."
            )
        for i in range(n):
            rows[i][j] = _as_str_na_empty(formatted[i])


def realign_count_pct_df(rows, column_names, nbsp: str = NBSP) -> None:
    """Realign the count-percent cells of every character column except the first.

    Mirrors R's ``.realign_count_pct_df`` used by ``align_count_pct=True``.
    Operates on ``rows`` in place.
    """
    if len(column_names) < 2:
        return
    fl = [None] + [
        (lambda col, _nbsp=nbsp: realign_count_pct(col, nbsp=_nbsp))
        for _ in range(len(column_names) - 1)
    ]
    apply_cell_format(rows, column_names, fl)
