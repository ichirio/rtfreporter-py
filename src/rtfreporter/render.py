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
)
from .borders import (
    Border,
    BorderSide,
    collect_border_colors,
    collect_table_border_colors,
    merge_border,
)
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
) -> str:
    """Build one cell's content string (``\\q..\\li..\\ri.. text\\cell``)."""
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
    return f"{align_cmd}\\li{li}\\ri{ri} {text}\\cell"


def build_row(cell_defs, cell_contents, row_height_twips=None, table_align="left") -> str:
    """Build one complete RTF table row string."""
    rh = ""
    if row_height_twips is not None and int(row_height_twips) != 0:
        rh = f"\\trrh{int(row_height_twips)}"
    align_cmd = _TABLE_ALIGN_CMD.get(table_align, "")
    return (
        r"\trowd" + rh + align_cmd + "".join(cell_defs) + "".join(cell_contents) + r"\row"
    )


def build_cell_defs(cellx, border, valign_cmd, color_index_map=None) -> list[str]:
    border_cmds = build_border_commands(border, color_index_map)
    return [f"{border_cmds}{valign_cmd}\\cellx{cx}" for cx in cellx]


def _header_outer_border(idx: int, n: int, zone: Border | None) -> Border | None:
    if zone is None:
        return None
    is_first = idx == 0
    is_last = idx == n - 1
    top = zone.top if is_first else None
    bot = zone.bottom if is_last else None
    lft = zone.left
    rgt = zone.right
    if top is None and bot is None and lft is None and rgt is None:
        return None
    return Border(top=top, bottom=bot, left=lft, right=rgt)


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
) -> str:
    ncols = len(cellx)
    coverage = [0] * ncols
    for k, sp in enumerate(spans, start=1):
        for j in range(sp.start, sp.end + 1):
            coverage[j] = k

    def cell_border(k: int | None, single_idx: int | None = None) -> Border | None:
        eff = border
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
    while j < ncols:
        k = coverage[j]
        if k > 0:
            end = spans[k - 1].end
            bc = build_border_commands(cell_border(k), color_index_map)
            cell_defs.append(f"{bc}{valign_cmd}\\cellx{cellx[end]}")
            j = end + 1
        else:
            bc = build_border_commands(cell_border(None, single_idx=j), color_index_map)
            cell_defs.append(f"{bc}{valign_cmd}\\cellx{cellx[j]}")
            j += 1

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
            cell_contents.append(f"{align_cmd}\\li{pad_l}\\ri{pad_r} {label}\\cell")
            j = sp.end + 1
        else:
            cell_contents.append(f"\\ql\\li{pad_l}\\ri{pad_r} \\cell")
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
) -> str:
    ncols = len(cellx)
    cell_defs = []
    for j in range(ncols):
        col_border = col_spec[j].border
        eff = _effective_row_border(border, col_border) if col_border is not None else border
        bc = build_border_commands(eff, color_index_map)
        cell_defs.append(f"{bc}{valign_cmd}\\cellx{cellx[j]}")

    cell_contents = []
    for j in range(ncols):
        spec = col_spec[j]
        raw = labels[j] if j < len(labels) else ""
        text = format_cell_text(raw, markup)
        align = spec.header_align or "center"
        cell_contents.append(
            build_cell_content(text, align, spec.header_bold, spec.header_italic,
                               False, 0, pad_l, pad_r)
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
) -> str:
    ncols = len(cellx)
    cell_borders = row_cell_styles.get("border") if row_cell_styles else None
    if isinstance(cell_borders, list) and any(b is not None for b in cell_borders):
        cell_defs = []
        for j in range(ncols):
            b = cell_borders[j] if j < len(cell_borders) else None
            eff = border if b is None else _effective_row_border(border, b)
            cell_defs.append(
                f"{build_border_commands(eff, color_index_map)}{valign_cmd}\\cellx{cellx[j]}"
            )
    else:
        cell_defs = build_cell_defs(cellx, border, valign_cmd, color_index_map)

    cell_contents = []
    for j in range(ncols):
        spec = col_spec[j]
        raw = vals[j] if j < len(vals) else None
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
        color_idx = (
            color_index_map.get(color_hex) if color_hex and color_index_map else None
        )
        cell_contents.append(
            build_cell_content(text, align, bold, italic, underline, indent,
                               pad_l, pad_r, color_idx=color_idx)
        )
    return build_row(cell_defs, cell_contents, row_height, table_align)


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
) -> list[str]:
    """Render an :class:`RtfTable` to a list of RTF row strings."""
    border = tbl.border
    col_spec = tbl.col_spec
    eff_markup = tbl.markup if tbl.markup is not None else resolve_markup(doc_markup)
    pad_l = tbl.cell_padding_left_twips if tbl.cell_padding_left_twips is not None else doc_pad_l
    pad_r = tbl.cell_padding_right_twips if tbl.cell_padding_right_twips is not None else doc_pad_r
    valign_cmd = C.CELL_VALIGN.get(tbl.cell_valign, r"\clvertalb")

    ncols = tbl.ncols
    if ncols == 0:
        return [C.EMPTY_TABLE]

    cellx = compute_cellx(ncols, writable, tbl)

    if tbl.row_height_twips is not None:
        base_rh = tbl.row_height_twips
    elif doc_row_height is not None:
        base_rh = doc_row_height
    else:
        base_rh = None
    effective = C.default_row_height_twips(font_half_points) if base_rh is None else int(base_rh)

    hdr_h = _apply_exact(
        tbl.header_row_height_twips if tbl.header_row_height_twips is not None else effective,
        tbl.row_height_exact,
    )
    data_h = _apply_exact(effective, tbl.row_height_exact)
    blank_h = _apply_exact(
        tbl.blank_row_height_twips if tbl.blank_row_height_twips is not None else effective,
        tbl.row_height_exact,
    )

    return _render_section(
        tbl, cellx, border, col_spec, hdr_h, data_h, blank_h,
        set(tbl.blank_rows), pad_l, pad_r, valign_cmd, tbl.table_align,
        color_index_map, eff_markup,
    )


def _render_section(
    tbl, cellx, border, col_spec, hdr_h, data_h, blank_h, blank_set,
    pad_l, pad_r, valign_cmd, table_align, color_index_map, markup,
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
                )
            )
        else:
            lines.append(
                _render_header_row(
                    hdr_row.labels, cellx, row_b, hdr_h, pad_l, pad_r, valign_cmd,
                    col_spec, table_align, markup, color_index_map,
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
            row_border = border.body if border else None
            if i == 0 and border and border.first_row:
                row_border = _effective_row_border(row_border, border.first_row)
            if i == nrows - 1 and border and border.last_row:
                row_border = _effective_row_border(row_border, border.last_row)
            rcs = None
            if tbl.cell_styles and i < len(tbl.cell_styles):
                rcs = tbl.cell_styles[i]
            add_data(
                _render_data_row(
                    row, cellx, row_border, data_h, pad_l, pad_r, valign_cmd,
                    col_spec, table_align, rcs, color_index_map, markup,
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
) -> list[str]:
    """Render a header/footer band to a list of RTF row strings."""
    if hf is None or not hf.rows:
        return []
    width = hf.width_twips if hf.width_twips is not None else writable
    rh_full = (
        hf.row_height_twips
        if hf.row_height_twips is not None
        else (doc_row_height if doc_row_height is not None else C.default_row_height_twips(font_half_points))
    )
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
            txt = render_tokens(cols_display[i], current_page=current_page, total_pages=total_pages)
            parts.append(f"{at}\\li{int(pad_l)}\\ri{int(pad_r)} {txt}\\cell")
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


def _normalize_text_block(block, is_footer: bool) -> list[dict]:
    def_align = "left" if is_footer else "center"
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
) -> list[str]:
    rows = _normalize_text_block(block, is_footer)
    if not rows:
        return []
    full_h = doc_row_height if doc_row_height is not None else C.default_row_height_twips(font_half_points)
    cellx = int(total_width)
    out = []
    for rec in rows:
        cell_def = f"{build_border_commands(rec['border'], color_index_map)}{valign_cmd}\\cellx{cellx}"
        if rec["blank"]:
            content = build_cell_content("", rec["align"], False, False, False, 0, pad_l, pad_r)
        else:
            color_idx = color_index_map.get(rec["color"]) if rec["color"] and color_index_map else None
            txt = format_cell_text(rec["text"], markup)
            content = build_cell_content(txt, rec["align"], rec["bold"], rec["italic"],
                                         rec["underline"], 0, pad_l, pad_r, color_idx)
        out.append(build_row([cell_def], [content], full_h, table_align))
    return out


def render_text_block_text(
    block, is_footer: bool, color_index_map=None, markup="script", pad_l=0, pad_r=0,
) -> list[str]:
    rows = _normalize_text_block(block, is_footer)
    if not rows:
        return []
    indent = f"\\li{int(pad_l)}\\ri{int(pad_r)}"
    out = []
    for rec in rows:
        align_cmd = _ALIGN_CMD.get(rec["align"], r"\ql")
        if rec["blank"]:
            out.append(f"\\pard{align_cmd}{indent}\\par")
            continue
        txt = format_cell_text(rec["text"], markup)
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
        cols.extend(text_block_colors(page.get("footnote"), is_footer=True))
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
    for s in tbl.col_spec:
        if s.color:
            out.append(s.color)
        out.extend(collect_border_colors(s.border))
    for hdr in tbl.col_header:
        if hdr.kind == "spanning":
            for sp in hdr.spans:
                out.extend(collect_border_colors(sp.border))
    if tbl.cell_styles:
        for cs in tbl.cell_styles:
            if isinstance(cs, dict):
                for c in cs.get("color", []) or []:
                    if c:
                        out.append(c)
                for b in cs.get("border", []) or []:
                    out.extend(collect_border_colors(b))
    return [c for c in out if c]
