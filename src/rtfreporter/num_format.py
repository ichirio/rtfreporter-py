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
    if math.isnan(x) or math.isinf(x):
        return x
    return float(round(x, digits))


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
