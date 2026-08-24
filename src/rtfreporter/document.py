"""The :class:`RtfDocument` builder and the RTF render driver.

Provides both a fluent, chainable API (``RtfDocument().add_section(...)
.add_table(...).save(path)``) and a plain functional layer
(:func:`to_rtf`, :func:`save`).

Ported from ``R/pipe-composition.R`` (the pipe API) and the driver at the tail
of ``R/generate_rtfreport.R``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from . import _commands as C
from . import render as R
from ._escape import resolve_markup
from .figure import Figure, rtfplot
from .header_footer import HeaderFooter, normalize_hf
from .page import DefaultFormat, Page
from .table import RtfTable, rtftable


@dataclass
class _Report:
    """Flat model consumed by the render driver."""

    page: Page
    default_format: DefaultFormat
    color_table: list[str] | None
    sections: list[dict]
    pages: list[dict]


class RtfDocument:
    """A composable RTF document of sections and content pages.

    Each *page* holds exactly one content item (a table or figure) plus an
    optional title and footnote.  Each *section* carries a running header and
    footer that apply from a given page onward.

    Example:
        >>> from rtfreporter import RtfDocument, rtf_header, rtf_footer
        >>> doc = (
        ...     RtfDocument()
        ...     .add_section(
        ...         header=rtf_header([{"l": "Protocol XYZ", "r": "Page {AUTO_PAGE}"}]),
        ...         footer=rtf_footer([{"c": "CONFIDENTIAL"}]),
        ...     )
        ...     .add_table({"Subject": ["001"], "Age": [34]},
        ...                title=["Demographics"])
        ... )
        >>> rtf = doc.to_rtf()
    """

    def __init__(
        self,
        page: Page | None = None,
        default_format: DefaultFormat | None = None,
        color_table: list[str] | None = None,
    ) -> None:
        self.page = page or Page()
        self.default_format = default_format or DefaultFormat()
        self.color_table = list(color_table) if color_table else None
        self._sections: list[dict] = []
        self._pages: list[dict] = []

    # -- copy-on-modify ------------------------------------------------------

    def _copy(self) -> RtfDocument:
        """Return an independent copy, as R's copy-on-modify semantics require.

        Every builder below works on a copy, so the document handed in is never
        changed.  This matters when a base document (shared page setup, colour
        table, fonts) is reused to start several reports: in R that is safe, and
        it must be safe here too.
        """
        new = RtfDocument.__new__(RtfDocument)
        new.page = self.page
        new.default_format = self.default_format
        new.color_table = list(self.color_table) if self.color_table else None
        new._sections = [dict(section) for section in self._sections]
        new._pages = [dict(page) for page in self._pages]
        return new

    # -- section / content builders -----------------------------------------

    def add_section(
        self,
        header: HeaderFooter | None = None,
        footer: HeaderFooter | None = None,
        from_page: int | None = None,
    ) -> RtfDocument:
        """Start a new section with a running ``header`` / ``footer``.

        Returns a **new** document; the receiver is left unchanged.

        Args:
            header, footer: Bands built with :func:`~rtfreporter.rtf_header` /
                :func:`~rtfreporter.rtf_footer`.  ``None`` inherits the previous
                section's band.
            from_page: 1-based first page of the section.  ``None`` uses the
                next page to be added.
        """
        new = self._copy()
        if from_page is None:
            from_page = len(new._pages) + 1
        new._sections.append(
            {"header": header, "footer": footer, "from_page": int(from_page)}
        )
        return new

    def add_table(
        self,
        table,
        title=None,
        footnote=None,
        **table_kwargs,
    ) -> RtfDocument:
        """Add one content page holding a table.

        Args:
            table: An :class:`~rtfreporter.RtfTable`, or any input accepted by
                :func:`~rtfreporter.rtftable` (a DataFrame, dict of columns,
                etc.).
            title: A title block (str or list of lines / row dicts).
            footnote: A footnote block (same shape as ``title``).
            **table_kwargs: Forwarded to :func:`~rtfreporter.rtftable` when
                ``table`` is not already an ``RtfTable``.
        """
        content = table if isinstance(table, RtfTable) else rtftable(table, **table_kwargs)
        if title is None and content.titles is not None:
            title = content.titles
        if footnote is None and content.footnotes is not None:
            footnote = content.footnotes
        new = self._copy()
        new._pages.append({"title": title, "content": content, "footnote": footnote})
        return new

    def add_figure(self, figure, title=None, footnote=None, **kwargs) -> RtfDocument:
        """Add one content page holding a figure.

        Args:
            figure: A :class:`~rtfreporter.Figure` or a path to a PNG/JPEG file.
            **kwargs: Forwarded to :func:`~rtfreporter.rtfplot` when ``figure``
                is a path.
        """
        content = figure if isinstance(figure, Figure) else rtfplot(figure, **kwargs)
        new = self._copy()
        new._pages.append({"title": title, "content": content, "footnote": footnote})
        return new

    def add_tables(self, tables, titles=None, footnotes=None, **table_kwargs) -> RtfDocument:
        """Add several table pages at once (one page per element).

        ``titles`` / ``footnotes`` are parallel lists, one entry per table.
        Returns a **new** document; the receiver is left unchanged.
        """
        new = self
        for i, tbl in enumerate(list(tables)):
            new = new.add_table(
                tbl,
                title=titles[i] if titles is not None and i < len(titles) else None,
                footnote=footnotes[i] if footnotes is not None and i < len(footnotes) else None,
                **table_kwargs,
            )
        return new if new is not self else self._copy()

    def titles(self, titles) -> RtfDocument:
        """Set the title of each existing page from a parallel list."""
        new = self._copy()
        for i, t in enumerate(titles):
            if i < len(new._pages):
                new._pages[i]["title"] = t
        return new

    def footnotes(self, footnotes) -> RtfDocument:
        """Set the footnote of each existing page from a parallel list."""
        new = self._copy()
        for i, f in enumerate(footnotes):
            if i < len(new._pages):
                new._pages[i]["footnote"] = f
        return new

    # -- output --------------------------------------------------------------

    def to_rtf(self) -> str:
        """Render the whole document to an RTF string."""
        return _generate(self._report())

    def save(self, path: str, overwrite: bool = True) -> str:
        """Render and write the document to ``path``.

        Args:
            path: Destination ``.rtf`` file path.
            overwrite: When ``False``, raises if the file already exists.

        Returns:
            The path written.
        """
        import os

        if os.path.exists(path) and not overwrite:
            raise FileExistsError(f"{path!r} already exists. Set overwrite=True.")
        rtf = self.to_rtf()
        with open(path, "w", encoding="ascii", newline="\n") as fh:
            fh.write(rtf)
        return path

    def _report(self) -> _Report:
        return _Report(
            page=self.page,
            default_format=self.default_format,
            color_table=self.color_table,
            sections=list(self._sections),
            pages=list(self._pages),
        )


# -- functional layer ---------------------------------------------------------


def rtf_document(
    page: Page | None = None,
    default_format: DefaultFormat | None = None,
    color_table: list[str] | None = None,
) -> RtfDocument:
    """Create a new :class:`RtfDocument` (mirrors R's ``rtf_document()``).

    This is the head of the module-level "pipe" API
    (``rtf_document() -> rtf_tables() -> ... -> generate_rtfreport()``); the
    fluent :class:`RtfDocument` methods are an equivalent convenience.
    """
    return RtfDocument(page=page, default_format=default_format, color_table=color_table)


def rtf_config(
    doc: RtfDocument,
    page=None,
    default_format=None,
    color_table=None,
    font_table=None,
) -> RtfDocument:
    """Return a copy of ``doc`` with page / default-format / colour overrides.

    Mirrors R's ``rtf_config()``: whole-object replacements for ``color_table``,
    per-field merges for ``page`` and ``default_format``.  ``page`` /
    ``default_format`` may each be a full :class:`~rtfreporter.Page` /
    :class:`~rtfreporter.DefaultFormat` object (replaces the whole object) or a
    dict of field overrides (merged onto the current object).

    Args:
        doc: The :class:`RtfDocument` to reconfigure.
        page: A :class:`~rtfreporter.Page` or a dict of :class:`Page` field
            overrides.
        default_format: A :class:`~rtfreporter.DefaultFormat` or a dict of field
            overrides.
        color_table: A replacement colour table (list of hex strings).
        font_table: Accepted for R signature parity; the Python renderer manages
            fonts automatically, so a non-``None`` value raises
            :class:`NotImplementedError`.

    Returns:
        A new :class:`RtfDocument` (the pages and sections are carried over).
    """
    if not isinstance(doc, RtfDocument):
        raise TypeError("`doc` must be an RtfDocument.")
    if font_table is not None:
        raise NotImplementedError(
            "rtf_config(font_table=...) is not supported; the Python renderer "
            "manages the font table automatically."
        )
    new_page = doc.page
    if page is not None:
        new_page = replace(doc.page, **page) if isinstance(page, dict) else page
    new_fmt = doc.default_format
    if default_format is not None:
        new_fmt = (
            replace(doc.default_format, **default_format)
            if isinstance(default_format, dict)
            else default_format
        )
    new_colors = doc.color_table if color_table is None else color_table

    out = RtfDocument(page=new_page, default_format=new_fmt, color_table=new_colors)
    out._sections = list(doc._sections)
    out._pages = list(doc._pages)
    return out


def rtf_tables(
    doc: RtfDocument,
    tables,
    titles=None,
    footnotes=None,
    **table_kwargs,
) -> RtfDocument:
    """Add one or more table content pages to ``doc`` (mirrors R ``rtf_tables()``).

    Args:
        doc: The :class:`RtfDocument` to add to.
        tables: A single table input (an :class:`~rtfreporter.RtfTable`, dict of
            columns, or DataFrame) or a list/tuple of them (one page each).
        titles, footnotes: A parallel list (one per table) or a single block
            applied to every table.
        **table_kwargs: Forwarded to :func:`~rtfreporter.rtftable`.

    Returns:
        A **new** document; ``doc`` is left unchanged (as in R).
    """
    if not isinstance(doc, RtfDocument):
        raise TypeError("`doc` must be an RtfDocument.")
    items = _as_table_list(tables)
    n = len(items)
    tlist = _broadcast_blocks(titles, n)
    flist = _broadcast_blocks(footnotes, n)
    out = doc
    for i, tbl in enumerate(items):
        out = out.add_table(
            tbl,
            title=tlist[i] if tlist is not None else None,
            footnote=flist[i] if flist is not None else None,
            **table_kwargs,
        )
    return out if out is not doc else doc._copy()


def rtf_figures(
    doc: RtfDocument,
    figures,
    titles=None,
    footnotes=None,
    **fig_kwargs,
) -> RtfDocument:
    """Add one or more figure content pages to ``doc`` (mirrors R ``rtf_figures()``)."""
    if not isinstance(doc, RtfDocument):
        raise TypeError("`doc` must be an RtfDocument.")
    if not isinstance(figures, (list, tuple)):
        figures = [figures]
    n = len(figures)
    tlist = _broadcast_blocks(titles, n)
    flist = _broadcast_blocks(footnotes, n)
    out = doc
    for i, fig in enumerate(figures):
        out = out.add_figure(
            fig,
            title=tlist[i] if tlist is not None else None,
            footnote=flist[i] if flist is not None else None,
            **fig_kwargs,
        )
    return out if out is not doc else doc._copy()


def rtf_titles(doc: RtfDocument, titles) -> RtfDocument:
    """Assign per-page titles (mirrors R ``rtf_titles()``).

    ``titles`` is a list of one block per page, or a single block common to all.
    """
    if not isinstance(doc, RtfDocument):
        raise TypeError("`doc` must be an RtfDocument.")
    n = len(doc._pages)
    if n == 0:
        raise ValueError("Cannot set titles before any content has been added.")
    blocks = _broadcast_blocks(titles, n, require_list=True)
    return doc.titles(blocks)


def rtf_footnotes(doc: RtfDocument, footnotes) -> RtfDocument:
    """Assign per-page footnotes (mirrors R ``rtf_footnotes()``)."""
    if not isinstance(doc, RtfDocument):
        raise TypeError("`doc` must be an RtfDocument.")
    n = len(doc._pages)
    if n == 0:
        raise ValueError("Cannot set footnotes before any content has been added.")
    blocks = _broadcast_blocks(footnotes, n, require_list=True)
    return doc.footnotes(blocks)


def rtf_section(
    doc: RtfDocument,
    page: int | None = None,
    header=None,
    footer=None,
) -> RtfDocument:
    """Attach a running header/footer from a given page onward (R ``rtf_section()``).

    Args:
        doc: The :class:`RtfDocument`.
        page: 1-based first *page number* of the section (``None`` = the next
            page to be added).  Page numbers are 1-based (they are page numbers,
            not zero-based indices).
        header, footer: Bands built with :func:`~rtfreporter.rtf_header` /
            :func:`~rtfreporter.rtf_footer`.  ``None`` inherits the previous
            section's band.
    """
    if not isinstance(doc, RtfDocument):
        raise TypeError("`doc` must be an RtfDocument.")
    return doc.add_section(header=header, footer=footer, from_page=page)


def generate_rtfreport(doc: RtfDocument, file_path: str, overwrite: bool = False) -> str:
    """Render ``doc`` and write it to ``file_path`` (mirrors R ``generate_rtfreport()``).

    Args:
        doc: The :class:`RtfDocument` to render.
        file_path: Destination ``.rtf`` path (required, as in R).
        overwrite: When ``False`` (the R default), raise if ``file_path`` exists.

    Returns:
        The path written.
    """
    if not isinstance(doc, RtfDocument):
        raise TypeError("`doc` must be an RtfDocument.")
    return doc.save(file_path, overwrite=overwrite)


def to_rtf(doc: RtfDocument) -> str:
    """Render an :class:`RtfDocument` to an RTF string (functional alias)."""
    return doc.to_rtf()


def save(doc: RtfDocument, path: str, overwrite: bool = True) -> str:
    """Render and write an :class:`RtfDocument` (functional alias)."""
    return doc.save(path, overwrite=overwrite)


def _as_table_list(tables) -> list:
    """A single table input -> ``[table]``; a list/tuple of tables -> as-is."""
    if isinstance(tables, RtfTable):
        return [tables]
    if isinstance(tables, dict):
        return [tables]
    if isinstance(tables, (list, tuple)):
        # A list of row-dicts is a single table; a list of frames/tables is many.
        if tables and isinstance(tables[0], dict):
            return [tables]
        return list(tables)
    return [tables]


def _broadcast_blocks(blocks, n: int, require_list: bool = False):
    """Normalise a ``titles`` / ``footnotes`` argument to length ``n`` or ``None``."""
    if blocks is None:
        return None
    if require_list and not isinstance(blocks, (list, tuple)):
        raise TypeError("`titles`/`footnotes` must be a list (one block per page).")
    if isinstance(blocks, (list, tuple)):
        if len(blocks) == n:
            return list(blocks)
        if len(blocks) == 1:
            return list(blocks) * n
        if not require_list and all(isinstance(b, (str, dict)) for b in blocks):
            # A single block expressed as a list of rows, common to all pages.
            return [blocks] * n
        raise ValueError(
            f"Expected {n} blocks (one per page) or 1 (common to all); got {len(blocks)}."
        )
    return [blocks] * n


# -- render driver ------------------------------------------------------------


def _resolve_sections(report: _Report) -> list[dict]:
    n_pages = len(report.pages)
    if n_pages == 0:
        return []
    sections = list(report.sections)
    if not sections:
        return [{"header": None, "footer": None, "from_page": 1, "to_page": n_pages}]

    # Order by from_page, then reassign contiguous ranges.
    order = sorted(range(len(sections)), key=lambda i: sections[i]["from_page"] or 1)
    sections = [sections[i] for i in order]
    from_pages = [s["from_page"] or 1 for s in sections]
    from_pages[0] = 1
    n_sec = len(sections)
    to_pages = [from_pages[i + 1] - 1 for i in range(n_sec - 1)] + [n_pages]
    return [
        {
            "header": sections[i]["header"],
            "footer": sections[i]["footer"],
            "from_page": from_pages[i],
            "to_page": to_pages[i],
        }
        for i in range(n_sec)
    ]


def _generate(report: _Report) -> str:
    geo = report.page.geometry()
    fmt = report.default_format
    writable = geo["width_twips"] - geo["margin_left_twips"] - geo["margin_right_twips"]
    header_dist = geo["header_dist_twips"]
    footer_dist = geo["footer_dist_twips"]

    total_pages = len(report.pages)
    doc_colors = R.collect_report_colors(report)
    color_table_str = R.build_color_table_rtf(doc_colors)
    color_index_map = R.build_color_index_map(doc_colors)

    orientation_cmd = r"\landscape" if geo["orientation"] == "landscape" else ""
    lines: list[str] = [
        C.RTF_HEADER_OPEN,
        C.FONT_TABLE_TEMPLATE.format(font_name=_esc(fmt.font)),
        color_table_str,
        C.PAGE_SETTINGS_TEMPLATE.format(
            width_twips=geo["width_twips"],
            height_twips=geo["height_twips"],
            orientation_cmd=orientation_cmd,
            margin_left_twips=geo["margin_left_twips"],
            margin_right_twips=geo["margin_right_twips"],
            margin_top_twips=geo["margin_top_twips"],
            margin_bottom_twips=geo["margin_bottom_twips"],
            header_dist_twips=header_dist,
            footer_dist_twips=footer_dist,
            font_size_half_points=fmt.font_size_half_points,
        ),
    ]

    fhp = int(fmt.font_size_half_points)
    fs_cmd = f"\\fs{fhp}"
    doc_row_height = fmt.row_height_twips
    doc_pad_l = fmt.cell_padding_left_twips if fmt.cell_padding_left_twips is not None else C.DEFAULT_CELL_PADDING_LEFT_TWIPS
    doc_pad_r = fmt.cell_padding_right_twips if fmt.cell_padding_right_twips is not None else C.DEFAULT_CELL_PADDING_RIGHT_TWIPS
    doc_markup = resolve_markup(fmt.markup)
    title_format = fmt.title_format
    footnote_format = fmt.footnote_format

    resolved = _resolve_sections(report)
    prev_header = None
    prev_footer = None

    for rs_idx, rs in enumerate(resolved):
        pg_from = rs["from_page"]
        pg_to = rs["to_page"]

        cur_header = normalize_hf(rs["header"]) or prev_header
        prev_header = cur_header
        cur_footer = normalize_hf(rs["footer"]) or prev_footer
        prev_footer = cur_footer

        def emit_preamble(pg_for_hf, cur_header=None, cur_footer=None):
            lines.append(C.SECTION_DEFAULTS)
            lnd = r"\lndscpsxn" if geo["orientation"] == "landscape" else ""
            lines.append(
                r"\sbkpage" + lnd
                + r"\pgwsxn" + str(geo["width_twips"])
                + r"\pghsxn" + str(geo["height_twips"])
                + r"\marglsxn" + str(geo["margin_left_twips"])
                + r"\margrsxn" + str(geo["margin_right_twips"])
                + r"\margtsxn" + str(geo["margin_top_twips"])
                + r"\margbsxn" + str(geo["margin_bottom_twips"])
                + r"\headery" + str(header_dist)
                + r"\footery" + str(footer_dist)
            )
            header_rtf = R.render_header_footer(
                cur_header, writable, is_footer=False, current_page=pg_for_hf,
                total_pages=total_pages, color_index_map=color_index_map,
                font_half_points=fhp, doc_row_height=doc_row_height,
                doc_pad_l=doc_pad_l, doc_pad_r=doc_pad_r)
            footer_rtf = R.render_header_footer(
                cur_footer, writable, is_footer=True, current_page=pg_for_hf,
                total_pages=total_pages, color_index_map=color_index_map,
                font_half_points=fhp, doc_row_height=doc_row_height,
                doc_pad_l=doc_pad_l, doc_pad_r=doc_pad_r)
            if header_rtf:
                lines.append(C.HEADER_WRAPPER.format(content=fs_cmd + "".join(header_rtf)))
            if footer_rtf:
                lines.append(C.FOOTER_WRAPPER.format(content=fs_cmd + "".join(footer_rtf)))

        from ._escape import uses_static_page_token

        needs_per_page = uses_static_page_token(cur_header) or uses_static_page_token(cur_footer)
        sec_pages = list(range(pg_from, pg_to + 1))
        if not needs_per_page:
            emit_preamble(pg_from, cur_header, cur_footer)

        for sp_idx, p_idx in enumerate(sec_pages):
            page = report.pages[p_idx - 1]
            if needs_per_page:
                emit_preamble(p_idx, cur_header, cur_footer)

            ct = page.get("content")
            content_w = R.content_width_twips(ct, writable)
            calign = R.content_align(ct)
            tf_valign = r"\clvertalt"

            # Title.
            if title_format == "text":
                lines.extend(R.render_text_block_text(
                    page.get("title"), is_footer=False, color_index_map=color_index_map,
                    markup=doc_markup, pad_l=doc_pad_l, pad_r=doc_pad_r))
            else:
                lines.extend(R.render_text_block_table(
                    page.get("title"), content_w, False, fhp, doc_pad_l, doc_pad_r,
                    tf_valign, calign, color_index_map, doc_row_height, doc_markup))

            # Content.
            if isinstance(ct, RtfTable):
                lines.extend(R.render_rtftable(
                    ct, writable, fhp, color_index_map,
                    doc_row_height=doc_row_height, doc_pad_l=doc_pad_l,
                    doc_pad_r=doc_pad_r, doc_markup=doc_markup))
            elif isinstance(ct, Figure):
                lines.append(R.render_rtfplot(ct, writable))

            # Footnote.
            if footnote_format == "text":
                lines.extend(R.render_text_block_text(
                    page.get("footnote"), is_footer=True, color_index_map=color_index_map,
                    markup=doc_markup, pad_l=doc_pad_l, pad_r=doc_pad_r))
            else:
                lines.extend(R.render_text_block_table(
                    page.get("footnote"), content_w, True, fhp, doc_pad_l, doc_pad_r,
                    tf_valign, calign, color_index_map, doc_row_height, doc_markup))

            is_last_in_section = sp_idx == len(sec_pages) - 1
            is_last_section = rs_idx == len(resolved) - 1
            if not is_last_in_section:
                if needs_per_page:
                    lines.extend([C.TABLE_END, C.SECTION_BREAK])
                else:
                    lines.append(C.PAGE_BREAK)
            elif not is_last_section:
                lines.extend([C.TABLE_END, C.SECTION_BREAK])
            else:
                lines.append(C.TABLE_END)

    lines.append(C.DOCUMENT_CLOSE)
    return "\n".join(lines) + "\n"


def _esc(text: str) -> str:
    from ._escape import escape

    return escape(text)
