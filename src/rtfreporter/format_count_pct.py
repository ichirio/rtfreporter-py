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
* :func:`fmt_value_paren` -- align ``value (parenthetical)`` cells whose value
  is any text (a mean, a median), the parenthetical block right-justified.

Every formatter takes ``na``, the text a missing value prints as (``""``, the
default, leaves the cell empty), and :func:`format_count_pct` rounds the
percent with the package rule (see :func:`~rtfreporter.round_num`).  Padding
uses a non-breaking space (U+00A0) by default so RTF / Word do not collapse
the alignment; pass ``nbsp=" "`` for plain-text output.
"""

from __future__ import annotations

import math
import re

from .num_format import rounder

NBSP = " "


def _is_na(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def _as_str_na(v, na: str = "") -> str:
    """``as.character`` with ``NA -> na`` (R's ``x[is.na(x)] <- na``)."""
    return na if _is_na(v) else str(v)


def _as_str_na_empty(v) -> str:
    return _as_str_na(v, "")


def check_na_text(na, arg: str = "na") -> str:
    """Validate a missing-value display text: a single string.  ``None`` reads
    as ``""``; the whole point of the argument is to say what a missing value
    should look like, so a non-string is an error."""
    if na is None:
        return ""
    if not isinstance(na, str):
        raise TypeError(
            f"`{arg}` must be a single string -- the text printed for a missing "
            'value (e.g. "-" or "NA").  "" (the default) leaves the cell empty.'
        )
    return na


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
    na: str = "",
    rounding: str | None = None,
) -> list[str]:
    """Format ``count`` + ``pct`` pairs to a uniform display width.

    Width rules -- every branch produces a 10-character string, and the
    closing parenthesis lands at column 10 so it lines up across rows::

        count missing (None/nan)  ->  the `na` token, right-justified in the
                                      count field ("" = empty cell)
        count = 0, or pct missing ->  "%3d       "     (no paren)
        pct  >= 100               ->  "%3d  (%3d)"     e.g. " 30  (100)"
        0 < pct < 10              ->  "%3d  (%3.1f)"   e.g. "  5  (5.0)"
        10 <= pct < 100           ->  "%3d (%4.1f)"    e.g. " 14 (50.0)"

    Args:
        count: An integer/float, or a list of them.
        pct: A percentage value or list.  By default a *fraction* in ``[0, 1]``;
            pass ``pct_unit="percent"`` when values are already in ``[0, 100]``.
            Recycled against ``count`` when one argument is length 1.
        pct_unit: ``"fraction"`` (default, ``0..1``) or ``"percent"`` (``0..100``).
        nbsp: Character used to replace padding spaces (default U+00A0).  Pass
            ``" "`` for plain text.
        pct_sign: When ``True``, a literal ``%`` is placed before the closing
            parenthesis and every branch is one character wider so the ``)``
            still aligns.
        na: The text a missing *count* prints as.  A missing percent next to a
            real count is not missing data, and still prints the count.
        rounding: ``"r"`` / ``"sas"``; ``None`` reads the package option.  The
            percent is rounded ONCE, with this rule, before any branch reads
            it: ``9.96`` no longer takes the "< 10" width and prints ``10.0``.

    Returns:
        A list of strings the same length as the recycled inputs.
    """
    if pct_unit not in ("fraction", "percent"):
        raise ValueError('`pct_unit` must be "fraction" or "percent".')
    rnd = rounder(rounding)
    na = check_na_text(na)
    counts = _seq(count)
    pcts = _seq(pct)
    for vals in (counts, pcts):
        for v in vals:
            if not (_is_na(v) or (isinstance(v, (int, float)) and not isinstance(v, bool))):
                raise TypeError("`count` and `pct` must both be numeric.")
    n_in = max(len(counts), len(pcts))
    if len(counts) == 1:
        counts = counts * n_in
    if len(pcts) == 1:
        pcts = pcts * n_in
    if len(counts) != len(pcts):
        raise ValueError(
            "`count` and `pct` must have the same length (or one of them be length 1)."
        )

    out: list[str] = []
    for c1, p in zip(counts, pcts, strict=True):
        if not _is_na(p) and pct_unit == "fraction":
            p = p * 100
        if not _is_na(p) and math.isfinite(p):
            p = rnd(float(p), 1)
        w = 11 if pct_sign else 10  # full width of a cell
        if _is_na(c1):
            # The count itself is missing -- print the token in the count field.
            if not na:
                out.append("")
                continue
            raw = na.rjust(3).ljust(w)
        elif not math.isfinite(c1):
            # Inf / -Inf is not missing; show it rather than hide a bad numerator.
            raw = _r_num(c1).rjust(3).ljust(w)
        elif _is_na(p) or not math.isfinite(p) or int(c1) == 0:
            # A real count with no usable percent still prints, on its own.
            raw = f"{int(c1):3d}" + ("        " if pct_sign else "       ")
        elif p >= 100:
            # Two spaces before '(' so the ')' aligns with the other
            # paren-bearing branches.
            p0 = int(rnd(p, 0))
            raw = f"{int(c1):3d}  ({p0:3d}%)" if pct_sign else f"{int(c1):3d}  ({p0:3d})"
        elif p < 10:
            raw = f"{int(c1):3d}  ({p:3.1f}%)" if pct_sign else f"{int(c1):3d}  ({p:3.1f})"
        else:
            raw = f"{int(c1):3d} ({p:4.1f}%)" if pct_sign else f"{int(c1):3d} ({p:4.1f})"
        if nbsp != " ":
            raw = raw.replace(" ", nbsp)
        out.append(raw)
    return out


def _r_num(v) -> str:
    """R's ``as.character()`` of a non-finite number."""
    if math.isnan(v):
        return "NaN"
    return "Inf" if v > 0 else "-Inf"


_REALIGN_RE = re.compile(r"^\s*(\d+)\s*\((\d+(?:\.\d+)?)(%?)\)\s*$")


def realign_count_pct(x, nbsp: str = NBSP, na: str = "") -> list[str]:
    """Re-pad existing ``"n (xx.x)"`` strings to a uniform display width.

    Cells matching ``^\\d+ \\(\\d+(\\.\\d+)?%?\\)$`` are reformatted through
    :func:`format_count_pct`; all others are returned unchanged.  An optional
    trailing ``%`` inside the parentheses is preserved.  A missing cell (or one
    holding the ``na`` token) is aligned like a missing count, following the
    column's ``%`` -- unless no count/percent cell exists to line it up with.
    """
    if x is None:
        return x
    na = check_na_text(na)
    items = _seq(x)
    if not items:
        return []
    out = [_as_str_na_empty(v) for v in items]
    matches = [_REALIGN_RE.match(s) for s in out]
    hit = [m is not None for m in matches]
    col_pct_sign = any(bool(m.group(3)) for m, h in zip(matches, hit, strict=True) if h)
    pad_na = bool(na) and any(hit)
    for i, s in enumerate(out):
        m = matches[i]
        if m:
            out[i] = format_count_pct(
                int(m.group(1)), float(m.group(2)), pct_unit="percent",
                nbsp=nbsp, pct_sign=bool(m.group(3)),
            )[0]
        elif na and (_is_na(items[i]) or s.strip() == na):
            out[i] = (
                format_count_pct(None, None, pct_unit="percent", nbsp=nbsp,
                                 pct_sign=col_pct_sign, na=na)[0]
                if pad_na else na  # shown, but with nothing to line it up with
            )
    return out


def fmt_right_align(x, nbsp: str = NBSP, na: str = "") -> list[str]:
    """Right-justify every non-empty cell of a column to its widest cell.

    Empty cells are left empty; a missing value prints as ``na`` first.
    ``nbsp`` (default U+00A0) is used for padding.
    """
    na = check_na_text(na)
    items = _seq(x)
    if not items:
        return []
    out = [_as_str_na(v, na) for v in items]
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


def _fmt_count_core(x, nbsp: str, bare: bool, na: str = "") -> list[str]:
    """Shared core for :func:`fmt_count_paren` / :func:`fmt_count_paren_bare`.

    ``na`` is the text a missing value prints as.  A missing cell is aligned
    like a BARE count whatever ``bare`` says -- asking for the token is asking
    to see it under the counts -- and the count field widens to the token if
    the token is the wider of the two, so the right edges still meet.
    """
    na = check_na_text(na)
    items = _seq(x)
    if not items:
        return []
    out = [_as_str_na(v, na) for v in items]
    n = len(out)
    counts: list[str | None] = [None] * n
    inners: list[str] = [""] * n
    haspar: list[bool] = [False] * n
    for i, s in enumerate(out):
        m = _COUNT_CORE_RE.match(s)
        if m and m.group(1):
            counts[i] = m.group(1)
            if m.group(2) is not None:
                haspar[i] = True
                inners[i] = m.group(3) if m.group(3) is not None else ""
    # Cells holding the missing-value token.  With na = "" (the default) `nat`
    # is all False and everything below behaves exactly as it did before.
    nat = [bool(na) and counts[i] is None and not _is_na(items[i]) and out[i].strip() == na
           for i in range(n)]
    do = [(counts[i] is not None and (haspar[i] or bare)) or nat[i] for i in range(n)]
    if not any(do):
        return out
    isc = [do[i] and not nat[i] for i in range(n)]
    wc = max([len(counts[i]) for i in range(n) if isc[i]] + ([len(na)] if any(nat) else []))
    inner_ws = [len(inners[i]) for i in range(n) if haspar[i] and do[i]]
    wi = max(inner_ws) if inner_ws else 0
    full = wc + (2 + wi + 1 if wi > 0 else 0)
    for i in range(n):
        if not do[i]:
            continue
        if nat[i]:
            val = na.rjust(wc).ljust(max(full, wc))
        else:
            cc = counts[i].rjust(wc)
            if haspar[i]:
                val = f"{cc} ({inners[i].rjust(wi)})"
            else:
                val = cc.ljust(max(full, wc))
        if nbsp != " ":
            val = val.replace(" ", nbsp)
        out[i] = val
    return out


def fmt_count_paren(x, nbsp: str = NBSP, na: str = "") -> list[str]:
    """Align ``count (parenthetical)`` cells to the column's digit widths.

    Only cells that have parentheses are touched; a lone count such as ``"0"``,
    a continuous statistic like ``"75.2 (8.6)"`` (count is not a bare integer),
    free text, and empty cells are returned unchanged.
    """
    return _fmt_count_core(x, nbsp=nbsp, bare=False, na=na)


def fmt_count_paren_bare(x, nbsp: str = NBSP, na: str = "") -> list[str]:
    """Like :func:`fmt_count_paren`, but also pad bare integer counts.

    A lone integer with no parentheses (e.g. ``"0"`` for a zero count, or a raw
    total) is padded into the same count field so it lines up under the
    parenthetical cells.
    """
    return _fmt_count_core(x, nbsp=nbsp, bare=True, na=na)


_VALUE_PAREN_RE = re.compile(r"^\s*([^()]*[^()\s])\s*\(([^()]*)\)\s*$")
_VALUE_BARE_RE = re.compile(r"^\s*([^()]*[^()\s])\s*$")


def fmt_value_paren(x, nbsp: str = NBSP, na: str = "") -> list[str]:
    """Align ``value (parenthetical)`` cells whose value is any text.

    The value (a mean, a median, a count) is right-justified in its field and
    the whole ``(...)`` block is right-justified to a common right edge, so the
    padding falls BEFORE the ``(`` and every ``)`` lands in the same column.  A
    zero count is one fact, not two: ``"0 (0.0)"`` prints as ``"0"``; and 100%
    prints without decimals, ``"(100.0)"`` -> ``"(100)"`` -- both as
    :func:`format_count_pct` renders them.  A label with a parenthesis of its
    own (``"Mean (SD) by visit"``) matches nothing and is left alone.
    """
    na = check_na_text(na)
    items = _seq(x)
    if not items:
        return []
    out = [_as_str_na(v, na) for v in items]
    n = len(out)
    value: list[str | None] = [None] * n  # the text before the parenthesis
    inner: list[str | None] = [None] * n  # the text inside it, None when there is none
    for i, s in enumerate(out):
        m = _VALUE_PAREN_RE.match(s)
        if m:
            value[i] = m.group(1)
            inner[i] = m.group(2).strip()
            continue
        m = _VALUE_BARE_RE.match(s)
        if m:
            value[i] = m.group(1)

    for i in range(n):
        if inner[i] is None:
            continue
        # "0 (0.0)" -> "0"; only an ALL-ZERO parenthetical is dropped.
        if re.fullmatch(r"0+", value[i] or "") and re.search(r"[0-9]", inner[i]) \
                and not re.search(r"[1-9]", inner[i]):
            inner[i] = None
            continue
        # "(100.0)" -> "(100)", "(100.0%)" -> "(100%)"; only a plain number.
        pc = inner[i][:-1] if inner[i].endswith("%") else inner[i]
        if re.fullmatch(r"[0-9]+(\.[0-9]+)?", pc) and float(pc) >= 100:
            inner[i] = str(int(round(float(pc)))) + ("%" if inner[i].endswith("%") else "")

    do = [v is not None for v in value]
    if not any(do):
        return out
    hp = [do[i] and inner[i] is not None for i in range(n)]
    wv = max(len(value[i]) for i in range(n) if do[i])
    wb = max(len(inner[i]) for i in range(n) if hp[i]) + 2 if any(hp) else 0
    full = wv + (1 + wb if wb > 0 else 0)
    for i in range(n):
        if not do[i]:
            continue
        v = value[i].rjust(wv)
        if hp[i]:
            val = f"{v} " + f"({inner[i]})".rjust(wb)
        else:
            val = v.ljust(max(full, wv))
        if nbsp != " ":
            val = val.replace(" ", nbsp)
        out[i] = val
    return out


# -- cell_format machinery (R cell_format.R) ---------------------------------

#: A built-in can be passed as the function itself or NAMED as a string --
#: what a report script, a config file or a recipe wants to write.  The
#: ``fmt_`` prefix is optional, so both "fmt_count_paren" and "count_paren"
#: resolve.
CELL_FORMATS = {
    "right_align": "fmt_right_align",
    "count_paren": "fmt_count_paren",
    "count_paren_bare": "fmt_count_paren_bare",
    "value_paren": "fmt_value_paren",
    "count_pct": "realign_count_pct",
    "realign_count_pct": "realign_count_pct",
}


def builtin_cell_format(name: str, arg: str = "cell_format"):
    """One built-in, by name.  Unknown names list what there is."""
    key = re.sub(r"^fmt_", "", name.strip())
    fn = CELL_FORMATS.get(key)
    if fn is None:
        names = ", ".join(f'"{k}"' for k in CELL_FORMATS if k != "realign_count_pct")
        raise ValueError(
            f'`{arg}`: "{name}" is not a built-in cell format.  The built-ins are '
            f'{names} (the "fmt_" prefix is optional), or pass a function of your own.'
        )
    return globals()[fn]


def _as_cell_format_fn(f, arg: str = "cell_format"):
    """One cell-format value -> a callable, or ``None`` when it is neither a
    callable nor a name.  A bad NAME is an error."""
    if callable(f):
        return f
    if isinstance(f, str):
        return builtin_cell_format(f, arg)
    return None


def resolve_cell_format(cell_format, ncol: int, arg: str = "cell_format"):
    """Resolve ``cell_format`` into a per-column list of callables (length ``ncol``).

    A single callable, or the NAME of a built-in, applies to columns
    ``1..ncol-1`` (column ``0`` -- the row label -- is left alone, the clinical
    convention).  A list is taken positionally (``cell_format[j]`` for column
    ``j``; entries may be callables or built-in names, anything else is
    skipped).  Returns ``None`` when nothing applies.
    """
    if cell_format is None or ncol < 1:
        return None
    fl: list = [None] * ncol
    single = _as_cell_format_fn(cell_format, arg)
    if single is not None:
        for j in range(1, ncol):
            fl[j] = single
    elif isinstance(cell_format, (list, tuple)):
        for j in range(min(len(cell_format), ncol)):
            f = _as_cell_format_fn(cell_format[j], arg)
            if f is not None:
                fl[j] = f
    else:
        raise TypeError(
            f"`{arg}` must be a function, the name of a built-in cell format, "
            "or a list of either."
        )
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


def _call_cell_format(f, col, na: str):
    """Call a cell formatter, handing it ``na`` when it takes one (R
    ``.call_cell_format()``), so a missing cell's text lines up too."""
    import inspect

    try:
        takes_na = "na" in inspect.signature(f).parameters
    except (TypeError, ValueError):
        takes_na = False
    return f(col, na=na) if takes_na else f(col)


def apply_cell_format(rows, column_names, fl, na: str = "") -> None:
    """Apply a resolved per-column format list to ``rows`` in place.

    Only character columns are reformatted (mirroring R, which skips non-string
    columns).  Each callable must return a sequence the same length as the
    column; one that takes ``na`` is given the call's missing-value text.
    """
    n = len(rows)
    for j, f in enumerate(fl):
        if not callable(f):
            continue
        if j >= len(column_names) or not _is_character_column(rows, j):
            continue
        col = [r[j] for r in rows]
        formatted = list(_call_cell_format(f, col, na))
        if len(formatted) != n:
            raise ValueError(
                "A `cell_format` function must return a vector the same length "
                f"as the column (got {len(formatted)}, expected {n})."
            )
        for i in range(n):
            rows[i][j] = _as_str_na_empty(formatted[i])


def realign_count_pct_df(rows, column_names, nbsp: str = NBSP, na: str = "") -> None:
    """Realign the count-percent cells of every character column except the first.

    Mirrors R's ``.realign_count_pct_df`` used by ``align_count_pct=True``.
    Operates on ``rows`` in place.
    """
    if len(column_names) < 2:
        return
    fl = [None] + [
        (lambda col, na="", _nbsp=nbsp: realign_count_pct(col, nbsp=_nbsp, na=na))
        for _ in range(len(column_names) - 1)
    ]
    apply_cell_format(rows, column_names, fl, na=na)
