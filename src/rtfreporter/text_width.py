"""Font-aware text width estimation for column sizing.

Ported from ``R/text_width.R``.  Provides :func:`text_width_in` (estimated
display width of a string in inches) and :func:`auto_col_widths` (suggested
per-column widths in twips for a table body).
"""

from __future__ import annotations

import re

# Courier New character width at 12pt, in points (monospace: one constant).
_COURIER_CHAR_W_PT_AT_12 = 7.22
# Arial approximate average character width at 12pt, in points.
_ARIAL_CHAR_W_PT_AT_12 = 6.0


def _char_width_in(font_lower: str, size_pt: float) -> float:
    """Width in inches of one character in ``font_lower`` at ``size_pt``."""
    base_w = {
        "courier": _COURIER_CHAR_W_PT_AT_12,
        "courier_new": _COURIER_CHAR_W_PT_AT_12,
        "courier new": _COURIER_CHAR_W_PT_AT_12,
        "arial": _ARIAL_CHAR_W_PT_AT_12,
    }.get(font_lower, _COURIER_CHAR_W_PT_AT_12)  # fallback: treat as Courier
    return (base_w * size_pt / 12) / 72


def _max_line_nchar(value) -> int:
    """Longest single line (split on CR/LF) of ``value`` as a string, in chars."""
    text = "" if value is None else str(value)
    lines = re.split(r"\r\n|\r|\n", text)
    return max((len(line) for line in lines), default=0)


def text_width_in(text, font: str = "courier_new", size_half_points: int = 18) -> list[float]:
    """Estimate the display width, in inches, of one or more strings.

    Reliable for Courier New (monospace); an average-width approximation for
    proportional fonts (Arial).

    Args:
        text: A string or an iterable of strings (``None`` is treated as ``""``).
        font: ``"courier_new"`` (default), ``"courier"``, or ``"arial"``.
            Unrecognised values fall back to Courier New.
        size_half_points: Font size in half-points (18 = 9pt).

    Returns:
        A list of estimated widths in inches (one per input string).  A single
        string in yields a single-element list.
    """
    items = [text] if isinstance(text, str) or text is None else list(text)
    size_pt = float(size_half_points) / 2
    char_w = _char_width_in(font.lower(), size_pt)
    return [len("" if t is None else str(t)) * char_w for t in items]


def auto_col_widths(
    df,
    col_header=None,
    font: str = "courier_new",
    size_half_points: int = 18,
    table_width_twips: int | None = None,
    min_col_width_twips: int = 720,
    col_padding_twips: int = 288,
    protect_cols=None,
) -> list[int]:
    """Suggest per-column widths (twips) sized to each column's widest content.

    Scans header labels and data values of every column and returns widths
    suitable for :func:`~rtfreporter.rtftable`'s ``column_widths_twips``.

    Args:
        df: A ``(column_names, rows)`` pair, dict of columns, list of row dicts,
            or a pandas/polars DataFrame.
        col_header: Header labels (``None`` uses the column names).  A list of
            strings, a pipe-delimited string, or a list of header rows (only the
            first row is used for width estimation).
        font: Font passed to :func:`text_width_in`.
        size_half_points: Font size in half-points.
        table_width_twips: If given, scale the widths so their sum equals this.
        min_col_width_twips: Minimum width per column (default 720 = 0.5in).
        col_padding_twips: Extra twips added per column (default 288 = 0.2in).
        protect_cols: 0-based column indices kept at natural width when scaling
            *down*; only the remaining columns shrink.  Dropped if it would push
            the scalable columns below ``min_col_width_twips``.

    Returns:
        An integer list of column widths in twips, one per column.
    """
    from .table import _coerce_data

    names, rows = _coerce_data(df)
    ncols = len(names)
    size_pt = float(size_half_points) / 2
    char_w = _char_width_in(font.lower(), size_pt)

    # Resolve header labels (use the first row when multi-row).
    if col_header is None:
        hdr = list(names)
    else:
        hdr = col_header
        if isinstance(hdr, str) and "|" in hdr:
            hdr = [seg.strip() for seg in hdr.split("|")]
        if hdr and isinstance(hdr[0], (list, tuple)):
            hdr = list(hdr[0])
        hdr = list(hdr)
    if len(hdr) < ncols:
        hdr = hdr + [""] * (ncols - len(hdr))

    col_w: list[int] = []
    for j in range(ncols):
        hdr_w = _max_line_nchar(hdr[j]) * char_w
        data_w = max((_max_line_nchar(r[j]) for r in rows), default=0) * char_w
        w = round(max(hdr_w, data_w) * 1440) + int(col_padding_twips)
        col_w.append(max(int(w), int(min_col_width_twips)))

    if table_width_twips is None:
        return col_w

    total_w = int(table_width_twips)
    protect = sorted({int(p) for p in (protect_cols or []) if 0 <= int(p) < ncols})
    scalable = [j for j in range(ncols) if j not in protect]

    if protect and scalable:
        fixed_w = sum(col_w[j] for j in protect)
        remaining = total_w - fixed_w
        min_needed = len(scalable) * int(min_col_width_twips)
        if remaining >= min_needed:
            nat = sum(col_w[j] for j in scalable)
            if nat > 0:
                for j in scalable:
                    col_w[j] = max(round(col_w[j] * remaining / nat), int(min_col_width_twips))
            drift = total_w - sum(col_w)
            col_w[scalable[-1]] += drift
            return col_w
        # Fall through to uniform scaling when protection cannot be honoured.

    total_natural = sum(col_w)
    if total_natural > 0:
        col_w = [round(w * total_w / total_natural) for w in col_w]
        col_w[ncols - 1] = total_w - sum(col_w[:-1])
        col_w = [max(w, int(min_col_width_twips)) for w in col_w]
    return col_w
