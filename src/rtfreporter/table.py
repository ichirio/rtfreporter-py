"""The :class:`RtfTable` table model and its column-header pieces.

Ported from ``R/rtftable.R``, ``R/col_header.R`` and ``R/col_drop.R``.  The
model stores:

* a rectangular body (``column_names`` + ``rows``),
* a stack of column-header rows (plain label rows and/or spanning rows),
* a per-column :class:`ColSpec` list,
* border zones (a :class:`~rtfreporter.borders.TableBorder`),
* geometry (column/table widths, alignment, row heights) and
* per-cell style overrides.

Column indices in the public API are **0-based**; a column *name* may be used
anywhere an index is accepted.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from ._escape import resolve_markup
from .borders import Border, TableBorder, border_tfl, normalize_table_border

_ALIGN = ("left", "center", "right")


@dataclass
class ColSpec:
    """Per-column formatting spec.

    Args:
        align: Body-cell alignment (``"left"``/``"center"``/``"right"``).
        bold, italic, underline: Body-cell decoration flags.
        indent_twips: Left indent (twips) added to the body cell.
        color: Body-cell text colour (hex string) or ``None``.
        border: Per-column :class:`~rtfreporter.borders.Border` override.
        header_align: Column-header alignment (defaults to ``align`` or center).
        header_bold, header_italic: Column-header decoration flags.
    """

    align: str | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    indent_twips: int = 0
    color: str | None = None
    border: Border | None = None
    header_align: str | None = None
    header_bold: bool = False
    header_italic: bool = False


@dataclass
class SpanCell:
    """A resolved spanning-header cell covering columns ``start..end`` (0-based)."""

    start: int
    end: int
    label: str = ""
    align: str | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    border: Border | None = None


@dataclass
class _ColCellSpec:
    """Unresolved spanning cell as written by :func:`col_cell` (name/index refs)."""

    pos: Any
    label: str = ""
    align: str | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    border: Border | None = None


def col_cell(
    cols,
    label: str = "",
    align: str | None = None,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    border: Border | None = None,
) -> _ColCellSpec:
    """Define one spanning column-header cell.

    Args:
        cols: A single 0-based column index, a ``(start, end)`` inclusive range,
            a column name, or a ``(name, name)`` pair.
        label: Cell text.
        align: ``"left"`` / ``"center"`` / ``"right"`` (defaults from the
            leftmost covered column's header alignment, then center).
        bold, italic, underline: Decoration flags.
        border: Optional per-cell :class:`~rtfreporter.borders.Border`.
    """
    if align is not None and align not in _ALIGN:
        raise ValueError('`align` must be None, "left", "center", or "right".')
    if border is not None and not isinstance(border, Border):
        raise TypeError("`border` must be None or a Border object.")
    return _ColCellSpec(
        pos=cols,
        label="" if label is None else str(label),
        align=align,
        bold=bold,
        italic=italic,
        underline=underline,
        border=border,
    )


@dataclass
class HeaderRow:
    """One column-header row: either plain labels or spanning cells."""

    kind: str  # "labels" | "spanning"
    labels: list[str] | None = None
    spans: list[SpanCell] | None = None


def _resolve_col(ref, names: list[str]) -> int:
    """Resolve a 0-based index or a column name to a 0-based index."""
    if isinstance(ref, str):
        if ref not in names:
            raise ValueError(f"Unknown column name {ref!r}.")
        return names.index(ref)
    idx = int(ref)
    if idx < 0 or idx >= len(names):
        raise ValueError(f"Column index {idx} out of range (0..{len(names) - 1}).")
    return idx


def _resolve_span_cell(spec: _ColCellSpec, names: list[str]) -> SpanCell:
    pos = spec.pos
    if isinstance(pos, (list, tuple)):
        if len(pos) == 1:
            start = end = _resolve_col(pos[0], names)
        elif len(pos) == 2:
            start = _resolve_col(pos[0], names)
            end = _resolve_col(pos[1], names)
        else:
            raise ValueError("`cols` must reference one or two columns.")
    else:
        start = end = _resolve_col(pos, names)
    if start > end:
        start, end = end, start
    return SpanCell(
        start=start,
        end=end,
        label=spec.label,
        align=spec.align,
        bold=spec.bold,
        italic=spec.italic,
        underline=spec.underline,
        border=spec.border,
    )


def _is_span_row(row) -> bool:
    if isinstance(row, (list, tuple)) and row:
        return all(isinstance(c, (_ColCellSpec, SpanCell)) for c in row)
    return False


def _normalize_col_header(col_header, ncols: int, names: list[str]) -> list[HeaderRow]:
    """Normalise the ``col_header`` argument to a list of :class:`HeaderRow`."""
    if col_header is None:
        return [HeaderRow(kind="labels", labels=list(names))]

    # A flat list of strings -> a single label row.
    if isinstance(col_header, (list, tuple)) and col_header and all(
        isinstance(c, str) for c in col_header
    ):
        return [HeaderRow(kind="labels", labels=_pad_labels(list(col_header), ncols))]

    # A single spanning row given directly.
    if _is_span_row(col_header):
        return [_span_header_row(col_header, names)]

    # Otherwise a list of rows.
    rows: list[HeaderRow] = []
    for row in col_header:
        if _is_span_row(row):
            rows.append(_span_header_row(row, names))
        elif isinstance(row, HeaderRow):
            rows.append(row)
        else:
            labels = [("" if x is None else str(x)) for x in row]
            rows.append(HeaderRow(kind="labels", labels=_pad_labels(labels, ncols)))
    return rows


def _span_header_row(row, names: list[str]) -> HeaderRow:
    spans = []
    for cell in row:
        if isinstance(cell, SpanCell):
            spans.append(cell)
        else:
            spans.append(_resolve_span_cell(cell, names))
    return HeaderRow(kind="spanning", spans=spans)


def _pad_labels(labels: list[str], ncols: int) -> list[str]:
    labels = list(labels)
    if len(labels) < ncols:
        labels += [""] * (ncols - len(labels))
    return labels[:ncols]


def _normalize_col_spec(
    col_spec,
    ncols: int,
    names: list[str],
    col_header_align=None,
) -> list[ColSpec]:
    """Build a per-column list of :class:`ColSpec` from user input."""
    specs = [ColSpec() for _ in range(ncols)]

    if col_spec:
        for entry in col_spec:
            if isinstance(entry, ColSpec):
                # Positional ColSpec objects require an explicit index elsewhere;
                # accept a (index, ColSpec) tuple form too.
                raise TypeError(
                    "Pass col_spec entries as dicts with a 'col' key, "
                    "or use style_cols() after construction."
                )
            if not isinstance(entry, dict):
                raise TypeError("Each col_spec entry must be a dict.")
            entry = dict(entry)
            col = entry.pop("col", None)
            if col is None:
                raise ValueError("Each col_spec entry needs a 'col' key.")
            idx = _resolve_col(col, names)
            cur = specs[idx]
            specs[idx] = replace(cur, **_validate_spec_fields(entry))

    # header_align cascade: explicit spec header_align > col_header_align >
    # the column's body align > center (resolved lazily in the renderer, but we
    # seed a sensible default here for spanning inheritance).
    aligns = _resolve_header_align(col_header_align, ncols)
    for i, spec in enumerate(specs):
        if spec.header_align is None:
            if aligns is not None and aligns[i] is not None:
                specs[i] = replace(spec, header_align=aligns[i])
            elif spec.align is not None:
                specs[i] = replace(spec, header_align=spec.align)
    return specs


def _validate_spec_fields(entry: dict) -> dict:
    allowed = {
        "align",
        "bold",
        "italic",
        "underline",
        "indent_twips",
        "color",
        "border",
        "header_align",
        "header_bold",
        "header_italic",
    }
    unknown = set(entry) - allowed
    if unknown:
        raise ValueError(f"Unknown col_spec field(s): {sorted(unknown)}.")
    for k in ("align", "header_align"):
        if entry.get(k) is not None and entry[k] not in _ALIGN:
            raise ValueError(f'`{k}` must be one of {_ALIGN}.')
    return entry


def _resolve_header_align(col_header_align, ncols):
    if col_header_align is None:
        return None
    if isinstance(col_header_align, str):
        return [col_header_align] * ncols
    lst = list(col_header_align)
    if len(lst) != ncols:
        raise ValueError("`col_header_align` length must equal the column count.")
    return lst


def _resolve_blank_rows(blank_rows, column_names, rows) -> list[int]:
    """Resolve a blank-row spec to a sorted list of positions.

    Accepts an int, an iterable of ints (``-1`` = after the last row, ``0`` =
    before the first), a :class:`~rtfreporter.blank_rows.BlankRowsByChange` /
    :class:`~rtfreporter.blank_rows.BlankRowsByRule` spec, or a list mixing any
    of these (positions are unioned).
    """
    from .blank_rows import BlankRowsByChange, BlankRowsByRule

    if blank_rows is None:
        return []
    nrows = len(rows)
    positions: set[int] = set()

    def add(item):
        if isinstance(item, (BlankRowsByChange, BlankRowsByRule)):
            positions.update(item.positions(column_names, rows))
        elif isinstance(item, (list, tuple, set)):
            for x in item:
                add(x)
        else:
            positions.add(int(item))

    add(blank_rows)
    resolved = {nrows if p == -1 else p for p in positions}
    return sorted(p for p in resolved if 0 <= p <= nrows)


@dataclass
class RtfTable:
    """A rendered-ready clinical table model.

    Construct via :func:`rtftable` (or an adapter such as
    :func:`~rtfreporter.adapters.as_rtftable`).  Instances are treated as
    immutable by the style verbs, which return modified copies.
    """

    column_names: list[str]
    rows: list[list[Any]]
    col_header: list[HeaderRow]
    col_spec: list[ColSpec]
    border: TableBorder | None = None
    blank_rows: list[int] = field(default_factory=list)
    col_rel_width: list[float] | None = None
    column_widths_twips: list[int] | None = None
    table_width_twips: int | None = None
    table_width_pct_of_writable: float | None = None
    table_align: str = "left"
    row_height_twips: int | None = None
    row_height_exact: bool = False
    header_row_height_twips: int | None = None
    blank_row_height_twips: int | None = None
    cell_padding_left_twips: int | None = None
    cell_padding_right_twips: int | None = None
    cell_valign: str = "bottom"
    cell_styles: list | None = None
    blank_row_normalize: frozenset = field(default_factory=lambda: frozenset({"detect", "collapse"}))
    markup: frozenset | None = None
    titles: list[str] | None = None
    footnotes: list[str] | None = None

    @property
    def ncols(self) -> int:
        return len(self.column_names)

    @property
    def nrows(self) -> int:
        return len(self.rows)

    def copy(self) -> RtfTable:
        """Return a shallow structural copy safe for style-verb mutation."""
        return replace(
            self,
            column_names=list(self.column_names),
            rows=[list(r) for r in self.rows],
            col_header=list(self.col_header),
            col_spec=[replace(s) for s in self.col_spec],
            blank_rows=list(self.blank_rows),
        )


def rtftable(
    data,
    col_header=None,
    col_header_align=None,
    col_spec=None,
    border="tfl",
    blank_rows=None,
    col_rel_width=None,
    column_widths_twips=None,
    table_width_twips=None,
    table_width_pct=None,
    table_align="left",
    row_height_twips=None,
    row_height_exact=False,
    header_row_height_twips=None,
    blank_row_height_twips=None,
    cell_padding_left_twips=None,
    cell_padding_right_twips=None,
    cell_valign="bottom",
    cell_styles=None,
    blank_row_normalize=("detect", "collapse"),
    markup=None,
) -> RtfTable:
    """Build an :class:`RtfTable` from tabular data.

    Args:
        data: A mapping of column name -> values, a ``(column_names, rows)``
            pair, a list of row dicts, or a pandas/polars DataFrame.
        col_header: ``None`` (use column names), a flat list of label strings,
            or a list of header rows (label lists and/or lists of
            :func:`col_cell`).
        col_header_align: A single alignment or one per column applied to the
            column headers.
        col_spec: A list of dicts, each with a ``col`` key (0-based index or
            name) plus any :class:`ColSpec` fields.
        border: ``"tfl"`` (default), ``"none"``/``None``, a
            :class:`~rtfreporter.borders.TableBorder`, or a
            :class:`~rtfreporter.borders.Border`.
        blank_rows: Int positions (``-1`` = after last), an iterable of them, or
            the output of :func:`blank_rows_by_change` / :func:`blank_rows_by_rule`.
        table_width_pct: Table width as a percentage (0, 100] of writable width.
    """
    column_names, rows = _coerce_data(data)
    ncols = len(column_names)

    header_rows = _normalize_col_header(col_header, ncols, column_names)
    specs = _normalize_col_spec(col_spec, ncols, column_names, col_header_align)
    border_resolved = normalize_table_border(border) if border != "tfl" else border_tfl()

    blank_positions = _resolve_blank_rows(blank_rows, column_names, rows)

    twpw = None
    if table_width_pct is not None:
        pct = float(table_width_pct)
        if pct <= 0 or pct > 100:
            raise ValueError("`table_width_pct` must be in (0, 100].")
        twpw = pct / 100.0

    if table_align not in _ALIGN:
        raise ValueError("`table_align` must be 'left', 'center', or 'right'.")
    if cell_valign not in ("top", "center", "bottom"):
        raise ValueError("`cell_valign` must be 'top', 'center', or 'bottom'.")

    if column_widths_twips is not None:
        column_widths_twips = [int(w) for w in column_widths_twips]
        if len(column_widths_twips) != ncols:
            raise ValueError("`column_widths_twips` length must match column count.")
    if col_rel_width is not None:
        col_rel_width = [float(w) for w in col_rel_width]
        if len(col_rel_width) != ncols:
            raise ValueError("`col_rel_width` length must match column count.")

    if cell_styles is not None and len(cell_styles) != len(rows):
        raise ValueError("`cell_styles` length must equal the number of data rows.")

    return RtfTable(
        column_names=column_names,
        rows=rows,
        col_header=header_rows,
        col_spec=specs,
        border=border_resolved,
        blank_rows=blank_positions,
        col_rel_width=col_rel_width,
        column_widths_twips=column_widths_twips,
        table_width_twips=int(table_width_twips) if table_width_twips is not None else None,
        table_width_pct_of_writable=twpw,
        table_align=table_align,
        row_height_twips=int(row_height_twips) if row_height_twips is not None else None,
        row_height_exact=bool(row_height_exact),
        header_row_height_twips=(
            int(header_row_height_twips) if header_row_height_twips is not None else None
        ),
        blank_row_height_twips=(
            int(blank_row_height_twips) if blank_row_height_twips is not None else None
        ),
        cell_padding_left_twips=(
            int(cell_padding_left_twips) if cell_padding_left_twips is not None else None
        ),
        cell_padding_right_twips=(
            int(cell_padding_right_twips) if cell_padding_right_twips is not None else None
        ),
        cell_valign=cell_valign,
        cell_styles=cell_styles,
        blank_row_normalize=frozenset(blank_row_normalize or ()),
        markup=resolve_markup(markup) if markup is not None else None,
    )


def _coerce_data(data) -> tuple[list[str], list[list[Any]]]:
    """Coerce accepted inputs to ``(column_names, rows)``."""
    # pandas / polars DataFrame (duck-typed to avoid a hard dependency).
    if hasattr(data, "to_dict") and hasattr(data, "columns") and hasattr(data, "iloc"):
        return _from_pandas(data)
    if hasattr(data, "to_pandas") and hasattr(data, "columns"):  # polars
        return _from_pandas(data.to_pandas())
    if isinstance(data, dict):
        names = list(data.keys())
        cols = [list(v) for v in data.values()]
        n = max((len(c) for c in cols), default=0)
        rows = [[cols[j][i] if i < len(cols[j]) else None for j in range(len(names))]
                for i in range(n)]
        return names, rows
    if isinstance(data, (list, tuple)):
        if data and isinstance(data[0], dict):
            names: list[str] = []
            for rec in data:
                for k in rec:
                    if k not in names:
                        names.append(k)
            rows = [[rec.get(k) for k in names] for rec in data]
            return names, rows
        # (column_names, rows) pair.
        if len(data) == 2 and isinstance(data[0], (list, tuple)):
            names = list(data[0])
            rows = [list(r) for r in data[1]]
            return names, rows
    raise TypeError(
        "`data` must be a dict of columns, a (names, rows) pair, a list of row "
        "dicts, or a pandas/polars DataFrame."
    )


def _from_pandas(df) -> tuple[list[str], list[list[Any]]]:
    import math

    names = [str(c) for c in df.columns]
    rows = []
    for rec in df.itertuples(index=False, name=None):
        row = []
        for v in rec:
            if v is None:
                row.append(None)
            elif isinstance(v, float) and math.isnan(v):
                row.append(None)
            else:
                row.append(v)
        rows.append(row)
    return names, rows
