"""Per-element style and block width.

Ported from ``R/element_style.R`` and ``R/block_width.R``.  A title, footnote,
header or footer band may carry its own font size, row height, markup and
alignment (#292) and its own width (#291); anything left ``None`` inherits the
document setting.  Font size and row height resolve **together**: a size given
without a height recomputes the height from that size rather than inheriting
one chosen for a different size, and an explicit height always wins.
"""

from __future__ import annotations

from . import _commands as C
from ._escape import resolve_markup


def check_font_size(x, arg: str) -> int | None:
    """A single positive integer (half-points), or ``None``."""
    if x is None:
        return None
    try:
        v = int(x)
    except (TypeError, ValueError):
        v = None
    if v is None or isinstance(x, bool) or v <= 0:
        raise ValueError(f"`{arg}` must be a single positive integer (half-points).")
    return v


def check_row_height(x, arg: str) -> int | None:
    """A single non-negative integer (twips), or ``None``."""
    if x is None:
        return None
    try:
        v = int(x)
    except (TypeError, ValueError):
        v = None
    if v is None or isinstance(x, bool) or v < 0:
        raise ValueError(f"`{arg}` must be a single non-negative integer (twips) or None.")
    return v


def check_align(x, arg: str) -> str | None:
    if x is None:
        return None
    if not isinstance(x, str) or x not in ("left", "center", "right"):
        raise ValueError(f'`{arg}` must be "left", "center" or "right".')
    return x


def check_font(x, arg: str):
    """Per-element font family (#293) -- not ported yet (rtfreporter-py #3)."""
    if x is None:
        return None
    raise NotImplementedError(
        f"`{arg}` is not supported yet: the variable-length font table the R "
        "package uses for per-element fonts is a later stage of "
        "https://github.com/ichirio/rtfreporter-py/issues/3."
    )


def resolve_element_metrics(own_fs, own_rh, doc_fs, doc_rh) -> tuple[int, int]:
    """Resolve one element's ``(font_size, row_height)`` together."""
    fs = check_font_size(own_fs, "font_size_half_points")
    if fs is None:
        fs = int(doc_fs if doc_fs is not None else 18)
    if own_rh is not None:
        rh = int(own_rh)
    elif own_fs is not None:
        rh = C.default_row_height_twips(fs)  # the size the element itself chose
    elif doc_rh is not None:
        rh = int(doc_rh)
    else:
        rh = C.default_row_height_twips(fs)
    return int(fs), int(rh)


def fs_cmd_for(fs, doc_fs) -> str:
    """The ``\\fs`` run command for an element, or ``""`` when it matches the document."""
    if fs is None or int(fs) == int(doc_fs):
        return ""
    return f"\\fs{int(fs)}"


def element_style(
    font_size_half_points=None,
    row_height_twips=None,
    markup=None,
    align=None,
    verb: str = "style",
) -> dict:
    """Collect the style an element was given, dropping the entries left unset."""
    out = {
        "font_size_half_points": check_font_size(
            font_size_half_points, f"{verb}(font_size_half_points)"
        ),
        "row_height_twips": check_row_height(row_height_twips, f"{verb}(row_height_twips)"),
        "markup": None if markup is None else resolve_markup(markup),
        "align": check_align(align, f"{verb}(align)"),
    }
    return {k: v for k, v in out.items() if v is not None}


# -- Block width (#291) -------------------------------------------------------
#
# Every block that renders as a table of its own -- the title, the footnote,
# the header and footer bands -- can say how wide it is, in one vocabulary:
#   "content"   the width of the table body on the page (the default for the
#               title and footnote, so they line up with the body)
#   "page"      the writable width (the default for a header / footer band)
#   0 < w <= 1  that fraction of the writable width
#   w > 1       twips


def check_block_width(w, arg: str):
    if w is None:
        return None
    if isinstance(w, str):
        if w not in ("content", "page"):
            raise ValueError(
                f'`{arg}` must be "content", "page", a fraction in (0, 1], or twips.'
            )
        return w
    if isinstance(w, bool) or not isinstance(w, (int, float)) or w <= 0:
        raise ValueError(
            f'`{arg}` must be "content", "page", a fraction in (0, 1], or twips.'
        )
    return w


def resolve_block_width(spec, content_width: int, writable: int, default: str = "content") -> int:
    """Resolve a block-width spec to twips."""
    if spec is None:
        spec = default
    if spec == "content":
        return int(content_width)
    if spec == "page":
        return int(writable)
    w = float(spec)
    # <= 1 is a fraction of the writable width; anything larger is already twips
    if w <= 1:
        return int(round(writable * w))
    return int(round(w))
