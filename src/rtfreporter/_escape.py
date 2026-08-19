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
) -> str:
    """Replace page tokens (after escaping) and return RTF-ready text.

    Recognised tokens: ``{AUTO_PAGE}``, ``{AUTO_TOTAL_PAGES}``,
    ``{SECTION_PAGES}`` (dynamic viewer fields) and ``{PAGE}`` /
    ``{TOTAL_PAGES}`` (static, baked in at render time).
    """
    if value is None:
        return ""
    out = escape(value)
    # After escaping, "{" -> "\{" and "}" -> "\}", so tokens appear as \{TOKEN\}.
    out = out.replace(r"\{AUTO_PAGE\}", C.AUTO_PAGE)
    fallback = str(total_pages) if total_pages is not None else "?"
    numpages = C.AUTO_TOTAL_PAGES.format(total_pages=fallback)
    out = out.replace(r"\{AUTO_TOTAL_PAGES\}", numpages)
    out = out.replace(r"\{SECTION_PAGES\}", C.SECTION_PAGES)
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
