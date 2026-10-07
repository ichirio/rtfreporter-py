"""Assemble several rendered RTF files into one deliverable with a TOC.

Ported from ``R/assemble_rtf.R`` and ``R/assemble_spec.R``.  Concatenates
RTF files produced by :func:`~rtfreporter.generate_rtfreport` into a single
document -- the font / colour tables and page setup come from the **first**
input -- optionally prefixed by a cover page and a clickable Table of Contents
with per-file bookmarks and ``PAGEREF`` page numbers.

The document header (fonts, colours, geometry) is taken from file 1; each input
becomes one or more ``\\sect`` sections of the output.

.. note::
   The ``toc="auto"`` title extraction parses the **rendered title format**
   (the first centred-bold paragraph of a page), so :func:`_extract_first_title`
   is kept in sync with how :mod:`rtfreporter.render` emits a title block
   (``\\pard\\qc\\li0\\ri0 \\b TITLE\\b0 \\par``).
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass

# -- TOC entry constructors ---------------------------------------------------


@dataclass
class TocHeading:
    """A TOC section heading (no link, no page number)."""

    label: str
    level: int = 1


@dataclass
class TocEntry:
    """A clickable TOC entry pointing at one input file."""

    label: str
    file: object = None
    level: int = 2


def _deprecated(key: str, msg: str) -> None:
    from .borders import _deprecate_once

    _deprecate_once(key, msg + "\n  Removed in 0.9.0.")


_TOC_TABLE_MSG = ("give `assemble_rtf(toc=)` a table (rows with the keys file, label, "
                  "heading, level).")


def toc_heading(label: str, level: int = 1) -> TocHeading:
    """Build a :class:`TocHeading` for :func:`assemble_rtf`'s ``toc`` list (deprecated).

    **Deprecated** (warns once a session, still works; removed in 0.9.0, as in
    R): give :func:`assemble_rtf` the table of contents as a table -- a row
    whose ``heading`` is filled starts a heading.
    """
    _deprecated("toc_heading", "`toc_heading()` is deprecated: " + _TOC_TABLE_MSG)
    return _toc_heading(label, level)


def _toc_heading(label: str, level: int = 1) -> TocHeading:
    return TocHeading(label=str(label), level=int(level))


def toc_entry(label: str, file=None, level: int = 2) -> TocEntry:
    """Build a :class:`TocEntry` pointing at one of ``input_files`` (deprecated).

    **Deprecated** (warns once a session, still works; removed in 0.9.0, as in
    R): give :func:`assemble_rtf` the table of contents as a table -- one row
    per file (``file``, ``label``, ``level``).

    Args:
        label: The entry text.
        file: A path in ``input_files``, a 0-based index into it, or ``None``
            (consume the next unused file in order).
        level: Indent depth (1 = flush left, 2 = small indent, ...).
    """
    _deprecated("toc_entry", "`toc_entry()` is deprecated: " + _TOC_TABLE_MSG)
    return _toc_entry(label, file, level)


def _toc_entry(label: str, file=None, level: int = 2) -> TocEntry:
    return TocEntry(label=str(label), file=file, level=int(level))


# -- RTF post-processing helpers ---------------------------------------------


def _rtf_drop_close(lines: list[str]) -> list[str]:
    """Strip the closing RTF ``}`` (and trailing blank lines) from ``lines``."""
    n = len(lines)
    while n > 0 and not lines[n - 1].strip():
        n -= 1
    if n > 0 and lines[n - 1].strip() == "}":
        return lines[: n - 1] + lines[n:]
    return lines


def _rtf_extract_section_content(lines: list[str]) -> list[str]:
    """Lines from the first ``\\sectd`` (inclusive) with the closing ``}`` removed."""
    for i, ln in enumerate(lines):
        if ln.strip() == "\\sectd":
            return _rtf_drop_close(lines[i:])
    raise ValueError(
        "No \\sectd found in RTF file. Only rtfreporter-generated files are supported."
    )


def _sanitize_bookmark(x: str) -> str:
    """Sanitise a string into a valid RTF bookmark name."""
    s = re.sub(r"\.rtf$", "", os.path.basename(str(x)), flags=re.IGNORECASE)
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    s = re.sub(r"_+", "_", s)
    s = re.sub(r"^_|_$", "", s)
    s = s[:32]
    return s if re.match(r"^[A-Za-z]", s) else f"bk_{s}"


_PREAMBLE_RE = re.compile(
    r"^\\(sbkpage|pgwsxn|pghsxn|marglsxn|margrsxn|margtsxn|margbsxn|lndscpsxn|"
    r"pgnrestart|pgndec|pgnlcrm|headery|footery)"
)


def _insert_bookmark(content: list[str], bookmark_name: str,
                     outline_label: str | None = None, outline_level: int = 0) -> list[str]:
    """Inject a bookmark (and optional invisible outline label) into a section."""
    sectd_idx = next((i for i, ln in enumerate(content) if ln.strip() == "\\sectd"), None)
    if sectd_idx is None:
        return content
    insert_after = sectd_idx
    i = sectd_idx + 1
    while i < len(content):
        line = content[i].strip()
        is_preamble = (
            _PREAMBLE_RE.match(line)
            or line.startswith("{\\header")
            or line.startswith("{\\footer")
        )
        if not is_preamble:
            break
        insert_after = i
        i += 1

    inserts = [f"{{\\*\\bkmkstart {bookmark_name}}}{{\\*\\bkmkend {bookmark_name}}}"]
    if outline_label:
        inserts.append(
            f"{{\\pard\\plain\\cf2\\fs2\\sl1\\slmult0\\sa0\\sb0"
            f"\\outlinelevel{int(outline_level)} {_toc_escape(outline_label)}\\par}}"
        )
    return content[: insert_after + 1] + inserts + content[insert_after + 1 :]


_PAGE_BREAK_RE = re.compile(r"\\page(?![a-zA-Z])")


def _count_rtf_pages(lines: list[str]) -> int:
    """Count the rendered pages of an RTF file's lines.

    Two things start a new page, and a file mixes them: ``\\sbkpage`` (a
    section break; one per ``rtf_section``, NOT one per rendered page) and
    ``\\page`` (a plain break between the sub-pages inside one section).  So
    the count is one page for the first section, plus one per further section
    start, plus one per in-section break.  Counting ``\\sbkpage`` alone
    reported 1 for any single-section file however long (#401).

    ``\\page`` is matched only when the control word ends there, so
    ``\\pagebb`` and friends cannot be mistaken for a break.
    """
    txt = "\n".join(lines)
    sections = txt.count("\\sbkpage")
    breaks = len(_PAGE_BREAK_RE.findall(txt))
    if sections == 0 and breaks == 0:
        return 0
    return max(sections, 1) + breaks


_NUMPAGES_CACHE_RE = re.compile(r"(\{\\field\{\\\*\\fldinst NUMPAGES\}\{\\fldrslt )[^{}]*(\}\})")


def _retotal_numpages(lines: list[str], total_pages: int | None) -> list[str]:
    """Point every NUMPAGES cache at the assembled document's page count (#415).

    ``{AUTO_TOTAL_PAGES}`` bakes the count of the document being written, so
    each input arrives claiming its own old total while sitting in a book of a
    different length.  Word recalculates header/footer fields during layout
    and so shows the right number anyway; what this fixes is the file as
    written -- for readers that display the cached result, for anything that
    parses rather than renders, and for a body-placed total.  Only the cached
    RESULT is rewritten; the field instruction is untouched.
    """
    if total_pages is None:
        return lines
    repl = r"\g<1>" + str(int(total_pages)) + r"\g<2>"
    return [_NUMPAGES_CACHE_RE.sub(repl, ln) for ln in lines]


def _insert_pgnrestart(content: list[str]) -> list[str]:
    """Insert ``\\pgnrestart\\pgndec`` right after the first ``\\sectd``."""
    sectd_idx = next((i for i, ln in enumerate(content) if ln.strip() == "\\sectd"), None)
    if sectd_idx is None:
        return content
    return content[: sectd_idx + 1] + ["\\pgnrestart\\pgndec"] + content[sectd_idx + 1 :]


def _toc_escape(x) -> str:
    """RTF-escape plain text (no markup, no token replacement)."""
    if x is None:
        return ""
    out = []
    for ch in str(x):
        cp = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == "{":
            out.append("\\{")
        elif ch == "}":
            out.append("\\}")
        elif cp > 127:
            out.append(f"\\u{cp}?")
        else:
            out.append(ch)
    return "".join(out)


_TITLE_RE = re.compile(r"\\qc\\li[0-9]+\\ri[0-9]+\s+\\b\s+(.+?)\\b0")


def _rtf_unescape(text: str) -> str:
    """Reverse the RTF escaping applied to a title cell."""
    # \uNNNN? -> the character; then the literal brace / backslash escapes.
    def _u(m):
        cp = int(m.group(1))
        return " " if cp == 160 else chr(((cp % 65536) + 65536) % 65536)

    text = re.sub(r"\\u(-?[0-9]+)\?", _u, text)
    text = text.replace("\\{", "{").replace("\\}", "}").replace("\\\\", "\\")
    return text.strip()


def _title_cells(lines: list[str]) -> list[str]:
    """Every centred-bold title cell before the first body table row / figure.

    The running header/footer bands are themselves rendered as ``{\\header ...}``
    / ``{\\footer ...}`` table lines, so they are skipped; scanning stops at the
    first body table row (a line beginning with ``\\trowd``) or a figure.
    """
    out: list[str] = []
    for ln in lines[:200]:
        s = ln.strip()
        if s.startswith("{\\header") or s.startswith("{\\footer"):
            continue
        if s.startswith("\\trowd") or "\\pict" in ln:
            break
        m = _TITLE_RE.search(ln)
        if m and m.group(1).strip():
            out.append(_rtf_unescape(m.group(1)))
    return out


def _extract_first_title(lines: list[str]) -> str | None:
    """The first centred-bold title of a rendered page (or ``None``)."""
    cells = _title_cells(lines)
    return cells[0] if cells else None


# -- TOC normalisation --------------------------------------------------------


def _read_lines(path: str) -> list[str]:
    """The file's lines as R's ``readLines()`` gives them: the newline that
    ends the last line does not start another, empty one."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    lines = text.split("\n")
    if text.endswith("\n"):
        lines.pop()
    return lines


def _normalize_toc(toc, input_files: list[str]) -> list[dict] | None:
    """Normalise ``toc`` into a uniform list of entry dicts."""
    if toc is None:
        return None

    # A table of contents as a table (file, label, heading, level)
    if _is_toc_table(toc):
        toc = _spec_to_toc(toc)

    if isinstance(toc, str) and toc == "auto":
        out = []
        for i, f in enumerate(input_files):
            ttl = _extract_first_title(_read_lines(f))
            if not ttl:
                ttl = re.sub(r"\.rtf$", "", os.path.basename(f), flags=re.IGNORECASE)
            out.append({"label": ttl, "level": 1, "file_idx": i, "type": "entry"})
        return out

    if isinstance(toc, (list, tuple)) and toc and all(isinstance(t, str) for t in toc):
        if len(toc) != len(input_files):
            raise ValueError("`toc` must be the same length as `input_files`.")
        return [
            {"label": t, "level": 1, "file_idx": i, "type": "entry"}
            for i, t in enumerate(toc)
        ]

    if isinstance(toc, (list, tuple)):
        used: list[int] = []

        def next_free():
            for j in range(len(input_files)):
                if j not in used:
                    return j
            return None

        out = []
        for e in toc:
            if isinstance(e, TocHeading):
                out.append({"label": e.label, "level": e.level,
                            "file_idx": None, "type": "heading"})
            elif isinstance(e, TocEntry):
                if e.file is None:
                    fi = next_free()
                elif isinstance(e.file, int):
                    fi = e.file
                elif isinstance(e.file, str):
                    try:
                        fi = input_files.index(e.file)
                    except ValueError:
                        raise ValueError(
                            f"toc_entry: file '{e.file}' is not in `input_files`."
                        ) from None
                else:
                    raise TypeError("toc_entry: `file` must be a path or integer index.")
                if fi is None or fi < 0 or fi >= len(input_files):
                    raise ValueError("toc_entry: file index out of range.")
                used.append(fi)
                out.append({"label": e.label, "level": e.level,
                            "file_idx": fi, "type": "entry"})
            else:
                raise TypeError("Each `toc` element must be toc_heading() or toc_entry().")
        return out

    raise TypeError(
        '`toc` must be None, "auto", a list of labels, a table (rows with the keys '
        "file, label, heading, level) or the path of one (.csv)."
    )


# -- Cover / TOC rendering ----------------------------------------------------


def _build_cover_section(cover: dict) -> list[str]:
    blocks = [
        "\\sectd\\sbkpage\\lndscpsxn",
        "\\pgwsxn15840\\pghsxn12240",
        "\\marglsxn864\\margrsxn864\\margtsxn1296\\margbsxn1296",
        "{\\pard\\fs18\\par}{\\pard\\fs18\\par}{\\pard\\fs18\\par}",
    ]
    if cover.get("title"):
        blocks += [f"{{\\pard\\qc\\b\\fs44 {_toc_escape(cover['title'])}\\par}}",
                   "{\\pard\\fs18\\par}"]
    if cover.get("subtitle"):
        blocks += [f"{{\\pard\\qc\\fs28 {_toc_escape(cover['subtitle'])}\\par}}",
                   "{\\pard\\fs18\\par}"]
    if cover.get("date"):
        blocks.append(f"{{\\pard\\qc\\fs22 {_toc_escape(cover['date'])}\\par}}")
    if cover.get("version"):
        blocks.append(f"{{\\pard\\qc\\fs22 {_toc_escape(cover['version'])}\\par}}")
    meta = cover.get("meta")
    if meta:
        blocks.append("{\\pard\\fs18\\par}")
        for line in meta:
            blocks.append(f"{{\\pard\\qc\\fs20 {_toc_escape(line)}\\par}}")
    return blocks


def _toc_indent_for_level(level: int) -> int:
    return 600 * (max(1, int(level)) - 1)


def _build_toc_section(toc_entries, bookmarks, toc_title, toc_leader="dot",
                       page_numbering="none", entry_pages=None) -> list[str]:
    leader_cmd = "\\tldot" if toc_leader == "dot" else ""
    tab_pos = 14400
    pg_cmd = {"roman": "\\pgnrestart\\pgnlcrm", "decimal": "\\pgnrestart\\pgndec",
              "none": ""}[page_numbering]
    lines = [
        f"\\sectd\\sbkpage\\lndscpsxn{pg_cmd}",
        "\\pgwsxn15840\\pghsxn12240",
        "\\marglsxn864\\margrsxn864\\margtsxn1296\\margbsxn1296",
        f"{{\\pard\\qc\\b\\fs28 {_toc_escape(toc_title)}\\par}}",
        "{\\pard\\fs18\\par}",
    ]
    for e in toc_entries:
        indent = _toc_indent_for_level(e["level"])
        indent_cmd = f"\\li{indent}" if indent > 0 else ""
        if e["type"] == "heading":
            lines.append(f"{{\\pard{indent_cmd}\\b\\fs22 {_toc_escape(e['label'])}\\par}}")
            continue
        bm = bookmarks[e["file_idx"]]
        txt = _toc_escape(e["label"])
        pg = 1
        if entry_pages is not None and e["file_idx"] < len(entry_pages):
            pg = int(entry_pages[e["file_idx"]])
        lines.append(
            f"{{\\pard{indent_cmd}\\fs20\\tqr{leader_cmd}\\tx{tab_pos} "
            f'{{\\field{{\\*\\fldinst HYPERLINK \\\\l "{bm}"}}'
            f"{{\\fldrslt {txt}}}}}"
            f"\\tab"
            f"{{\\field{{\\*\\fldinst PAGEREF {bm} \\\\h}}"
            f"{{\\fldrslt {pg}}}}}"
            f"\\par}}"
        )
    return lines


# -- assemble_rtf() -----------------------------------------------------------


def _fill_book_page_slots(lines, book_page, total_pages):
    """Fill every ``{BOOK_PAGE}`` slot with the compiled document's page number
    (R ``.fill_book_page_slots()``, #413)."""
    import re

    from . import _commands as C
    from ._escape import render_tokens

    book_page = str(book_page)
    if re.search(r"(?:^|[^A-Z_])\{(PAGE|TOTAL_PAGES)\}", book_page):
        raise ValueError(
            "`book_page` cannot use the static `{PAGE}` / `{TOTAL_PAGES}` tokens: "
            "the slot sits in one band shared by every page of a section, so a "
            "single substitution cannot give each page its own number.\n"
            "  Use `{AUTO_PAGE}` / `{AUTO_TOTAL_PAGES}`, which the reader "
            "resolves per page."
        )
    filled = render_tokens(book_page, current_page=None, total_pages=total_pages)
    return [line.replace(C.BOOK_PAGE_SLOT, filled) for line in lines]


def assemble_rtf(input_files=None, output_file=None, overwrite: bool = False,
                 cover: dict | None = None, toc=None,
                 toc_title: str = "Table of Contents", toc_leader: str = "dot",
                 toc_page_numbering: str = "none",
                 bookmark_prefix: str = "tfl_", book_page: str | None = None) -> str:
    """Assemble several rendered RTF files into one deliverable.

    Args:
        input_files: Paths to at least two RTF files (from
            :func:`~rtfreporter.generate_rtfreport`).  May be left out when
            ``toc`` is a table (or its path): the table's ``file`` column, in
            its order.
        output_file: Destination path for the assembled RTF (required).
        overwrite: When ``False`` (default), raise if ``output_file`` exists.
        cover: Optional cover-page dict (``title`` / ``subtitle`` / ``date`` /
            ``version`` / ``meta``).
        toc: ``None`` (no TOC), ``"auto"`` (extract each file's title), a list of
            one label per file, or -- for multi-level (chapter / table)
            layouts -- a **table**: one row per file, in order, as a list of
            dicts or a pandas / polars DataFrame, with ``file`` (the path),
            ``label`` (the entry text) and optionally ``heading`` (a heading
            printed above the row's entry whenever it changes; ``None`` =
            none), ``level`` (the entry's indent, default 2) and ``order``.
            :func:`assemble_folder` makes one from a folder, ready to edit.
            The path of such a table (a ``.csv``, e.g. the one
            ``assemble_folder(spec_file=)`` wrote) works too.  A list of
            :func:`toc_heading` / :func:`toc_entry` is the older spelling
            (deprecated).
        toc_title: Centred title on the TOC page.
        toc_leader: ``"dot"`` (dotted leader) or ``"none"``.
        toc_page_numbering: ``"none"`` (default) / ``"roman"`` / ``"decimal"``.
        bookmark_prefix: Prefix for auto-generated bookmark names.
        book_page: Text for the compiled document's page number, put into every
            ``{BOOK_PAGE}`` slot the inputs reserved (R #413); ``None`` leaves
            the slots empty.  A deliverable bound into a book needs two page
            numbers, its own and the book's; it reserves the position with
            ``{BOOK_PAGE}`` in any band and renders it empty, and this fills it
            -- e.g. ``"Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"``, where the
            total is the book's.  The static ``{PAGE}`` / ``{TOTAL_PAGES}``
            cannot be used: one band serves every page of a section.

    Returns:
        ``output_file``.
    """
    # A table of contents given as a table, or as the path of one: its rows in
    # `order`, and its files when `input_files` is left out.
    if isinstance(toc, str) and re.search(r"[.](xlsx|csv)$", toc, re.IGNORECASE):
        toc = _read_spec(toc)
    if _is_toc_table(toc):
        toc = _check_toc_table(toc)
        if input_files is None:
            input_files = [r["file"] for r in toc]
    if output_file is None:
        raise TypeError("assemble_rtf() needs `output_file`.")
    if toc_leader not in ("dot", "none"):
        raise ValueError('`toc_leader` must be "dot" or "none".')
    if toc_page_numbering not in ("none", "roman", "decimal"):
        raise ValueError('`toc_page_numbering` must be "none", "roman", or "decimal".')
    input_files = list(input_files) if input_files is not None else []
    if len(input_files) < 2:
        raise ValueError("`input_files` must have at least 2 elements.")
    for f in input_files:
        if not os.path.exists(f):
            raise FileNotFoundError(f"Input file not found: {f}")
    if os.path.exists(output_file) and not overwrite:
        raise FileExistsError("`output_file` already exists. Set overwrite=True.")

    toc_entries = _normalize_toc(toc, input_files)
    use_toc = toc_entries is not None
    use_cover = cover is not None

    bookmarks = [""] * len(input_files)
    file_outline_labels: list[str | None] = [None] * len(input_files)
    entry_pages = None
    if use_toc:
        bookmarks = [bookmark_prefix + _sanitize_bookmark(f) for f in input_files]
        # De-duplicate collisions by suffixing "_1", "_2", ...
        counts: dict[str, int] = {}
        for b in bookmarks:
            counts[b] = counts.get(b, 0) + 1
        for b, c in counts.items():
            if c > 1:
                idxs = [i for i, x in enumerate(bookmarks) if x == b]
                for k, i in enumerate(idxs, start=1):
                    bookmarks[i] = f"{b}_{k}"
        for e in toc_entries:
            if e["type"] == "entry" and e["file_idx"] is not None:
                if file_outline_labels[e["file_idx"]] is None:
                    file_outline_labels[e["file_idx"]] = e["label"]
        for i in range(len(file_outline_labels)):
            if file_outline_labels[i] is None:
                file_outline_labels[i] = re.sub(
                    r"\.rtf$", "", os.path.basename(input_files[i]), flags=re.IGNORECASE
                )

        npages = [_count_rtf_pages(_read_lines(f)) for f in input_files]
        if toc_page_numbering == "roman":
            front = 0
        else:
            front = (1 if use_cover else 0) + 1
        entry_pages = []
        cum = 0
        for k in range(len(input_files)):
            entry_pages.append(front + 1 + cum)
            cum += npages[k]

    # File 1: keep everything but the closing brace.
    body = _rtf_drop_close(_read_lines(input_files[0]))

    if use_toc or use_cover:
        sectd_idx = next((i for i, ln in enumerate(body) if ln.strip() == "\\sectd"), None)
        if sectd_idx is None:
            raise ValueError("File 1 has no \\sectd; cannot insert cover / TOC.")
        head_lines = body[:sectd_idx]
        tail_lines = body[sectd_idx:]

        front_matter: list[str] = []
        if use_cover:
            front_matter += _build_cover_section(cover)
        if use_toc:
            if front_matter:
                front_matter.append("\\sect")
            front_matter += _build_toc_section(
                toc_entries, bookmarks, toc_title, toc_leader=toc_leader,
                page_numbering=toc_page_numbering, entry_pages=entry_pages,
            )
        if use_toc and toc_page_numbering == "roman":
            tail_lines = _insert_pgnrestart(tail_lines)
        if use_toc:
            tail_lines = _insert_bookmark(tail_lines, bookmarks[0],
                                          outline_label=file_outline_labels[0])
        body = head_lines + front_matter + ["\\sect"] + tail_lines

    # Files 2..N.
    for i in range(1, len(input_files)):
        content = _rtf_extract_section_content(_read_lines(input_files[i]))
        if use_toc:
            content = _insert_bookmark(content, bookmarks[i],
                                       outline_label=file_outline_labels[i])
        body = body + ["\\sect"] + content

    # The assembled document's own page count, known only here.  Front matter
    # counts: a cover is one page, the TOC one more.  Then make every NUMPAGES
    # cache -- the inputs' own included -- agree with the book it now sits in.
    body_pages = sum(_count_rtf_pages(_read_lines(f)) for f in input_files)
    front_pages = (1 if use_cover else 0) + (1 if use_toc else 0)
    book_pages = body_pages + front_pages
    if book_page is not None:
        body = _fill_book_page_slots(body, book_page, book_pages)
    body = _retotal_numpages(body, book_pages)

    body = body + ["}"]
    with open(output_file, "w", encoding="utf-8") as fh:
        # As R's writeLines(): every line, the last included, ends in a newline.
        fh.write("\n".join(body) + "\n")
    return output_file


# -- Spec / folder helpers ----------------------------------------------------


def _natural_order(strings: list[str]) -> list[int]:
    """Indices ordering ``strings`` so embedded numbers sort numerically."""
    def key(s):
        parts = re.findall(r"[0-9]+|[^0-9]+", s)
        return "".join(f"{int(p):015d}" if p.isdigit() else p for p in parts)

    return sorted(range(len(strings)), key=lambda i: key(strings[i]))


def assemble_files(dir, pattern: str = r"\.rtf$", recursive: bool = False,
                   sort: bool = True) -> list[str]:
    """List the ``.rtf`` files in ``dir`` (natural-sorted by default; deprecated).

    **Deprecated** (warns once a session, still works; removed in 0.9.0, as in
    R): :func:`assemble_folder` gives the folder's table of contents (its
    ``file`` column).
    """
    _deprecated("assemble_files",
                "`assemble_files()` is deprecated: `assemble_folder(dir)` gives the "
                "folder's table of contents (its `file` column).")
    return _assemble_files(dir, pattern, recursive, sort)


def _assemble_files(dir, pattern: str = r"\.rtf$", recursive: bool = False,
                    sort: bool = True) -> list[str]:
    if not os.path.isdir(dir):
        raise FileNotFoundError(f"Directory not found: {dir}")
    rx = re.compile(pattern, re.IGNORECASE)
    files = []
    if recursive:
        for root, _dirs, names in os.walk(dir):
            files += [os.path.join(root, n) for n in names if rx.search(n)]
    else:
        files = [os.path.join(dir, n) for n in sorted(os.listdir(dir)) if rx.search(n)]
    if sort and files:
        order = _natural_order([os.path.basename(f) for f in files])
        files = [files[i] for i in order]
    return files


def _rtf_table_label(file: str) -> dict:
    """Read a file's TOC label from its rendered title block (Python adaptation)."""
    cells = _title_cells(_read_lines(file))
    tabnum = None
    title = None
    title_inline = None
    for c in cells:
        m = re.match(r"^Table\s+([0-9][0-9.A-Za-z-]*)\b\s*(.*)$", c)
        if m and m.group(1):
            tabnum = m.group(1)
            title_inline = m.group(2).strip()
            break
    cand = [c for c in cells if not c.startswith("Table ")
            and not re.match(r"^<.*>$", c) and c]
    if cand:
        title = max(cand, key=len)
    if tabnum is not None and title_inline and title is None:
        title = title_inline
    base = re.sub(r"\.rtf$", "", os.path.basename(file), flags=re.IGNORECASE)
    if tabnum is not None:
        label = ("Table " + tabnum + (f"  {title}" if title else "")).strip()
    elif title:
        label = title
    else:
        label = base
    return {"file": file, "table": tabnum, "title": title, "label": label}


def assemble_spec(dir=None, files=None, recursive: bool = False) -> list[dict]:
    """Build an editable assembly spec (one dict per RTF file; deprecated).

    **Deprecated** (warns once a session, still works; removed in 0.9.0, as in
    R): it is :func:`assemble_folder` without an ``output_file``.
    """
    _deprecated("assemble_spec",
                "`assemble_spec()` is deprecated: it is `assemble_folder(dir)` "
                "(no `output_file`).")
    return _assemble_spec(dir, files, recursive)


def _assemble_spec(dir=None, files=None, recursive: bool = False) -> list[dict]:
    if files is None:
        if dir is None:
            raise ValueError("Supply `dir` or `files`.")
        files = _assemble_files(dir, recursive=recursive)
    files = list(files)
    if len(files) == 0:
        raise ValueError("No RTF files found.")
    info = [_rtf_table_label(f) for f in files]
    tabs = [x["table"] for x in info]
    sort_keys = [t if t is not None else "~" + os.path.basename(f)
                 for t, f in zip(tabs, files, strict=True)]
    order = _natural_order(sort_keys)
    info = [info[i] for i in order]
    files = [files[i] for i in order]
    spec = []
    for k, (f, inf) in enumerate(zip(files, info, strict=True)):
        spec.append({
            "order": k + 1,
            "file": f,
            "table": inf["table"],
            "heading": None,
            "label": inf["label"],
            "level": 2,
            "pages": _count_rtf_pages(_read_lines(f)),
        })
    return spec


def _na(v) -> bool:
    """A missing cell: ``None``, a float NaN (pandas) or an empty string (csv)."""
    return v is None or (isinstance(v, float) and v != v) or v == ""


def _is_toc_table(toc) -> bool:
    """A table of contents given as a table: a list of row dicts, or a
    pandas / polars DataFrame."""
    if hasattr(toc, "columns") and not isinstance(toc, (list, tuple, dict, str)):
        return True
    return isinstance(toc, (list, tuple)) and bool(toc) and all(isinstance(r, dict) for r in toc)


def _check_toc_table(spec) -> list[dict]:
    """A table of contents given as a table: rows as dicts, the keys it needs,
    its rows in ``order`` when it has one, and its files present."""
    if not isinstance(spec, (list, tuple)):
        from .pagination import as_frame

        frame = as_frame(spec)
        spec = [dict(zip(frame.column_names, r, strict=True)) for r in frame.rows]
    rows = [dict(r) for r in spec]
    if not rows or not all("file" in r and "label" in r for r in rows):
        raise ValueError(
            "A table of contents needs the columns `file` and `label` (and "
            "optionally `heading`, `level`, `order`; see assemble_folder())."
        )
    if all(not _na(r.get("order")) for r in rows):
        rows = sorted(rows, key=lambda r: r["order"])
    for r in rows:
        r["file"] = str(r["file"])
        r["label"] = str(r["label"])
        r["heading"] = None if _na(r.get("heading")) else str(r["heading"])
    missing = [r["file"] for r in rows if not os.path.exists(r["file"])]
    if missing:
        raise FileNotFoundError(
            "The table of contents names missing file(s): " + ", ".join(missing)
        )
    return rows


def _spec_to_toc(spec) -> list:
    """Convert an assembly spec (a table of contents) into a ``toc=`` list.
    A new heading is emitted whenever the ``heading`` value changes."""
    toc: list = []
    last_heading = None
    for row in _check_toc_table(spec):
        h = row.get("heading")
        if h and h.strip() and h != last_heading:
            toc.append(_toc_heading(h.strip(), level=1))
            last_heading = h
        lvl = 2 if _na(row.get("level")) else int(row["level"])
        toc.append(_toc_entry(row["label"], file=row["file"], level=lvl))
    return toc


def assemble_toc(files=None, spec=None, **kwargs) -> list:
    """Build a ``toc=`` list from ``files`` or a ``spec`` (deprecated).

    **Deprecated** (warns once a session, still works; removed in 0.9.0, as in
    R): give :func:`assemble_rtf` the table of contents itself
    (``toc=`` the table from :func:`assemble_folder`).
    """
    _deprecated("assemble_toc",
                "`assemble_toc()` is deprecated: give `assemble_rtf(toc=)` the table "
                "of contents (from `assemble_folder()`).")
    if spec is None:
        if files is None:
            raise ValueError("Supply `files` or `spec`.")
        spec = _assemble_spec(files=files, **kwargs)
    return _spec_to_toc(spec)


_SPEC_FIELDS = ("order", "file", "table", "heading", "label", "level", "pages")


def _write_spec(spec: list[dict], path: str) -> str:
    if not path.lower().endswith(".csv"):
        raise ValueError("`spec_file` must end in .csv.")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(_SPEC_FIELDS))
        w.writeheader()
        for row in spec:
            w.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in _SPEC_FIELDS})
    return path


def _read_spec(path: str) -> list[dict]:
    if not path.lower().endswith(".csv"):
        raise ValueError("Spec file must end in .csv.")
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        row = dict(r)
        for k in ("order", "level", "pages"):
            if row.get(k) not in (None, ""):
                row[k] = int(float(row[k]))
        for k in ("table", "heading"):
            if row.get(k) == "":
                row[k] = None
        out.append(row)
    return out


def assemble_from_spec(spec, output_file, toc_title: str = "Table of Contents",
                       toc_leader: str = "dot", toc_page_numbering: str = "decimal",
                       overwrite: bool = False, **kwargs) -> str:
    """Assemble RTF files using a TOC built from an assembly spec (deprecated).

    **Deprecated** (warns once a session, still works; removed in 0.9.0, as in
    R): it is ``assemble_rtf(toc=spec)`` -- :func:`assemble_rtf` takes the
    table (or its ``.csv`` path) as ``toc``.

    Args:
        spec: An assembly-spec list of dicts (from :func:`assemble_folder`) or
            a path to a saved ``.csv`` spec.
        output_file: Destination path.
        toc_title, toc_leader, toc_page_numbering, overwrite: Passed to
            :func:`assemble_rtf`.
    """
    _deprecated("assemble_from_spec",
                "`assemble_from_spec()` is deprecated: it is `assemble_rtf(toc=spec)` "
                "(a table or its .csv path).")
    return _assemble_from_spec(spec, output_file, toc_title=toc_title,
                               toc_leader=toc_leader,
                               toc_page_numbering=toc_page_numbering,
                               overwrite=overwrite, **kwargs)


def _assemble_from_spec(spec, output_file, toc_title: str = "Table of Contents",
                        toc_leader: str = "dot", toc_page_numbering: str = "decimal",
                        overwrite: bool = False, **kwargs) -> str:
    if isinstance(spec, str):
        spec = _read_spec(spec)
    if not isinstance(spec, list) or not all(
        isinstance(r, dict) and "file" in r and "label" in r for r in spec
    ):
        raise TypeError("`spec` must be an assembly-spec list (see assemble_folder()) or a path.")
    if spec and spec[0].get("order") is not None:
        spec = sorted(spec, key=lambda r: r["order"])
    missing = [r["file"] for r in spec if not os.path.exists(r["file"])]
    if missing:
        raise FileNotFoundError("Spec references missing file(s): " + ", ".join(missing))
    toc = _spec_to_toc(spec)
    return assemble_rtf(
        [r["file"] for r in spec], output_file, overwrite=overwrite, toc=toc,
        toc_title=toc_title, toc_leader=toc_leader,
        toc_page_numbering=toc_page_numbering, **kwargs,
    )


def assemble_folder(dir, output_file=None, spec_file=None, recursive: bool = False,
                    toc_title: str = "Table of Contents", toc_leader: str = "dot",
                    toc_page_numbering: str = "decimal", overwrite: bool = False,
                    **kwargs):
    """A folder's table of contents, and the assembled deliverable when asked.

    Scans ``dir`` for ``.rtf`` files (natural-sorted, so ``t2`` comes before
    ``t10``) and reads each file's table number and title from its title
    block into a **table of contents**: a list of row dicts, one per file.
    With an ``output_file`` it assembles the deliverable with that table of
    contents (:func:`assemble_rtf`); without one it only returns the table, to
    edit (rename labels, fill ``heading`` to group entries, change ``level``,
    reorder or drop rows) and hand to ``assemble_rtf(toc=)``.

    Each row has the keys ``order`` (the assembly order), ``file``, ``table``
    (the table number read from the title, or ``None``), ``heading`` (a
    heading printed above the entry whenever it changes; ``None`` = none),
    ``label`` (the entry text, ``"Table N  <title>"``), ``level`` (the
    entry's indent, default 2) and ``pages`` (informational).

    Args:
        dir: The folder to scan.
        output_file: Path of the assembled ``.rtf`` to write, or ``None``
            (default): return the table of contents only.
        spec_file: Also write the table of contents to this ``.csv``.
        recursive: Scan sub-folders too.
        toc_title, toc_leader, toc_page_numbering, overwrite, **kwargs: Passed
            to :func:`assemble_rtf`.

    Returns:
        Without ``output_file``, the table of contents.  With one, a dict with
        ``output`` (the assembled file) and ``spec`` (the table of contents
        used).
    """
    spec = _assemble_spec(dir=dir, recursive=recursive)
    if spec_file is not None:
        _write_spec(spec, spec_file)
    if output_file is None:
        return spec
    _assemble_from_spec(spec, output_file, toc_title=toc_title, toc_leader=toc_leader,
                        toc_page_numbering=toc_page_numbering, overwrite=overwrite, **kwargs)
    return {"output": output_file, "spec": spec}
