"""RTF renderer core.

Ported from ``R/generate_rtfreport.R``.  Produces a valid RTF document from the
document model (sections + pages of tables/figures with titles/footnotes).

All measurements are in twips.  A ``"none"`` border side emits no command; text
is ASCII-safe via ``\\uNNNN?`` escapes.
"""

from __future__ import annotations

from . import _commands as C
from ._escape import (
    format_cell_text,
    render_tokens,
    resolve_markup,
    substitute_page_tokens,
)
from .borders import (
    Border,
    BorderSide,
    cell_edge_border,
    collect_border_colors,
    collect_table_border_colors,
    expand_table_border,
    merge_border,
    zone_row_border,
)
from .element_style import f_cmd_for, fs_cmd_for, resolve_block_width, resolve_element_metrics
from .figure import Figure
from .header_footer import HeaderFooter, normalize_hf
from .table import HeaderRow, RtfTable, SpanCell

_ALIGN_CMD = {"left": r"\ql", "right": r"\qr", "center": r"\qc"}
_TABLE_ALIGN_CMD = {"center": r"\trqc", "right": r"\trqr"}


# -- Border command building --------------------------------------------------


def _side_command(side: BorderSide | None, prefix: str, color_index_map) -> str:
    if side is None or side.style == "none":
        return ""
    style_cmd = C.BORDER_STYLE.get(side.style)
    if style_cmd is None:
        raise ValueError(f"Unknown border style: {side.style!r}")
    color_cmd = ""
    if side.color is not None and color_index_map:
        idx = color_index_map.get(side.color)
        if idx is not None:
            color_cmd = f"\\brdrcf{idx}"
    return f"{prefix}{style_cmd}\\brdrw{side.width}{color_cmd}"


def build_border_commands(border: Border | None, color_index_map=None) -> str:
    """Build the RTF border commands for all four sides of a cell."""
    if border is None:
        return ""
    return (
        _side_command(border.top, C.BORDER_SIDE_PREFIX["top"], color_index_map)
        + _side_command(border.bottom, C.BORDER_SIDE_PREFIX["bottom"], color_index_map)
        + _side_command(border.left, C.BORDER_SIDE_PREFIX["left"], color_index_map)
        + _side_command(border.right, C.BORDER_SIDE_PREFIX["right"], color_index_map)
    )


def _effective_row_border(base: Border | None, over: Border | None) -> Border | None:
    if over is None:
        return base
    if base is None:
        return over
    return merge_border(base, over)


# -- Column widths ------------------------------------------------------------


def compute_cellx(ncols: int, writable: int, tbl: RtfTable) -> list[int]:
    """Cumulative right-edge positions (twips) for each column."""
    if tbl.column_widths_twips is not None:
        widths = [int(w) for w in tbl.column_widths_twips]
        if len(widths) != ncols:
            raise ValueError("`column_widths_twips` length must match column count.")
        return _cumsum(widths)

    if tbl.table_width_twips is not None:
        total = int(tbl.table_width_twips)
    elif tbl.table_width_pct_of_writable is not None:
        total = int(round(writable * tbl.table_width_pct_of_writable))
    else:
        total = int(writable)

    if tbl.col_rel_width is not None:
        rel = [float(w) for w in tbl.col_rel_width]
        if any(w <= 0 for w in rel):
            raise ValueError("`col_rel_width` values must be positive.")
        s = sum(rel)
        widths = [int(round(total * w / s)) for w in rel]
        widths[-1] = total - sum(widths[:-1])
        return _cumsum(widths)

    cell_w = max(1, total // ncols)
    widths = [cell_w] * ncols
    widths[-1] = total - sum(widths[:-1])
    return _cumsum(widths)


def _cumsum(values: list[int]) -> list[int]:
    out = []
    acc = 0
    for v in values:
        acc += v
        out.append(acc)
    return out


def content_width_twips(content, writable: int) -> int:
    """Rendered width (twips) of a page's content (for title/footnote sizing)."""
    if isinstance(content, RtfTable):
        ncols = content.ncols
        if ncols == 0:
            return int(writable)
        cellx = compute_cellx(ncols, writable, content)
        return int(cellx[-1])
    if isinstance(content, Figure):
        return int(content.display_twips()["w"])
    return int(writable)


def content_align(content) -> str:
    if isinstance(content, RtfTable):
        return content.table_align or "left"
    if isinstance(content, Figure):
        return content.align or "center"
    return "left"


# -- Cell / row builders ------------------------------------------------------


def build_cell_content(
    text: str,
    align: str = "left",
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    indent_twips: int = 0,
    pad_l: int = 0,
    pad_r: int = 0,
    color_idx: int | None = None,
    fs_cmd: str = "",
) -> str:
    """Build one cell's content string (``\\q..\\li..\\ri.. text\\cell``).

    ``fs_cmd`` is the element's own ``\\fs`` run command, or ``""`` when it
    matches the document (see :func:`~rtfreporter.element_style.fs_cmd_for`).
    """
    align_cmd = _ALIGN_CMD.get(align, r"\ql")
    li = int(pad_l) + int(indent_twips)
    ri = int(pad_r)
    if underline:
        text = f"\\ul {text}\\ulnone "
    if italic:
        text = f"\\i {text}\\i0 "
    if bold:
        text = f"\\b {text}\\b0 "
    if color_idx is not None:
        text = f"\\cf{int(color_idx)} {text}\\cf1 "
    return f"{align_cmd}\\li{li}\\ri{ri}{fs_cmd} {text}\\cell"


def build_row(cell_defs, cell_contents, row_height_twips=None, table_align="left") -> str:
    """Build one complete RTF table row string."""
    rh = ""
    if row_height_twips is not None and int(row_height_twips) != 0:
        rh = f"\\trrh{int(row_height_twips)}"
    align_cmd = _TABLE_ALIGN_CMD.get(table_align, "")
    return (
        r"\trowd" + rh + align_cmd + "".join(cell_defs) + "".join(cell_contents) + r"\row"
    )


def cell_shading_cmd(hex_color, color_index_map=None) -> str:
    """``\\clcbpat<N>``: a colour-table index as the cell's fill (R
    ``.cell_shading_cmd()``).  It belongs in the cell DEFINITION, next to the
    borders -- a fill is a property of the cell, not of its text."""
    if not hex_color or not color_index_map:
        return ""
    idx = color_index_map.get(hex_color)
    return "" if idx is None else f"\\clcbpat{int(idx)}"


def row_backgrounds(col_spec, row_cell_styles, ncols: int) -> list:
    """Each cell's fill: the column's ``background``, overridden by a set
    ``cell_styles["background"]`` entry -- resolved as text colour is."""
    cs = row_cell_styles.get("background") if row_cell_styles else None
    out = []
    for j in range(ncols):
        bg = col_spec[j].background if j < len(col_spec) else None
        if cs is not None and j < len(cs) and cs[j] is not None:
            bg = str(cs[j])
        out.append(bg)
    return out


def build_cell_defs(cellx, border, valign_cmd, color_index_map=None, shade=None) -> list[str]:
    """Cell definition strings (border + fill + valign + ``\\cellx``) for all columns.

    A row's ``left`` / ``right`` are its outer edges and ``inside_v`` the rule
    between its cells, so the vertical rules are distributed per cell.  Nothing
    to distribute when the row carries none, the common case.
    """
    n = len(cellx)
    shade_cmds = [cell_shading_cmd(shade[j] if shade and j < len(shade) else None,
                                   color_index_map) for j in range(n)]
    if border is None or (border.left is None and border.right is None and border.inside_v is None):
        border_cmds = build_border_commands(border, color_index_map)
        return [f"{border_cmds}{shade_cmds[j]}{valign_cmd}\\cellx{cellx[j]}" for j in range(n)]
    return [
        f"{build_border_commands(cell_edge_border(border, j, n), color_index_map)}"
        f"{shade_cmds[j]}{valign_cmd}\\cellx{cellx[j]}"
        for j in range(n)
    ]


def _header_outer_border(idx: int, n: int, zone: Border | None) -> Border | None:
    """Outer-frame border for a header row at position ``idx`` of ``n``: the
    same outer/inside rule as every other zone."""
    if zone is None:
        return None
    b = zone_row_border(zone, idx, n)
    if b.top is None and b.bottom is None and b.left is None and b.right is None \
            and b.inside_v is None:
        return None
    return Border(top=b.top, bottom=b.bottom, left=b.left, right=b.right, inside_v=b.inside_v)


# -- Header-row coverage (for spanning-cell group underlines) ------------------


def _header_row_coverage(row: HeaderRow, ncols: int) -> list[int]:
    if row.kind != "spanning":
        return list(range(1, ncols + 1))
    cov = [0] * ncols
    k = 0
    for cell in row.spans:
        k += 1
        for j in range(cell.start, cell.end + 1):
            cov[j] = k
    for j in range(ncols):
        if cov[j] == 0:
            k += 1
            cov[j] = k
    return cov


def _header_row_boundaries(cov: list[int]) -> list[int]:
    return [b for b in range(len(cov) - 1) if cov[b] != cov[b + 1]]


# -- Header renderers ---------------------------------------------------------


def _render_spanning_row(
    spans: list[SpanCell],
    cellx: list[int],
    border: Border | None,
    row_height: int | None,
    pad_l: int,
    pad_r: int,
    valign_cmd: str,
    col_spec,
    table_align: str,
    group_bottom_side: BorderSide | None,
    next_boundaries: list[int] | None,
    markup,
    color_index_map,
    fs_cmd: str = "",
) -> str:
    ncols = len(cellx)
    coverage = [0] * ncols
    for k, sp in enumerate(spans, start=1):
        for j in range(sp.start, sp.end + 1):
            coverage[j] = k

    # Count the emitted cells first -- a span counts once -- so that inside_v
    # can be placed on cell boundaries rather than column boundaries.
    n_cells = 0
    j = 0
    while j < ncols:
        k = coverage[j]
        n_cells += 1
        j = spans[k - 1].end + 1 if k > 0 else j + 1

    def cell_border(k: int | None, single_idx: int | None = None,
                    cell_idx: int = 0) -> Border | None:
        eff = cell_edge_border(border, cell_idx, n_cells)
        if k is not None and k > 0:
            sp = spans[k - 1]
            multi_col = sp.end > sp.start
            span_broken = next_boundaries is None or any(
                sp.start <= b <= sp.end - 1 for b in next_boundaries
            )
            if multi_col and group_bottom_side is not None and span_broken:
                if eff is None:
                    eff = Border()
                eff = merge_border(eff, Border(bottom=group_bottom_side))
            cb = col_spec[sp.start].border if sp.start < len(col_spec) else None
            if cb is not None:
                eff = cb if eff is None else merge_border(eff, cb)
            if sp.border is not None:
                eff = sp.border if eff is None else merge_border(eff, sp.border)
        elif single_idx is not None and single_idx < len(col_spec):
            cb = col_spec[single_idx].border
            if cb is not None:
                eff = cb if eff is None else merge_border(eff, cb)
        return eff

    cell_defs: list[str] = []
    j = 0
    ci = 0
    while j < ncols:
        k = coverage[j]
        if k > 0:
            end = spans[k - 1].end
            bc = build_border_commands(cell_border(k, cell_idx=ci), color_index_map)
            cell_defs.append(f"{bc}{valign_cmd}\\cellx{cellx[end]}")
            j = end + 1
        else:
            bc = build_border_commands(cell_border(None, single_idx=j, cell_idx=ci),
                                       color_index_map)
            cell_defs.append(f"{bc}{valign_cmd}\\cellx{cellx[j]}")
            j += 1
        ci += 1

    def span_align(sp: SpanCell) -> str:
        if sp.align is not None:
            return sp.align
        if sp.start < len(col_spec):
            below = col_spec[sp.start].header_align
            if below:
                return below
        return "center"

    cell_contents: list[str] = []
    j = 0
    while j < ncols:
        k = coverage[j]
        if k > 0:
            sp = spans[k - 1]
            label = format_cell_text(sp.label or "", markup)
            if sp.underline:
                label = f"\\ul {label}\\ulnone "
            if sp.italic:
                label = f"\\i {label}\\i0 "
            if sp.bold:
                label = f"\\b {label}\\b0 "
            align_cmd = _ALIGN_CMD.get(span_align(sp), r"\qc")
            cell_contents.append(f"{align_cmd}\\li{pad_l}\\ri{pad_r}{fs_cmd} {label}\\cell")
            j = sp.end + 1
        else:
            cell_contents.append(f"\\ql\\li{pad_l}\\ri{pad_r}{fs_cmd} \\cell")
            j += 1

    return build_row(cell_defs, cell_contents, row_height, table_align)


def _render_header_row(
    labels: list[str],
    cellx: list[int],
    border: Border | None,
    row_height: int | None,
    pad_l: int,
    pad_r: int,
    valign_cmd: str,
    col_spec,
    table_align: str,
    markup,
    color_index_map,
    fs_cmd: str = "",
) -> str:
    ncols = len(cellx)
    cell_defs = []
    for j in range(ncols):
        eff = cell_edge_border(border, j, ncols)
        col_border = col_spec[j].border
        if col_border is not None:
            eff = _effective_row_border(eff, col_border)
        bc = build_border_commands(eff, color_index_map)
        shade = cell_shading_cmd(col_spec[j].header_background, color_index_map)
        cell_defs.append(f"{bc}{shade}{valign_cmd}\\cellx{cellx[j]}")

    cell_contents = []
    for j in range(ncols):
        spec = col_spec[j]
        raw = labels[j] if j < len(labels) else ""
        text = format_cell_text(raw, markup)
        align = spec.header_align or "center"
        cell_contents.append(
            build_cell_content(text, align, spec.header_bold, spec.header_italic,
                               False, 0, pad_l, pad_r, fs_cmd=fs_cmd)
        )
    return build_row(cell_defs, cell_contents, row_height, table_align)


def _render_data_row(
    vals: list,
    cellx: list[int],
    border: Border | None,
    row_height: int | None,
    pad_l: int,
    pad_r: int,
    valign_cmd: str,
    col_spec,
    table_align: str,
    row_cell_styles: dict | None,
    color_index_map,
    markup,
    fs_cmd: str = "",
    dsplit_row=None,
    dsplit=None,
) -> str:
    ncols = len(cellx)
    # A spanned label row (stub_cols(label_span=True), R #312) is ONE cell
    # running to the table's right edge: its first non-empty value, styled as
    # the first column.
    if row_cell_styles and row_cell_styles.get("span_row"):
        txt = next((v for v in vals if v is not None and str(v) != ""), "")
        cell_def = (f"{build_border_commands(border, color_index_map)}"
                    f"{valign_cmd}\\cellx{cellx[-1]}")
        content = _data_cell_content(col_spec[0], txt, 0, row_cell_styles, pad_l, pad_r,
                                     markup, color_index_map, fs_cmd)
        return build_row([cell_def], [content], row_height, table_align)
    if dsplit_row is not None:
        return _render_data_row_split(
            vals, cellx, border, row_height, pad_l, pad_r, valign_cmd, col_spec,
            table_align, row_cell_styles, color_index_map, markup, dsplit_row, dsplit,
            fs_cmd=fs_cmd)
    cell_borders = row_cell_styles.get("border") if row_cell_styles else None
    # Cell fill, resolved per column the way text colour is.
    shade = row_backgrounds(col_spec, row_cell_styles, ncols)
    if isinstance(cell_borders, list) and any(b is not None for b in cell_borders):
        cell_defs = []
        for j in range(ncols):
            b = cell_borders[j] if j < len(cell_borders) else None
            eff = cell_edge_border(border, j, ncols)
            if b is not None:
                eff = _effective_row_border(eff, b)
            cell_defs.append(
                f"{build_border_commands(eff, color_index_map)}"
                f"{cell_shading_cmd(shade[j], color_index_map)}{valign_cmd}\\cellx{cellx[j]}"
            )
    else:
        cell_defs = build_cell_defs(cellx, border, valign_cmd, color_index_map, shade=shade)

    cell_contents = [
        _data_cell_content(col_spec[j], vals[j] if j < len(vals) else None, j,
                           row_cell_styles, pad_l, pad_r, markup, color_index_map, fs_cmd)
        for j in range(ncols)
    ]
    return build_row(cell_defs, cell_contents, row_height, table_align)


def _render_data_row_split(vals, cellx, border, row_height, pad_l, pad_r, valign_cmd,
                           col_spec, table_align, row_cell_styles, color_index_map,
                           markup, dsplit_row, dsplit, fs_cmd: str = "") -> str:
    """One data row on the decimal-split geometry (R
    ``.render_data_row_split()``).  A pair whose cell was not split-eligible
    on this row collapses back into one cell carrying the ORIGINAL column's
    spec.  Every cell carries the table's own font switch and its fill, as an
    ordinary row does (R #509 / #510)."""
    _, merge_to, merge_spec = dsplit_row
    interior, pad_flag = dsplit["interior"], dsplit["pad_flag"]
    starts = [j for j, t in enumerate(merge_to) if t is not None]
    # The pair's interior edge carries no padding.
    pad_l_v = [0 if f == "right" else int(pad_l) for f in pad_flag]
    pad_r_v = [0 if f == "left" else int(pad_r) for f in pad_flag]
    cell_borders = row_cell_styles.get("border") if row_cell_styles else None
    cs_bg = row_cell_styles.get("background") if row_cell_styles else None
    n_cells = len(starts)
    cell_defs, cell_contents = [], []
    for ci, j in enumerate(starts):
        to = merge_to[j]
        merged = to != j
        # A pair merged back into one cell is styled by the ORIGINAL column.
        spec = merge_spec[j] if merged and merge_spec[j] is not None else col_spec[j]
        # Fill: the column's background, overridden by cell_styles.
        bg = spec.background
        if cs_bg is not None and j < len(cs_bg) and cs_bg[j] is not None:
            bg = str(cs_bg[j])
        eff = cell_edge_border(border, ci, n_cells)
        b = cell_borders[j] if isinstance(cell_borders, list) and j < len(cell_borders) else None
        if b is not None:
            eff = _effective_row_border(eff, b)
        if to == j and interior[j] is not None:
            eff = _effective_row_border(eff, interior[j])
        cell_defs.append(f"{build_border_commands(eff, color_index_map)}"
                         f"{cell_shading_cmd(bg, color_index_map)}{valign_cmd}"
                         f"\\cellx{cellx[to]}")
        is_half = not merged and interior[j] is not None
        cell_contents.append(_data_cell_content(
            spec, vals[j], j, row_cell_styles, pad_l_v[j], pad_r_v[to], markup,
            color_index_map, fs_cmd, force_align=spec.align if is_half else None))
    return build_row(cell_defs, cell_contents, row_height, table_align)


def _data_cell_content(spec, raw, j, row_cell_styles, pad_l, pad_r, markup,
                       color_index_map, fs_cmd, force_align=None) -> str:
    """One body cell's content: the column's spec, overridden per cell by the
    row's ``cell_styles`` (R ``.data_cell_content()``)."""
    text = format_cell_text("" if raw is None else str(raw), markup)
    align = spec.align or "left"
    bold = spec.bold
    italic = spec.italic
    underline = spec.underline
    indent = int(spec.indent_twips or 0)
    color_hex = spec.color
    if row_cell_styles:
        cs = row_cell_styles

        def pick(key, cur, j=j, cs=cs):
            seq = cs.get(key)
            if seq is not None and j < len(seq) and seq[j] is not None:
                return seq[j]
            return cur

        align = pick("align", align)
        bold = _as_bool(pick("bold", bold))
        italic = _as_bool(pick("italic", italic))
        underline = _as_bool(pick("underline", underline))
        indent = int(pick("indent_twips", indent))
        color_hex = pick("color", color_hex)
    if force_align is not None:
        align = force_align
    color_idx = (
        color_index_map.get(color_hex) if color_hex and color_index_map else None
    )
    return build_cell_content(text, align, bold, italic, underline, indent,
                              pad_l, pad_r, color_idx=color_idx, fs_cmd=fs_cmd)


def _as_bool(v):
    return bool(v) if v is not None else False


# -- rtftable renderer --------------------------------------------------------


def _apply_exact(h, exact: bool):
    if exact and h is not None and int(h) > 0:
        return -int(h)
    return h


def render_rtftable(
    tbl: RtfTable,
    writable: int,
    font_half_points: int = 18,
    color_index_map=None,
    doc_row_height=None,
    doc_pad_l=0,
    doc_pad_r=0,
    doc_markup="script",
    font_index_map=None,
) -> list[str]:
    """Render an :class:`RtfTable` to a list of RTF row strings."""
    border = expand_table_border(tbl.border, has_header=bool(tbl.col_header))
    col_spec = tbl.col_spec
    eff_markup = tbl.markup if tbl.markup is not None else resolve_markup(doc_markup)
    pad_l = tbl.cell_padding_left_twips if tbl.cell_padding_left_twips is not None else doc_pad_l
    pad_r = tbl.cell_padding_right_twips if tbl.cell_padding_right_twips is not None else doc_pad_r
    valign_cmd = C.CELL_VALIGN.get(tbl.cell_valign, r"\clvertalb")

    ncols = tbl.ncols
    if ncols == 0:
        return [C.EMPTY_TABLE]

    cellx = compute_cellx(ncols, writable, tbl)

    # Font size and row height resolve together (R #292): a table that sets its
    # own size gets the height that size implies.
    fs, effective = resolve_element_metrics(
        tbl.font_size_half_points, tbl.row_height_twips, font_half_points, doc_row_height)
    fs_cmd = f_cmd_for(tbl.font, font_index_map) + fs_cmd_for(fs, font_half_points)

    hdr_h = _apply_exact(
        tbl.header_row_height_twips if tbl.header_row_height_twips is not None else effective,
        tbl.row_height_exact,
    )
    data_h = _apply_exact(effective, tbl.row_height_exact)
    blank_h = _apply_exact(
        tbl.blank_row_height_twips if tbl.blank_row_height_twips is not None else effective,
        tbl.row_height_exact,
    )

    # set_decimal_split(): the data rows' expanded geometry, or None.
    from .decimal_split import plan as decimal_split_plan

    dsplit = decimal_split_plan(tbl, cellx, col_spec, eff_markup)

    return _render_section(
        tbl, cellx, border, col_spec, hdr_h, data_h, blank_h,
        set(tbl.blank_rows), pad_l, pad_r, valign_cmd, tbl.table_align,
        color_index_map, eff_markup, fs_cmd, dsplit=dsplit,
    )


def _render_section(
    tbl, cellx, border, col_spec, hdr_h, data_h, blank_h, blank_set,
    pad_l, pad_r, valign_cmd, table_align, color_index_map, markup, fs_cmd="",
    dsplit=None,
) -> list[str]:
    ncols = len(cellx)
    lines: list[str] = []

    hdr_border = border.header if border else None
    span_border = (border.spanning if border and border.spanning else hdr_border)

    header_rows: list[HeaderRow] = list(tbl.col_header)
    n_hdr = len(header_rows)

    for idx, hdr_row in enumerate(header_rows):
        zone = span_border if hdr_row.kind == "spanning" else hdr_border
        row_b = _header_outer_border(idx, n_hdr, zone)
        if hdr_row.kind == "spanning":
            if idx < n_hdr - 1:
                nb = _header_row_boundaries(
                    _header_row_coverage(header_rows[idx + 1], ncols)
                )
                gbs = None
                if hdr_border and hdr_border.bottom:
                    gbs = hdr_border.bottom
                elif span_border and span_border.bottom:
                    gbs = span_border.bottom
                else:
                    gbs = BorderSide()
            else:
                nb = []
                gbs = None
            lines.append(
                _render_spanning_row(
                    hdr_row.spans, cellx, row_b, hdr_h, pad_l, pad_r, valign_cmd,
                    col_spec, table_align, gbs, nb, markup, color_index_map,
                    fs_cmd=fs_cmd,
                )
            )
        else:
            lines.append(
                _render_header_row(
                    hdr_row.labels, cellx, row_b, hdr_h, pad_l, pad_r, valign_cmd,
                    col_spec, table_align, markup, color_index_map, fs_cmd=fs_cmd,
                )
            )

    align_cmd = _TABLE_ALIGN_CMD.get(table_align, "")

    def blank_row_rtf() -> str:
        total_w = cellx[ncols - 1]
        return (
            f"\\trowd\\trgaph0\\trleft0\\trrh{blank_h}{align_cmd}"
            f"\\clvertalb\\cellx{total_w} \\cell\\row"
        )

    detect_blank = "detect" in tbl.blank_row_normalize
    collapse_blank = "collapse" in tbl.blank_row_normalize

    def row_all_empty(row) -> bool:
        return all(v is None or not str(v).strip() for v in row)

    out: list[str] = []
    state = {"prev_blank": False}

    def add_blank():
        if collapse_blank and state["prev_blank"]:
            return
        out.append(blank_row_rtf())
        state["prev_blank"] = True

    def add_data(txt):
        out.append(txt)
        state["prev_blank"] = False

    nrows = tbl.nrows
    if 0 in blank_set:
        add_blank()

    for i in range(nrows):
        row = tbl.rows[i]
        if detect_blank and row_all_empty(row):
            add_blank()
        else:
            row_border = zone_row_border(border.body, i, nrows) if border else None
            if i == 0 and border and border.first_row:
                row_border = _effective_row_border(row_border, border.first_row)
            if i == nrows - 1 and border and border.last_row:
                row_border = _effective_row_border(row_border, border.last_row)
            rcs = None
            if tbl.cell_styles and i < len(tbl.cell_styles):
                rcs = tbl.cell_styles[i]
            if dsplit is None:
                add_data(
                    _render_data_row(
                        row, cellx, row_border, data_h, pad_l, pad_r, valign_cmd,
                        col_spec, table_align, rcs, color_index_map, markup, fs_cmd=fs_cmd,
                    )
                )
            else:
                from .decimal_split import split_cell_styles, split_row

                drow = split_row(dsplit, row, i)
                add_data(
                    _render_data_row(
                        drow[0], dsplit["cellx"], row_border, data_h, pad_l, pad_r,
                        valign_cmd, dsplit["col_spec"], table_align,
                        split_cell_styles(dsplit, rcs), color_index_map, markup,
                        fs_cmd=fs_cmd, dsplit_row=drow, dsplit=dsplit,
                    )
                )
        if (i + 1) in blank_set:
            add_blank()

    return lines + out


# -- Figure renderer ----------------------------------------------------------


def render_rtfplot(fig: Figure, writable: int) -> str:
    """Render a :class:`Figure` to an RTF ``\\pict`` string."""
    disp = fig.display_twips()
    hex_chars = fig._raw.hex().upper()
    hex_lines = [hex_chars[i : i + 126] for i in range(0, len(hex_chars), 126)]
    hex_block = "\n".join(hex_lines)
    align_cmd = _ALIGN_CMD.get(fig.align, r"\qc")
    template = C.PNG_TEMPLATE if fig.img_type == "png" else C.JPEG_TEMPLATE
    return template.format(
        align=align_cmd,
        picw=fig.img_width,
        pich=fig.img_height,
        picwgoal=disp["w"],
        pichgoal=disp["h"],
        hex=hex_block,
    )


# -- Header / footer renderer -------------------------------------------------


def render_header_footer(
    hf: HeaderFooter | None,
    writable: int,
    is_footer: bool = False,
    current_page: int | None = None,
    total_pages: int | None = None,
    color_index_map=None,
    font_half_points: int = 18,
    doc_row_height=None,
    doc_pad_l=None,
    doc_pad_r=None,
    doc_markup=None,
    font_index_map=None,
) -> list[str]:
    """Render a header/footer band to a list of RTF row strings."""
    if hf is None or not hf.rows:
        return []
    hf_markup = hf.markup if hf.markup is not None else doc_markup
    # Width: the absolute `width_twips` wins (the legacy form), then the shared
    # `width` vocabulary, then the writable width.  A header/footer band has no
    # table body above it, so "content" resolves to the writable width too.
    if hf.width_twips is not None:
        width = int(hf.width_twips)
    elif hf.width is not None:
        width = resolve_block_width(hf.width, writable, writable, default="page")
    else:
        width = writable
    # Font size and row height resolve together (#292): a band that sets its
    # own size gets the height that size implies.
    hf_fs_pt, rh_full = resolve_element_metrics(
        hf.font_size_half_points, hf.row_height_twips, font_half_points, doc_row_height
    )
    hf_fs = f_cmd_for(hf.font, font_index_map) + fs_cmd_for(hf_fs_pt, font_half_points)
    rh_str = C.ROW_HEIGHT_TEMPLATE.format(row_height_twips=rh_full)

    pad_l = _first_not_none(hf.cell_padding_left_twips, doc_pad_l, C.DEFAULT_CELL_PADDING_LEFT_TWIPS, 0)
    pad_r = _first_not_none(hf.cell_padding_right_twips, doc_pad_r, C.DEFAULT_CELL_PADDING_RIGHT_TWIPS, 0)

    out_rows = []
    for row_idx, row in enumerate(hf.rows):
        cols_display, aligns = _hf_row_columns(row)
        n_cols = len(cols_display)
        cell_w = width // n_cols
        cellx = _cumsum([cell_w] * n_cols)
        border_cmds = (
            build_border_commands(hf.border, color_index_map) if row_idx == 0 else ""
        )
        parts = [C.ROW_START, rh_str]
        for cx in cellx:
            if border_cmds:
                parts.append(f"{border_cmds}\\cellx{cx}")
            else:
                parts.append(f"\\cellx{cx}")
        for i in range(n_cols):
            at = _ALIGN_CMD.get(aligns[i], r"\ql")
            txt = render_tokens(cols_display[i], current_page=current_page,
                                total_pages=total_pages, markup=hf_markup)
            parts.append(f"{at}\\li{int(pad_l)}\\ri{int(pad_r)}{hf_fs} {txt}\\cell")
        parts.append(C.ROW_END)
        out_rows.append("".join(parts))
    return out_rows


def _hf_row_columns(row: dict) -> tuple[list[str], list[str]]:
    has_l = "l" in row
    has_r = "r" in row
    has_c = "c" in row
    if has_c and (has_l or has_r):
        return ([row.get("l", ""), row.get("c", ""), row.get("r", "")],
                ["left", "center", "right"])
    if has_l and has_r:
        return [row["l"], row["r"]], ["left", "right"]
    if has_c:
        return [row["c"]], ["center"]
    if has_l:
        return [row["l"]], ["left"]
    if has_r:
        return [row["r"]], ["right"]
    # Fallback: single centered empty cell.
    return [""], ["center"]


def _first_not_none(*values):
    for v in values:
        if v is not None:
            return v
    return 0


# -- Title / footnote blocks --------------------------------------------------


def _normalize_text_block(block, is_footer: bool, align: str | None = None) -> list[dict]:
    def_align = align if align is not None else ("left" if is_footer else "center")
    def_bold = not is_footer
    if block is None:
        if is_footer:
            return []
        block = [""]
    if isinstance(block, str):
        block = [block]
    if len(block) == 0:
        return []
    out = []
    for r in block:
        if r is None or isinstance(r, str):
            txt = "" if r is None else r
            rec = {"text": txt, "align": def_align, "bold": def_bold,
                   "italic": False, "underline": False, "color": None, "border": None}
        elif isinstance(r, dict):
            rec = {
                "text": r.get("text", ""),
                "align": r.get("align", def_align),
                "bold": def_bold if r.get("bold") is None else bool(r.get("bold")),
                "italic": bool(r.get("italic", False)),
                "underline": bool(r.get("underline", False)),
                "color": r.get("color"),
                "border": r.get("border"),
            }
            if rec["border"] is not None and not isinstance(rec["border"], Border):
                raise ValueError("A title/footnote row `border` must be a Border or None.")
        else:
            raise ValueError("Each title/footnote row must be a string or dict.")
        rec["blank"] = not str(rec["text"])
        out.append(rec)
    if is_footer and out and out[0]["border"] is None:
        out[0]["border"] = Border(top=BorderSide(style="single", width=15))
    return out


def text_block_colors(block, is_footer: bool) -> list[str]:
    try:
        rows = _normalize_text_block(block, is_footer)
    except Exception:
        return []
    cols = []
    for rec in rows:
        if rec["color"]:
            cols.append(rec["color"])
        if rec["border"]:
            cols.extend(collect_border_colors(rec["border"]))
    return cols


def render_text_block_table(
    block, total_width: int, is_footer: bool, font_half_points: int,
    pad_l: int, pad_r: int, valign_cmd: str, table_align: str,
    color_index_map=None, doc_row_height=None, markup="script",
    style: dict | None = None, current_page=None, total_pages=None,
    font_index_map=None,
) -> list[str]:
    style = style or {}
    rows = _normalize_text_block(block, is_footer, style.get("align"))
    if not rows:
        return []
    # Title / footnote rows inherit the document default row height, else the
    # font-aware baseline; a block-level size recomputes the height (#292).
    fs, full_h = resolve_element_metrics(
        style.get("font_size_half_points"), style.get("row_height_twips"),
        font_half_points, doc_row_height,
    )
    fs_cmd = f_cmd_for(style.get("font"), font_index_map) + fs_cmd_for(fs, font_half_points)
    if style.get("markup") is not None:
        markup = style["markup"]
    cellx = int(total_width)
    out = []
    for rec in rows:
        cell_def = f"{build_border_commands(rec['border'], color_index_map)}{valign_cmd}\\cellx{cellx}"
        if rec["blank"]:
            content = build_cell_content("", rec["align"], False, False, False, 0, pad_l, pad_r,
                                         fs_cmd=fs_cmd)
        else:
            color_idx = color_index_map.get(rec["color"]) if rec["color"] and color_index_map else None
            txt = substitute_page_tokens(format_cell_text(rec["text"], markup),
                                         current_page, total_pages)
            content = build_cell_content(txt, rec["align"], rec["bold"], rec["italic"],
                                         rec["underline"], 0, pad_l, pad_r, color_idx,
                                         fs_cmd=fs_cmd)
        out.append(build_row([cell_def], [content], full_h, table_align))
    return out


def render_text_block_text(
    block, is_footer: bool, color_index_map=None, markup="script", pad_l=0, pad_r=0,
    style: dict | None = None, font_half_points: int = 18,
    current_page=None, total_pages=None, font_index_map=None,
) -> list[str]:
    style = style or {}
    rows = _normalize_text_block(block, is_footer, style.get("align"))
    if not rows:
        return []
    if style.get("markup") is not None:
        markup = style["markup"]
    fs_cmd = (f_cmd_for(style.get("font"), font_index_map)
              + fs_cmd_for(style.get("font_size_half_points", font_half_points), font_half_points))
    indent = f"\\li{int(pad_l)}\\ri{int(pad_r)}{fs_cmd}"
    out = []
    for rec in rows:
        align_cmd = _ALIGN_CMD.get(rec["align"], r"\ql")
        if rec["blank"]:
            out.append(f"\\pard{align_cmd}{indent}\\par")
            continue
        txt = substitute_page_tokens(format_cell_text(rec["text"], markup),
                                     current_page, total_pages)
        if rec["underline"]:
            txt = f"\\ul {txt}\\ulnone "
        if rec["italic"]:
            txt = f"\\i {txt}\\i0 "
        if rec["bold"]:
            txt = f"\\b {txt}\\b0 "
        if rec["color"] and color_index_map and color_index_map.get(rec["color"]) is not None:
            txt = f"\\cf{int(color_index_map[rec['color']])} {txt}\\cf1 "
        out.append(f"\\pard{align_cmd}{indent} {txt}\\par")
    return out


# -- Colour table -------------------------------------------------------------


def build_color_table_rtf(hex_colors: list[str]) -> str:
    base = r"{\colortbl;\red0\green0\blue0;\red255\green255\blue255;"
    if not hex_colors:
        return base + "}"
    entries = []
    for h in hex_colors:
        hh = h.lstrip("#")
        r = int(hh[0:2], 16)
        g = int(hh[2:4], 16)
        b = int(hh[4:6], 16)
        entries.append(f"\\red{r}\\green{g}\\blue{b};")
    return base + "".join(entries) + "}"


def build_color_index_map(hex_colors: list[str]) -> dict:
    return {h: i + 3 for i, h in enumerate(hex_colors)}  # 1=black, 2=white reserved


def collect_report_colors(report) -> list[str]:
    cols: list[str] = []
    if report.color_table:
        cols.extend(report.color_table)
    for sec in report.sections:
        for hf in (normalize_hf(sec.get("header")), normalize_hf(sec.get("footer"))):
            if hf and hf.border:
                cols.extend(collect_border_colors(hf.border))
    for page in report.pages:
        ct = page.get("content")
        if isinstance(ct, RtfTable):
            cols.extend(_table_colors(ct))
        cols.extend(text_block_colors(page.get("title"), is_footer=False))
    fn_border = (getattr(report, "footnote_style", None) or {}).get("border")
    if fn_border is not None:
        cols.extend(collect_border_colors(fn_border))
    seen = []
    for c in cols:
        if not c:
            continue
        if c.upper() in ("#000000", "#FFFFFF"):
            continue
        if c not in seen:
            seen.append(c)
    return seen


def _table_colors(tbl: RtfTable) -> list[str]:
    out = collect_table_border_colors(tbl.border)
    out.extend(s.color for s in tbl.col_spec if s.color)
    out.extend(s.background for s in tbl.col_spec if s.background)
    out.extend(s.header_background for s in tbl.col_spec if s.header_background)
    for s in tbl.col_spec:
        out.extend(collect_border_colors(s.border))
    for hdr in tbl.col_header:
        if hdr.kind == "spanning":
            for sp in hdr.spans:
                out.extend(collect_border_colors(sp.border))
    if tbl.cell_styles:
        dicts = [cs for cs in tbl.cell_styles if isinstance(cs, dict)]
        for key in ("color", "background"):
            for cs in dicts:
                out.extend(c for c in (cs.get(key) or []) if c)
        for cs in dicts:
            for b in cs.get("border", []) or []:
                out.extend(collect_border_colors(b))
    return [c for c in out if c]
