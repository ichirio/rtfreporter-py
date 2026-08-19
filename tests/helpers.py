"""Importable test helpers (pytest puts the tests dir on sys.path)."""

from __future__ import annotations


def assert_valid_rtf(rtf: str) -> None:
    """Assert an RTF string is well-formed enough to open in a word processor."""
    assert rtf.startswith("{\\rtf1"), "RTF must start with {\\rtf1"
    assert rtf.rstrip().endswith("}"), "RTF must end with a closing brace"
    assert rtf.count("{") == rtf.count("}"), "unbalanced RTF group braces"
    assert all(ord(c) < 128 for c in rtf), "RTF must be ASCII-safe"
    assert rtf.count("\\trowd") == rtf.count("\\row"), "unbalanced \\trowd/\\row"
