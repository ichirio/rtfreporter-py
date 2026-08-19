"""The :class:`RtfDocument` builder and the RTF render driver.

Provides both a fluent, chainable API (``RtfDocument().add_section(...)
.add_table(...).save(path)``) and a plain functional layer
(:func:`to_rtf`, :func:`save`).

Ported from ``R/pipe-composition.R`` (the pipe API) and the driver at the tail
of ``R/generate_rtfreport.R``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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
        >>> from rtfreporter import RtfDocument, header, footer
        >>> doc = (
        ...     RtfDocument()
        ...     .add_section(
        ...         header=header([{"l": "Protocol XYZ", "r": "Page {AUTO_PAGE}"}]),
        ...         footer=footer([{"c": "CONFIDENTIAL"}]),
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

    # -- section / content builders -----------------------------------------

    def add_section(
        self,
        header: HeaderFooter | None = None,
        footer: HeaderFooter | None = None,
        from_page: int | None = None,
    ) -> RtfDocument:
        """Start a new section with a running ``header`` / ``footer``.

        Args:
            header, footer: Bands built with :func:`~rtfreporter.header` /
                :func:`~rtfreporter.footer`.  ``None`` inherits the previous
                section's band.
            from_page: 1-based first page of the section.  ``None`` uses the
                next page to be added.
        """
        if from_page is None:
            from_page = len(self._pages) + 1
        self._sections.append(
            {"header": header, "footer": footer, "from_page": int(from_page)}
        )
        return self

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
        self._pages.append({"title": title, "content": content, "footnote": footnote})
        return self

    def add_figure(self, figure, title=None, footnote=None, **kwargs) -> RtfDocument:
        """Add one content page holding a figure.

        Args:
            figure: A :class:`~rtfreporter.Figure` or a path to a PNG/JPEG file.
            **kwargs: Forwarded to :func:`~rtfreporter.rtfplot` when ``figure``
                is a path.
        """
        content = figure if isinstance(figure, Figure) else rtfplot(figure, **kwargs)
        self._pages.append({"title": title, "content": content, "footnote": footnote})
        return self

    def add_tables(self, tables, titles=None, footnotes=None, **table_kwargs) -> RtfDocument:
        """Add several table pages at once (one page per element).

        ``titles`` / ``footnotes`` are parallel lists, one entry per table.
        """
        tables = list(tables)
        for i, tbl in enumerate(tables):
            self.add_table(
                tbl,
                title=titles[i] if titles is not None and i < len(titles) else None,
                footnote=footnotes[i] if footnotes is not None and i < len(footnotes) else None,
                **table_kwargs,
            )
        return self

    def titles(self, titles) -> RtfDocument:
        """Set the title of each existing page from a parallel list."""
        for i, t in enumerate(titles):
            if i < len(self._pages):
                self._pages[i]["title"] = t
        return self

    def footnotes(self, footnotes) -> RtfDocument:
        """Set the footnote of each existing page from a parallel list."""
        for i, f in enumerate(footnotes):
            if i < len(self._pages):
                self._pages[i]["footnote"] = f
        return self

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


def document(
    page: Page | None = None,
    default_format: DefaultFormat | None = None,
    color_table: list[str] | None = None,
) -> RtfDocument:
    """Create a new :class:`RtfDocument` (functional alias)."""
    return RtfDocument(page=page, default_format=default_format, color_table=color_table)


def to_rtf(doc: RtfDocument) -> str:
    """Render an :class:`RtfDocument` to an RTF string (functional alias)."""
    return doc.to_rtf()


def save(doc: RtfDocument, path: str, overwrite: bool = True) -> str:
    """Render and write an :class:`RtfDocument` (functional alias)."""
    return doc.save(path, overwrite=overwrite)


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
