"""Full-featured ``great_tables`` (GT) adapter.

Ported from the R package's ``R/gt_adapter.R``.  Reads a ``great_tables.GT``
object into the pieces :func:`~rtfreporter.rtftable` consumes:

* the **rendered/display body** (``fmt_*`` formatted values, hidden columns
  dropped, row groups interleaved as indented stub rows),
* **column labels** (``cols_label``) and **multi-level spanners**
  (``tab_spanner``) as stacked header rows,
* per-column **alignment** and **widths**,
* per-cell **styles** from ``tab_style`` (bold / italic / underline / align /
  text colour and cell borders) mapped onto the table model's ``cell_styles``
  and header channels,
* **title + subtitle** into the title block and **footnotes + source notes**
  into the footnote block,
* best-effort **summary / grand-summary rows** where the installed
  great_tables version exposes them.

Which of these metadata channels are read is controlled by ``read_meta`` -- a
token mechanism equivalent to the R adapter's (see :data:`GT_META_TOKENS`).
The clean reshaped body is *always* produced; only the metadata channels are
gated.

**Dependency philosophy** (inherited from the R package): prefer great_tables'
public API; when unavailable, read the object's own data slots directly.  Every
version-fragile read is isolated behind a small helper with a fallback, so a
great_tables upgrade degrades gracefully rather than crashing.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from typing import Any

from .borders import Border, BorderSide, merge_border
from .table import HeaderRow, SpanCell

#: The metadata tokens ``read_meta`` may enable for a GT object.  ``True`` reads
#: them all, ``False`` reads none (the clean body is still produced), and a
#: list/tuple of these names reads exactly the named channels.
GT_META_TOKENS = (
    "col_header",
    "alignment",
    "spanning",
    "widths",
    "titles",
    "footnotes",
    "styles",
)

# solid/double/dashed/dotted/hidden -> rtfreporter border styles.
_BORDER_STYLE_MAP = {
    "solid": "single",
    "double": "double",
    "dashed": "dash",
    "dotted": "dot",
    "hidden": "none",
}

# A minimal CSS named-colour table (great_tables accepts hex or names).  Unknown
# names fall back to "no colour" (the RTF default), matching the R adapter's
# graceful behaviour when a colour cannot be resolved.
_NAMED_COLORS = {
    "black": "#000000",
    "white": "#FFFFFF",
    "red": "#FF0000",
    "green": "#008000",
    "lime": "#00FF00",
    "blue": "#0000FF",
    "yellow": "#FFFF00",
    "orange": "#FFA500",
    "gray": "#808080",
    "grey": "#808080",
    "silver": "#C0C0C0",
    "navy": "#000080",
    "purple": "#800080",
    "maroon": "#800000",
    "teal": "#008080",
    "olive": "#808000",
    "aqua": "#00FFFF",
    "cyan": "#00FFFF",
    "fuchsia": "#FF00FF",
    "magenta": "#FF00FF",
}


# ============================================================================
#  read_meta token resolution (shared, equivalent to R's .resolve_meta_tokens)
# ============================================================================


def resolve_meta_tokens(read, allowed, label: str) -> tuple[str, ...]:
    """Resolve a ``read_meta`` value to the concrete set of tokens to read.

    Args:
        read: ``False``/``None`` (no tokens), ``True`` (all ``allowed``), or an
            iterable of token names.
        allowed: The tokens valid for this adapter.
        label: A short adapter name used in the error message.

    Returns:
        A tuple of the tokens to read (possibly empty).

    Raises:
        ValueError: If ``read`` contains a token not in ``allowed``.
    """
    if read is None or read is False:
        return ()
    if read is True:
        return tuple(allowed)
    if isinstance(read, str):
        read = [read]
    try:
        tokens = list(read)
    except TypeError as exc:  # not iterable
        raise ValueError(
            "`read_meta` must be False/True or a list of token names."
        ) from exc
    bad = [t for t in tokens if t not in allowed]
    if bad:
        raise ValueError(
            f"Unknown {label} read_meta token(s): {sorted(bad)}. "
            f"Allowed: {list(allowed)}."
        )
    return tuple(tokens)


# ============================================================================
#  Detection + version-fragile slot access
# ============================================================================


def is_gt(x) -> bool:
    """Return True if ``x`` is a great_tables ``GT`` object (cheap duck-check)."""
    return type(x).__name__ == "GT" and hasattr(x, "_tbl_data") and hasattr(x, "_boxhead")


def _slot(gt, name, default=None):
    """Read ``gt.<name>`` defensively (returns ``default`` on any failure)."""
    try:
        return getattr(gt, name)
    except Exception:  # pragma: no cover - defensive
        return default


# ============================================================================
#  Small value helpers
# ============================================================================


def _is_na(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    try:
        import pandas as pd

        res = pd.isna(v)
        if res is True:
            return True
    except Exception:
        pass
    return False


_TAG_RE = re.compile(r"<[^>]+>")
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)


def _strip_html(s: str) -> str:
    """Strip the HTML great_tables' HTML formatters can emit; ``<br>`` -> newline."""
    if "<" not in s:
        return s
    s = _BR_RE.sub("\n", s)
    s = _TAG_RE.sub("", s)
    s = (
        s.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    if not s.strip():
        return ""
    return s


def _to_text(v) -> str:
    if _is_na(v):
        return ""
    return str(v)


def _flatten_label(label) -> str:
    if label is None:
        return ""
    if isinstance(label, (list, tuple)):
        return " ".join(_flatten_label(x) for x in label if x is not None)
    return str(label)


def _normalize_color(x) -> str | None:
    """``"#RRGGBB"`` / ``"#RGB"`` / a CSS name -> ``"#RRGGBB"``; ``None`` if unusable.

    An ``"#RRGGBBAA"`` alpha suffix is dropped.  Returns ``None`` for anything
    that cannot be resolved so the caller simply omits the colour.
    """
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    if s.startswith("#"):
        hexpart = s[1:]
        if len(hexpart) in (3, 4) and all(c in "0123456789abcdefABCDEF" for c in hexpart):
            hexpart = "".join(c * 2 for c in hexpart[:3])
        if len(hexpart) >= 6 and all(c in "0123456789abcdefABCDEF" for c in hexpart[:6]):
            return "#" + hexpart[:6].upper()
        return None
    return _NAMED_COLORS.get(s.lower())


def _color_is_transparent(raw) -> bool:
    """A transparent / zero-alpha border colour yields NO border (R gotcha)."""
    if raw is None:
        return False
    s = str(raw).strip().lower()
    if s == "transparent":
        return True
    # 8-digit hex "#RRGGBBAA" with AA == 00.
    if s.startswith("#") and len(s) >= 9 and s[7:9] == "00":
        return True
    return False


# ============================================================================
#  tab_style() -> (border, text) extraction
# ============================================================================


def _style_class(obj) -> str:
    return type(obj).__name__


def _px_or_pt_to_twips(weight) -> int:
    """great_tables border weight ('1px' / '2pt' / int) -> twips (px x15, pt x20)."""
    if weight is None:
        return 15
    s = str(weight).strip().lower()
    m = re.match(r"^([0-9.]+)\s*(px|pt)?$", s)
    if not m:
        return 15
    num = float(m.group(1))
    unit = m.group(2)
    if unit == "pt":
        return max(1, int(round(num * 20)))
    return max(1, int(round(num * 15)))  # px and bare numbers


def _border_side_from_decl(color, style, weight) -> BorderSide | None:
    """One great_tables border declaration -> :class:`BorderSide` or ``None``."""
    if _color_is_transparent(color):
        return None
    rtf_style = _BORDER_STYLE_MAP.get(str(style or "solid").lower())
    if rtf_style is None:
        return None
    if rtf_style == "none":
        return BorderSide(style="none")
    width = _px_or_pt_to_twips(weight)
    hexcol = _normalize_color(color)
    if hexcol == "#000000":
        hexcol = None  # black is the RTF default; omit it
    return BorderSide(style=rtf_style, width=width, color=hexcol)


def _borders_from_cellstyle(cs) -> Border | None:
    """A great_tables ``CellStyleBorders`` -> :class:`Border` (or ``None``)."""
    sides = getattr(cs, "sides", "all")
    if isinstance(sides, str):
        sides = [sides]
    sides = list(sides or [])
    if "all" in sides:
        sides = ["top", "bottom", "left", "right"]
    side = _border_side_from_decl(
        getattr(cs, "color", "#000000"),
        getattr(cs, "style", "solid"),
        getattr(cs, "weight", "1px"),
    )
    if side is None:
        return None
    kw = {s: side for s in sides if s in ("top", "bottom", "left", "right")}
    if not kw:
        return None
    return Border(**kw)


def _text_from_cellstyle(cs) -> dict:
    """A great_tables ``CellStyleText`` -> a dict of the fields rtfreporter keeps."""
    out: dict[str, Any] = {}
    if str(getattr(cs, "weight", "") or "") == "bold":
        out["bold"] = True
    if str(getattr(cs, "style", "") or "") == "italic":
        out["italic"] = True
    decorate = getattr(cs, "decorate", None)
    if decorate is not None and "underline" in str(decorate):
        out["underline"] = True
    align = str(getattr(cs, "align", "") or "")
    if align in ("left", "center", "right"):
        out["align"] = align
    color = _normalize_color(getattr(cs, "color", None))
    if color is not None:
        out["color"] = color
    return out


def _split_style_set(style_list) -> tuple[Border | None, dict]:
    """A great_tables style set (list of CellStyle*) -> (border, text-dict)."""
    border: Border | None = None
    text: dict[str, Any] = {}
    for cs in style_list or []:
        cls = _style_class(cs)
        if cls == "CellStyleBorders":
            b = _borders_from_cellstyle(cs)
            if b is not None:
                border = b if border is None else merge_border(border, b)
        elif cls == "CellStyleText":
            text.update(_text_from_cellstyle(cs))
        # CellStyleFill / CellStyleCss have no RTF counterpart; ignored.
    return border, text


@dataclass
class _LocStyle:
    """Accumulated (border, text) for one styled location."""

    border: Border | None = None
    text: dict[str, Any] | None = None

    def merge(self, border: Border | None, text: dict) -> None:
        if border is not None:
            self.border = border if self.border is None else merge_border(self.border, border)
        if text:
            if self.text is None:
                self.text = {}
            self.text.update(text)


def _styles_by_location(gt) -> dict[str, dict]:
    """Fold ``gt._styles`` into per-location accumulators.

    Returns a dict with keys ``"label"`` (by column var), ``"spanner"`` (by
    spanner id), ``"body"`` (by ``(var, rownum)``) and ``"stub"`` (by rownum).
    Later declarations override earlier ones per field (great_tables' order).
    """
    acc = {"label": {}, "spanner": {}, "body": {}, "stub": {}}
    styles = _slot(gt, "_styles") or []
    for si in styles:
        border, text = _split_style_set(getattr(si, "styles", None))
        if border is None and not text:
            continue
        loc = getattr(si, "locname", None)
        loc_cls = _style_class(loc)
        if loc_cls == "LocColumnLabels":
            key = getattr(si, "colname", None)
            bucket = "label"
        elif loc_cls == "LocSpannerLabels":
            grp = getattr(si, "grpname", None)
            # grpname may be a list of spanner ids.
            for sid in (grp if isinstance(grp, (list, tuple)) else [grp]):
                if sid is None:
                    continue
                acc["spanner"].setdefault(str(sid), _LocStyle()).merge(border, text)
            continue
        elif loc_cls == "LocBody":
            key = (getattr(si, "colname", None), getattr(si, "rownum", None))
            bucket = "body"
        elif loc_cls == "LocStub":
            key = getattr(si, "rownum", None)
            bucket = "stub"
        else:
            continue  # title / stubhead / row groups / footnotes: no per-cell home
        if key is None or (isinstance(key, tuple) and key[0] is None):
            continue
        acc[bucket].setdefault(key, _LocStyle()).merge(border, text)
    return acc


# ============================================================================
#  Boxhead / body reshaping
# ============================================================================


def _type_name(col) -> str:
    t = getattr(col, "type", None)
    name = getattr(t, "name", None)
    if name:
        return name
    return str(t).rsplit(".", 1)[-1]


def _raw_columns(tbl_data) -> dict[str, list]:
    """A pandas/polars frame -> ``{column_name: [values]}`` (no hard dependency)."""
    mod = type(tbl_data).__module__.split(".")[0]
    if mod == "polars":
        return {k: list(v) for k, v in tbl_data.to_dict(as_series=False).items()}
    # pandas (duck-typed).
    return {str(c): list(tbl_data[c]) for c in tbl_data.columns}


def _display_matrix(gt) -> dict[str, list[str]]:
    """Rendered/display value for every data column (formatted where available)."""
    raw = _raw_columns(gt._tbl_data)
    disp = {c: [_to_text(v) for v in vals] for c, vals in raw.items()}
    try:
        built = gt._build_data(context="html")
        body = _raw_columns(built._body.body)
        for c, bvals in body.items():
            if c not in disp:
                continue
            col = disp[c]
            for i, bv in enumerate(bvals):
                if i < len(col) and not _is_na(bv):
                    col[i] = _strip_html(_to_text(bv))
    except Exception:  # pragma: no cover - version-fragile, degrade to raw
        pass
    return disp


@dataclass
class _Boxh:
    group_var: str | None
    stub_var: str | None
    default_vars: list[str]
    align: dict[str, str | None]
    width: dict[str, Any]


def _read_boxhead(gt) -> _Boxh:
    boxhead = _slot(gt, "_boxhead") or []
    group_var = stub_var = None
    default_vars: list[str] = []
    align: dict[str, str | None] = {}
    width: dict[str, Any] = {}
    for col in boxhead:
        var = getattr(col, "var", None)
        tname = _type_name(col)
        align[var] = getattr(col, "column_align", None)
        width[var] = getattr(col, "column_width", None)
        if tname == "row_group" and group_var is None:
            group_var = var
        elif tname == "stub" and stub_var is None:
            stub_var = var
        elif tname == "default":
            default_vars.append(var)
        # "hidden" columns are dropped.
    return _Boxh(group_var, stub_var, default_vars, align, width)


def _stub_rows(gt):
    """Return ``(rows_meta, group_order)`` where rows_meta is a list of
    ``(data_idx, group_id, rowname, indent)`` and group_order the render order
    of group ids (empty when the table has no row groups)."""
    stub = _slot(gt, "_stub")
    rows_meta = []
    group_order: list = []
    if stub is not None:
        try:
            group_order = [g for g in (getattr(stub, "group_ids", None) or []) if g is not None]
            for r in stub:
                rows_meta.append(
                    (
                        getattr(r, "rownum_i", len(rows_meta)),
                        getattr(r, "group_id", None),
                        getattr(r, "rowname", None),
                        int(getattr(r, "indent", 0) or 0),
                    )
                )
        except Exception:  # pragma: no cover - defensive
            rows_meta = []
            group_order = []
    return rows_meta, group_order


# ============================================================================
#  Central mapping: GT -> rtftable kwargs
# ============================================================================


@dataclass
class GTResult:
    """The reshaped GT table plus the metadata channels rtfreporter can use."""

    column_names: list[str]
    rows: list[list[Any]]
    col_header: list[HeaderRow] | None
    col_spec: list[dict] | None
    cell_styles: list | None
    col_rel_width: list[float] | None
    column_widths_twips: list[int] | None
    titles: list[str] | None
    footnotes: list[str] | None


def gt_to_result(gt, read_meta=True, stub_indent: int = 4) -> GTResult:
    """Read a great_tables ``GT`` object into a :class:`GTResult`.

    Args:
        gt: A ``great_tables.GT`` object.
        read_meta: ``True`` / ``False`` / a list of :data:`GT_META_TOKENS`.
        stub_indent: Spaces prepended to each stub row that sits under a group
            label (mirrors the ``stub_cols`` indent convention).
    """
    tokens = resolve_meta_tokens(read_meta, GT_META_TOKENS, "gt")

    bx = _read_boxhead(gt)
    disp = _display_matrix(gt)
    n_data = max((len(v) for v in disp.values()), default=0)
    rows_meta, group_order = _stub_rows(gt)
    if not rows_meta:
        rows_meta = [(i, None, None, 0) for i in range(n_data)]

    has_groups = bool(group_order)
    has_stub = bx.stub_var is not None or has_groups
    stub_off = 1 if has_stub else 0

    default_vars = bx.default_vars
    stub_name = bx.stub_var or ("__group__" if has_groups else "__stub__")
    column_names = ([stub_name] if has_stub else []) + list(default_vars)
    ncols = len(column_names)

    # ---- reshape the body: interleave group labels, indent stub rows --------
    out_rows: list[list[Any]] = []
    data_to_out: dict[int, int] = {}

    def _emit_data_row(data_idx, rowname, indent_levels):
        cells = []
        if has_stub:
            text = "" if rowname is None else str(rowname)
            if indent_levels > 0:
                text = " " * (indent_levels * stub_indent) + text
            cells.append(text)
        for v in default_vars:
            col = disp.get(v, [])
            cells.append(col[data_idx] if data_idx < len(col) else "")
        data_to_out[data_idx] = len(out_rows)
        out_rows.append(cells)

    if has_groups:
        by_group: dict[Any, list] = {}
        for (data_idx, gid, rowname, indent) in rows_meta:
            by_group.setdefault(gid, []).append((data_idx, rowname, indent))
        seen = set()
        for gid in list(group_order) + [g for g in by_group if g not in group_order]:
            if gid not in by_group or gid in seen:
                continue
            seen.add(gid)
            out_rows.append([_flatten_label(gid)] + [None] * len(default_vars))
            for (data_idx, rowname, indent) in by_group[gid]:
                _emit_data_row(data_idx, rowname, 1 + indent)
    else:
        for (data_idx, _gid, rowname, indent) in rows_meta:
            _emit_data_row(data_idx, rowname, indent)

    # ---- summary / grand-summary rows (best effort) -------------------------
    _append_summary_rows(gt, out_rows, default_vars, stub_off, has_stub)

    # ---- column labels ------------------------------------------------------
    labels = list(column_names)
    if "col_header" in tokens:
        if has_stub:
            labels[0] = _flatten_label(_slot(gt, "_stubhead")) or ""
        for j, v in enumerate(default_vars):
            lab = _boxhead_label(gt, v)
            labels[stub_off + j] = lab if lab is not None else v

    # ---- per-cell styles ----------------------------------------------------
    sty = _styles_by_location(gt) if "styles" in tokens else None

    # ---- header rows: spanners (multi-level) + labels -----------------------
    header_rows: list[HeaderRow] = []
    if "spanning" in tokens:
        header_rows.extend(
            _spanner_rows(gt, default_vars, stub_off, ncols, sty)
        )

    # ---- col_spec: alignment + label text styling ---------------------------
    col_spec_map: dict[int, dict] = {}
    if "alignment" in tokens:
        for j in range(ncols):
            var = column_names[j] if not (has_stub and j == 0) else bx.stub_var
            a = bx.align.get(var) if var is not None else None
            if a not in ("left", "center", "right"):
                a = "left"
            col_spec_map.setdefault(j, {"col": j})["align"] = a

    label_row = _build_label_row(labels, sty, stub_off, default_vars, col_spec_map, ncols)
    header_rows.append(label_row)

    col_spec = [col_spec_map[j] for j in sorted(col_spec_map)] if col_spec_map else None
    col_header = header_rows if ("col_header" in tokens or "spanning" in tokens) else None

    # ---- body / stub cell styles -> cell_styles -----------------------------
    cell_styles = None
    if sty is not None and (sty["body"] or sty["stub"]):
        cell_styles = _build_cell_styles(
            sty, data_to_out, len(out_rows), ncols, default_vars, stub_off, has_stub
        )

    # ---- widths -------------------------------------------------------------
    col_rel_width = None
    column_widths_twips = None
    if "widths" in tokens:
        col_rel_width, column_widths_twips = _parse_widths(
            bx, column_names, has_stub
        )

    # ---- titles / footnotes -------------------------------------------------
    titles = _extract_titles(gt) if "titles" in tokens else None
    footnotes = _extract_footnotes(gt) if "footnotes" in tokens else None

    return GTResult(
        column_names=column_names,
        rows=out_rows,
        col_header=col_header,
        col_spec=col_spec,
        cell_styles=cell_styles,
        col_rel_width=col_rel_width,
        column_widths_twips=column_widths_twips,
        titles=titles,
        footnotes=footnotes,
    )


def _boxhead_label(gt, var) -> str | None:
    boxhead = _slot(gt, "_boxhead") or []
    for col in boxhead:
        if getattr(col, "var", None) == var:
            return _flatten_label(getattr(col, "column_label", None))
    return None


def _spanner_rows(gt, default_vars, stub_off, ncols, sty) -> list[HeaderRow]:
    spanners = _slot(gt, "_spanners") or []
    if not spanners:
        return []
    levels = sorted({int(getattr(s, "spanner_level", 0)) for s in spanners}, reverse=True)
    pos_of = {v: stub_off + i for i, v in enumerate(default_vars)}
    rows: list[HeaderRow] = []
    for lv in levels:
        cells: list[SpanCell] = []
        for sp in spanners:
            if int(getattr(sp, "spanner_level", 0)) != lv:
                continue
            svars = [v for v in (getattr(sp, "vars", None) or []) if v in pos_of]
            if not svars:
                continue
            idxs = sorted(pos_of[v] for v in svars)
            if any(idxs[k + 1] - idxs[k] != 1 for k in range(len(idxs) - 1)):
                continue  # non-contiguous under the visible columns; skip
            label = _flatten_label(getattr(sp, "spanner_label", "") or "")
            cell = SpanCell(start=idxs[0], end=idxs[-1], label=label)
            if sty is not None:
                s = sty["spanner"].get(str(getattr(sp, "spanner_id", "")))
                if s is not None:
                    cell = _apply_style_to_spancell(cell, s)
            cells.append(cell)
        if not cells:
            continue
        covered = set()
        for c in cells:
            covered.update(range(c.start, c.end + 1))
        for j in range(ncols):
            if j not in covered:
                cells.append(SpanCell(start=j, end=j, label=""))
        cells.sort(key=lambda c: c.start)
        rows.append(HeaderRow(kind="spanning", spans=cells))
    return rows


def _apply_style_to_spancell(cell: SpanCell, s: _LocStyle) -> SpanCell:
    text = s.text or {}
    return replace(
        cell,
        align=text.get("align", cell.align),
        bold=bool(text.get("bold", cell.bold)),
        italic=bool(text.get("italic", cell.italic)),
        underline=bool(text.get("underline", cell.underline)),
        border=s.border if s.border is not None else cell.border,
    )


def _build_label_row(labels, sty, stub_off, default_vars, col_spec_map, ncols) -> HeaderRow:
    """Build the bottom label row.

    Text bold/italic/align ride on ``col_spec`` (``header_*``); a per-cell
    border or underline (which the labels renderer cannot express) promotes the
    whole row to single-column spanning cells, exactly as R's adapter does.
    """
    promote = False
    label_styles: dict[int, _LocStyle] = {}
    if sty is not None:
        pos_of = {v: stub_off + i for i, v in enumerate(default_vars)}
        for var, s in sty["label"].items():
            j = pos_of.get(var)
            if j is None:
                continue
            label_styles[j] = s
            text = s.text or {}
            spec = col_spec_map.setdefault(j, {"col": j})
            if text.get("bold"):
                spec["header_bold"] = True
            if text.get("italic"):
                spec["header_italic"] = True
            if text.get("align"):
                spec["header_align"] = text["align"]
            if s.border is not None or text.get("underline"):
                promote = True

    if not promote:
        return HeaderRow(kind="labels", labels=list(labels))

    spans: list[SpanCell] = []
    for j in range(ncols):
        s = label_styles.get(j)
        text = (s.text if s else None) or {}
        spec = col_spec_map.get(j, {})
        spans.append(
            SpanCell(
                start=j,
                end=j,
                label=labels[j] if j < len(labels) else "",
                align=spec.get("header_align"),
                bold=bool(spec.get("header_bold", False)),
                italic=bool(spec.get("header_italic", False)),
                underline=bool(text.get("underline", False)),
                border=s.border if s else None,
            )
        )
    return HeaderRow(kind="spanning", spans=spans)


def _build_cell_styles(sty, data_to_out, n_out, ncols, default_vars, stub_off, has_stub):
    pos_of = {v: stub_off + i for i, v in enumerate(default_vars)}
    rows: list[dict | None] = [None] * n_out

    def _entry(out_idx):
        e = rows[out_idx]
        if e is None:
            e = {}
            rows[out_idx] = e
        return e

    def _set(entry, key, j, value):
        seq = entry.get(key)
        if seq is None:
            seq = [None] * ncols
            entry[key] = seq
        seq[j] = value

    def _apply(out_idx, j, s: _LocStyle):
        entry = _entry(out_idx)
        text = s.text or {}
        if text.get("bold"):
            _set(entry, "bold", j, True)
        if text.get("italic"):
            _set(entry, "italic", j, True)
        if text.get("underline"):
            _set(entry, "underline", j, True)
        if text.get("align"):
            _set(entry, "align", j, text["align"])
        if text.get("color"):
            _set(entry, "color", j, text["color"])
        if s.border is not None:
            seq = entry.get("border")
            if seq is None:
                seq = [None] * ncols
                entry["border"] = seq
            seq[j] = s.border if seq[j] is None else merge_border(seq[j], s.border)

    for (var, rownum), s in sty["body"].items():
        j = pos_of.get(var)
        out_idx = data_to_out.get(rownum)
        if j is None or out_idx is None:
            continue
        _apply(out_idx, j, s)

    if has_stub:
        for rownum, s in sty["stub"].items():
            out_idx = data_to_out.get(rownum)
            if out_idx is None:
                continue
            _apply(out_idx, 0, s)

    if not any(r is not None for r in rows):
        return None
    return rows


def _parse_widths(bx: _Boxh, column_names, has_stub):
    """Parse boxhead widths to ``col_rel_width`` (pct) or ``column_widths_twips`` (px).

    Only applied when *every* output column carries a width of the same kind,
    matching the R adapter (a partial width map is dropped rather than guessed).
    """
    def var_for(j):
        if has_stub and j == 0:
            return bx.stub_var
        return column_names[j]

    kinds = []
    px_vals = []
    pct_vals = []
    for j in range(len(column_names)):
        w = bx.width.get(var_for(j))
        parsed = _parse_one_width(w)
        kinds.append(parsed[0])
        px_vals.append(parsed[1])
        pct_vals.append(parsed[1])
    if kinds and all(k == "px" for k in kinds):
        return None, [max(1, int(round(v * 15))) for v in px_vals]
    if kinds and all(k == "pct" for k in kinds):
        return [float(v) for v in pct_vals], None
    return None, None


def _parse_one_width(w):
    if w is None:
        return ("missing", 0.0)
    s = str(w).strip().lower()
    m = re.match(r"^([0-9.]+)\s*px$", s)
    if m:
        return ("px", float(m.group(1)))
    m = re.match(r"^([0-9.]+)\s*%$", s)
    if m:
        return ("pct", float(m.group(1)))
    return ("unknown", 0.0)


def _extract_titles(gt) -> list[str] | None:
    heading = _slot(gt, "_heading")
    if heading is None:
        return None
    lines = []
    for field in ("title", "subtitle", "preheader"):
        v = _flatten_label(getattr(heading, field, None))
        if v:
            lines.append(v)
    return lines or None


def _extract_footnotes(gt) -> list[str] | None:
    out: list[str] = []
    for fn in _slot(gt, "_footnotes") or []:
        texts = getattr(fn, "footnotes", None)
        if not texts:
            continue
        for t in texts if isinstance(texts, (list, tuple)) else [texts]:
            v = _flatten_label(t)
            if v:
                out.append(v)
    for note in _slot(gt, "_source_notes") or []:
        v = _flatten_label(note)
        if v:
            out.append(v)
    return out or None


def _append_summary_rows(gt, out_rows, default_vars, stub_off, has_stub):
    """Append grand-summary rows to the body (best effort, version-tolerant).

    great_tables' summary-row support is still maturing; where the grand
    summary is exposed as ``SummaryRowInfo`` entries with a ``values`` dict we
    render each as a labelled full-width stub row.  Anything else is skipped.
    """
    grand = _slot(gt, "_summary_rows_grand")
    if not grand:
        return
    try:
        entries = list(getattr(grand, "_d", {}).get("grand", []))
    except Exception:  # pragma: no cover - defensive
        return
    for info in entries:
        values = getattr(info, "values", None) or {}
        label = _flatten_label(getattr(info, "label", "") or "")
        cells = []
        if has_stub:
            cells.append(label)
        for v in default_vars:
            cells.append(_to_text(values.get(v)) if v in values else "")
        out_rows.append(cells)
