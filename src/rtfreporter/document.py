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
from .element_style import element_style, resolve_block_width
from .figure import Figure, rtfplot
from .footnote_band import footnote_hf, footnote_rows
from .header_footer import HeaderFooter, normalize_hf
from .page import DefaultFormat, Page
from .table import RtfTable, rtftable

#: "Argument not given", where ``None`` is itself a value (a section that
#: switches the watermark off).
_NOT_GIVEN = object()


def _font_names(font_table) -> list[str] | None:
    """A font table -- a list of family names, or of ``{"name": ...}`` dicts
    as R writes it -- as a list of names, first = the document default."""
    if font_table is None:
        return None
    if isinstance(font_table, str):
        font_table = [font_table]
    names = []
    for f in font_table:
        name = f.get("name") if isinstance(f, dict) else f
        if not isinstance(name, str):
            raise ValueError("`font_table` must be a list of font family names.")
        if name:
            names.append(name)
    return names or None


def _collect_fonts(report) -> list[str]:
    """Every family the document needs: the declared table first (its first
    entry is the default), then any family an element asked for (R
    ``.collect_fonts()`` / ``.collect_report_fonts()``)."""
    declared = list(report.font_table) if report.font_table else [report.default_format.font]
    wanted = [report.title_style.get("font"), report.footnote_style.get("font")]
    for page in report.pages:
        ct = page.get("content")
        if isinstance(ct, RtfTable):
            wanted.append(ct.font)
    for sec in report.sections:
        for band in (sec.get("header"), sec.get("footer")):
            wanted.append(getattr(band, "font", None))
    return list(dict.fromkeys(declared + [f for f in wanted if f]))


@dataclass
class _Report:
    """Flat model consumed by the render driver."""

    page: Page
    default_format: DefaultFormat
    color_table: list[str] | None
    sections: list[dict]
    pages: list[dict]
    title_style: dict
    footnote_style: dict
    watermark: object = None
    font_table: list | None = None


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
        program: str | None = None,
        watermark=None,
        font_table=None,
    ) -> None:
        from .watermark import normalize_watermark

        self.page = page or Page()
        #: The program ``{PROGRAM}`` names (R ``rtf_document(program=)``).
        self.program = program
        #: The watermark on every page (R ``rtf_document(watermark=)``).
        self.watermark = normalize_watermark(watermark)
        #: The declared fonts, first = the document default (R ``font_table``);
        #: ``None`` declares ``default_format.font`` alone.
        self.font_table = _font_names(font_table)
        self.default_format = default_format or DefaultFormat()
        self.color_table = list(color_table) if color_table else None
        self._sections: list[dict] = []
        self._pages: list[dict] = []
        #: Block-level style for the title / footnote blocks (R #292 / #296):
        #: ``font_size_half_points``, ``row_height_twips``, ``markup``,
        #: ``align`` and (footnote only) ``border``.
        self.title_style: dict = {}
        self.footnote_style: dict = {}

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
        new.program = self.program
        new.watermark = self.watermark
        new.font_table = list(self.font_table) if self.font_table else None
        new._sections = [dict(section) for section in self._sections]
        new._pages = [dict(page) for page in self._pages]
        new.title_style = dict(self.title_style)
        new.footnote_style = dict(self.footnote_style)
        return new

    # -- section / content builders -----------------------------------------

    def add_section(
        self,
        header: HeaderFooter | None = None,
        footer: HeaderFooter | None = None,
        from_page: int | None = None,
        watermark=_NOT_GIVEN,
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
        section = {"header": header, "footer": footer, "from_page": int(from_page)}
        if watermark is not _NOT_GIVEN:
            from .watermark import normalize_watermark

            section["watermark"] = normalize_watermark(watermark)
        new._sections.append(section)
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

    def add_tables(
        self,
        tables,
        titles=None,
        footnotes=None,
        auto_section: bool = False,
        section_label_align: str = "left",
        **table_kwargs,
    ) -> RtfDocument:
        """Add several table pages at once (one page per element).

        ``titles`` / ``footnotes`` are parallel lists, one entry per table.
        ``auto_section`` opens a section per **named** page -- see
        :func:`rtf_tables`.  Returns a **new** document; the receiver is left
        unchanged.
        """
        new = self
        base_header = _auto_section_base(self) if auto_section else None
        open_label = None
        for i, tbl in enumerate(list(tables)):
            if auto_section:
                label = getattr(tbl, "name", None)
                if label and str(label) != open_label:
                    open_label = str(label)
                    new = _open_auto_section(
                        new,
                        _auto_section_header(base_header, open_label, section_label_align),
                    )
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

    def to_rtf(self, program: str | None = None) -> str:
        """Render the whole document to an RTF string.

        Args:
            program: The program the run tokens (``{PROGRAM}`` ...) name;
                ``None`` uses the document's, then the ``program`` option, then
                the script Python is running.
        """
        from ._run_tokens import run_context

        with run_context(program if program is not None else self.program):
            return _generate(self._report())

    def save(self, path: str, overwrite: bool = True, program: str | None = None) -> str:
        """Render and write the document to ``path``.

        Args:
            path: Destination ``.rtf`` file path.
            overwrite: When ``False``, raises if the file already exists.
            program: As in :meth:`to_rtf`.

        Returns:
            The path written.
        """
        import os

        if os.path.exists(path) and not overwrite:
            raise FileExistsError(f"{path!r} already exists. Set overwrite=True.")
        rtf = self.to_rtf(program=program)
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
            title_style=dict(self.title_style),
            footnote_style=dict(self.footnote_style),
            watermark=self.watermark,
            font_table=self.font_table,
        )


# -- functional layer ---------------------------------------------------------


def rtf_document(
    page: Page | None = None,
    default_format: DefaultFormat | None = None,
    color_table: list[str] | None = None,
    program: str | None = None,
    watermark=None,
    font_table=None,
) -> RtfDocument:
    """Create a new :class:`RtfDocument` (mirrors R's ``rtf_document()``).

    This is the head of the module-level "pipe" API
    (``rtf_document() -> rtf_tables() -> ... -> generate_rtfreport()``); the
    fluent :class:`RtfDocument` methods are an equivalent convenience.

    Args:
        program: The path of the program that writes the file, for the
            ``{PROGRAM}`` / ``{PROGRAM_NAME}`` / ``{PROGRAM_DIR}`` tokens.
            ``None`` falls back to the ``program`` option, then the script
            Python is running; :func:`generate_rtfreport` can also say it.
        watermark: A diagonal word behind the page body on every page: an
            :func:`~rtfreporter.rtf_watermark`, or a bare string
            (``"DRAFT"``) for the defaults.  A section can override it
            (:func:`rtf_section`), ``None`` there switching it off.
        font_table: The fonts to declare, first = the document default: a list
            of family names (or ``{"name": ...}`` dicts).  ``None`` declares
            ``default_format.font``.  A font an element asks for (a table's,
            a title's, a header's ``font=``) is added after these.
    """
    return RtfDocument(page=page, default_format=default_format,
                       color_table=color_table, program=program,
                       watermark=watermark, font_table=font_table)


def rtf_config(
    doc: RtfDocument,
    page=None,
    default_format=None,
    color_table=None,
    font_table=None,
    watermark=_NOT_GIVEN,
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
        watermark: A new watermark (an :func:`~rtfreporter.rtf_watermark` or a
            string); ``None`` / ``""`` removes it.  Not given: unchanged.
        font_table: A replacement font table (see :func:`rtf_document`).

    Returns:
        A new :class:`RtfDocument` (the pages and sections are carried over).
    """
    if not isinstance(doc, RtfDocument):
        raise TypeError("`doc` must be an RtfDocument.")
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

    out = RtfDocument(page=new_page, default_format=new_fmt, color_table=new_colors,
                      program=doc.program,
                      watermark=doc.watermark if watermark is _NOT_GIVEN else watermark,
                      font_table=doc.font_table if font_table is None else font_table)
    out._sections = list(doc._sections)
    out._pages = list(doc._pages)
    out.title_style = dict(doc.title_style)
    out.footnote_style = dict(doc.footnote_style)
    return out


#: Where the auto-appended section label sits in its header row.
_LABEL_SLOT = {"left": "l", "center": "c", "right": "r"}


def _auto_section_base(doc: RtfDocument) -> HeaderFooter | None:
    """The running header that every auto-section builds on.

    Captured **once**, before any auto-sections are added, so each section is
    the base plus its own label -- never the previous section's label as well.
    Corresponds to R's ``"_default"`` section entry.
    """
    for section in reversed(doc._sections):
        if section.get("header") is not None:
            return section["header"]
    return None


def _auto_section_header(
    base: HeaderFooter | None, label: str, label_align: str
) -> HeaderFooter:
    """``base`` plus one row carrying the section ``label``.

    Mirrors R's ``.build_auto_section_header()``: every section keeps the
    report's running header and gains its own heading row.  With no base the
    label becomes the whole header.
    """
    slot = _LABEL_SLOT.get(label_align)
    if slot is None:
        raise ValueError(
            '`section_label_align` must be "left", "center" or "right"; '
            f"got {label_align!r}."
        )
    label_row = {slot: label}
    if base is None:
        return HeaderFooter(rows=[label_row])
    return replace(base, rows=list(base.rows) + [label_row])


def _open_auto_section(doc: RtfDocument, header: HeaderFooter) -> RtfDocument:
    r"""Open an auto-section, superseding an empty one that starts on the page.

    R keeps the running header as a template rather than a section, so it emits
    exactly one section per named element.  Here the base header is a real
    section, and if no pages were added under it yet, it starts on the same page
    as the first auto-section and would never render -- only an extra
    ``\sectd``.  Replacing it keeps the emitted sections identical to R's.
    """
    new = doc.add_section(header=header)
    if len(new._sections) >= 2 and new._sections[-2]["from_page"] == new._sections[-1]["from_page"]:
        superseded = new._sections.pop(-2)
        # Keep an inherited footer that the dropped section carried.
        if new._sections[-1].get("footer") is None:
            new._sections[-1]["footer"] = superseded.get("footer")
    return new


def rtf_tables(
    doc: RtfDocument,
    tables,
    titles=None,
    footnotes=None,
    auto_section: bool = False,
    section_label_align: str = "left",
    auto_title: bool = False,
    title_label_align: str = "left",
    **table_kwargs,
) -> RtfDocument:
    """Add one or more table content pages to ``doc`` (mirrors R ``rtf_tables()``).

    Args:
        doc: The :class:`RtfDocument` to add to.
        tables: A single table input (an :class:`~rtfreporter.RtfTable`, dict of
            columns, or DataFrame) or a list/tuple of them (one page each).
        titles, footnotes: A parallel list (one per table) or a single block
            applied to every table.
        auto_section: When ``True``, a section opens where the page **name
            changes**; its header is the running header plus a row carrying the
            name.  A page name is a heading, so a run of pages sharing one (the
            pages of a group that outgrew ``max_rows``) is one section, and an
            unnamed page falls through into the section already in effect.
            Page names come from :func:`~rtfreporter.combine_sections` or from
            ``split="by_value"``.
        section_label_align: Where the auto-appended label sits --
            ``"left"`` (default), ``"center"`` or ``"right"``.
        auto_title: When ``True``, a named page's name is appended as the
            **last row of its title block**, just above the table; titles
            already there (from ``titles`` or carried by the table) are kept
            before it.  Composes with ``auto_section``.
        title_label_align: Alignment of that row (default ``"left"``).
        **table_kwargs: Forwarded to :func:`~rtfreporter.rtftable` for raw
            data.  For a pre-built :class:`~rtfreporter.RtfTable` (e.g. from
            :func:`~rtfreporter.as_rtftables`), the formatting arguments passed
            here (``font``, ``font_size_half_points``, ``row_height_twips``,
            ``border``, ``col_header``, widths, ...) override its own values;
            those left out keep them.

    Returns:
        A **new** document; ``doc`` is left unchanged (as in R).
    """
    if not isinstance(doc, RtfDocument):
        raise TypeError("`doc` must be an RtfDocument.")
    if auto_title and title_label_align not in ("left", "center", "right"):
        raise ValueError('`title_label_align` must be "left", "center", or "right".')
    items = _as_table_list(tables)
    n = len(items)
    tlist = _broadcast_blocks(titles, n)
    flist = _broadcast_blocks(footnotes, n)
    # A pre-built table takes the explicitly passed formatting arguments as
    # overrides (R .override_rtftable_fields()); raw data is built with them.
    from .table import override_rtftable_fields

    items = [override_rtftable_fields(t, table_kwargs) if isinstance(t, RtfTable) else t
             for t in items]
    out = doc
    base_header = _auto_section_base(doc) if auto_section else None
    open_label = None
    for i, tbl in enumerate(items):
        # auto_section: a section opens where the page NAME CHANGES, carrying
        # the running header plus a heading row.  A page name is a heading, so
        # consecutive pages that carry the same one are one section of several
        # pages (R #433); an unnamed page falls through into the section
        # already in effect.
        if auto_section:
            label = getattr(tbl, "name", None)
            if label and str(label) != open_label:
                open_label = str(label)
                out = _open_auto_section(
                    out, _auto_section_header(base_header, open_label, section_label_align)
                )
        title = tlist[i] if tlist is not None else None
        # auto_title: the page name as the LAST row of its title block, after
        # the titles given or carried by the table.
        label = getattr(tbl, "name", None)
        if auto_title and label:
            if title is None:
                title = getattr(tbl, "titles", None)
            rows = [] if title is None else ([title] if isinstance(title, str) else list(title))
            title = rows + [{"text": str(label), "align": title_label_align}]
        out = out.add_table(
            tbl,
            title=title,
            footnote=flist[i] if flist is not None else None,
            **table_kwargs,
        )
    return out if out is not doc else doc._copy()


def rtf_figures(
    doc: RtfDocument,
    figures,
    width_twips: int | None = None,
    height_twips: int | None = None,
    align: str = "center",
    titles=None,
    footnotes=None,
) -> RtfDocument:
    """Add one or more figure content pages to ``doc`` (mirrors R ``rtf_figures()``).

    Args:
        doc: The :class:`RtfDocument` to add to.
        figures: An image path (PNG / JPEG) or a :class:`~rtfreporter.Figure`,
            or a list of them; one page each.
        width_twips: Display width for the paths; ``None`` = the full writable
            width.
        height_twips: Display height for the paths; ``None`` = from the image's
            aspect ratio.
        align: ``"center"`` (default), ``"left"`` or ``"right"``, for the paths.
            A :class:`~rtfreporter.Figure` already built with
            :func:`~rtfreporter.rtfplot` keeps its own settings.
        titles, footnotes: One block per figure, or one common to all.
    """
    fig_kwargs = {"width_twips": width_twips, "height_twips": height_twips, "align": align}
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


def rtf_titles(
    doc: RtfDocument,
    titles,
    font_size_half_points: int | None = None,
    row_height_twips: int | None = None,
    markup=None,
    font: str | None = None,
    align: str | None = None,
) -> RtfDocument:
    """Assign per-page titles (mirrors R ``rtf_titles()``).

    ``titles`` is a list of one block per page, or a single block common to all.

    Args:
        font_size_half_points, row_height_twips, markup, align: Style for the
            title block, overriding the document default.  Anything left
            ``None`` is inherited.  A size given without a height recomputes
            the height from that size; an explicit height always wins.
            ``align`` sets the block's default row alignment; a per-row
            ``align`` still beats it.
        font: Font family for the block; declared in the font table as needed.
    """
    if not isinstance(doc, RtfDocument):
        raise TypeError("`doc` must be an RtfDocument.")
    n = len(doc._pages)
    if n == 0:
        raise ValueError("Cannot set titles before any content has been added.")
    blocks = _broadcast_blocks(titles, n, require_list=True)
    st = element_style(font_size_half_points, row_height_twips, markup, align,
                       verb="rtf_titles", font=font)
    new = doc.titles(blocks)
    if st:
        new.title_style = st
    return new


def rtf_footnotes(
    doc: RtfDocument,
    footnotes,
    font_size_half_points: int | None = None,
    row_height_twips: int | None = None,
    markup=None,
    font: str | None = None,
    align: str | None = None,
    border=None,
) -> RtfDocument:
    """Assign per-page footnotes (mirrors R ``rtf_footnotes()``).

    Same shape as :func:`rtf_titles`: a list with one block per page (or length
    1, common to all).  A block is a list of rows; a row is a single string, or
    a dict ``{"l": ..., "c": ..., "r": ...}`` giving up to three cells
    positioned left / centre / right -- the same row model
    :func:`~rtfreporter.rtf_footer` uses.  A bare string lands in whichever
    slot ``align`` selects.  ``None`` per element suppresses the footnote for
    that page.

    Args:
        border: ``None`` (default) for **no rule** -- unlike the page footer,
            the footnote draws none unless asked.  A
            :class:`~rtfreporter.Border` puts one on the first row, e.g.
            ``border=rtf_border(top=True)``.
        font_size_half_points, row_height_twips, markup, align: Style for the
            block, overriding the document default (see :func:`rtf_titles`).
        font: Font family for the block; declared in the font table as needed.
    """
    from .borders import Border

    if not isinstance(doc, RtfDocument):
        raise TypeError("`doc` must be an RtfDocument.")
    n = len(doc._pages)
    if n == 0:
        raise ValueError("Cannot set footnotes before any content has been added.")
    blocks = _broadcast_blocks(footnotes, n, require_list=True)
    st = element_style(
        font_size_half_points, row_height_twips, markup, align, verb="rtf_footnotes",
        font=font,
    )
    if border is not None:
        if not isinstance(border, Border):
            raise TypeError("`rtf_footnotes(border=)` must be None or an rtf_border() object.")
        st["border"] = border
    new = doc.footnotes(blocks)
    if st:
        new.footnote_style = st
    return new


def rtf_section(
    doc: RtfDocument,
    page: int | None = None,
    header=None,
    footer=None,
    watermark=_NOT_GIVEN,
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
        watermark: This section's watermark, overriding the document's (R
            ``secinfo$watermark``); ``None`` switches it off for this section.
            Not given: the document's.
    """
    if not isinstance(doc, RtfDocument):
        raise TypeError("`doc` must be an RtfDocument.")
    return doc.add_section(header=header, footer=footer, from_page=page,
                           watermark=watermark)


def generate_rtfreport(report: RtfDocument, file_path: str, overwrite: bool = False,
                       program: str | None = None) -> str:
    """Render ``report`` and write it to ``file_path`` (mirrors R ``generate_rtfreport()``).

    Args:
        report: The :class:`RtfDocument` to render.
        file_path: Destination ``.rtf`` path (required, as in R).
        overwrite: When ``False`` (the R default), raise if ``file_path`` exists.
        program: The program the run tokens name (``{PROGRAM}``,
            ``{PROGRAM_NAME}``, ``{PROGRAM_DIR}``); ``None`` uses the
            document's, then the ``program`` option, then the running script.
            ``{DATETIME}`` is the time of this call (or the ``render_time``
            option), the same on every page.

    Returns:
        The path written.
    """
    if not isinstance(report, RtfDocument):
        raise TypeError("`report` must be an RtfDocument.")
    return report.save(file_path, overwrite=overwrite, program=program)


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
    # A section that names a watermark (None included) wins over the
    # document's; the others take the document's.

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
            **({"watermark": sections[i]["watermark"]} if "watermark" in sections[i] else {}),
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

    # Fonts: the declared table plus any an element asked for (R #293).
    doc_fonts = _collect_fonts(report)
    font_index_map = {name: i for i, name in enumerate(doc_fonts)}

    orientation_cmd = r"\landscape" if geo["orientation"] == "landscape" else ""
    lines: list[str] = [
        C.RTF_HEADER_OPEN,
        "{\\fonttbl" + "".join(
            f"{{\\f{i}\\fnil\\fcharset0 {_esc(name)};}}" for i, name in enumerate(doc_fonts)
        ) + "}",
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

        # The watermark rides in the header group, so it is resolved per
        # section: one the section names wins, else the document's.
        from .watermark import render_watermark_rtf

        watermark_rtf = render_watermark_rtf(
            rs["watermark"] if "watermark" in rs else report.watermark,
            geo["width_twips"], geo["height_twips"], default_font=fmt.font)

        def emit_preamble(pg_for_hf, cur_header=None, cur_footer=None,
                          watermark_rtf=watermark_rtf):
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
                doc_pad_l=doc_pad_l, doc_pad_r=doc_pad_r, doc_markup=doc_markup,
                font_index_map=font_index_map)
            footer_rtf = R.render_header_footer(
                cur_footer, writable, is_footer=True, current_page=pg_for_hf,
                total_pages=total_pages, color_index_map=color_index_map,
                font_half_points=fhp, doc_row_height=doc_row_height,
                doc_pad_l=doc_pad_l, doc_pad_r=doc_pad_r, doc_markup=doc_markup,
                font_index_map=font_index_map)
            # The watermark goes in even when there is no header text; then the
            # header group carries the shape and nothing else.
            if header_rtf or watermark_rtf:
                lines.append(C.HEADER_WRAPPER.format(
                    content=watermark_rtf + fs_cmd + "".join(header_rtf)))
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
            # Per-element width (#291): "content" (the default -- follow the
            # body), "page", a fraction of the writable width, or twips.
            title_st = report.title_style
            footnote_st = report.footnote_style
            title_w = resolve_block_width(fmt.title_width, content_w, writable)
            footnote_w = resolve_block_width(fmt.footnote_width, content_w, writable)

            # Title.
            if title_format == "text":
                lines.extend(R.render_text_block_text(
                    page.get("title"), is_footer=False, color_index_map=color_index_map,
                    markup=doc_markup, pad_l=doc_pad_l, pad_r=doc_pad_r,
                    style=title_st, font_half_points=fhp,
                    current_page=p_idx, total_pages=total_pages,
                    font_index_map=font_index_map))
            else:
                lines.extend(R.render_text_block_table(
                    page.get("title"), title_w, False, fhp, doc_pad_l, doc_pad_r,
                    tf_valign, calign, color_index_map, doc_row_height, doc_markup,
                    style=title_st, current_page=p_idx, total_pages=total_pages,
                    font_index_map=font_index_map))

            # Content.
            if isinstance(ct, RtfTable):
                lines.extend(R.render_rtftable(
                    ct, writable, fhp, color_index_map,
                    doc_row_height=doc_row_height, doc_pad_l=doc_pad_l,
                    doc_pad_r=doc_pad_r, doc_markup=doc_markup,
                    font_index_map=font_index_map))
            elif isinstance(ct, Figure):
                lines.append(R.render_rtfplot(ct, writable))

            # Footnote: the page footer's mechanism, as a table of its own
            # (#296).  footnote_format = "text" switches to plain paragraphs.
            if footnote_format == "text":
                lines.extend(R.render_text_block_text(
                    footnote_rows(page.get("footnote"), footnote_st.get("align", "left"), "text"),
                    is_footer=True, color_index_map=color_index_map,
                    markup=doc_markup, pad_l=doc_pad_l, pad_r=doc_pad_r,
                    style=footnote_st, font_half_points=fhp,
                    current_page=p_idx, total_pages=total_pages,
                    font_index_map=font_index_map))
            else:
                fn_rtf = R.render_header_footer(
                    footnote_hf(page.get("footnote"), footnote_st, footnote_w),
                    footnote_w, is_footer=True, current_page=p_idx,
                    total_pages=total_pages, color_index_map=color_index_map,
                    font_half_points=fhp, doc_row_height=doc_row_height,
                    doc_pad_l=doc_pad_l, doc_pad_r=doc_pad_r, doc_markup=doc_markup,
                    font_index_map=font_index_map)
                # An INDEPENDENT table: RTF merges consecutive \trowd runs that
                # no paragraph separates, so without this the footnote would
                # still be the body table wearing different \cellx values --
                # and could not carry a width of its own.  \fs2 keeps the
                # separating paragraph from adding visible space.
                if fn_rtf:
                    lines.append(r"{\pard\fs2\par}")
                    lines.extend(fn_rtf)

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
