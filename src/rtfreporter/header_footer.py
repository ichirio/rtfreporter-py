"""Running page header and footer bands.

Ported from the R ``rtf_header()`` / ``rtf_footer()`` model.  A band is a stack
of rows; each row has 1-3 columns keyed by position:

* ``l`` -> left, ``c`` -> center, ``r`` -> right.
* ``l`` + ``r`` -> a two-column (left/right) row.
* ``l`` + ``c`` + ``r`` -> a three-column row.
* a plain string -> a single centered column.

Cells may contain page tokens (``{AUTO_PAGE}``, ``{AUTO_TOTAL_PAGES}``,
``{PAGE}``, ``{TOTAL_PAGES}``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from ._escape import resolve_markup
from .borders import Border, BorderSide

Row = dict


def _normalize_row(row) -> dict:
    """Normalise one header/footer row to a dict of position -> text."""
    if row is None:
        return {"c": ""}
    if isinstance(row, str):
        return {"c": row}
    if isinstance(row, dict):
        out = {}
        for key, value in row.items():
            if key not in ("l", "c", "r"):
                raise ValueError(
                    f"Header/footer row keys must be 'l', 'c', or 'r'; got {key!r}."
                )
            out[key] = "" if value is None else str(value)
        if not out:
            return {"c": ""}
        return out
    if isinstance(row, (list, tuple)):
        n = len(row)
        if n == 0:
            return {"c": ""}
        if n == 1:
            return {"c": str(row[0])}
        if n == 2:
            return {"l": str(row[0]), "r": str(row[1])}
        if n == 3:
            return {"l": str(row[0]), "c": str(row[1]), "r": str(row[2])}
        raise ValueError("Header/footer supports up to 3 columns per row.")
    raise TypeError("Each header/footer row must be a str, dict, or sequence.")


@dataclass
class HeaderFooter:
    """A running header or footer band (a stack of 1-3 column rows)."""

    rows: list[dict] = field(default_factory=list)
    border: Border | None = None
    row_height_twips: int | None = None
    cell_padding_left_twips: int | None = None
    cell_padding_right_twips: int | None = None
    width_twips: int | None = None
    is_footer: bool = False
    #: Per-band style (R #291 / #292): ``width`` in the block-width vocabulary
    #: (``"page"``, ``"content"``, a fraction of the writable width, or twips),
    #: ``font_size_half_points``, ``font`` and ``markup``.  ``None`` inherits
    #: the document setting.
    width: object = None
    font_size_half_points: int | None = None
    font: str | None = None
    markup: object = None
    #: Leave out a row whose tokens of one's own are all empty (R #571).
    drop_empty_rows: bool = False

    def __post_init__(self) -> None:
        from .element_style import check_block_width, check_font, check_font_size

        self.rows = [_normalize_row(r) for r in self.rows]
        verb = "rtf_footer" if self.is_footer else "rtf_header"
        self.width = check_block_width(self.width, f"{verb}(width)")
        self.font_size_half_points = check_font_size(
            self.font_size_half_points, f"{verb}(font_size_half_points)"
        )
        self.font = check_font(self.font, f"{verb}(font)")
        if self.markup is not None and not isinstance(self.markup, frozenset):
            self.markup = resolve_markup(self.markup)
        if not isinstance(self.drop_empty_rows, bool):
            raise ValueError("`drop_empty_rows` must be True or False.")


_TOKEN_IN_ROW = re.compile(r"\{[A-Z][A-Z0-9_]*\}")


def hf_row_empty(row: dict, tokens) -> bool:
    """A band row left with nothing to say (``drop_empty_rows=True``): it has
    tokens of one's own, every one empty, and the rest is blanks and brackets
    (``"<{POPULATION}>"``).  A row with no token, or one of rtfreporter's own
    (``{PAGE}``) or an unknown one, is never empty (R ``.hf_row_empty()``)."""
    tokens = tokens or {}
    txt = " ".join(str(v) for v in row.values() if v is not None)
    found = _TOKEN_IN_ROW.findall(txt)
    if not found:
        return False
    names = [m[1:-1] for m in found]
    if not all(n in tokens for n in names):
        return False
    if any(tokens[n].strip() for n in names):
        return False
    return re.sub(r"[\][\s<>():;,.|/-]", "", _TOKEN_IN_ROW.sub("", txt)) == ""



#: A footer band carries a top rule by default, as in R (`rtf_border_top()`);
#: pass ``border=None`` for no rule.
_FOOTER_RULE = Border(top=BorderSide(style="single", width=15))


def rtf_header(
    rows,
    border: Border | None = None,
    row_height_twips: int | None = None,
    cell_padding_left_twips: int | None = None,
    cell_padding_right_twips: int | None = None,
    width_twips: int | None = None,
    width=None,
    font_size_half_points: int | None = None,
    font: str | None = None,
    markup=None,
    drop_empty_rows: bool = False,
) -> HeaderFooter:
    """Build a page-header band.

    Args:
        rows: A list of rows.  Each row is a str (centered), a dict with ``l``
            / ``c`` / ``r`` keys, or a short sequence.
        border: Optional :class:`~rtfreporter.borders.Border` on the first row.
        width: The band's width -- ``"page"`` (the default: the writable
            width), a fraction of it, or twips.  ``width_twips`` is the older
            absolute spelling and wins when both are given.
        font_size_half_points, markup: Style for this band, overriding the
            document default.  A size given without ``row_height_twips``
            recomputes the height from that size.
        font: Per-band font family.
        drop_empty_rows: ``True``: a row whose tokens of one's own
            (``rtf_document(tokens=)``, ``rtfreporter_options(tokens=)``) are
            all empty when the file is written, and which says nothing else
            but blanks and brackets (``"<{POPULATION}>"``), is left out.  One
            header can then serve every report of a study, a report with no
            value for a line going without it.  ``False`` (default): every
            row is written.
    """
    return HeaderFooter(
        rows=list(rows),
        border=border,
        row_height_twips=row_height_twips,
        cell_padding_left_twips=cell_padding_left_twips,
        cell_padding_right_twips=cell_padding_right_twips,
        width_twips=width_twips,
        is_footer=False,
        width=width,
        font_size_half_points=font_size_half_points,
        font=font,
        markup=markup,
        drop_empty_rows=drop_empty_rows,
    )


def rtf_footer(
    rows,
    border: Border | None = _FOOTER_RULE,
    row_height_twips: int | None = None,
    cell_padding_left_twips: int | None = None,
    cell_padding_right_twips: int | None = None,
    width_twips: int | None = None,
    width=None,
    font_size_half_points: int | None = None,
    font: str | None = None,
    markup=None,
    drop_empty_rows: bool = False,
) -> HeaderFooter:
    """Build a page-footer band (same shape as :func:`rtf_header`)."""
    return HeaderFooter(
        rows=list(rows),
        border=border,
        row_height_twips=row_height_twips,
        cell_padding_left_twips=cell_padding_left_twips,
        cell_padding_right_twips=cell_padding_right_twips,
        width_twips=width_twips,
        is_footer=True,
        width=width,
        font_size_half_points=font_size_half_points,
        font=font,
        markup=markup,
        drop_empty_rows=drop_empty_rows,
    )


def _update_hf_rows(hf: HeaderFooter, row: int, content) -> HeaderFooter:
    if not isinstance(hf, HeaderFooter):
        raise TypeError("First argument must be an rtf_header() or rtf_footer() object.")
    row = int(row)
    if row < 0:
        raise ValueError("`row` must be >= 0 (0-based; the top row is 0).")
    rows = list(hf.rows)
    norm = _normalize_row(content)
    if row >= len(rows):
        # Fill any gap with empty centre rows, then place the content at `row`.
        rows.extend({"c": ""} for _ in range(row - len(rows)))
        rows.append(norm)
    else:
        rows[row] = norm
    return replace(hf, rows=rows)


def update_header_row(header: HeaderFooter, row: int, content) -> HeaderFooter:
    """Add or replace a single row of a header band (deprecated; mirrors ``update_header_row()``).

    **Deprecated** (warns once a session, still works; removed in 0.9.0, as in
    R): make the header again with ``rtf_header(rows=)`` -- its rows are a
    list, and a list is edited with Python.

    Returns a **copy** with row ``row`` (0-based; the top row is ``0``) set to
    ``content`` (a str, an ``l``/``c``/``r`` dict, or a short sequence).  A
    ``row`` beyond the current rows extends the band, filling any gap with empty
    centred rows.
    """
    from .borders import _deprecate_once

    _deprecate_once(
        "update_header_row",
        "`update_header_row()` is deprecated: make the header again with "
        "`rtf_header(rows=)` (a list of rows).\n  Removed in 0.9.0.",
    )
    return _update_hf_rows(header, row, content)


def update_footer_row(footer: HeaderFooter, row: int, content) -> HeaderFooter:
    """Add or replace a single row of a footer band (deprecated; see :func:`update_header_row`).

    **Deprecated**: make the footer again with ``rtf_footer(rows=)``.
    """
    from .borders import _deprecate_once

    _deprecate_once(
        "update_footer_row",
        "`update_footer_row()` is deprecated: make the footer again with "
        "`rtf_footer(rows=)` (a list of rows).\n  Removed in 0.9.0.",
    )
    return _update_hf_rows(footer, row, content)


def normalize_hf(value) -> HeaderFooter | None:
    """Coerce a header/footer value (band, list of rows, or None) to a band."""
    if value is None:
        return None
    if isinstance(value, HeaderFooter):
        return value
    if isinstance(value, (list, tuple)):
        return HeaderFooter(rows=list(value))
    if isinstance(value, (str, dict)):
        return HeaderFooter(rows=[value])
    raise TypeError("A header/footer must be a HeaderFooter, list of rows, or None.")
