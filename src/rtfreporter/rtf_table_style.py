"""Shared table style objects (the R ``rtf_table_style`` family).

Ported from ``R/rtf_table_style.R``.  A :class:`TableStyle` bundles per-zone
borders and text-formatting defaults that :func:`~rtfreporter.rtftable`'s
``style=`` argument folds in *under* any explicit argument (explicit always
wins).  Build one with :func:`rtf_table_style`, start from the clinical preset
with :func:`rtf_table_style_tfl`, and derive variants with
:func:`rtf_table_style_with`.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

from .borders import Border, TableBorder, rtf_border_side

_ALIGN = ("left", "center", "right")


@dataclass(frozen=True)
class TableStyle:
    """A reusable table style (per-zone borders + text defaults).

    The zone borders (``border_header`` ... ``border_last_row``) are assembled
    into a :class:`~rtfreporter.borders.TableBorder` exposed as :attr:`border`,
    which :func:`~rtfreporter.rtftable` consumes when ``border`` is left at its
    ``"tfl"`` default.  ``align`` / ``bold`` / ``italic`` / ``underline`` and the
    ``header_*`` fields seed the per-column defaults.
    """

    border_header: Border | None = None
    border_spanning: Border | None = None
    border_body: Border | None = None
    border_first_row: Border | None = None
    border_last_row: Border | None = None
    header_align: str | None = None
    header_bold: bool = False
    header_italic: bool = False
    align: str | None = "left"
    bold: bool = False
    italic: bool = False
    underline: bool = False
    cell_padding_left_twips: int | None = None
    cell_padding_right_twips: int | None = None
    row_height_twips: int | None = None

    @property
    def border(self) -> TableBorder:
        """The per-zone borders assembled into a :class:`TableBorder`."""
        return TableBorder(
            header=self.border_header,
            spanning=self.border_spanning,
            body=self.border_body,
            first_row=self.border_first_row,
            last_row=self.border_last_row,
        )


def _check_border(b, name: str) -> None:
    if b is not None and not isinstance(b, Border):
        raise TypeError(f"`{name}` must be None or a Border object.")


def rtf_table_style(
    border_header: Border | None = None,
    border_spanning: Border | None = None,
    border_body: Border | None = None,
    border_first_row: Border | None = None,
    border_last_row: Border | None = None,
    header_align: str | None = None,
    header_bold: bool = False,
    header_italic: bool = False,
    align: str | None = "left",
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    cell_padding_left_twips: int | None = None,
    cell_padding_right_twips: int | None = None,
    row_height_twips: int | None = None,
) -> TableStyle:
    """Build a shared :class:`TableStyle` (mirrors R's ``rtf_table_style()``).

    Args:
        border_header, border_spanning, border_body, border_first_row,
        border_last_row: Per-zone :class:`~rtfreporter.borders.Border` (or
            ``None``).  ``first_row`` / ``last_row`` override ``body``.
        header_align: Column-header alignment (``None`` inherits the body align).
        header_bold, header_italic: Column-header decoration defaults.
        align: Body alignment default (``"left"`` by default).
        bold, italic, underline: Body decoration defaults.
        cell_padding_left_twips, cell_padding_right_twips: Cell padding defaults.
        row_height_twips: Default data-row height.
    """
    for b, name in (
        (border_header, "border_header"),
        (border_spanning, "border_spanning"),
        (border_body, "border_body"),
        (border_first_row, "border_first_row"),
        (border_last_row, "border_last_row"),
    ):
        _check_border(b, name)
    for name, val in (("header_align", header_align), ("align", align)):
        if val is not None and val not in _ALIGN:
            raise ValueError(f"`{name}` must be None, 'left', 'center', or 'right'.")
    return TableStyle(
        border_header=border_header,
        border_spanning=border_spanning,
        border_body=border_body,
        border_first_row=border_first_row,
        border_last_row=border_last_row,
        header_align=header_align,
        header_bold=bool(header_bold),
        header_italic=bool(header_italic),
        align=align,
        bold=bool(bold),
        italic=bool(italic),
        underline=bool(underline),
        cell_padding_left_twips=cell_padding_left_twips,
        cell_padding_right_twips=cell_padding_right_twips,
        row_height_twips=row_height_twips,
    )


def rtf_table_style_with(style: TableStyle, **overrides) -> TableStyle:
    """Return a copy of ``style`` with the named fields replaced.

    Mirrors R's ``rtf_table_style_with()``: a non-mutating field override.
    Unknown field names raise :class:`ValueError`.
    """
    if not isinstance(style, TableStyle):
        raise TypeError("`style` must be a TableStyle object.")
    allowed = {f.name for f in fields(TableStyle)}
    unknown = set(overrides) - allowed
    if unknown:
        raise ValueError(f"Unknown style field(s): {sorted(unknown)}.")
    return replace(style, **overrides)


def rtf_table_style_tfl() -> TableStyle:
    """The clinical TFL preset as a :class:`TableStyle`.

    Borders on the column-header block only (top on the topmost header row,
    bottom on the bottommost); no data-area borders, no bold headers, and the
    header alignment inherits the body alignment.
    """
    s = rtf_border_side()
    return rtf_table_style(
        border_header=Border(top=s, bottom=s),
        header_bold=False,
        header_align=None,
    )
