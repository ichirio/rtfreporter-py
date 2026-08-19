"""Shared pytest fixtures and RTF-structure assertion helpers."""

from __future__ import annotations

import pytest


def assert_valid_rtf(rtf: str) -> None:
    """Assert an RTF string is well-formed enough to open in a word processor."""
    assert rtf.startswith("{\\rtf1"), "RTF must start with {\\rtf1"
    assert rtf.rstrip().endswith("}"), "RTF must end with a closing brace"
    assert rtf.count("{") == rtf.count("}"), "unbalanced RTF group braces"
    assert all(ord(c) < 128 for c in rtf), "RTF must be ASCII-safe"
    # Every table row is opened and closed.
    assert rtf.count(r"\trowd") == rtf.count(r"\row"), "unbalanced \\trowd/\\row"


@pytest.fixture
def demog_df():
    pd = pytest.importorskip("pandas")
    return pd.DataFrame(
        {
            "Subject": ["001", "002", "003"],
            "Arm": ["Active", "Placebo", "Active"],
            "Age": [34, 45, 28],
            "Sex": ["M", "F", "M"],
        }
    )
