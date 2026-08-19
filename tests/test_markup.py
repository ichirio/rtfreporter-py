"""Cell-text markup, escaping and page tokens (markup, escape)."""

import pytest

from rtfreporter._escape import (
    escape,
    escape_unicode_raw,
    format_cell_text,
    render_tokens,
    resolve_markup,
    uses_static_page_token,
)
from rtfreporter.header_footer import header

# -- escaping -----------------------------------------------------------------

def test_escape_braces_and_backslash():
    assert escape_unicode_raw("a{b}c\\d") == "a\\{b\\}c\\\\d"


def test_escape_newline_to_line():
    assert escape_unicode_raw("a\nb") == "a\\line b"


def test_escape_empty_string():
    assert escape_unicode_raw("") == ""


def test_escape_unicode_plus_minus():
    assert escape_unicode_raw("±") == "\\u177?"


def test_escape_keeps_ascii_safe():
    assert all(ord(c) < 128 for c in escape_unicode_raw("café"))


def test_escape_helper_none_empty():
    assert escape(None) == ""


# -- script markup ------------------------------------------------------------

def test_superscript():
    assert format_cell_text("x^{2}", "script") == "x{\\super 2}"


def test_subscript():
    assert format_cell_text("H_{2}O", "script") == "H{\\sub 2}O"


def test_nested_super_in_text():
    out = format_cell_text("a^{b}c^{d}", "script")
    assert out.count("\\super") == 2


def test_markup_none_keeps_literal():
    out = format_cell_text("x^{2}", "none")
    assert "\\super" not in out
    assert "\\{" in out


def test_unmatched_brace_literal():
    out = format_cell_text("x^{2", "script")
    assert "\\super" not in out


def test_none_value_empty_string():
    assert format_cell_text(None, "script") == ""


# -- relational markup --------------------------------------------------------

def test_relational_ge():
    assert format_cell_text(">=5", "relational") == "\\u8805?5"


def test_relational_le():
    assert format_cell_text("<=5", "relational") == "\\u8804?5"


def test_relational_off_by_default_script():
    out = format_cell_text(">=5", "script")
    assert "\\u8805" not in out


# -- resolve_markup -----------------------------------------------------------

def test_resolve_all():
    assert resolve_markup("all") == frozenset({"script", "relational"})


def test_resolve_none():
    assert resolve_markup("none") == frozenset()


def test_resolve_default_is_script():
    assert resolve_markup(None) == frozenset({"script"})


def test_resolve_list():
    assert resolve_markup(["script", "relational"]) == frozenset({"script", "relational"})


def test_resolve_unknown_raises():
    with pytest.raises(ValueError):
        resolve_markup("bogus")


# -- page tokens --------------------------------------------------------------

def test_token_auto_page():
    assert render_tokens("Page {AUTO_PAGE}") == "Page \\chpgn "


def test_token_total_pages_field():
    out = render_tokens("of {AUTO_TOTAL_PAGES}", total_pages=7)
    assert "NUMPAGES" in out and "7" in out


def test_token_static_page():
    assert render_tokens("Page {PAGE}", current_page=3) == "Page 3"


def test_token_static_total_pages():
    assert render_tokens("of {TOTAL_PAGES}", total_pages=9) == "of 9"


def test_token_section_pages_field():
    out = render_tokens("{SECTION_PAGES}")
    assert "SECTIONPAGES" in out


def test_uses_static_page_token_true():
    assert uses_static_page_token(header([{"r": "Page {PAGE}"}]))


def test_uses_static_page_token_false_for_auto():
    assert not uses_static_page_token(header([{"r": "Page {AUTO_PAGE}"}]))


def test_uses_static_page_token_none():
    assert not uses_static_page_token(None)
