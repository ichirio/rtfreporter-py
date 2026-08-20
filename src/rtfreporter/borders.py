"""Border specifications for cells, rows, and table zones.

Ported from ``R/rtf_border.R``.  Three dataclasses compose the model:

* :class:`BorderSide` -- one edge (style, width, colour).
* :class:`Border` -- four edges of a single cell/row.
* :class:`TableBorder` -- per-zone borders for a whole table.

Every value is an immutable, copy-friendly record, so passing a border into
multiple tables is always safe.  A side with ``style="none"`` is an *explicit
no-line* that **overrides** an inherited border when merged on top of another
spec -- distinct from ``None`` (side simply unset).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from . import _commands as C

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _check_color(color: str | None) -> None:
    if color is None:
        return
    if not isinstance(color, str) or not _HEX_RE.match(color):
        raise ValueError(
            "`color` must be None or a 6-digit hex string (e.g. '#FF0000')."
        )


@dataclass(frozen=True)
class BorderSide:
    """A single-edge border: line style, weight (twips), and colour.

    Args:
        style: One of ``"single"`` (default), ``"double"``, ``"thick"``,
            ``"dash"``, ``"dot"``, or ``"none"``.  ``"none"`` is an explicit
            no-line that removes an inherited border when merged.
        width: Line weight in twips (default 15 ~ 0.5pt). Ignored for ``"none"``.
        color: ``None`` (black) or a 6-digit hex string such as ``"#003366"``.
    """

    style: str = "single"
    width: int = 15
    color: str | None = None

    def __post_init__(self) -> None:
        valid = (*C.VALID_BORDER_STYLES, "none")
        if self.style not in valid:
            raise ValueError(f"`style` must be one of {valid}; got {self.style!r}.")
        object.__setattr__(self, "width", int(self.width))
        if self.style != "none" and self.width < 1:
            raise ValueError("`width` must be a positive integer (twips).")
        _check_color(self.color)


@dataclass(frozen=True)
class Border:
    """Borders for up to four sides of a cell or row.

    Each side is ``None`` (no border) or a :class:`BorderSide`.
    """

    top: BorderSide | None = None
    bottom: BorderSide | None = None
    left: BorderSide | None = None
    right: BorderSide | None = None

    def with_sides(
        self,
        top: BorderSide | None = None,
        bottom: BorderSide | None = None,
        left: BorderSide | None = None,
        right: BorderSide | None = None,
    ) -> Border:
        """Return a copy with the supplied (non-None) sides replaced."""
        return Border(
            top=top if top is not None else self.top,
            bottom=bottom if bottom is not None else self.bottom,
            left=left if left is not None else self.left,
            right=right if right is not None else self.right,
        )


@dataclass(frozen=True)
class TableBorder:
    """Per-zone borders for a table.

    ``first_row`` / ``last_row`` are *overrides* merged on top of ``body``.
    Each zone is ``None`` or a :class:`Border`.
    """

    header: Border | None = None
    spanning: Border | None = None
    body: Border | None = None
    first_row: Border | None = None
    last_row: Border | None = None


# -- Convenience constructors -------------------------------------------------


def rtf_border_side(style: str = "single", width: int = 15, color: str | None = None) -> BorderSide:
    """Build a :class:`BorderSide` (functional alias)."""
    return BorderSide(style, width, color)


def rtf_border(
    top: BorderSide | None = None,
    bottom: BorderSide | None = None,
    left: BorderSide | None = None,
    right: BorderSide | None = None,
) -> Border:
    """Build a :class:`Border` (functional alias)."""
    return Border(top, bottom, left, right)


def rtf_border_none() -> Border:
    """A :class:`Border` with all sides unset."""
    return Border()


def rtf_border_top(style: str = "single", width: int = 15, color: str | None = None) -> Border:
    """A top-edge-only border."""
    return Border(top=BorderSide(style, width, color))


def rtf_border_bottom(style: str = "single", width: int = 15, color: str | None = None) -> Border:
    """A bottom-edge-only border."""
    return Border(bottom=BorderSide(style, width, color))


def rtf_border_box(style: str = "single", width: int = 15, color: str | None = None) -> Border:
    """A four-edge box border."""
    s = BorderSide(style, width, color)
    return Border(top=s, bottom=s, left=s, right=s)


def rtf_border_tfl(style: str = "single", width: int = 15, color: str | None = None) -> TableBorder:
    """The standard clinical TFL border preset.

    Borders on the column-header block only: a top rule on the topmost header
    row and a bottom rule on the bottommost header row.  No data-area borders.
    A multi-column spanning cell additionally receives a group underline where
    the column grouping changes below it (added automatically by the renderer).
    """
    s = BorderSide(style, width, color)
    return TableBorder(header=Border(top=s, bottom=s))


def rtf_table_border(
    header: Border | None = None,
    spanning: Border | None = None,
    body: Border | None = None,
    first_row: Border | None = None,
    last_row: Border | None = None,
) -> TableBorder:
    """Build a :class:`TableBorder` with per-zone borders.

    Mirrors the R ``rtf_table_border()`` constructor.  ``first_row`` /
    ``last_row`` are overrides merged on top of ``body``.
    """
    return TableBorder(
        header=header,
        spanning=spanning,
        body=body,
        first_row=first_row,
        last_row=last_row,
    )


# -- Merge / colour helpers ---------------------------------------------------


def merge_border(base: Border | None, over: Border | None) -> Border | None:
    """Override sides of ``base`` with the non-None sides of ``over``."""
    if base is None:
        return over
    if over is None:
        return base
    return replace(
        base,
        top=over.top if over.top is not None else base.top,
        bottom=over.bottom if over.bottom is not None else base.bottom,
        left=over.left if over.left is not None else base.left,
        right=over.right if over.right is not None else base.right,
    )


def effective_row_border(base: Border | None, over: Border | None) -> Border | None:
    """Merge an override border on top of a base border (None-safe)."""
    if over is None:
        return base
    if base is None:
        return over
    return merge_border(base, over)


def collect_border_colors(b: Border | None) -> list[str]:
    """Collect hex colours referenced by a :class:`Border`."""
    if b is None:
        return []
    out = []
    for side in (b.top, b.bottom, b.left, b.right):
        if side is not None and side.color is not None:
            out.append(side.color)
    return out


def collect_table_border_colors(tb: TableBorder | None) -> list[str]:
    """Collect hex colours referenced by a :class:`TableBorder`."""
    if tb is None:
        return []
    out = []
    for zone in (tb.header, tb.spanning, tb.body, tb.first_row, tb.last_row):
        out.extend(collect_border_colors(zone))
    return out


def normalize_table_border(spec) -> TableBorder | None:
    """Normalise a user ``border`` argument to a :class:`TableBorder` or None.

    Accepts ``"tfl"``, ``"none"``/``None``, a :class:`TableBorder`, or a
    :class:`Border` (applied to the header zone).
    """
    if spec is None or spec == "none":
        return None
    if isinstance(spec, str):
        if spec == "tfl":
            return rtf_border_tfl()
        raise ValueError(f"Unknown border preset {spec!r}; use 'tfl' or 'none'.")
    if isinstance(spec, TableBorder):
        return spec
    if isinstance(spec, Border):
        return TableBorder(header=spec)
    raise TypeError("`border` must be 'tfl'/'none', a TableBorder, or a Border.")
