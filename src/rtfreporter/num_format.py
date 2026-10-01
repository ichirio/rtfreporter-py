"""Numeric -> text: one rounding rule for the whole package.

Ported from ``R/num_format.R`` (#476).  ``"r"`` (the default) rounds an exact
half to the even digit, as R's ``round()`` and Python's :func:`round` do;
``"sas"`` rounds it away from zero, as SAS ``ROUND()`` does, and absorbs a
binary representation error the way SAS's fuzz does (``2.675 -> 2.68``).  A
study that has to match a SAS-produced table says so **once**, with
``rtfreporter_options(rounding="sas")``; an explicit ``rounding=`` still wins.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from .config import _opt

_SQRT_EPS = math.sqrt(2.220446049250313e-16)


def _round_half_up(x: float, digits: int = 0) -> float:
    """Half-away-from-zero rounding, as SAS does it.  The epsilon term defeats
    the binary representation of values like 2.675 (stored as 2.67499...)."""
    if math.isnan(x) or math.isinf(x):
        return x
    z = abs(x) * 10**digits
    return math.copysign(math.floor(z + 0.5 + _SQRT_EPS * abs(z)) / 10**digits, x) if x != 0 else 0.0


def _round_half_even(x: float, digits: int = 0) -> float:
    """``base::round()`` as R >= 4.0 does it (``fround()`` in R's nmath).

    Not Python's :func:`round`, which rounds the binary value: R takes the two
    candidates either side, keeps the nearer, and on a tie (as the doubles
    subtract) the even one.  So ``23.445`` -> ``23.44`` and ``0.05`` -> ``0.0``
    at 1 digit, where Python gives ``23.45`` and ``0.1``.
    """
    if math.isnan(x) or math.isinf(x) or x == 0:
        return x
    if digits == 0:
        return math.copysign(float(round(x)), x)  # nearbyint: half to even, sign kept
    sgn = -1.0 if x < 0 else 1.0
    x = abs(x)
    l10x = math.log10(2) * (0.5 + math.floor(math.log2(x)))
    if l10x + digits > 15:  # DBL_DIG: nothing left to round
        return sgn * x
    pow10 = 10.0**digits
    x10 = pow10 * x
    i10 = math.floor(x10)
    xd = i10 / pow10
    xu = math.ceil(x10) / pow10
    du = xu - x
    dd = x - xd
    return sgn * (xu if (du < dd or (du == dd and math.fmod(i10, 2.0) == 1)) else xd)


def rounding_type(rounding: str | None = None) -> str:
    """The rounding family, resolved once: ``None`` reads the
    ``rtfreporter.rounding`` option."""
    if rounding is None:
        rounding = _opt("rounding")
    if not isinstance(rounding, str) or rounding not in ("r", "sas"):
        raise ValueError(
            '`rounding` must be "r" (half to even, as round() does) '
            'or "sas" (half away from zero, as SAS ROUND() does).'
        )
    return rounding


def rounder(rounding: str | None = None) -> Callable[[float, int], float]:
    """The scalar rounding function for ``rounding``."""
    return _round_half_up if rounding_type(rounding) == "sas" else _round_half_even


def _check_digits(d, arg: str, fn: str) -> int:
    try:
        v = int(d)
    except (TypeError, ValueError):
        v = None
    if v is None or isinstance(d, bool) or v < 0:
        raise ValueError(f"`{fn}({arg}=)` must be a single non-negative integer.")
    return v


def round_num(x, digits: int = 0, rounding: str | None = None):
    """Round a number, or a list of numbers, with the package's rule.

    Args:
        x: A number, or a list / tuple of numbers (``None`` and ``nan`` pass
            through).
        digits: Decimal places.
        rounding: ``"r"`` (half to even) or ``"sas"`` (half away from zero);
            ``None`` reads ``rtfreporter_options()["rounding"]``.

    Example:
        >>> round_num([0.5, 1.5, 2.5, -0.5])
        [0.0, 2.0, 2.0, -0.0]
        >>> round_num([0.5, 1.5, 2.5, -0.5], rounding="sas")
        [1.0, 2.0, 3.0, -1.0]
        >>> round_num(2.675, 2, rounding="sas")
        2.68
    """
    d = _check_digits(digits, "digits", "round_num")
    rnd = rounder(rounding)

    def one(v):
        if v is None:
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise TypeError(f"`round_num()` rounds numeric input; got {type(v).__name__}.")
        return rnd(float(v), d)

    if isinstance(x, (list, tuple)):
        return [one(v) for v in x]
    return one(x)


# -- fmt_signif() / fmt_round() / fmt_numeric() -------------------------------


def _int_digits(x: float) -> int:
    ax = math.floor(abs(x))
    return 1 if ax < 1 else int(math.floor(math.log10(ax))) + 1


def _signif_decimals(x: float, digits: int, small: str) -> int:
    """Decimal places implied by a significant-digit request for ONE value."""
    if x == 0:
        return max(0, digits - 1)
    if abs(x) < 1 and small == "signif":
        return max(0, digits - 1 - int(math.floor(math.log10(abs(x)))))
    return max(0, digits - _int_digits(x))


def _is_missing(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def _fmt_num_one(v, dec_fun, rnd, na: str, recompute: bool) -> str:
    if _is_missing(v):
        return na
    v = float(v)
    if math.isinf(v):
        return "Inf" if v > 0 else "-Inf"
    d = dec_fun(v)
    r = rnd(v, d)
    if recompute:
        # rounding can carry |x| into another decade (99.995 -> 100.0)
        d2 = dec_fun(r)
        if d2 != d:
            d = d2
            r = rnd(v, d)
    return f"{r:.{int(d)}f}"


def _check_num_value(v, fn: str) -> None:
    if _is_missing(v):
        return
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(
            f"`{fn}()` formats numeric input; got {type(v).__name__}. Character "
            "columns are taken as already formatted -- leave them alone."
        )


def _as_values(x) -> tuple[list, bool]:
    """A scalar or a vector (list / tuple / Series / array) as a list, and
    whether it was a vector."""
    if isinstance(x, (int, float)) or x is None:
        return [x], False
    if hasattr(x, "tolist"):
        return list(x.tolist()), True
    return list(x), True


def _check_small(small: str) -> str:
    if small not in ("signif", "fixed"):
        raise ValueError('`small` must be "signif" or "fixed".')
    return small


def fmt_signif(x, digits: int = 3, rounding: str | None = None,
               small: str = "signif", na: str = ""):
    """Format numbers to a number of significant digits (R ``fmt_signif()``).

    Counts **total printed digits including the integer part** -- the
    convention a SAP means by "report to 4 significant digits":
    ``fmt_signif([0, 10.2, 103.4, 20.333333, 23.4463], 4)`` is
    ``["0.000", "10.20", "103.4", "20.33", "23.45"]``.  An integer part longer
    than ``digits`` prints whole; when rounding carries a value into another
    decade the decimals are recomputed (``99.995`` -> ``"100.0"``).

    Args:
        x: A number or a vector of numbers.  Text is an error -- a character
            column is taken as already formatted.
        digits: Total significant digits.
        rounding: ``"r"`` (half to even) or ``"sas"`` (half away from zero);
            ``None`` reads ``rtfreporter_options()["rounding"]``.
        small: What a value below 1 means.  ``"signif"`` counts from its first
            significant digit (``0.0004567`` at 4 is ``"0.0004567"``);
            ``"fixed"`` applies the integer-counting rule (``"0.000"``).
        na: Text for a missing value (``None`` / ``nan``).

    Returns:
        A string for a scalar, else a list of strings.  ``inf`` prints as
        ``"Inf"`` / ``"-Inf"``, as in R.
    """
    vals, vec = _as_values(x)
    for v in vals:
        _check_num_value(v, "fmt_signif")
    d = _check_digits(digits, "digits", "fmt_signif")
    small = _check_small(small)
    rnd = rounder(rounding)
    out = [_fmt_num_one(v, lambda z: _signif_decimals(z, d, small), rnd, na, True)
           for v in vals]
    return out if vec else out[0]


def fmt_round(x, digits: int = 2, rounding: str | None = None, na: str = ""):
    """Format numbers to a fixed number of decimal places (R ``fmt_round()``).

    Prints every decimal place, trailing zeros included: ``fmt_round(2.5, 2)``
    is ``"2.50"``.  Arguments as :func:`fmt_signif`, with ``digits`` the
    decimal places.
    """
    vals, vec = _as_values(x)
    for v in vals:
        _check_num_value(v, "fmt_round")
    d = _check_digits(digits, "digits", "fmt_round")
    rnd = rounder(rounding)
    out = [_fmt_num_one(v, lambda z: d, rnd, na, False) for v in vals]
    return out if vec else out[0]


def _format_rule_to_dec(rule, key: str, small: str):
    if not isinstance(rule, dict):
        raise ValueError(
            f"`fmt_numeric(formats=)` entry '{key}' must be a dict, e.g. {{'signif': 4}}."
        )
    has_s = rule.get("signif") is not None
    has_d = rule.get("digits") is not None
    if has_s == has_d:
        raise ValueError(
            f"`fmt_numeric(formats=)` entry '{key}' must give exactly one of "
            "`signif` or `digits`."
        )
    sm = _check_small(rule.get("small", small))
    if has_s:
        s = _check_digits(rule["signif"], "signif", "fmt_numeric")
        return lambda v: _signif_decimals(v, s, sm)
    d = _check_digits(rule["digits"], "digits", "fmt_numeric")
    return lambda v: d


def _is_numeric_column(values: list) -> bool:
    present = [v for v in values if not _is_missing(v)]
    return bool(present) and all(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in present
    )


def fmt_numeric(data, cols, by=None, formats=None, signif=None, digits=None,
                rounding: str | None = None, small: str = "signif", na: str = ""):
    """Format the numeric columns of a table for display (R ``fmt_numeric()``).

    Applies :func:`fmt_signif` or :func:`fmt_round` to the selected
    **numeric** columns; text columns, and columns outside ``cols``, are left
    alone.  With ``by``, a carrier column (it may be the row-heading column;
    values are matched after trimming, so ``"  Mean"`` keys on ``"Mean"``)
    picks a rule per row from ``formats``::

        fmt_numeric(df, cols=["trt"], by="stat",
                    formats={"n": {"digits": 0}, "Mean": {"signif": 4},
                             ".default": {"signif": 4}})

    A row whose selected cells are all missing needs no rule; a non-missing
    cell whose key matches nothing and has no ``".default"`` is an error.

    Args:
        data: A pandas or polars DataFrame, or a dict of columns.
        cols: Columns to format: names or 0-based positions.
        by: Optional carrier column (name or 0-based position).
        formats: Rules keyed by the carrier's values (used with ``by``): each a
            dict with exactly one of ``signif`` / ``digits``, optionally
            ``small``.  ``".default"`` covers unmatched keys.
        signif, digits: Used **without** ``by``: one rule for every selected
            cell.  Give exactly one.
        rounding, small, na: As in :func:`fmt_signif`.

    Returns:
        ``data`` (the same kind) with the selected numeric columns as text.
    """
    from .table import _coerce_data, _resolve_col

    small = _check_small(small)
    rnd = rounder(rounding)
    names, rows = _coerce_data(data)
    columns = {n: [r[j] for r in rows] for j, n in enumerate(names)}
    sel = cols if isinstance(cols, (list, tuple)) else [cols]
    col_idx = [_resolve_col(c, names) for c in sel]
    num_idx = [j for j in col_idx if _is_numeric_column(columns[names[j]])]
    if not num_idx:
        return data

    new: dict[str, list] = {}
    if by is not None:
        if signif is not None or digits is not None:
            raise ValueError("Give either `by` + `formats`, or `signif` / `digits` -- not both.")
        if not isinstance(formats, dict) or not formats:
            raise ValueError("`fmt_numeric(by=)` needs a `formats` dict.")
        if isinstance(by, (list, tuple)):
            if len(by) != 1:
                raise ValueError("`fmt_numeric(by=)` must name a single column.")
            by = by[0]
        keys = ["" if _is_missing(v) else str(v).strip()
                for v in columns[names[_resolve_col(by, names)]]]
        rules = {k: _format_rule_to_dec(r, k, small) for k, r in formats.items()}
        if ".default" not in rules:
            needed = [any(not _is_missing(columns[names[j]][i]) for j in num_idx)
                      for i in range(len(rows))]
            missing_keys = list(dict.fromkeys(
                k for k, need in zip(keys, needed, strict=True) if need and k not in rules))
            if missing_keys:
                them = "it" if len(missing_keys) == 1 else "them"
                raise ValueError(
                    "`fmt_numeric()`: no format for "
                    + ", ".join(f"'{k}'" for k in missing_keys)
                    + f". Add {them} to `formats`, or a `.default` entry."
                )
        for j in num_idx:
            v = columns[names[j]]
            out = []
            for i in range(len(v)):
                rule = rules.get(keys[i]) or rules.get(".default")
                if rule is None:
                    out.append(na if _is_missing(v[i]) else None)
                else:
                    out.append(_fmt_num_one(v[i], rule, rnd, na, True))
            new[names[j]] = out
    else:
        if (signif is None) == (digits is None):
            raise ValueError(
                "Give exactly one of `signif` or `digits` (or use `by` + `formats`)."
            )
        if signif is not None:
            s = _check_digits(signif, "signif", "fmt_numeric")
            dec, recompute = (lambda z: _signif_decimals(z, s, small)), True
        else:
            d = _check_digits(digits, "digits", "fmt_numeric")
            dec, recompute = (lambda z: d), False
        for j in num_idx:
            new[names[j]] = [_fmt_num_one(v, dec, rnd, na, recompute)
                             for v in columns[names[j]]]
    return _replace_columns(data, names, columns, new)


def _replace_columns(data, names, columns, new):
    """``data`` with the columns in ``new`` replaced, as the same kind."""
    if type(data).__module__.split(".")[0] == "polars":
        import polars as pl

        return data.with_columns([pl.Series(k, v, dtype=pl.Utf8) for k, v in new.items()])
    if hasattr(data, "columns") and hasattr(data, "itertuples"):  # pandas
        out = data.copy()
        for k, v in new.items():
            out[k] = v
        return out
    return {n: new.get(n, columns[n]) for n in names}
