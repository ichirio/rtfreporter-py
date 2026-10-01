"""RTF text escaping, cell-text markup, and page-token substitution.

Ported from ``generate_rtfreport.R`` (``.rtf_escape_unicode_raw``,
``.process_markup``, ``.format_cell_text``, ``.render_tokens``).

The output is always ASCII-safe: any code point above 127 is emitted as an
``\\uNNNN?`` escape with a single ``?`` fallback char (matching the document
header's ``\\uc1``).
"""

from __future__ import annotations

from . import _commands as C

# Markup token vocabulary.
_MARKUP_TOKENS = frozenset({"script", "relational"})


def resolve_markup(markup: str | list[str] | set[str] | None) -> frozenset[str]:
    """Normalise a markup selector to a frozenset of enabled tokens.

    Accepts ``"script"`` (default), ``"relational"``, ``"all"``, ``"none"``, or
    an iterable of those individual tokens.
    """
    if markup is None:
        return frozenset({"script"})
    if isinstance(markup, str):
        items = [markup]
    else:
        items = list(markup)
    out: set[str] = set()
    for item in items:
        item = str(item).strip().lower()
        if item == "all":
            out |= set(_MARKUP_TOKENS)
        elif item == "none":
            pass
        elif item in _MARKUP_TOKENS:
            out.add(item)
        else:
            raise ValueError(
                f"Unknown markup token {item!r}; use 'script', 'relational', "
                "'all', or 'none'."
            )
    return frozenset(out)


def escape_unicode_raw(text: str) -> str:
    """Character-level RTF escape + Unicode conversion.

    Escapes ``\\``, ``{``, ``}``, turns newlines into ``\\line ``, and converts
    any non-ASCII code point to ``\\uNNNN?``.
    """
    if not text:
        return text
    out: list[str] = []
    for ch in text:
        cp = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif ch == "{":
            out.append("\\{")
        elif ch == "}":
            out.append("\\}")
        elif ch == "\n":
            out.append("\\line ")
        elif cp > 127:
            out.append(f"\\u{cp}?")
        else:
            out.append(ch)
    return "".join(out)


def _process_markup(text: str) -> str:
    """Recursively parse ``^{...}`` / ``_{...}`` markup, escaping plain parts."""
    if not text:
        return text

    # Find the earliest ^{ or _{ marker.
    pos = None
    kind = ""
    i_super = text.find("^{")
    i_sub = text.find("_{")
    if i_super != -1:
        pos, kind = i_super, "super"
    if i_sub != -1 and (pos is None or i_sub < pos):
        pos, kind = i_sub, "sub"

    if kind == "":
        return escape_unicode_raw(text)

    before = text[:pos]
    rest = text[pos + 2 :]

    # Find the matching closing brace.
    depth = 1
    end = -1
    for idx, ch in enumerate(rest):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = idx
                break
    if end == -1:
        # Unmatched brace: treat the whole thing as literal text.
        return escape_unicode_raw(text)

    inner = rest[:end]
    after = rest[end + 1 :]
    cmd = r"\super " if kind == "super" else r"\sub "
    return (
        _process_markup(before)
        + "{"
        + cmd
        + _process_markup(inner)
        + "}"
        + _process_markup(after)
    )


def format_cell_text(value: object, markup: frozenset[str] | str | None = "script") -> str:
    """Full cell-text pipeline: markup + RTF escape + Unicode + newlines.

    ``markup`` may be a resolved frozenset or a raw selector string.
    """
    if value is None:
        return ""
    tokens = markup if isinstance(markup, frozenset) else resolve_markup(markup)
    text = str(value)
    relational = "relational" in tokens
    script = "script" in tokens

    if relational:
        text = text.replace(">=", "\x01GE\x01").replace("<=", "\x01LE\x01")

    result = _process_markup(text) if script else escape_unicode_raw(text)

    if relational:
        # U+2265 (>=) and U+2264 (<=) emitted as literal RTF unicode escapes.
        result = result.replace("\x01GE\x01", "\\u8805?").replace("\x01LE\x01", "\\u8804?")
    return result


def escape(value: object) -> str:
    """RTF-safe escape for header/footer text (no markup, supports tokens)."""
    if value is None:
        return ""
    return escape_unicode_raw(str(value))


def render_tokens(
    value: object,
    current_page: int | None = None,
    total_pages: int | None = None,
    markup=None,
) -> str:
    """Escape ``value`` (through the markup rules when ``markup`` is given, as a
    band that asks for markup needs), then replace the page tokens.

    Recognised tokens: ``{AUTO_PAGE}``, ``{AUTO_TOTAL_PAGES}`` (dynamic viewer
    fields), ``{PAGE}`` / ``{TOTAL_PAGES}`` (static, baked in at render
    time), ``{BOOK_PAGE}`` (a slot :func:`~rtfreporter.assemble_rtf` fills) and
    the run tokens ``{PROGRAM}`` / ``{PROGRAM_NAME}`` / ``{PROGRAM_DIR}`` /
    ``{DATETIME}`` / ``{DATETIME:<format>}``.  ``{SECTION_PAGES}`` was
    removed (#410) and is an error.
    """
    if value is None:
        return ""
    out = format_cell_text(value, markup) if markup else escape(value)
    return substitute_page_tokens(out, current_page, total_pages)


def substitute_page_tokens(
    out: str, current_page: int | None = None, total_pages: int | None = None
) -> str:
    """The substitution half of :func:`render_tokens`, on text that is ALREADY
    escaped (``{`` -> ``\\{``), so a token reads ``\\{PAGE\\}``.

    Split out so the title and footnote blocks, which escape through
    :func:`format_cell_text` themselves, resolve the same tokens with the same
    semantics instead of printing them literally (#398).
    """
    from ._run_tokens import substitute_run_tokens

    out = substitute_run_tokens(out)
    if r"\{SECTION_PAGES\}" in out:
        raise ValueError(
            "`{SECTION_PAGES}` was removed: the RTF SECTIONPAGES field it wrote "
            "equals `{AUTO_TOTAL_PAGES}` in a standalone file, and after "
            "assemble_rtf() it keeps counting one table while the page number "
            'counts the whole document ("Page 4 of 2").\n'
            "  per-table total  -> `{TOTAL_PAGES}` (static, survives assembly)\n"
            "  document total   -> `{AUTO_TOTAL_PAGES}`"
        )
    # The reserved slot for the compiled document's page number (R #413): an
    # empty ignorable destination unless assemble_rtf(book_page=) fills it.
    out = out.replace(r"\{BOOK_PAGE\}", C.BOOK_PAGE_SLOT)
    out = out.replace(r"\{AUTO_PAGE\}", C.AUTO_PAGE)
    fallback = str(total_pages) if total_pages is not None else "?"
    out = out.replace(r"\{AUTO_TOTAL_PAGES\}", C.AUTO_TOTAL_PAGES.format(total_pages=fallback))
    if current_page is not None:
        out = out.replace(r"\{PAGE\}", str(current_page))
    if total_pages is not None:
        out = out.replace(r"\{TOTAL_PAGES\}", str(total_pages))
    return out


def uses_static_page_token(header_footer) -> bool:
    """Does any cell of a header/footer contain the static ``{PAGE}`` token?

    Matches ``{PAGE}`` but not ``{AUTO_PAGE}``.
    """
    import re

    if header_footer is None:
        return False
    rows = getattr(header_footer, "rows", None)
    if not rows:
        return False
    pattern = re.compile(r"(?:^|[^A-Z_])\{PAGE\}")
    for row in rows:
        for cell in row.values():
            if cell is None:
                continue
            if pattern.search(str(cell)):
                return True
    return False
