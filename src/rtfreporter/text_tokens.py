"""The tokens a header, footer, title or footnote may carry.

Ported from ``R/text_tokens.R``.  One list, so a program that offers them (a
GUI's "insert" menu, a preview that fills them) asks rtfreporter instead of
keeping a copy that drifts.  The substitution itself is
``substitute_page_tokens()`` / ``substitute_run_tokens()``; the tests check
that every token listed here is replaced there.
"""

from __future__ import annotations

_BASE = [
    ("{PAGE}", "page", "render",
     "Page number, written into the file (the first page of the section)", "1"),
    ("{TOTAL_PAGES}", "page", "render",
     "Total pages of this file, written into the file", "3"),
    ("{AUTO_PAGE}", "page", "viewer",
     "Page number the word processor shows (right after assemble_rtf())", "1"),
    ("{AUTO_TOTAL_PAGES}", "page", "viewer",
     "Total pages the word processor counts (the whole document)", "3"),
    ("{BOOK_PAGE}", "page", "assemble",
     "Page number in the assembled book; empty until assemble_rtf(book_page=)", ""),
    ("{PROGRAM}", "run", "render",
     "Path of the program that wrote the file, as given", "programs/t_14_1_1.py"),
    ("{PROGRAM_FULL}", "run", "render",
     "The same path, absolute (the system's separator)",
     "C:\\studies\\ABC-101\\programs\\t_14_1_1.py"),
    ("{PROGRAM_NAME}", "run", "render", "File name of that program", "t_14_1_1.py"),
    ("{PROGRAM_DIR}", "run", "render", "Folder of that program", "programs"),
    ("{DATETIME}", "run", "render",
     "Date and time the file was written; {DATETIME:<format>} for another format",
     "04OCT2026  10:05"),
]


def rtf_text_tokens(doc=None) -> list[dict]:
    """The tokens a page's text may carry (mirrors R ``rtf_text_tokens()``).

    The ``{TOKEN}``s that :func:`~rtfreporter.generate_rtfreport` fills in
    headers, footers, titles and footnotes, with what each becomes and when.
    A program that offers them -- an "insert" menu, a preview -- reads them
    here.

    * ``when="render"``: filled when the file is written.
    * ``when="viewer"``: an RTF field the word processor computes when the
      file is opened, so it stays right after
      :func:`~rtfreporter.assemble_rtf` joins files.
    * ``when="assemble"``: a slot left empty until
      :func:`~rtfreporter.assemble_rtf` fills it.

    ``{DATETIME}`` also takes a format, ``{DATETIME:%Y-%m-%d}`` (strftime
    codes); ``example`` shows one.

    Tokens of one's own (``rtf_document(tokens=)``,
    ``rtfreporter_options(tokens=)``) follow, ``kind="own"``, their value as
    the example: the session's, and a document's when ``doc`` is given.

    Args:
        doc: An :class:`~rtfreporter.RtfDocument` whose tokens of one's own
            are listed too; ``None`` (default): the session's only.

    Returns:
        A list of dicts (one per token, a table's rows) with the keys
        ``token`` (as written, with its braces), ``kind`` (``"page"``,
        ``"run"`` or ``"own"``), ``when``, ``description`` and ``example``
        (what it might print, for a preview).
    """
    from ._run_tokens import _user_tokens
    from .document import RtfDocument

    if doc is not None and not isinstance(doc, RtfDocument):
        raise TypeError("`doc` is an RtfDocument (or None).")
    keys = ("token", "kind", "when", "description", "example")
    out = [dict(zip(keys, row, strict=True)) for row in _BASE]
    own = _user_tokens(doc.tokens if doc is not None else None)
    for name, value in (own or {}).items():
        out.append({
            "token": "{" + name + "}", "kind": "own", "when": "render",
            "description": "A token of one's own (rtf_document(tokens=) or the option)",
            "example": value,
        })
    return out
