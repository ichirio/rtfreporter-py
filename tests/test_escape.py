"""Tests for RTF escaping, markup, and page-token substitution."""

from rtfreporter._escape import (
    escape_unicode_raw,
    format_cell_text,
    render_tokens,
    resolve_markup,
)


def test_escape_special_chars():
    assert escape_unicode_raw("a{b}c\\d") == "a\\{b\\}c\\\\d"


def test_escape_newline():
    assert escape_unicode_raw("a\nb") == "a\\line b"


def test_escape_non_ascii():
    # U+00B1 PLUS-MINUS -> \u177?
    assert escape_unicode_raw("±") == "\\u177?"
    assert all(ord(c) < 128 for c in escape_unicode_raw("café"))


def test_markup_superscript():
    assert format_cell_text("x^{2}", "script") == "x{\\super 2}"


def test_markup_subscript():
    assert format_cell_text("H_{2}O", "script") == "H{\\sub 2}O"


def test_markup_disabled_keeps_literal():
    out = format_cell_text("x^{2}", "none")
    assert "\\super" not in out
    assert "\\{" in out  # the { is escaped literally


def test_markup_relational():
    out = format_cell_text(">=5", "relational")
    assert out == "\\u8805?5"


def test_resolve_markup_all():
    assert resolve_markup("all") == frozenset({"script", "relational"})
    assert resolve_markup("none") == frozenset()


def test_render_tokens_auto_page():
    assert render_tokens("Page {AUTO_PAGE}") == "Page \\chpgn "


def test_render_tokens_total_pages_field():
    out = render_tokens("of {AUTO_TOTAL_PAGES}", total_pages=7)
    assert "NUMPAGES" in out
    assert "7" in out


def test_render_tokens_static_page():
    assert render_tokens("Page {PAGE}", current_page=3) == "Page 3"
