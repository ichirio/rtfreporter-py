"""Listing preparation -- ``listing_col()`` / ``listing_spec()`` / ``build_listing()``.

Ported from ``R/listing.R`` and ``R/listing_fit.R`` (R #241).  A clinical
listing is a data problem before it is an RTF problem: several source
variables joined into one printed column, long cells broken over physical
rows to fit a column so many characters wide, blank gutter columns, a blank
row after each record, and no page break inside a record.  ``build_listing()``
makes that body -- with a hidden record-id column -- and
``as_rtftables(listing=)`` runs it as a hook, pointing a group-safe split at
the record column and hiding it after pagination.
"""

from __future__ import annotations

import inspect
import math
import re
import unicodedata
from dataclasses import dataclass, field, replace

from .catx import catx

# -- measurements --------------------------------------------------------------


def listing_disp_width(x):
    """Display width of text: a full-width (CJK) glyph counts two (R
    ``nchar(type = "width")``).  A string gives an int, a list a list."""
    def one(v):
        s = "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)
        w = 0
        for ch in s:
            if unicodedata.combining(ch):
                continue
            w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        return w
    if isinstance(x, (list, tuple)):
        return [one(v) for v in x]
    return one(x)


def listing_take(x: str, width: int) -> str:
    """The longest leading piece of ``x`` that fits ``width`` (at least one
    character)."""
    if not x:
        return ""
    best = 1
    for i in range(1, len(x) + 1):
        if listing_disp_width(x[:i]) <= width:
            best = i
        else:
            break
    return x[:best]


def listing_split_after(text: str, sep):
    """``text`` split AFTER each ``sep`` (the separator stays on the left piece)."""
    if not sep:
        return [text]
    parts = re.split(f"(?<={re.escape(sep)})", text)
    parts = [p for p in parts if p != ""] if len(parts) > 1 else parts
    return parts or [text]


def _r_split_keep(text: str, pattern: str) -> list[str]:
    """R's ``strsplit(x, "(?<=...)", perl = TRUE)``: split at zero-width
    matches, dropping a trailing empty piece."""
    parts = re.split(pattern, text)
    while len(parts) > 1 and parts[-1] == "":
        parts.pop()
    return parts


def _r_trim(s: str) -> str:
    return re.sub(r"^[\t\r\n ]+|[\t\r\n ]+$", "", s)


# -- the "multiline" wrapping rule ---------------------------------------------


def _listing_wrap_words(text, width):
    """Break a piece at word boundaries (after a space, comma or hyphen); a
    token still too wide on its own is hard-split, so every line fits."""
    words = _r_split_keep(text, r"(?<=[ ,-])")
    if not words:
        words = [text]
    out = []
    cur = ""
    for w in words:
        if listing_disp_width(_r_trim(w)) > width:
            if _r_trim(cur):
                out.append(_r_trim(cur))
            tok = re.sub(r"^\s+", "", w)
            while listing_disp_width(_r_trim(tok)) > width:
                piece = listing_take(tok, width)
                out.append(piece)
                tok = tok[len(piece):]
            cur = tok
            continue
        if not cur:
            cur = w
        elif listing_disp_width(cur) + listing_disp_width(w) <= width:
            cur = cur + w
        else:
            out.append(_r_trim(cur))
            cur = w
    if _r_trim(cur):
        out.append(_r_trim(cur))
    return out


def _listing_flow(parts, width):
    """Refill separator-delimited pieces into lines of at most ``width``."""
    out = []
    cur = ""
    for p in parts:
        if not cur:
            cur = p
        elif listing_disp_width(_r_trim(cur + p)) <= width:
            cur = cur + p
        else:
            out.append(cur)
            cur = p
    if cur:
        out.append(cur)
    return out


def _listing_wrap_sep_word(text, width, sep, layout="stack"):
    """Break after the separator first, and only inside a piece that is still
    too long fall back to word boundaries.  A ``"\\n"`` in the data is a break
    the author asked for.  With no ``width`` the text stands as it is."""
    if text is None or (isinstance(text, float) and math.isnan(text)):
        text = ""
    text = str(text)
    chunks = text.split("\n")
    if width is None or (isinstance(width, float) and math.isnan(width)):
        chunks = [_r_trim(c) for c in chunks]
        return [""] if all(not c for c in chunks) else chunks
    out = []
    for ch in chunks:
        parts = listing_split_after(ch, sep)
        if layout == "flow":
            parts = _listing_flow(parts, width)
        for p in parts:
            p = _r_trim(p)
            if not p:
                continue
            if listing_disp_width(p) <= width:
                out.append(p)
            else:
                out.extend(_listing_wrap_words(p, width))
    return out or [""]


def listing_wrap(text, width, sep: str = "/", layout: str = "stack"):
    """The listing's wrapping rule on its own (R ``listing_wrap()``).

    A string gives its list of lines; a list of strings, a list of those.
    """
    if layout not in ("stack", "flow"):
        raise ValueError('`layout` must be "stack" or "flow".')
    if sep is not None and not isinstance(sep, str):
        raise ValueError("`sep` must be a single string, or None.")
    if width is not None and not (isinstance(width, (int, float)) and width >= 1):
        raise ValueError("`width` must be a single positive number, or None.")
    if isinstance(text, (list, tuple)):
        return [_listing_wrap_sep_word(t, width, sep, layout) for t in text]
    return _listing_wrap_sep_word(text, width, sep, layout)


def listing_wrap_code(name: str = "my_wrap") -> str:
    """The wrapping rule as Python source to copy and edit (R
    ``listing_wrap_code()``): the three policy functions, renamed after
    ``name``; the measurements they use stay rtfreporter's own."""
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError("`name` must be a valid Python identifier.")
    parts = {"_listing_flow": f"{name}_flow", "_listing_wrap_words": f"{name}_words",
             "_listing_wrap_sep_word": name}
    src = "\n\n".join(inspect.getsource(f) for f in
                      (_r_split_keep, _r_trim, _listing_flow, _listing_wrap_words,
                       _listing_wrap_sep_word))
    for old in sorted(parts, key=len, reverse=True):
        src = src.replace(old, parts[old])
    head = (
        f'# The "multiline" wrapping rule from rtfreporter, to edit.\n#\n'
        f"#   listing_spec(cols, wrap={name})\n#\n"
        "# Keep the contract: called with (text, width, sep, layout); `width` may\n"
        '# be None; `layout` is "stack" or "flow"; return a non-empty list of lines.\n#\n'
        "import re\n\nfrom rtfreporter import listing_disp_width, listing_split_after, "
        "listing_take\n\n\n"
    )
    return head + src


# -- templates ------------------------------------------------------------------


def _templates():
    return {"multiline": {"sep": "/", "spacer": True, "spacer_rel_width": 1,
                          "blank_row": True, "blank_row_first": True, "align": "left",
                          "layout": "stack", "wrap": _listing_wrap_sep_word}}


def _template(type_):
    if not isinstance(type_, str) or not type_:
        raise ValueError("`type` must be a single listing-template name.")
    reg = _templates()
    if type_ not in reg:
        raise ValueError(f'Unknown listing type "{type_}".  Available: '
                         + ", ".join(f'"{k}"' for k in reg) + ".")
    return reg[type_]


# -- one printed column ------------------------------------------------------------


@dataclass
class ListingCol:
    """One printed column of a listing, built by :func:`listing_col`."""

    vars: list
    sep: str | None = None
    width: int | None = None
    label: str | None = None
    name: str | None = None
    rel_width: float | None = None
    align: str | None = None
    layout: str | None = None
    collapse_repeats: bool = False


def listing_col(vars, sep=None, width=None, label=None, name=None, rel_width=None,
                align=None, layout=None, collapse_repeats: bool = False) -> ListingCol:
    """One printed column: its source variables (joined with ``sep``), its
    wrap ``width`` in characters, header ``label`` (a list is one line per
    element), output ``name``, ``rel_width``, ``align``, ``layout``
    (``"stack"`` / ``"flow"``) and whether it is a key column whose repeats
    are blanked (``collapse_repeats``)."""
    vars = [vars] if isinstance(vars, str) else list(vars or [])
    if not vars or not all(isinstance(v, str) and v for v in vars):
        raise ValueError("`vars` must be one or more non-empty source column names.")
    if sep is not None and not isinstance(sep, str):
        raise ValueError("`sep` must be a single string, or None.")
    if width is not None:
        if isinstance(width, bool) or not isinstance(width, (int, float)) or width < 1:
            raise ValueError("`width` must be a single positive number of characters, or None.")
        width = int(width)
    if rel_width is not None:
        if isinstance(rel_width, bool) or not isinstance(rel_width, (int, float)) or rel_width <= 0:
            raise ValueError("`rel_width` must be a single positive number, or None.")
        rel_width = float(rel_width)
    if label is not None:
        if isinstance(label, (list, tuple)):
            if not label or not all(isinstance(s, str) for s in label):
                raise ValueError("`label` must be a string, or a list of header lines, or None.")
            label = "\n".join(label)
        elif not isinstance(label, str):
            raise ValueError("`label` must be a string, or a list of header lines, or None.")
    if name is not None and (not isinstance(name, str) or not name):
        raise ValueError("`name` must be a single non-empty string, or None.")
    if align is not None and align not in ("left", "center", "right"):
        raise ValueError('`align` must be "left", "center" or "right".')
    if layout is not None and layout not in ("stack", "flow"):
        raise ValueError('`layout` must be "stack" or "flow".')
    if not isinstance(collapse_repeats, bool):
        raise ValueError("`collapse_repeats` must be True or False.")
    return ListingCol(vars=vars, sep=sep, width=width, label=label,
                      name=vars[0] if name is None else name, rel_width=rel_width,
                      align=align, layout=layout, collapse_repeats=collapse_repeats)


# -- the listing as a whole ---------------------------------------------------------


@dataclass
class ListingSpec:
    """A whole listing, built by :func:`listing_spec`."""

    cols: list
    type: str = "multiline"
    sep: str = "/"
    spacer: bool = True
    spacer_rel_width: float = 1
    blank_row: bool = True
    blank_row_first: bool = True
    align: str = "left"
    layout: str = "stack"
    wrap: object = None
    wrap_custom: bool = False
    record_col: str | None = ".rtf_record"
    fit: dict | None = field(default=None, repr=False)


def _make_unique(names):
    """R's ``make.unique(sep = "_")``."""
    seen, out = {}, []
    used = set(names)
    for n in names:
        if n not in seen:
            seen[n] = 0
            out.append(n)
            continue
        k = seen[n]
        while True:
            k += 1
            cand = f"{n}_{k}"
            if cand not in used:
                break
        seen[n] = k
        used.add(cand)
        out.append(cand)
    return out


def listing_spec(cols, type="multiline", sep=None, spacer=None, spacer_rel_width=None,
                 blank_row=None, blank_row_first=None, align=None, layout=None,
                 wrap=None, record=True) -> ListingSpec:
    """A listing: its printed columns and the ``type``'s defaults, any of
    which an argument overrides (R ``listing_spec()``).

    Args:
        cols: The printed columns, in order: :func:`listing_col` objects or
            source column names.
        type: The template (``"multiline"``: ``"/"`` separator, gutters, a blank
            row per record and before the first, left-aligned, ``"stack"``).
        wrap: A function ``(text, width, sep, layout)`` returning the lines,
            replacing the type's rule; see :func:`listing_wrap_code`.
        record: ``True`` for the hidden ``".rtf_record"`` column that keeps a
            record on one page, ``False`` for none, or its name.
    """
    tpl = _template(type)
    if cols is None:
        raise ValueError("`cols` is required: the printed columns, in order.")
    if isinstance(cols, (ListingCol, str)):
        cols = [cols]
    cols = list(cols)
    if not cols:
        raise ValueError("`cols` must be a non-empty list of listing_col() objects "
                         "(or column names).")
    out = []
    for j, cl in enumerate(cols):
        if isinstance(cl, (str, list, tuple)):
            cl = listing_col(cl)
        if not isinstance(cl, ListingCol):
            raise ValueError(f"`cols[{j}]` must be a listing_col() or source column names.")
        out.append(replace(cl))
    for cl, nm in zip(out, _make_unique([c.name for c in out]), strict=True):
        cl.name = nm
    for v, nm in ((spacer, "spacer"), (blank_row, "blank_row"),
                  (blank_row_first, "blank_row_first")):
        if v is not None and not isinstance(v, bool):
            raise ValueError(f"`{nm}` must be True or False, or None.")
    if spacer_rel_width is not None and not (isinstance(spacer_rel_width, (int, float))
                                             and spacer_rel_width > 0):
        raise ValueError("`spacer_rel_width` must be a single positive number, or None.")
    if align is not None and align not in ("left", "center", "right"):
        raise ValueError('`align` must be "left", "center" or "right".')
    if layout is not None and layout not in ("stack", "flow"):
        raise ValueError('`layout` must be "stack" or "flow".')
    if wrap is not None:
        if not callable(wrap):
            raise ValueError("`wrap` must be a function(text, width, sep, layout) returning "
                             "the lines, or None for the type's own rule.")
        if len(inspect.signature(wrap).parameters) < 4:
            raise ValueError("`wrap` must accept four arguments: text, width, sep, layout.")
    if record is True:
        record_col = ".rtf_record"
    elif record is False:
        record_col = None
    elif isinstance(record, str) and record:
        record_col = record
    else:
        raise ValueError("`record` must be True, False, or a single column name.")
    return ListingSpec(
        cols=out, type=type,
        sep=tpl["sep"] if sep is None else sep,
        spacer=tpl["spacer"] if spacer is None else spacer,
        spacer_rel_width=tpl["spacer_rel_width"] if spacer_rel_width is None else spacer_rel_width,
        blank_row=tpl["blank_row"] if blank_row is None else blank_row,
        blank_row_first=tpl["blank_row_first"] if blank_row_first is None else blank_row_first,
        align=tpl["align"] if align is None else align,
        layout=tpl["layout"] if layout is None else layout,
        wrap=tpl["wrap"] if wrap is None else wrap,
        wrap_custom=wrap is not None, record_col=record_col)


# -- layout: the one place output columns are enumerated ---------------------------


def _default_rel_width(cl: ListingCol) -> float:
    if cl.rel_width is not None:
        return float(cl.rel_width)
    if cl.width is not None:
        return float(cl.width)
    if cl.label is not None:
        lines = cl.label.split("\n")
        if lines:
            return float(max(max(listing_disp_width(lines)), 1))
    return 10.0


def _layout(spec: ListingSpec):
    items = []
    k = len(spec.cols)
    for j, cl in enumerate(spec.cols):
        items.append({"kind": "col", "index": j, "name": cl.name,
                      "label": "" if cl.label is None else cl.label,
                      "rel_width": _default_rel_width(cl),
                      "align": spec.align if cl.align is None else cl.align})
        if spec.spacer and j < k - 1:
            items.append({"kind": "spacer", "index": None, "name": f".sp{j + 1}", "label": "",
                          "rel_width": float(spec.spacer_rel_width), "align": spec.align})
    return items


def _min_wrap_width(text, sep) -> int:
    if not text:
        return 0
    pieces = str(text).split("\n")
    pieces = [q for p in pieces for q in listing_split_after(p, sep)]
    tokens = [_r_trim(t) for p in pieces for t in _r_split_keep(p, r"(?<=[ ,-])")]
    tokens = [t for t in tokens if t]
    return max(listing_disp_width(tokens)) if tokens else 0


def _var_label(v, labels=None):
    if labels and v in labels and isinstance(labels[v], str) and labels[v]:
        return labels[v]
    return v


def _wrap_call(fn, text, width, sep, layout):
    if fn is None:
        fn = _listing_wrap_sep_word
    out = fn(text, width, sep, layout)
    if isinstance(out, str) or not out or not all(isinstance(s, str) for s in out):
        raise ValueError("The listing's `wrap` function must return a non-empty list "
                         "of lines.")
    return list(out)


def _resolve_label(cl, sep, layout, labels=None, wrap=True, wrap_fn=None):
    if cl.label is not None:
        if not wrap or "\n" in cl.label:
            return cl.label
        return "\n".join(_wrap_call(wrap_fn, cl.label, cl.width, sep, layout))
    joined = sep.join(_var_label(v, labels) for v in cl.vars) if sep is not None else \
        "".join(_var_label(v, labels) for v in cl.vars)
    if not wrap:
        return joined
    return "\n".join(_wrap_call(wrap_fn, joined, cl.width, sep, layout))


def listing_metadata(spec: ListingSpec, body_names):
    """Header labels, relative widths and alignments for a built body, in the
    body's own coordinates (record column included)."""
    lay = _layout(spec)
    hdr = [it["label"] for it in lay]
    rw = [it["rel_width"] for it in lay]
    aligns = [it["align"] for it in lay]
    if spec.record_col is not None and spec.record_col in body_names:
        hdr.append("")
        rw.append(1.0)
    return {"col_header": hdr, "col_rel_width": rw,
            "col_spec": [{"col": it["name"], "align": a} for it, a in zip(lay, aligns, strict=True)]}


# -- build_listing() ---------------------------------------------------------------


def _combine(names, rows, cl, sep):
    missing = [v for v in cl.vars if v not in names]
    if missing:
        raise ValueError(f"Column{'s' if len(missing) > 1 else ''} "
                         + ", ".join(f'"{m}"' for m in missing)
                         + f' not in `data` (listing column "{cl.name}").')
    if not rows:
        return []
    cols = [[r[names.index(v)] for r in rows] for v in cl.vars]
    return catx("" if sep is None else sep, *cols)


def build_listing(data, spec: ListingSpec):
    """Lay the source data out as a listing body (R ``build_listing()``).

    Returns a :class:`~rtfreporter.pagination.Frame`: the printed columns (the
    joined, wrapped cells, one physical row per line), the blank gutters, a
    blank row after each record, and the hidden record-id column.  It carries
    the resolved spec as ``listing``, so ``as_rtftables()`` uses it as it is.
    """
    from .pagination import Frame
    from .table import _coerce_data

    if not isinstance(spec, ListingSpec):
        raise ValueError(f"`spec` must be a listing_spec(); got '{type(spec).__name__}'.")
    if getattr(data, "listing", None) is not None:
        raise ValueError("`data` has already been through build_listing() -- building it "
                         "again would join columns that are already joined.")
    names, rows = _coerce_data(data)
    spec = replace(spec, cols=[replace(c) for c in spec.cols])
    n, k = len(rows), len(spec.cols)
    lines = []
    for cl in spec.cols:
        sepj = spec.sep if cl.sep is None else cl.sep
        lay = spec.layout if cl.layout is None else cl.layout
        txt = _combine(names, rows, cl, sepj)
        cl.label = _resolve_label(cl, sepj, lay, wrap_fn=spec.wrap)
        lines.append([_wrap_call(spec.wrap, s, cl.width, sepj, lay) for s in txt])

    nl = [max([len(L[i]) for L in lines] + [1]) for i in range(n)]
    if spec.blank_row:
        nl = [v + 1 for v in nl]
    total = sum(nl)
    start, acc = [], 0
    for v in nl:
        start.append(acc)
        acc += v

    filled = []
    for j in range(k):
        v = [""] * total
        down = spec.cols[j].collapse_repeats
        for i in range(n):
            L = lines[j][i]
            if not L:
                continue
            body_rows = nl[i] - 1 if spec.blank_row else nl[i]
            if down and len(L) == 1 and body_rows > 1:
                for r in range(body_rows):
                    v[start[i] + r] = L[0]
            else:
                for r, s in enumerate(L):
                    v[start[i] + r] = s
        filled.append(v)

    lay = _layout(spec)
    out_names = [it["name"] for it in lay]
    columns = [filled[it["index"]] if it["kind"] == "col" else [""] * total for it in lay]
    if spec.record_col is not None:
        if spec.record_col in out_names:
            raise ValueError(f'The record column "{spec.record_col}" collides with a printed '
                             "column of the same name; rename one.")
        out_names.append(spec.record_col)
        columns.append([i + 1 for i in range(n) for _ in range(nl[i])])
    body_rows_out = [[c[r] for c in columns] for r in range(total)]
    frame = Frame(column_names=out_names, rows=body_rows_out)
    frame.listing = spec
    return frame


# -- fit_listing_widths() / listing_code() -------------------------------------------


def _quantile7(values, prob):
    """R's ``quantile(type = 7)``."""
    v = sorted(values)
    if not v:
        return 0.0
    h = (len(v) - 1) * prob
    lo = math.floor(h)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (h - lo) * (v[hi] - v[lo])


def _writable_twips(page) -> int:
    from .page import Page

    page = page or Page()
    geo = page.geometry()
    w = geo["width_twips"] - (float(page.margin_left_in) + float(page.margin_right_in)) * 1440
    if not math.isfinite(w) or w <= 0:
        raise ValueError("The page's margins leave no writable width.")
    return int(round(w))


def _r_round_int(x: float) -> int:
    return int(round(x))


def fit_listing_widths(data, spec: ListingSpec, page=None, font: str = "courier_new",
                       size_half_points: int = 18, total_width=None, labels=None,
                       header_lines=4, min_width: int = 6, probs: float = 0.9) -> ListingSpec:
    """Propose each column's ``width`` from the data and the page (R
    ``fit_listing_widths()``).

    A column's demand is the ``probs`` quantile of its cell widths (so one
    long value wraps rather than widening everything), at least the widest
    token its header cannot break and the width that keeps the header within
    ``header_lines`` lines; the demands are fitted into what the page leaves
    after the gutters.  A ``width`` you set is never touched.  The fitted spec
    also gets each column's ``rel_width`` and (unwrapped) ``label`` written
    down, so :func:`listing_code` shows everything to tune.
    """
    from .table import _coerce_data
    from .text_width import text_width_in

    if not isinstance(spec, ListingSpec):
        raise ValueError(f"`spec` must be a listing_spec(); got '{type(spec).__name__}'.")
    if getattr(data, "listing", None) is not None:
        raise ValueError("`data` has already been through build_listing(); fit the widths "
                         "on the source data instead.")
    names, rows = _coerce_data(data)
    if labels is not None:
        if not isinstance(labels, dict) or not labels:
            raise ValueError("`labels` must be a dict mapping SOURCE column names to labels.")
        labels = {k: ("" if v is None else v) for k, v in labels.items()}
    if not (isinstance(header_lines, (int, float)) and header_lines >= 1):
        raise ValueError("`header_lines` must be a single number >= 1, or math.inf.")
    min_width = int(min_width)
    if min_width < 1:
        raise ValueError("`min_width` must be a single positive integer.")
    if not (isinstance(probs, (int, float)) and 0 <= probs <= 1):
        raise ValueError("`probs` must be a single number in [0, 1].")
    if total_width is None:
        char_in = text_width_in("0", font=font, size_half_points=size_half_points)[0]
        total_width = int(math.floor(_writable_twips(page) / (char_in * 1440)))
    total_width = int(total_width)
    if total_width < 1:
        raise ValueError("`total_width` must be a single positive number of characters.")

    spec = replace(spec, cols=[replace(c) for c in spec.cols])
    k = len(spec.cols)
    fixed = [c.width is not None for c in spec.cols]
    n_gut = max(k - 1, 0) if spec.spacer else 0
    gutter = n_gut * float(spec.spacer_rel_width)
    budget = total_width - gutter - sum(float(c.width) for c in spec.cols if c.width is not None)
    n_free = fixed.count(False)
    if n_free and budget < n_free * min_width:
        raise ValueError(
            f"A total width of {total_width} character(s) leaves {budget:g} for the {n_free} "
            f"column(s) to be fitted, which cannot each be {min_width} wide.  Widen the "
            "page, shrink the font, or set the widths yourself.")

    floor_hdr = [0.0] * k
    demand = []
    for j, cl in enumerate(spec.cols):
        sepj = spec.sep if cl.sep is None else cl.sep
        lay = spec.layout if cl.layout is None else cl.layout
        cells = _combine(names, rows, cl, sepj) if rows else []
        cell_w = _quantile7(listing_disp_width(cells), probs) if cells else 0.0
        lab = _resolve_label(cl, sepj, lay, labels, wrap_fn=spec.wrap)
        hdr_w = _min_wrap_width(lab, sepj)
        floor_hdr[j] = hdr_w
        hdr_h = (math.ceil(sum(listing_disp_width(lab.split("\n"))) / header_lines)
                 if math.isfinite(header_lines) else 0)
        demand.append(max(cell_w, hdr_w, hdr_h, min_width))

    out = [float(c.width) if c.width is not None else None for c in spec.cols]
    if n_free:
        free_idx = [j for j in range(k) if not fixed[j]]
        free = [demand[j] for j in free_idx]
        scaled = [f * (budget / sum(free)) for f in free]
        fit = [max(min_width, _r_round_int(s)) for s in scaled]
        floors = [max(min_width, floor_hdr[j]) for j in free_idx]
        target = _r_round_int(budget)
        if sum(floors) <= budget:
            fit = [max(f, fl) for f, fl in zip(fit, floors, strict=True)]
            over = sum(fit) - target
            while over > 0:
                slack = [f - fl for f, fl in zip(fit, floors, strict=True)]
                if all(s <= 0 for s in slack):
                    break
                tot = sum(slack)
                take = [min(s, max(1, math.ceil(over * s / tot))) if s > 0 else 0
                        for s in slack]
                if sum(take) > over:
                    order = sorted(range(len(slack)), key=lambda i: -slack[i])
                    take = [0] * len(slack)
                    left = over
                    for i in order:
                        if left <= 0:
                            break
                        t = min(left, slack[i])
                        take[i] = t
                        left -= t
                fit = [f - t for f, t in zip(fit, take, strict=True)]
                over = sum(fit) - target
        drift = target - sum(fit)
        if drift != 0:
            jmax = max(range(len(fit)), key=lambda i: (fit[i], -i))
            fit[jmax] = max(min_width, fit[jmax] + drift)
        for j, f in zip(free_idx, fit, strict=True):
            out[j] = float(f)

    for j, cl in enumerate(spec.cols):
        cl.width = int(out[j])
        if cl.rel_width is None:
            cl.rel_width = float(cl.width)
        if cl.label is None:
            sepj = spec.sep if cl.sep is None else cl.sep
            lay = spec.layout if cl.layout is None else cl.layout
            cl.label = _resolve_label(cl, sepj, lay, labels, wrap=False, wrap_fn=spec.wrap)
    spec.fit = {"total_width": total_width, "gutter": gutter,
                "demand": {c.name: round(d, 1) for c, d in zip(spec.cols, demand, strict=True)},
                "fixed": fixed}
    return spec


def _py(value) -> str:
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return repr(value)


def listing_code(spec: ListingSpec, name: str | None = None, indent: int = 4) -> str:
    """The spec as Python source to paste into the program and tune (R
    ``listing_code()``): every column's settings, the spec's own where they
    differ from the type's defaults."""
    if not isinstance(spec, ListingSpec):
        raise ValueError(f"`spec` must be a listing_spec(); got '{type(spec).__name__}'.")
    if name is not None and (not isinstance(name, str) or not name):
        raise ValueError("`name` must be a single non-empty string, or None.")
    pad = " " * int(indent)
    tpl = _template(spec.type)
    col_lines = []
    for cl in spec.cols:
        vars_ = _py(cl.vars[0]) if len(cl.vars) == 1 else "[" + ", ".join(_py(v) for v in cl.vars) + "]"
        args = []
        for nm, val in (("width", cl.width), ("sep", cl.sep), ("layout", cl.layout)):
            if val is not None:
                args.append(f"{nm}={_py(val)}")
        if cl.name != cl.vars[0]:
            args.append(f"name={_py(cl.name)}")
        for nm, val in (("rel_width", cl.rel_width), ("align", cl.align)):
            if val is not None:
                args.append(f"{nm}={_py(val)}")
        if cl.collapse_repeats:
            args.append("collapse_repeats=True")
        line = f"{pad}listing_col({vars_}" + "".join(f", {a}" for a in args)
        if cl.label is not None:
            line += f",\n{pad * 2}label={_py(cl.label)}"
        col_lines.append(line + "),")
    spec_args = []
    if spec.type != "multiline":
        spec_args.append(f"type={_py(spec.type)}")
    for nm in ("sep", "spacer", "spacer_rel_width", "blank_row", "blank_row_first",
               "align", "layout"):
        val = getattr(spec, nm)
        if val != tpl[nm]:
            spec_args.append(f"{nm}={_py(val)}")
    if spec.record_col is None:
        spec_args.append("record=False")
    elif spec.record_col != ".rtf_record":
        spec_args.append(f"record={_py(spec.record_col)}")
    head = ("" if name is None else f"{name} = ") + "listing_spec(["
    tail = "]" + "".join(f", {a}" for a in spec_args) + ")"
    note = ("# NOTE: this listing uses a custom `wrap` function, which cannot be\n"
            "# written out here -- add `wrap=` back when you paste this.\n"
            if spec.wrap_custom else "")
    return note + head + "\n" + "\n".join(col_lines) + "\n" + tail
