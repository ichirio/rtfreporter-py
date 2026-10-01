"""decimal_split -- render-time column splitting for decimal-point alignment.

Ported from ``R/decimal_split.R`` (R #304).  A statistics column mixes
integers and decimals of differing widths; right-alignment lines up the last
character, not the decimal point.  A split column renders as TWO adjacent
cells on the data rows -- the part before the first decimal separator
(right-aligned) and the separator plus the rest (left-aligned) -- so the
points line up exactly, independent of font metrics.

The data are never rewritten; the pair still ends at the column's right edge,
so the table width, every other column and the header block (which keeps the
ORIGINAL geometry) are unaffected.  A cell that is not split-eligible (free
text, and by default compound values such as ``"12.3 (4.56)"``) renders as ONE
cell spanning the pair, exactly as without the feature.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import replace

from .borders import Border, BorderSide, merge_border

_WS = "[ \t\r\n ]"
_GATE = re.compile(r"^[<>=~+-]{0,2}[0-9.]")


def _trim(x: str) -> str:
    return re.sub(f"^{_WS}+|{_WS}+$", "", x)


def split_cells(values, decimal_mark: str = ".", include_compound: bool = False):
    """Classify and split one column's cell text: ``(left, right, split)``."""
    left, right, split = [], [], []
    for v in values:
        x = "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)
        s = _trim(x)
        empty = s == ""
        ok = (not empty and _GATE.search(s) is not None
              and re.search("[0-9]", s) is not None)
        if ok and not include_compound and re.search(r"[\s()]", s):
            ok = False
        if ok:
            pos = s.find(decimal_mark)
            if pos >= 0:  # a mark in the first place still splits, as in R
                left.append(s[:pos])
                right.append(s[pos:])
            else:
                left.append(s)
                right.append("")
        else:
            left.append(s if empty else x)
            right.append("")
        split.append(ok or empty)
    return left, right, split


def _width(x: str, markup) -> int:
    """Display width after markup substitution (R ``nchar(type = "width")``)."""
    if markup and "relational" in markup:
        x = x.replace(">=", "≥").replace("<=", "≤")
    if markup and "script" in markup:
        x = re.sub(r"\^\{|_\{|\}", "", x)
    w = 0
    for ch in x:
        if unicodedata.combining(ch):
            continue
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def split_ratio(wl, wr, pad_chars=None, min_chars=None, max_chars=None) -> float:
    """The integer half's share of the column, from the two measured widths."""
    pad = (1.0, 1.0) if pad_chars is None else tuple(float(v) for v in pad_chars)
    flr = (4.0, 6.0) if min_chars is None else tuple(float(v) for v in min_chars)
    cap = 10.0 if max_chars is None else float(max_chars)
    if wl + wr > cap:
        le, re_ = float(wl), float(wr)
    else:
        le = max(wl + pad[0], flr[0])
        re_ = max(wr + pad[1], flr[1])
    if le + re_ <= 0:
        return 0.5
    return le / (le + re_)


def _half_border(b, side: str):
    """The half's border: the ORIGINAL column's, with its interior edge off."""
    none = BorderSide("none")
    over = Border(right=none) if side == "left" else Border(left=none)
    if b is None:
        return over
    return merge_border(b, over)


def _r_round(x: float) -> int:
    """R's round() at 0 digits: half to even."""
    return int(round(x))


def plan(tbl, cellx, col_spec, markup):
    """The data rows' expanded geometry, or ``None`` when nothing is split."""
    spec = tbl.decimal_split
    if not spec:
        return None
    n0 = len(cellx)
    cols = sorted({c for c in spec["cols"] if 0 <= c < n0})
    if not cols:
        return None
    parts = [None] * n0
    do_split = [False] * n0
    for j in cols:
        vals = [r[j] if j < len(r) else None for r in tbl.rows]
        p = split_cells(vals, spec["decimal_mark"], spec["include_compound"])
        if not any(p[1]):
            continue
        parts[j] = p
        do_split[j] = True
    if not any(do_split):
        return None

    new_cellx, new_spec, interior, pad_flag = [], [], [], []
    left_of, right_of = [0] * n0, [None] * n0
    for j in range(n0):
        if not do_split[j]:
            left_of[j] = len(new_cellx)
            new_cellx.append(cellx[j])
            new_spec.append(col_spec[j])
            interior.append(None)
            pad_flag.append("")
            continue
        left, right, split = parts[j]
        wl = max([1] + [_width(s, markup) for s, ok in zip(left, split, strict=True) if ok])
        wr = max([1] + [_width(s, markup) for s, ok in zip(right, split, strict=True) if ok])
        r = (float(spec["ratio"]) if spec.get("ratio") is not None
             else split_ratio(wl, wr, spec.get("pad_chars"), spec.get("min_chars"),
                              spec.get("max_chars")))
        x0 = 0 if j == 0 else int(cellx[j - 1])
        x1 = int(cellx[j])
        xs = x0 + _r_round((x1 - x0) * r)
        xs = max(x0 + 1, min(x1 - 1, xs))
        base = col_spec[j]
        left_of[j] = len(new_cellx)
        new_cellx.append(xs)
        new_spec.append(replace(base, align="right", border=_half_border(base.border, "left")))
        interior.append(_half_border(None, "left"))
        pad_flag.append("left")
        right_of[j] = len(new_cellx)
        new_cellx.append(x1)
        new_spec.append(replace(base, align="left", indent_twips=0,
                                border=_half_border(base.border, "right")))
        interior.append(_half_border(None, "right"))
        pad_flag.append("right")
    return {"n0": n0, "n1": len(new_cellx), "cellx": new_cellx, "col_spec": new_spec,
            "orig_spec": col_spec, "left_of": left_of, "right_of": right_of,
            "do_split": do_split, "pad_flag": pad_flag, "interior": interior,
            "parts": parts}


def split_row(pl, vals, i: int):
    """One data row on the plan's geometry: ``(vals, merge_to, merge_spec)``."""
    n1 = pl["n1"]
    out = [""] * n1
    merge_to = [None] * n1
    merge_spec = [None] * n1
    for j in range(pl["n0"]):
        a = pl["left_of"][j]
        if not pl["do_split"][j]:
            raw = vals[j] if j < len(vals) else None
            out[a] = "" if raw is None or (isinstance(raw, float) and math.isnan(raw)) else raw
            merge_to[a] = a
            continue
        b = pl["right_of"][j]
        left, right, split = pl["parts"][j]
        if split[i]:
            out[a], out[b] = left[i], right[i]
            merge_to[a], merge_to[b] = a, b
        else:
            # Not split-eligible on this row: one cell across the pair, styled
            # by the original column.
            out[a] = left[i]
            merge_to[a] = b
            merge_spec[a] = pl["orig_spec"][j]
    return out, merge_to, merge_spec


def split_cell_styles(pl, rcs):
    """A row's cell_styles on the plan's geometry: each original column's
    value duplicated across its pair."""
    if not rcs:
        return rcs
    idx = [0] * pl["n1"]
    for j in range(pl["n0"]):
        idx[pl["left_of"][j]] = j
        if pl["right_of"][j] is not None:
            idx[pl["right_of"][j]] = j
    return {k: ([v[m] for m in idx] if isinstance(v, list) and len(v) == pl["n0"] else v)
            for k, v in rcs.items()}
