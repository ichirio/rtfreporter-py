"""Low-level RTF command strings and package defaults.

Ported faithfully from the R package's ``inst/resources/rtf_commands.R`` and
``inst/resources/rtfreporter_defaults.R``.  All measurements are in *twips*
(1 twip = 1/1440 inch = 1/20 point).

These constants are deliberately kept as plain module-level values so the
renderer reads like the R source and the mapping between the two is easy to
audit.
"""

from __future__ import annotations

# -- Document-level templates -------------------------------------------------

#: Document header. ``\ansicpg1252`` declares the ANSI code page, ``\deflang1033``
#: the default language (US English), and ``\uc1`` says every ``\uN`` unicode
#: escape is followed by exactly one fallback char (matching the ``\uN?`` form
#: this package emits).
RTF_HEADER_OPEN = r"{\rtf1\ansi\ansicpg1252\deff0\deflang1033\uc1"

#: Font table. ``\fnil\fcharset0`` = unknown family, ANSI charset.
FONT_TABLE_TEMPLATE = r"{{\fonttbl{{\f0\fnil\fcharset0 {font_name};}}}}"

PAGE_SETTINGS_TEMPLATE = (
    r"\paperw{width_twips}\paperh{height_twips}{orientation_cmd}"
    r"\margl{margin_left_twips}\margr{margin_right_twips}"
    r"\margt{margin_top_twips}\margb{margin_bottom_twips}"
    r"\headery{header_dist_twips}\footery{footer_dist_twips}"
    r"\widowctrl\fs{font_size_half_points}"
)

SECTION_DEFAULTS = r"\sectd"

#: Table terminator emitted after a page's content before a break/close.
TABLE_END = r"\pard"

#: Manual page break wrapped in tiny empty paragraphs (a bare ``\page`` is
#: dropped by Word when not flanked by real paragraphs).
PAGE_BREAK = r"{\pard\fs2\par}\page{\pard\fs2\par}"

SECTION_BREAK = r"\sect"
HEADER_WRAPPER = r"{{\header {content}}}"
FOOTER_WRAPPER = r"{{\footer {content}}}"
DOCUMENT_CLOSE = "}"

# -- Paragraph templates ------------------------------------------------------

EMPTY_TABLE = r"\par [empty table]\par"

# -- Table templates ----------------------------------------------------------

ROW_START = r"\trowd"
ROW_END = r"\row"
ROW_HEIGHT_TEMPLATE = r"\trrh{row_height_twips}"
CELL_BOUNDARY_TEMPLATE = r"\cellx{cx}"

# -- Alignment ----------------------------------------------------------------

ALIGNMENT = {
    "left": r"\ql",
    "right": r"\qr",
    "center": r"\qc",
    "default": r"\ql",
}

# -- Borders ------------------------------------------------------------------

BORDER_SIDE_PREFIX = {
    "top": r"\clbrdrt",
    "bottom": r"\clbrdrb",
    "left": r"\clbrdrl",
    "right": r"\clbrdrr",
}

BORDER_STYLE = {
    "single": r"\brdrs",
    "double": r"\brdrdb",
    "thick": r"\brdrth",
    "dash": r"\brdrdash",
    "dot": r"\brdrdot",
}

VALID_BORDER_STYLES = ("single", "double", "thick", "dash", "dot")

# -- Cell vertical alignment --------------------------------------------------

CELL_VALIGN = {
    "top": r"\clvertalt",
    "center": r"\clvertalc",
    "bottom": r"\clvertalb",
}

# -- Picture templates --------------------------------------------------------

PNG_TEMPLATE = (
    r"\pard{align}{{\pict\pngblip\picw{picw}\pich{pich}"
    r"\picwgoal{picwgoal}\pichgoal{pichgoal}" + "\n{hex}\n" + r"}}\par"
)
JPEG_TEMPLATE = (
    r"\pard{align}{{\pict\jpegblip\picw{picw}\pich{pich}"
    r"\picwgoal{picwgoal}\pichgoal{pichgoal}" + "\n{hex}\n" + r"}}\par"
)

# -- Dynamic field templates --------------------------------------------------

AUTO_PAGE = r"\chpgn "
AUTO_TOTAL_PAGES = r"{{\field{{\*\fldinst NUMPAGES}}{{\fldrslt {total_pages}}}}}"
SECTION_PAGES = r"{\field{\*\fldinst SECTIONPAGES}{\fldrslt 1}}"

# ============================================================================
#  Package defaults (rtfreporter_defaults.R)
# ============================================================================

#: Row height (twips) by font size in half-points.
DEFAULT_ROW_HEIGHT_BY_FONT_HALF_POINTS = {
    16: 210,  # 8pt
    18: 230,  # 9pt  <- package default
    20: 250,  # 10pt
    22: 270,  # 11pt
    24: 290,  # 12pt
    26: 310,  # 13pt
    28: 330,  # 14pt
}
DEFAULT_ROW_HEIGHT_PER_HALF_POINT = 12.8
DEFAULT_ROW_HEIGHT_MIN = 180
DEFAULT_CELL_PADDING_LEFT_TWIPS = 0
DEFAULT_CELL_PADDING_RIGHT_TWIPS = 0

#: Named paper-size presets, portrait base dimensions in inches (w <= h).
PAPER_SIZES = {
    "letter": (8.5, 11.0),
    "legal": (8.5, 14.0),
    "a4": (8.2677, 11.6929),
    "a3": (11.6929, 16.5354),
    "a5": (5.8268, 8.2677),
}


def default_row_height_twips(font_half_points: int = 18) -> int:
    """Resolve the default row height (twips) for a font size in half-points."""
    fhp = int(font_half_points or 18)
    if fhp in DEFAULT_ROW_HEIGHT_BY_FONT_HALF_POINTS:
        h = DEFAULT_ROW_HEIGHT_BY_FONT_HALF_POINTS[fhp]
    else:
        h = int(round(fhp * DEFAULT_ROW_HEIGHT_PER_HALF_POINT))
    return max(h, DEFAULT_ROW_HEIGHT_MIN)


def in_to_twips(inches: float) -> int:
    """Convert inches to twips (rounded to the nearest integer)."""
    return int(round(inches * 1440))
