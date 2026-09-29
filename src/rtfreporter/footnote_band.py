"""Footnote block -- the page footer's mechanism, as a table of its own.

Ported from ``R/footnote_band.R`` (#296).  The footnote used to have a row
model all its own: one cell per row, with per-row bold / italic / colour /
border.  It now uses exactly what :func:`~rtfreporter.rtf_footer` uses --
``{"l": ..., "c": ..., "r": ...}``, up to three cells positioned left / centre
/ right -- differing only in its defaults:

    page footer     a top rule by default
    footnote        no rule at all by default

A bare string is not ambiguous: the block's ``align`` decides which of l / c /
r it becomes, so ``"text"`` is a single left-aligned cell spanning the block.

It is also emitted as an INDEPENDENT table.  RTF treats consecutive
``\\trowd ... \\row`` runs with no paragraph between them as one table, and the
footnote used to follow the body's rows directly -- so it was really the body
table wearing different ``\\cellx`` values.  A ``\\pard\\par`` in between makes
it a table of its own, which is what having a width of its own requires.
"""

from __future__ import annotations

from .header_footer import HeaderFooter

_SLOT = {"left": "l", "center": "c", "right": "r"}
_OLD_STYLE_KEYS = ("text", "bold", "italic", "underline", "color", "border", "align")


def footnote_rows(block, align: str = "left", format: str = "table") -> list:
    """Turn a footnote block into the rows shape the footer renderer consumes.

    ``align`` picks the slot a bare string lands in.
    """
    if block is None:
        return []
    rows = list(block) if isinstance(block, (list, tuple)) else [block]
    if not rows:
        return []
    slot = _SLOT.get(align, "l")

    out = []
    for r in rows:
        if r is None:
            r = ""
        if isinstance(r, dict):
            if any(k in r for k in _OLD_STYLE_KEYS) or not r:
                raise ValueError(
                    "A footnote row is a string or a named vector such as "
                    '{"l": "...", "r": "..."}. Per-row styling lists are no '
                    "longer supported -- set the style on the block instead, "
                    "via rtf_footnotes(font_size_half_points=, align=, ...)."
                )
            bad = [k for k in r if k not in ("l", "c", "r")]
            if bad:
                raise ValueError(
                    "A footnote row may only be named l / c / r; got "
                    + ", ".join(f"'{k}'" for k in bad)
                    + "."
                )
            if format == "text":
                raise ValueError(
                    'A {"l": , "c": , "r": } footnote row needs the table form. '
                    'Set footnote_format = "table" (the default), or give the '
                    "row as a single string."
                )
            out.append({k: ("" if v is None else str(v)) for k, v in r.items()})
            continue
        if isinstance(r, (list, tuple)):
            raise ValueError(
                "A footnote row must be one string, or a named vector like "
                '{"l": "...", "r": "..."}.'
            )
        txt = str(r)
        if format == "text":
            out.append(txt)  # the paragraph form wants text
        else:
            out.append({slot: txt})
    return out


def footnote_hf(block, style: dict | None, width_twips: int, format: str = "table") -> HeaderFooter:
    """Build the band object the footer renderer takes, from the footnote block
    plus the block-level style the author set."""
    style = style or {}
    return HeaderFooter(
        rows=footnote_rows(block, style.get("align", "left"), format),
        border=style.get("border"),  # None -> no rule, unlike the footer
        width_twips=int(width_twips),
        row_height_twips=style.get("row_height_twips"),
        font_size_half_points=style.get("font_size_half_points"),
        font=style.get("font"),
        markup=style.get("markup"),
        is_footer=True,
    )
