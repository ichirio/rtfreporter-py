"""Importable test helpers (pytest puts the tests dir on sys.path)."""

from __future__ import annotations

from rtfreporter.render import render_rtftable


def assert_valid_rtf(rtf: str) -> None:
    """Assert an RTF string is well-formed enough to open in a word processor."""
    assert rtf.startswith("{\\rtf1"), "RTF must start with {\\rtf1"
    assert rtf.rstrip().endswith("}"), "RTF must end with a closing brace"
    assert rtf.count("{") == rtf.count("}"), "unbalanced RTF group braces"
    assert all(ord(c) < 128 for c in rtf), "RTF must be ASCII-safe"
    assert rtf.count("\\trowd") == rtf.count("\\row"), "unbalanced \\trowd/\\row"


def render(tbl, writable: int = 12000, **kwargs) -> str:
    """Render an RtfTable to a single joined RTF string (no document chrome)."""
    return "".join(render_rtftable(tbl, writable, **kwargs))
