"""``rtf_watermark()``: a diagonal watermark behind the page body.

Ported from ``R/watermark.R``.  The shape is emitted inside the section's
``{\\header ...}`` group -- what Word's own Insert > Watermark writes -- so it
repeats on every page of its section and stays scoped to that section, and
``assemble_rtf()`` cannot let one deliverable's watermark bleed into the next.

shapeType 136 is the plain-text WordArt shape; ``fGtext 1`` turns the text
into WordArt so it can be rotated and scaled as a unit.  ``rotation`` is a
fixed-point number (degrees << 16).  ``\\shpfblwtxt1`` puts the shape behind
the text; ``\\shpbxpage`` / ``\\shpbypage`` anchor the offsets to the page.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Watermark:
    """A watermark built by :func:`rtf_watermark`."""

    text: str
    font_size_half_points: int = 144
    color: str = "#C8C8C8"
    angle: float = -45.0
    font: str | None = None
    width_in: float = 6.0
    height_in: float = 2.0


def rtf_watermark(text, font_size_half_points: int = 144, color: str = "#C8C8C8",
                  angle: float = -45, font: str | None = None,
                  width_in: float = 6, height_in: float = 2) -> Watermark:
    """A diagonal word drawn behind the page body (R ``rtf_watermark()``).

    Pass it to :func:`~rtfreporter.rtf_document` / :func:`~rtfreporter.rtf_config`
    (``watermark=``) for every page, or to :func:`~rtfreporter.rtf_section` for
    one section; a bare string (``watermark="DRAFT"``) uses these defaults.

    Args:
        text: The word to draw, e.g. ``"DRAFT"``.
        font_size_half_points: Size in half-points (default 144 = 72 pt).
        color: ``"#RRGGBB"`` fill colour (default a light grey).
        angle: Rotation in degrees (default -45, bottom-left to top-right).
        font: Font family; ``None`` uses the document's font.
        width_in, height_in: The box the text is scaled into, in inches,
            centred on the page.
    """
    if text is None:
        raise ValueError('`text` is required; give the word to draw, e.g. "DRAFT".')
    text = "" if isinstance(text, float) and math.isnan(text) else str(text)
    if (isinstance(font_size_half_points, bool)
            or not isinstance(font_size_half_points, (int, float))
            or not font_size_half_points > 0):
        raise ValueError("`font_size_half_points` must be one positive number.")
    if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        raise ValueError(f"`color` must be one \"#RRGGBB\" string; got '{color}'.")
    if isinstance(angle, bool) or not isinstance(angle, (int, float)) or math.isnan(angle):
        raise ValueError("`angle` must be one number, in degrees.")
    for name, v in (("width_in", width_in), ("height_in", height_in)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not v > 0:
            raise ValueError(f"`{name}` must be one positive number, in inches.")
    if font is not None and not isinstance(font, str):
        raise ValueError("`font` must be None or one font-family name.")
    return Watermark(text=text, font_size_half_points=int(font_size_half_points),
                     color=color, angle=float(angle), font=font,
                     width_in=float(width_in), height_in=float(height_in))


def normalize_watermark(x) -> Watermark | None:
    """A :class:`Watermark`, a bare string, or ``None`` / ``""`` / ``False`` /
    ``nan`` for none."""
    if x is None or x is False:
        return None
    if isinstance(x, Watermark):
        return x if x.text else None
    if isinstance(x, float) and math.isnan(x):
        return None
    if isinstance(x, str):
        return rtf_watermark(x) if x else None
    raise ValueError(
        "`watermark` must be an rtf_watermark object, a single string, or "
        "None for none."
    )


def _bgr(hex_color: str) -> int:
    """``"#RRGGBB"`` -> the BGR integer an Office shape property wants."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return b * 65536 + g * 256 + r


def render_watermark_rtf(wm, page_w_twips: int, page_h_twips: int,
                         default_font: str = "Times New Roman") -> str:
    """The ``{\\shp ...}`` group, centred on the page; ``""`` for none."""
    from .assemble import _toc_escape

    wm = normalize_watermark(wm)
    if wm is None:
        return ""
    w = int(round(wm.width_in * 1440))
    h = int(round(wm.height_in * 1440))
    left = int(round((page_w_twips - w) / 2))
    top = int(round((page_h_twips - h) / 2))

    def sp(name, value):
        return "{\\sp{\\sn " + name + "}{\\sv " + str(value) + "}}"

    return (
        "{\\shp{\\*\\shpinst"
        f"\\shpleft{left}\\shptop{top}\\shpright{left + w}\\shpbottom{top + h}"
        "\\shpfhdr1\\shpbxpage\\shpbypage\\shpwr3\\shpwrk0\\shpfblwtxt1\\shpz0"
        + sp("shapeType", 136)
        + sp("fFilled", 1)
        + sp("fillColor", _bgr(wm.color))
        + sp("fLine", 0)
        + sp("fBehindDocument", 1)
        + sp("posrelh", 1)
        + sp("posrelv", 1)
        + sp("rotation", int(round(wm.angle * 65536)))
        + sp("fGtext", 1)
        + sp("gtextUNICODE", _toc_escape(wm.text))
        + sp("gtextFont", wm.font if wm.font is not None else default_font)
        + sp("gtextSize", wm.font_size_half_points * 10)
        + sp("fHidden", 0)
        + "}}"
    )
