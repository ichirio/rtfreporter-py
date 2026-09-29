"""Border specifications for cells, rows, and table zones.

Ported from ``R/rtf_border.R``.  Two types compose the model:

* :class:`BorderSide` -- one *line*: style, weight (twips), colour.
* :class:`Border` -- a *selection*: its four outer edges (``top`` / ``bottom``
  / ``left`` / ``right``) and the rules **inside** it (``inside_h`` between its
  rows, ``inside_v`` between its cells).  Where the selection is, is decided by
  where the border is attached: ``rtftable(border=)`` is the whole table,
  ``style_zone()`` one kind of row, ``col_cell(border=)`` one cell,
  ``rtf_header()`` / ``rtf_footer()`` that band -- the model Word uses, where
  one dialog acts on whatever is selected (R #342).

:class:`TableBorder` is the renderer's own five-zone vocabulary (header /
spanning / body / first_row / last_row); a whole-table :class:`Border` is
expanded onto it by :func:`expand_table_border` before rendering.

Every value is an immutable, copy-friendly record.  A side with
``style="none"`` is an *explicit no-line* that **overrides** an inherited
border when merged on top of another spec -- distinct from ``None`` (side
simply unset, so inherited).

The single-purpose constructors R deprecated in 0.5 (``rtf_border_none()``,
``rtf_border_top()``, ``rtf_border_bottom()``, ``rtf_border_box()``,
``rtf_border_with()``, ``rtf_border_tfl()``, ``rtf_table_border()``) still
work here too, and warn once per session; they are scheduled for removal at
the same time as in R (before its CRAN submission, v0.9.0).
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field, replace

from . import _commands as C

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

#: The four physical edges an RTF cell can carry.
BORDER_EDGES = ("top", "bottom", "left", "right")
#: Plus the two "between" axes.  These are not edges: they say what the rules
#: *between* a row's cells (inside_v) and *between* a zone's rows (inside_h)
#: look like.  RTF has no such concept -- the renderer distributes them onto
#: real edges of the right cells.
BORDER_SLOTS = (*BORDER_EDGES, "inside_h", "inside_v")
#: The five row kinds a table border addresses.
TABLE_BORDER_ZONES = ("header", "spanning", "body", "first_row", "last_row")


def _check_color(color: str | None) -> None:
    if color is None:
        return
    if not isinstance(color, str) or not _HEX_RE.match(color):
        raise ValueError(
            "`color` must be None or a 6-digit hex string (e.g. '#FF0000')."
        )


# -- Deprecation, once per session --------------------------------------------

_deprecation_state: set[str] = set()


def _deprecate_once(key: str, msg: str) -> bool:
    if key in _deprecation_state:
        return False
    _deprecation_state.add(key)
    warnings.warn(msg, DeprecationWarning, stacklevel=3)
    return True


def _reset_deprecations() -> None:
    """Forget which deprecation warnings were shown (for tests)."""
    _deprecation_state.clear()


@dataclass(frozen=True)
class BorderSide:
    """A single line: style, weight (twips), and colour.

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


def as_border_side(x, arg: str) -> BorderSide | None:
    """Resolve whatever a caller wrote for one side into a :class:`BorderSide`.

    ``None`` -> unset (inherit); ``True`` -> a default rule (single, 15 twips,
    black); ``False`` -> an explicit "no line", same as ``"none"``; a style
    name such as ``"double"`` -> that style at the default weight and colour;
    a :class:`BorderSide` -> taken as-is, for a weight and colour of its own.
    The first four are shorthands for the fifth: a line's *type* is what gets
    named most often, so it should not need a constructor.
    """
    if x is None:
        return None
    if isinstance(x, BorderSide):
        return x
    if x is True:
        return BorderSide()
    if x is False:
        return BorderSide("none")
    if isinstance(x, str):
        ok = (*C.VALID_BORDER_STYLES, "none")
        if x not in ok:
            raise ValueError(
                f"`{arg}` must be one of " + ", ".join(f'"{s}"' for s in ok) + f', not "{x}".'
            )
        return BorderSide(x)
    raise TypeError(
        f"`{arg}` must be True, False, a border style name, an rtf_border_side(), or None."
    )


@dataclass(frozen=True)
class Border:
    """A border for a *selection*: its outer edges and the rules inside it.

    Each slot is ``None`` (unset: inherit) or a :class:`BorderSide`.
    ``top`` / ``bottom`` / ``left`` / ``right`` are the selection's **outer**
    edges; ``inside_h`` is the rule between its rows and ``inside_v`` the rule
    between its cells, an absent one meaning no rule.  Build one with
    :func:`rtf_border`.
    """

    top: BorderSide | None = None
    bottom: BorderSide | None = None
    left: BorderSide | None = None
    right: BorderSide | None = None
    inside_h: BorderSide | None = None
    inside_v: BorderSide | None = None
    #: Not part of the value, only of its provenance: whether ``inside_h`` /
    #: ``inside_v`` were *named* when the border was written.  It lets the
    #: renderer tell a border written for the pre-0.5 uniform reading from one
    #: written for the outer/inside reading (see :func:`warn_old_edge_reading`).
    #: Dropped by any merge -- a merged border is a new statement.
    inside_named: tuple = field(default=(False, False), compare=False, repr=False)

    def __post_init__(self) -> None:
        for slot in BORDER_SLOTS:
            v = getattr(self, slot)
            if v is not None and not isinstance(v, BorderSide):
                raise TypeError(f"`{slot}` must be None or a BorderSide object.")

    def with_sides(self, **sides) -> Border:
        """Return a copy with the supplied (non-None) slots replaced."""
        return merge_border(self, Border(**{k: v for k, v in sides.items() if v is not None}))

    def is_empty(self) -> bool:
        return all(getattr(self, slot) is None for slot in BORDER_SLOTS)


@dataclass(frozen=True)
class TableBorder:
    """Per-zone borders for a table: the renderer's five-zone vocabulary.

    ``first_row`` / ``last_row`` are *overrides* merged on top of ``body``.
    ``outer`` / ``inside_h`` / ``inside_v`` are a "selection = the whole table"
    way of saying what the five zones say row-kind by row-kind; they are
    expanded onto the zones by :func:`expand_table_border` before the
    renderer sees them.
    """

    header: Border | None = None
    spanning: Border | None = None
    body: Border | None = None
    first_row: Border | None = None
    last_row: Border | None = None
    outer: Border | None = None
    inside_h: BorderSide | None = None
    inside_v: BorderSide | None = None


# -- Constructors -------------------------------------------------------------


def rtf_border_side(style: str = "single", width: int = 15, color: str | None = None) -> BorderSide:
    """Build a :class:`BorderSide` -- one line's style, weight and colour."""
    return BorderSide(style, width, color)


def rtf_border(
    all=None,
    top=None,
    bottom=None,
    left=None,
    right=None,
    inside_h=None,
    inside_v=None,
) -> Border:
    """Build a :class:`Border` -- which edges of a selection carry a rule.

    Each side takes ``True`` (a default rule), ``False`` or ``"none"`` (an
    explicit no-line), a style name such as ``"double"``, or a
    :class:`BorderSide` for a weight or colour of its own.  ``all`` is the four
    outer edges at once; a side named explicitly wins over it.  Sides that
    differ fit in one call::

        rtf_border(top=rtf_border_side(color="#C9372C"),
                   bottom=rtf_border_side("double", 30))
    """
    if all is not None:
        top = all if top is None else top
        bottom = all if bottom is None else bottom
        left = all if left is None else left
        right = all if right is None else right
    return Border(
        top=as_border_side(top, "top"),
        bottom=as_border_side(bottom, "bottom"),
        left=as_border_side(left, "left"),
        right=as_border_side(right, "right"),
        inside_h=as_border_side(inside_h, "inside_h"),
        inside_v=as_border_side(inside_v, "inside_v"),
        inside_named=(inside_h is not None, inside_v is not None),
    )


def rtf_border_with(
    border: Border | None,
    top=None,
    bottom=None,
    left=None,
    right=None,
    inside_h=None,
    inside_v=None,
) -> Border:
    """Deprecated: layering happens where a border is attached.

    ``style_zone()`` / ``style_header()`` / ``style_body()`` merge side by
    side, so a second call adds to the first instead of replacing it.  A
    border that needs different weights or colours per side says so in one
    call: ``rtf_border(top=rtf_border_side(...), bottom=rtf_border_side(...))``.
    """
    _deprecate_once(
        "rtf_border_with",
        "`rtf_border_with()` is deprecated. Layering happens where a border is "
        "attached:\n    style_zone() / style_header() / style_body() merge side by "
        "side, so a\n    second call adds to the first instead of replacing it.\n"
        "  A border that needs different weights or colours per side says so in "
        "one\n  call: rtf_border(top=rtf_border_side(...), bottom=rtf_border_side(...)).",
    )
    if border is None:
        border = rtf_border()
    if not isinstance(border, Border):
        raise TypeError("`border` must be None or an rtf_border object.")
    # Forward only what was supplied (R #348 follow-up): naming an absent
    # inside_* would make the result look as though it declared its interior.
    given = {k: v for k, v in dict(top=top, bottom=bottom, left=left, right=right,
                                   inside_h=inside_h, inside_v=inside_v).items()
             if v is not None}
    return merge_border(border, rtf_border(**given))


def _deprecate_sugar(fn: str, replacement: str) -> None:
    _deprecate_once(fn, f"`{fn}()` is deprecated: write `{replacement}` instead.  See rtf_border().")


def rtf_border_none() -> Border:
    """Deprecated: write ``rtf_border()``."""
    _deprecate_sugar("rtf_border_none", "rtf_border()")
    return rtf_border()


def rtf_border_top(style: str = "single", width: int = 15, color: str | None = None) -> Border:
    """Deprecated: write ``rtf_border(top=True)`` (or ``top=rtf_border_side(...)``)."""
    _deprecate_sugar("rtf_border_top", "rtf_border(top=True)")
    return rtf_border(top=BorderSide(style, width, color))


def rtf_border_bottom(style: str = "single", width: int = 15, color: str | None = None) -> Border:
    """Deprecated: write ``rtf_border(bottom=True)``."""
    _deprecate_sugar("rtf_border_bottom", "rtf_border(bottom=True)")
    return rtf_border(bottom=BorderSide(style, width, color))


def rtf_border_box(style: str = "single", width: int = 15, color: str | None = None) -> Border:
    """Deprecated: write ``rtf_border(all=True)``."""
    _deprecate_sugar("rtf_border_box", "rtf_border(all=True)")
    return rtf_border(all=BorderSide(style, width, color))


def rtf_border_tfl(style: str = "single", width: int = 15, color: str | None = None) -> TableBorder:
    """Deprecated: the clinical TFL rules are ``rtftable(border="tfl")``, and a
    reusable value is ``rtf_table_style_tfl()``."""
    _deprecate_once(
        "rtf_border_tfl",
        "`rtf_border_tfl()` is deprecated: the clinical TFL rules are already "
        'reachable as\n  `rtftable(border="tfl")`, and as a reusable value '
        "from `rtf_table_style_tfl()`.",
    )
    return _rtf_border_tfl(style, width, color)


def _rtf_border_tfl(style: str = "single", width: int = 15, color: str | None = None) -> TableBorder:
    """The preset itself, for ``border="tfl"`` and ``rtf_table_style_tfl()``:
    a top rule on the topmost header row and a bottom rule on the bottommost
    header row, no data-area borders."""
    s = BorderSide(style, width, color)
    return _rtf_table_border(header=Border(top=s, bottom=s))


def rtf_table_border(
    header: Border | None = None,
    spanning: Border | None = None,
    body: Border | None = None,
    first_row: Border | None = None,
    last_row: Border | None = None,
    outer: Border | None = None,
    inside_h: BorderSide | None = None,
    inside_v: BorderSide | None = None,
) -> TableBorder:
    """Deprecated: a border is written once with :func:`rtf_border`, and
    *where* it applies is decided by where you attach it (``rtftable(border=)``
    for the whole table, ``style_zone()`` for one row kind, ``col_cell(border=)``
    for one cell).  ``outer=`` becomes the four edges of that ``rtf_border()``;
    ``inside_h=`` and ``inside_v=`` keep their names."""
    _deprecate_once(
        "rtf_table_border",
        "`rtf_table_border()` is deprecated: a border is now written once with "
        "`rtf_border()`, and *where* it applies is decided by where you attach "
        "it.\n  whole table : rtftable(border=rtf_border(...))\n"
        "  one row kind: style_zone(header=rtf_border(...), body=...)\n"
        "  one cell    : col_cell(border=rtf_border(...))\n"
        "  `outer=` becomes the four edges of that rtf_border(); `inside_h=` "
        "and `inside_v=` keep their names.",
    )
    return _rtf_table_border(header, spanning, body, first_row, last_row,
                             outer, inside_h, inside_v)


def _rtf_table_border(
    header=None, spanning=None, body=None, first_row=None, last_row=None,
    outer=None, inside_h=None, inside_v=None,
) -> TableBorder:
    """The five-zone map, unexported.  It stays the renderer's internal
    vocabulary; users address a row kind with ``style_zone()`` or
    ``rtf_table_style(border_*=)``."""
    for nm, v in (("header", header), ("spanning", spanning), ("body", body),
                  ("first_row", first_row), ("last_row", last_row)):
        if v is not None and not isinstance(v, Border):
            raise TypeError(f"`{nm}` must be None or an rtf_border object.")
    if outer is not None and not isinstance(outer, Border):
        raise TypeError(
            "`outer` must be None or an rtf_border object (the table's four outermost edges)."
        )
    for nm, v in (("inside_h", inside_h), ("inside_v", inside_v)):
        if v is not None and not isinstance(v, BorderSide):
            raise TypeError(f"`{nm}` must be None or an rtf_border_side object.")
    return TableBorder(header=header, spanning=spanning, body=body,
                       first_row=first_row, last_row=last_row,
                       outer=outer, inside_h=inside_h, inside_v=inside_v)


# -- Merge / colour helpers ---------------------------------------------------


def merge_border(base: Border | None, over: Border | None) -> Border | None:
    """Override the slots of ``base`` with the non-None slots of ``over``."""
    if base is None:
        return over
    if over is None:
        return base
    out = replace(base, inside_named=(False, False))
    for slot in BORDER_SLOTS:
        v = getattr(over, slot)
        if v is not None:
            out = replace(out, **{slot: v})
    return out


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
    for slot in BORDER_SLOTS:
        side = getattr(b, slot)
        if side is not None and side.color is not None:
            out.append(side.color)
    return out


def collect_table_border_colors(tb: TableBorder | None) -> list[str]:
    """Collect hex colours referenced by a :class:`TableBorder`."""
    if tb is None:
        return []
    out = []
    for zone in TABLE_BORDER_ZONES:
        out.extend(collect_border_colors(getattr(tb, zone)))
    out.extend(collect_border_colors(tb.outer))
    for side in (tb.inside_h, tb.inside_v):
        if side is not None and side.color is not None:
            out.append(side.color)
    return out


def normalize_table_border(spec) -> TableBorder | None:
    """Normalise a user ``border`` argument to a :class:`TableBorder` or None.

    Accepts ``"tfl"``, ``"none"`` / ``None``, a :class:`TableBorder`, or a
    :class:`Border` -- which selects the **whole table**: its four edges are
    the table's outer frame and its ``inside_h`` / ``inside_v`` are the rules
    between rows and between cells (R #342; before that this was an error,
    #326, so nothing that worked before changes meaning).
    """
    if spec is None or spec == "none":
        return None
    if isinstance(spec, str):
        if spec == "tfl":
            return _rtf_border_tfl()
        raise ValueError(f"Unknown border preset {spec!r}; use 'tfl' or 'none'.")
    if isinstance(spec, TableBorder):
        return spec
    if isinstance(spec, Border):
        return _rtf_table_border(outer=spec, inside_h=spec.inside_h, inside_v=spec.inside_v)
    raise TypeError("`border` must be 'tfl'/'none', a TableBorder, or a Border.")


def expand_table_border(tb: TableBorder | None, has_header: bool = True) -> TableBorder | None:
    """Expand the whole-table shortcuts onto the five zones.

    ``outer`` / ``inside_h`` / ``inside_v`` are a "selection = the whole
    table" way of saying what the five zones say row-kind by row-kind.  They
    are expanded here, once, before the renderer ever sees them:

    * ``outer.top`` -> the top edge of the topmost row (header, else first_row);
    * ``outer.bottom`` -> the bottom edge of the last data row (last_row);
    * ``outer.left`` / ``outer.right`` -> every zone's left/right, marked as
      OUTER edges by setting ``inside_v`` on each zone;
    * ``inside_h`` -> every row boundary inside the table: between header
      rows, between the header block and the body, and between data rows;
    * ``inside_v`` -> every cell boundary inside a row.

    Explicit zone arguments are merged on top afterwards and therefore win,
    which keeps "whole table, except ..." expressible.
    """
    if tb is None:
        return None
    outer, ih, iv = tb.outer, tb.inside_h, tb.inside_v
    if outer is None and ih is None and iv is None:
        return tb

    def vertical(b: Border | None) -> Border | None:
        if outer is None and iv is None:
            return b
        return merge_border(
            b if b is not None else Border(),
            Border(left=outer.left if outer else None,
                   right=outer.right if outer else None, inside_v=iv),
        )

    base = {z: None for z in TABLE_BORDER_ZONES}
    base["header"] = vertical(Border(inside_h=ih) if ih is not None else None)
    base["body"] = vertical(Border(inside_h=ih) if ih is not None else None)
    # `spanning` REPLACES `header` on spanning rows rather than layering over
    # it, so filling it in unconditionally would strip the frame off the
    # topmost row.  Leave it None (the renderer then falls back to `header`)
    # unless the caller named it, in which case their value layers over the
    # header expansion.
    base["spanning"] = None if tb.spanning is None else base["header"]

    # The table's own top and bottom edges.
    if outer is not None and outer.top is not None:
        if has_header:
            base["header"] = merge_border(base["header"], Border(top=outer.top))
        else:
            base["first_row"] = merge_border(base["first_row"], Border(top=outer.top))
    if outer is not None and outer.bottom is not None:
        base["last_row"] = merge_border(base["last_row"], Border(bottom=outer.bottom))

    # The header/body seam is an *inside* horizontal rule, not an outer one.
    if ih is not None and has_header:
        base["header"] = merge_border(base["header"], Border(bottom=ih))

    zones = {z: merge_border(base[z], getattr(tb, z)) for z in TABLE_BORDER_ZONES}
    return TableBorder(**zones)


def cell_edge_border(b: Border | None, j: int, n: int) -> Border | None:
    """Resolve one cell's vertical edges within a row of ``n`` cells.

    A :class:`Border` always describes a *selection*: ``left`` / ``right`` are
    the selection's outer edges and ``inside_v`` is what separates the cells
    inside it.  ``j`` is the cell's 0-based index; ``j`` and ``n`` count
    *cells*, not columns: on a row with a spanning cell the interior rules land
    on cell boundaries, so nothing is drawn inside a merged cell.  Same as Word.
    """
    if b is None:
        return None
    return replace(b, left=b.left if j == 0 else b.inside_v,
                   right=b.right if j == n - 1 else b.inside_v)


def zone_row_border(b: Border | None, idx: int, n: int) -> Border | None:
    """Resolve one row's horizontal edges within a zone of ``n`` rows.

    Mirror image of :func:`cell_edge_border` on the other axis: ``top`` /
    ``bottom`` are the zone's outer edges and ``inside_h`` is what separates
    its rows.  Interior boundaries are drawn once, as the bottom of the upper
    row.  ``idx`` is 0-based.
    """
    if b is None:
        return None
    return replace(b, top=b.top if idx == 0 else None,
                   bottom=b.bottom if idx == n - 1 else b.inside_h)


def warn_old_edge_reading(tb: TableBorder | None, ncols: int, nrows: int) -> bool:
    """Warn once when a zone border is written in the pre-0.5 uniform reading.

    Before R 0.5.0 ``left`` / ``right`` were drawn on every cell of a row, and
    a multi-row zone's ``top`` / ``bottom`` on every one of its rows.  Both now
    mean the selection's outer edge only.  The two readings are spelled
    identically, so the only honest signal is "edges set, matching inside_*
    never named" -- and it is worth raising only where the readings actually
    differ, which is why ``ncols`` / ``nrows`` are needed.
    """
    if tb is None:
        return False

    def differs(b: Border | None, multi_row: bool) -> bool:
        if not isinstance(b, Border):
            return False
        named_h, named_v = b.inside_named
        v = ncols > 1 and not named_v and (b.left is not None or b.right is not None)
        h = multi_row and nrows > 1 and not named_h and (b.top is not None or b.bottom is not None)
        return v or h

    # `header` has always read top/bottom as the block's outer edges, so only
    # its vertical axis can have changed; `first_row` / `last_row` are single
    # rows.  `outer` is deliberately not checked: rtftable(border=<Border>)
    # was an error before, so no existing code can mean the old thing by it.
    hit = (differs(tb.body, True) or differs(tb.header, False) or differs(tb.spanning, False)
           or differs(tb.first_row, False) or differs(tb.last_row, False))
    if not hit:
        return False
    return _deprecate_once(
        "border_edge_reading",
        "The edges of `rtf_border()` now mean the *outer* edges of whatever you "
        "attach it to.\n  Before R 0.5.0 `left`/`right` were drawn on every cell of "
        "a row, and a multi-row zone's\n  `top`/`bottom` on every one of its rows.  "
        "To keep that look, name the interior rule:\n"
        "    rtf_border(left=s, right=s, inside_v=s)   # was: left/right alone\n"
        "    rtf_border(bottom=s, inside_h=s)          # was: bottom alone on a body zone\n"
        '  Naming `inside_h` / `inside_v` (with rtf_border_side("none") for "no rule") '
        "silences this.",
    )
