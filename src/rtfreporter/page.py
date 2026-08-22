"""Page geometry and document-wide default formatting.

Ported from ``R/rtf_page.R`` and ``R/rtfreport.R`` (``.resolve_page_geometry``).
Defaults: landscape US Letter with uniform 0.75" margins, Courier 9pt.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import _commands as C
from ._escape import resolve_markup
from .config import _UNSET, _resolve


@dataclass
class Page:
    """Page geometry for an RTF document.

    Args:
        paper_size: ``"letter"`` (default), ``"legal"``, ``"a4"``, ``"a3"``,
            ``"a5"`` (case-insensitive).  Ignored when ``width_in`` /
            ``height_in`` are given.
        orientation: ``"landscape"`` (default) or ``"portrait"``.
        width_in, height_in: Explicit page size in inches.  When supplied these
            win over ``paper_size`` and orientation is inferred
            (``width_in >= height_in`` means landscape).
        margin_*_in: The four page margins in inches (default 0.75).
        header_dist_in, footer_dist_in: Distance (inches) of the header/footer
            band from the page edge.  ``None`` derives it as the full top/bottom
            margin.
    """

    paper_size: str = "letter"
    orientation: str = "landscape"
    width_in: float | None = None
    height_in: float | None = None
    margin_top_in: float = 0.75
    margin_bottom_in: float = 0.75
    margin_left_in: float = 0.75
    margin_right_in: float = 0.75
    header_dist_in: float | None = None
    footer_dist_in: float | None = None

    def __post_init__(self) -> None:
        if self.orientation not in ("landscape", "portrait"):
            raise ValueError('`orientation` must be "landscape" or "portrait".')

    def geometry(self) -> dict:
        """Resolve to twips: orientation, width, height, margins, band distances."""
        orientation, width_twips, height_twips = _resolve_geometry(
            self.paper_size, self.orientation, self.width_in, self.height_in
        )
        ml = C.in_to_twips(self.margin_left_in)
        mr = C.in_to_twips(self.margin_right_in)
        mt = C.in_to_twips(self.margin_top_in)
        mb = C.in_to_twips(self.margin_bottom_in)
        header_dist = (
            C.in_to_twips(self.header_dist_in)
            if self.header_dist_in is not None
            else max(0, mt)
        )
        footer_dist = (
            C.in_to_twips(self.footer_dist_in)
            if self.footer_dist_in is not None
            else max(0, mb)
        )
        return {
            "orientation": orientation,
            "width_twips": width_twips,
            "height_twips": height_twips,
            "margin_left_twips": ml,
            "margin_right_twips": mr,
            "margin_top_twips": mt,
            "margin_bottom_twips": mb,
            "header_dist_twips": header_dist,
            "footer_dist_twips": footer_dist,
        }


def rtf_page(
    paper_size=_UNSET,
    orientation=_UNSET,
    width_in: float | None = None,
    height_in: float | None = None,
    margin_top_in=_UNSET,
    margin_bottom_in=_UNSET,
    margin_left_in=_UNSET,
    margin_right_in=_UNSET,
    header_dist_in: float | None = None,
    footer_dist_in: float | None = None,
) -> Page:
    """Build a :class:`Page` (mirrors R's ``rtf_page()``).

    Any argument left unset falls back to the ``rtfreporter.page.*`` option and
    then the factory default (see :func:`~rtfreporter.rtfreporter_options`).
    """
    return Page(
        paper_size=_resolve(paper_size, "page.paper_size"),
        orientation=_resolve(orientation, "page.orientation"),
        width_in=width_in,
        height_in=height_in,
        margin_top_in=_resolve(margin_top_in, "page.margin_top_in"),
        margin_bottom_in=_resolve(margin_bottom_in, "page.margin_bottom_in"),
        margin_left_in=_resolve(margin_left_in, "page.margin_left_in"),
        margin_right_in=_resolve(margin_right_in, "page.margin_right_in"),
        header_dist_in=header_dist_in,
        footer_dist_in=footer_dist_in,
    )


def _resolve_geometry(
    paper_size: str | None,
    orientation: str | None,
    width_in: float | None,
    height_in: float | None,
) -> tuple[str, int, int]:
    if width_in is not None or height_in is not None:
        w = width_in if width_in is not None else 11.0
        h = height_in if height_in is not None else 8.5
        inferred = "landscape" if w >= h else "portrait"
        return inferred, C.in_to_twips(w), C.in_to_twips(h)

    key = (paper_size or "letter").lower()
    if key not in C.PAPER_SIZES:
        known = ", ".join(C.PAPER_SIZES)
        raise ValueError(f'Unknown paper_size "{paper_size}". Known sizes: {known}.')
    base_w, base_h = C.PAPER_SIZES[key]
    long_side = C.in_to_twips(max(base_w, base_h))
    short_side = C.in_to_twips(min(base_w, base_h))
    orient = orientation or "landscape"
    if orient == "landscape":
        return "landscape", long_side, short_side
    return "portrait", short_side, long_side


@dataclass
class DefaultFormat:
    """Document-wide default formatting.

    Args:
        font_size_half_points: Body font size in half-points (18 = 9pt).
        row_height_twips: Default row height for every table-shaped element.
            ``None`` keeps the font-aware baseline.
        cell_padding_left_twips, cell_padding_right_twips: Default cell padding
            (border-to-text). ``None`` keeps the resource baseline (0).
        markup: ``"script"`` (default), ``"relational"``, ``"all"``, ``"none"``.
        title_format: How the title renders -- ``"text"`` (default) or ``"table"``.
        footnote_format: How the footnote renders -- ``"table"`` (default) or
            ``"text"``.
        font: Font family name (default ``"Courier"``).
    """

    font_size_half_points: int = 18
    row_height_twips: int | None = None
    cell_padding_left_twips: int | None = None
    cell_padding_right_twips: int | None = None
    markup: str = "script"
    title_format: str = "text"
    footnote_format: str = "table"
    font: str = "Courier"

    def __post_init__(self) -> None:
        if self.font_size_half_points <= 0:
            raise ValueError("`font_size_half_points` must be positive.")
        # Validate markup tokens eagerly.
        resolve_markup(self.markup)
        for name, val in (
            ("title_format", self.title_format),
            ("footnote_format", self.footnote_format),
        ):
            if val not in ("text", "table"):
                raise ValueError(f'`{name}` must be "text" or "table"; got {val!r}.')


def rtf_default_format(
    font_size_half_points=_UNSET,
    row_height_twips: int | None = None,
    cell_padding_left_twips: int | None = None,
    cell_padding_right_twips: int | None = None,
    markup=_UNSET,
    title_format=_UNSET,
    footnote_format=_UNSET,
) -> DefaultFormat:
    """Build a :class:`DefaultFormat` (mirrors R's ``rtf_default_format()``).

    ``font_size_half_points``, ``markup``, ``title_format`` and
    ``footnote_format`` fall back to the matching ``rtfreporter.*`` option (then
    the factory default) when left unset; see
    :func:`~rtfreporter.rtfreporter_options`.

    Args:
        font_size_half_points: Body font size in half-points (18 = 9pt).
        row_height_twips: Default row height, or ``None`` for the baseline.
        cell_padding_left_twips, cell_padding_right_twips: Default cell padding.
        markup: ``"script"`` / ``"relational"`` / ``"all"`` / ``"none"``.
        title_format, footnote_format: ``"text"`` or ``"table"``.
    """
    for name, val in (
        ("row_height_twips", row_height_twips),
        ("cell_padding_left_twips", cell_padding_left_twips),
        ("cell_padding_right_twips", cell_padding_right_twips),
    ):
        if val is not None and (not isinstance(val, int) or val < 0):
            raise ValueError(f"`{name}` must be a non-negative integer (twips) or None.")
    return DefaultFormat(
        font_size_half_points=_resolve(font_size_half_points, "font_size_half_points"),
        row_height_twips=row_height_twips,
        cell_padding_left_twips=cell_padding_left_twips,
        cell_padding_right_twips=cell_padding_right_twips,
        markup=_resolve(markup, "markup"),
        title_format=_resolve(title_format, "title_format"),
        footnote_format=_resolve(footnote_format, "footnote_format"),
    )
