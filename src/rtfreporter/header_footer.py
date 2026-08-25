"""Running page header and footer bands.

Ported from the R ``rtf_header()`` / ``rtf_footer()`` model.  A band is a stack
of rows; each row has 1-3 columns keyed by position:

* ``l`` -> left, ``c`` -> center, ``r`` -> right.
* ``l`` + ``r`` -> a two-column (left/right) row.
* ``l`` + ``c`` + ``r`` -> a three-column row.
* a plain string -> a single centered column.

Cells may contain page tokens (``{AUTO_PAGE}``, ``{AUTO_TOTAL_PAGES}``,
``{PAGE}``, ``{TOTAL_PAGES}``, ``{SECTION_PAGES}``).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

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

    def __post_init__(self) -> None:
        self.rows = [_normalize_row(r) for r in self.rows]



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
) -> HeaderFooter:
    """Build a page-header band.

    Args:
        rows: A list of rows.  Each row is a str (centered), a dict with ``l``
            / ``c`` / ``r`` keys, or a short sequence.
        border: Optional :class:`~rtfreporter.borders.Border` on the first row.
    """
    return HeaderFooter(
        rows=list(rows),
        border=border,
        row_height_twips=row_height_twips,
        cell_padding_left_twips=cell_padding_left_twips,
        cell_padding_right_twips=cell_padding_right_twips,
        width_twips=width_twips,
        is_footer=False,
    )


def rtf_footer(
    rows,
    border: Border | None = _FOOTER_RULE,
    row_height_twips: int | None = None,
    cell_padding_left_twips: int | None = None,
    cell_padding_right_twips: int | None = None,
    width_twips: int | None = None,
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
    """Add or replace a single row of a header band (mirrors ``update_header_row()``).

    Returns a **copy** with row ``row`` (0-based; the top row is ``0``) set to
    ``content`` (a str, an ``l``/``c``/``r`` dict, or a short sequence).  A
    ``row`` beyond the current rows extends the band, filling any gap with empty
    centred rows.
    """
    return _update_hf_rows(header, row, content)


def update_footer_row(footer: HeaderFooter, row: int, content) -> HeaderFooter:
    """Add or replace a single row of a footer band (see :func:`update_header_row`)."""
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
