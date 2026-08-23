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
from .borders import Border, TableBorder, normalize_table_border, rtf_border_tfl

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


def rtf_col_header(*rows) -> list:
    """Collect column-header rows (top-to-bottom) for ``rtftable(col_header=...)``.

    Mirrors R's ``rtf_col_header(...)``.  Each argument is one header row: a
    list of label strings, or a list of :func:`col_cell` spanning cells.
    Returns a plain list suitable to pass as ``col_header``.

    Example:
        >>> hdr = rtf_col_header(
        ...     [col_cell(0, ""), col_cell((1, 2), "Treatment")],
        ...     ["Item", "N", "Mean"],
        ... )
    """
    return list(rows)


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


def _spanning_header_row(spanning_header, ncols: int, names: list[str]) -> HeaderRow:
    """Build one spanning :class:`HeaderRow` from a ``spanning_header`` spec.

    Each element is a :class:`SpanCell`, a :func:`col_cell` spec, or a dict with
    ``from`` / ``to`` (0-based inclusive column indices or names), ``label``, and
    optional ``underline`` / ``align`` / ``bold`` / ``italic``.
    """
    spans: list[SpanCell] = []
    for cell in spanning_header:
        if isinstance(cell, SpanCell):
            spans.append(cell)
        elif isinstance(cell, _ColCellSpec):
            spans.append(_resolve_span_cell(cell, names))
        elif isinstance(cell, dict):
            spec = dict(cell)
            frm = spec.get("from")
            to = spec.get("to", frm)
            if frm is None:
                raise ValueError("Each `spanning_header` entry needs a 'from' key.")
            start = _resolve_col(frm, names)
            end = _resolve_col(to, names)
            if start > end:
                raise ValueError("`spanning_header` 'from' must be <= 'to'.")
            underline = spec.get("underline", False)
            border = None
            if underline:
                from .borders import BorderSide

                border = Border(bottom=BorderSide())
            spans.append(
                SpanCell(
                    start=start,
                    end=end,
                    label="" if spec.get("label") is None else str(spec["label"]),
                    align=spec.get("align"),
                    bold=bool(spec.get("bold", False)),
                    italic=bool(spec.get("italic", False)),
                    underline=bool(spec.get("underline_text", False)),
                    border=border,
                )
            )
        else:
            raise TypeError(
                "Each `spanning_header` entry must be a SpanCell, col_cell(), or dict."
            )
    return HeaderRow(kind="spanning", spans=spans)


def _read_attr_blank_rows(data):
    """Read a ``rtf_blank_rows`` attribute off ``data`` (pandas ``.attrs`` or Frame)."""
    # A Frame / stub result carrying blank positions from set_blank_rows().
    fbr = getattr(data, "blank_rows", None)
    if fbr is not None and not hasattr(data, "columns"):
        return fbr
    attrs = getattr(data, "attrs", None)
    if isinstance(attrs, dict):
        return attrs.get("rtf_blank_rows")
    return None


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


def _normalize_row_title(row_title, ncols: int, names: list[str]) -> list[int]:
    """Resolve ``row_title`` to a list of 0-based row-heading column indices.

    ``None`` (default) means the first column only.  Otherwise a single
    index/name or an iterable of indices/names (all 0-based).
    """
    if row_title is None:
        return [0] if ncols else []
    refs = row_title if isinstance(row_title, (list, tuple)) else [row_title]
    out: list[int] = []
    for ref in refs:
        idx = _resolve_col(ref, names)
        if idx < 0 or idx >= ncols:
            raise ValueError(f"`row_title` index {idx} out of range 0..{ncols - 1}.")
        out.append(idx)
    return out


def _default_aligns_from_row_title(row_title_idx: list[int], ncols: int) -> list[str]:
    """Row-heading columns default to ``"left"``; every other column ``"center"``."""
    heading = set(row_title_idx)
    return ["left" if i in heading else "center" for i in range(ncols)]


def _apply_table_style(
    style,
    border,
    table_align,
    cell_padding_left_twips,
    cell_padding_right_twips,
    row_height_twips,
    header_row_height_twips,
    markup,
):
    """Fold a shared ``style`` object's defaults under explicit arguments.

    ``style`` is any object (e.g. from :func:`~rtfreporter.rtf_table_style`)
    exposing a subset of the recognised attributes.  An explicit argument always
    wins over the corresponding style attribute; the style only fills in values
    left at their default (``None``, or ``"tfl"`` for ``border``).  Returns the
    resolved ``(border, table_align, pad_l, pad_r, row_h, header_row_h, markup,
    style_aligns)`` tuple.
    """

    def g(name):
        return getattr(style, name, None)

    if border == "tfl" and g("border") is not None:
        border = g("border")
    if cell_padding_left_twips is None and g("cell_padding_left_twips") is not None:
        cell_padding_left_twips = g("cell_padding_left_twips")
    if cell_padding_right_twips is None and g("cell_padding_right_twips") is not None:
        cell_padding_right_twips = g("cell_padding_right_twips")
    if row_height_twips is None and g("row_height_twips") is not None:
        row_height_twips = g("row_height_twips")
    if header_row_height_twips is None and g("header_row_height_twips") is not None:
        header_row_height_twips = g("header_row_height_twips")
    if markup is None and g("markup") is not None:
        markup = g("markup")
    # `table_align` has no ``None`` default; the style fills in only when the
    # argument is still at its factory default ("left").
    if table_align == "left" and g("table_align") is not None:
        table_align = g("table_align")

    style_aligns = None
    if g("align") is not None:
        style_aligns = g("align")
    return (
        border,
        table_align,
        cell_padding_left_twips,
        cell_padding_right_twips,
        row_height_twips,
        header_row_height_twips,
        markup,
        style_aligns,
    )


def _normalize_col_spec(
    col_spec,
    ncols: int,
    names: list[str],
    col_header_align=None,
    default_aligns=None,
    default_spec: ColSpec | None = None,
) -> list[ColSpec]:
    """Build a per-column list of :class:`ColSpec` from user input.

    ``default_aligns`` (one entry per column) seeds the body alignment of any
    column whose alignment is not set explicitly by ``col_spec``; it is derived
    from ``row_title`` (see :func:`_default_aligns_from_row_title`).
    ``default_spec`` seeds the per-column decoration defaults (e.g. from a shared
    ``style``); explicit ``col_spec`` entries override it.
    """
    base = default_spec if default_spec is not None else ColSpec()
    specs = [replace(base) for _ in range(ncols)]

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

    # Seed the body alignment default from row_title where not set explicitly.
    if default_aligns is not None:
        for i, spec in enumerate(specs):
            if spec.align is None:
                specs[i] = replace(spec, align=default_aligns[i])

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
    """Resolve a public blank-row spec to internal positions.

    Accepts (any of, mixed in a list -- positions are unioned):

    * a 0-based integer ``i`` meaning "insert a blank row **after** data row
      ``i``";
    * the sentinel :data:`~rtfreporter.blank_rows.BEFORE_FIRST` (before the
      first row) or :data:`~rtfreporter.blank_rows.AFTER_LAST` (after the last
      row);
    * a :class:`~rtfreporter.blank_rows.BlankRowsByChange` /
      :class:`~rtfreporter.blank_rows.BlankRowsByRule` spec.

    A bare negative integer is rejected with a message pointing at
    ``AFTER_LAST``.  The returned list uses the *internal* convention (position
    ``p`` in ``0..nrows`` means "insert before data row ``p``"; ``0`` is before
    the first row and ``nrows`` is after the last row).
    """
    from .blank_rows import (
        AFTER_LAST,
        BEFORE_FIRST,
        BlankRowsByChange,
        BlankRowsByRule,
        _BlankRowSentinel,
    )

    if blank_rows is None:
        return []
    nrows = len(rows)
    positions: set[int] = set()

    def add(item):
        if item is BEFORE_FIRST:
            positions.add(0)
        elif item is AFTER_LAST:
            positions.add(nrows)
        elif isinstance(item, _BlankRowSentinel):  # pragma: no cover - defensive
            raise ValueError(f"Unknown blank-row sentinel {item!r}.")
        elif isinstance(item, (BlankRowsByChange, BlankRowsByRule)):
            positions.update(item.positions(column_names, rows))
        elif isinstance(item, (list, tuple, set)):
            for x in item:
                add(x)
        elif isinstance(item, bool):
            raise TypeError("`blank_rows` positions must be integers, not bool.")
        elif isinstance(item, str):
            raise ValueError(
                "`blank_rows` string shorthand is only resolved by as_rtftables(); "
                f"got {item!r}. Use blank_rows_by_change() here instead."
            )
        else:
            iv = int(item)
            if iv < 0:
                raise ValueError(
                    "`blank_rows` positions are 0-based; a bare negative integer "
                    "is not allowed. Use the AFTER_LAST sentinel to add a blank "
                    "row after the last data row."
                )
            # Public i ("after data row i") -> internal i + 1 ("before row i+1").
            positions.add(iv + 1)

    add(blank_rows)
    return sorted(p for p in positions if 0 <= p <= nrows)


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
    name: str | None = None

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
    spanning_header=None,
    col_spec=None,
    row_title=None,
    border="tfl",
    blank_rows=None,
    read_attributes=True,
    style=None,
    col_rel_width=None,
    column_widths_twips=None,
    table_width_twips=None,
    table_width_pct_of_writable=None,
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
    _blank_positions=None,
) -> RtfTable:
    """Build an :class:`RtfTable` from tabular data.

    Argument names follow the R ``rtftable()`` function.  All index-taking
    arguments are **0-based** (a deliberate divergence from R's 1-based indices).

    Args:
        data: A mapping of column name -> values, a ``(column_names, rows)``
            pair, a list of row dicts, or a pandas/polars DataFrame.
        col_header: ``None`` (use column names), a flat list of label strings,
            or a list of header rows (label lists and/or lists of
            :func:`col_cell`).
        col_header_align: A single alignment or one per column applied to the
            column headers.
        spanning_header: A standalone spanning row placed **above** the
            ``col_header`` rows.  A list of :class:`SpanCell` / :func:`col_cell`
            specs or dicts (``from`` / ``to`` 0-based inclusive, ``label``,
            ``underline``).  New code should put spanning rows directly in
            ``col_header``.
        col_spec: A list of dicts, each with a ``col`` key (0-based index or
            name) plus any :class:`ColSpec` fields.
        row_title: Which column(s) are row-heading columns (0-based index/name
            or a list).  ``None`` (default) means the first column.  Row-heading
            columns default to ``"left"`` body alignment; every other column
            defaults to ``"center"``.  Explicit ``col_spec`` alignment overrides.
        border: ``"tfl"`` (default), ``"none"``/``None``, a
            :class:`~rtfreporter.borders.TableBorder`, or a
            :class:`~rtfreporter.borders.Border`.
        blank_rows: 0-based int positions (``i`` = after data row ``i``), the
            :data:`~rtfreporter.blank_rows.BEFORE_FIRST` /
            :data:`~rtfreporter.blank_rows.AFTER_LAST` sentinels, an iterable of
            those, or the output of :func:`blank_rows_by_change` /
            :func:`blank_rows_by_rule`.
        read_attributes: When ``True`` (default) and ``blank_rows`` is ``None``,
            fold a ``rtf_blank_rows`` attribute read off ``data`` (a pandas
            ``.attrs`` entry, as written by :func:`set_blank_rows`) into
            ``blank_rows``.
        style: An optional shared style object (see
            :func:`~rtfreporter.rtf_table_style`) providing defaults for
            ``border`` / ``table_align`` / padding / row heights / alignment;
            explicit arguments always override.
        table_width_twips: Total table width in twips.
        table_width_pct_of_writable: Table width as a fraction ``(0, 1]`` of the
            writable page width.
        table_width_pct: Table width as a percentage ``(0, 100]`` of writable
            width (convenience alias for ``table_width_pct_of_writable * 100``).
    """
    column_names, rows = _coerce_data(data)
    ncols = len(column_names)

    if style is not None:
        (
            border,
            table_align,
            cell_padding_left_twips,
            cell_padding_right_twips,
            row_height_twips,
            header_row_height_twips,
            markup,
            _style_aligns,
        ) = _apply_table_style(
            style,
            border,
            table_align,
            cell_padding_left_twips,
            cell_padding_right_twips,
            row_height_twips,
            header_row_height_twips,
            markup,
        )
        _style_default_spec = ColSpec(
            bold=bool(getattr(style, "bold", False)),
            italic=bool(getattr(style, "italic", False)),
            underline=bool(getattr(style, "underline", False)),
            header_bold=bool(getattr(style, "header_bold", False)),
            header_italic=bool(getattr(style, "header_italic", False)),
        )
        if col_header_align is None and getattr(style, "header_align", None) is not None:
            col_header_align = style.header_align
    else:
        _style_aligns = None
        _style_default_spec = None

    if blank_rows is None and read_attributes:
        blank_rows = _read_attr_blank_rows(data)

    row_title_idx = _normalize_row_title(row_title, ncols, column_names)
    default_aligns = _default_aligns_from_row_title(row_title_idx, ncols)
    if _style_aligns is not None:
        if isinstance(_style_aligns, str):
            default_aligns = [_style_aligns] * ncols
        else:
            sa = list(_style_aligns)
            if len(sa) != ncols:
                raise ValueError("`style.align` length must equal the column count.")
            default_aligns = sa

    header_rows = _normalize_col_header(col_header, ncols, column_names)
    if spanning_header is not None:
        header_rows = [
            _spanning_header_row(spanning_header, ncols, column_names)
        ] + header_rows
    specs = _normalize_col_spec(
        col_spec, ncols, column_names, col_header_align, default_aligns,
        default_spec=_style_default_spec,
    )
    border_resolved = normalize_table_border(border) if border != "tfl" else rtf_border_tfl()

    if _blank_positions is not None:
        blank_positions = sorted(p for p in set(_blank_positions) if 0 <= p <= len(rows))
    else:
        blank_positions = _resolve_blank_rows(blank_rows, column_names, rows)

    twpw = None
    if table_width_pct_of_writable is not None and table_width_pct is not None:
        raise ValueError(
            "Pass only one of `table_width_pct_of_writable` or `table_width_pct`."
        )
    if table_width_pct_of_writable is not None:
        frac = float(table_width_pct_of_writable)
        if frac <= 0 or frac > 1:
            raise ValueError("`table_width_pct_of_writable` must be in (0, 1].")
        twpw = frac
    elif table_width_pct is not None:
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
    # A pagination Frame / stub_cols result (duck-typed on its two fields).
    if hasattr(data, "column_names") and hasattr(data, "rows") and not hasattr(data, "columns"):
        return list(data.column_names), [list(r) for r in data.rows]
    # pandas / polars DataFrame (duck-typed to avoid a hard dependency).
    if type(data).__module__.split(".")[0] == "polars":
        cols = data.to_dict(as_series=False)
        return _coerce_data(cols)
    if hasattr(data, "columns") and hasattr(data, "itertuples"):  # pandas
        return _from_pandas(data)
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
