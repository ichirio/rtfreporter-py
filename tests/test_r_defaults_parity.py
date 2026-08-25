"""Pin the argument defaults that must match the R package.

Each expectation below was read out of the R implementation (or produced by
running the equivalent call in R), not chosen here.  A default that silently
drifts from R changes rendered output without failing anything else, which is
why these get their own tests.
"""

from __future__ import annotations

import inspect

import pytest

import rtfreporter as rr


# ------------------------------------------------------- header / footer ----
def test_footer_carries_a_top_rule_by_default():
    """R: ``rtf_footer(border = rtf_border_top())`` -- single, width 15."""
    band = rr.rtf_footer([{"l": "Note: percentages are of non-missing subjects."}])
    assert band.border is not None, "the footer band must default to a top rule"
    assert band.border.top is not None
    assert band.border.top.style == "single"
    assert band.border.top.width == 15
    assert band.border.bottom is None
    assert band.border.left is None
    assert band.border.right is None


def test_footer_rule_can_be_switched_off():
    assert rr.rtf_footer([{"l": "x"}], border=None).border is None


def test_header_has_no_border_by_default():
    """R: ``rtf_header(border = NULL)`` -- only the footer gets a rule."""
    assert rr.rtf_header([{"l": "Protocol XYZ"}]).border is None


def _footer_band(rtf: str) -> str:
    """The ``{\\footer ...}`` group of a rendered document."""
    start = rtf.find(chr(92) + "footer ")
    assert start != -1, "no footer band in the output"
    return rtf[start : rtf.find("}", start)]


def test_footer_rule_reaches_the_rendered_output():
    """The band emits a top cell border: ``\\clbrdrt\\brdrs\\brdrw15``."""
    pages = rr.as_rtftables({"v": [1]}, col_rel_width=[100])
    ruled = rr.to_rtf(
        rr.rtf_tables(
            rr.rtf_section(rr.rtf_document(), footer=rr.rtf_footer([{"l": "Note"}])),
            pages,
        )
    )
    plain = rr.to_rtf(
        rr.rtf_tables(
            rr.rtf_section(
                rr.rtf_document(), footer=rr.rtf_footer([{"l": "Note"}], border=None)
            ),
            pages,
        )
    )
    bs = chr(92)
    assert bs + "clbrdrt" + bs + "brdrs" + bs + "brdrw15" in _footer_band(ruled)
    assert bs + "clbrdrt" not in _footer_band(plain)
    assert "Note" in _footer_band(ruled) and "Note" in _footer_band(plain)


# ------------------------------------------------------ blank_rows_by_change --
def test_by_change_fences_the_block_by_default():
    """R: ``blank_rows_by_change(cols, include_before_first = TRUE, include_after_last = TRUE)``.

    Checked in R: ``A,A,B,B`` yields ``[0, 2, 4]``.
    """
    sig = inspect.signature(rr.blank_rows_by_change)
    assert sig.parameters["include_before_first"].default is True
    assert sig.parameters["include_after_last"].default is True

    pages = rr.as_rtftables(
        {"g": ["A", "A", "B", "B"], "v": [1, 2, 3, 4]},
        blank_rows=rr.blank_rows_by_change("g"),
    )
    assert pages[0].blank_rows == [0, 2, 4]


def test_by_change_accepts_group_by_like_r():
    """R's spec carries its own ``group_by``; the port must too."""
    sig = inspect.signature(rr.blank_rows_by_change)
    assert "group_by" in sig.parameters
    assert sig.parameters["group_by"].default == "value"


def test_by_change_group_by_indent():
    nbsp = chr(0xA0)
    rows = [["SOC1"], [nbsp + "PT a"], [nbsp + "PT b"], ["SOC2"], [nbsp + "PT c"]]
    spec = rr.blank_rows_by_change(
        0, group_by="indent", include_before_first=False, include_after_last=False
    )
    assert spec.positions(["Event"], rows) == {3}


def test_by_change_group_by_needs_a_single_column():
    spec = rr.blank_rows_by_change([0, 1], group_by="indent")
    with pytest.raises(ValueError, match="exactly one column"):
        spec.positions(["a", "b"], [["x", "y"]])


# ------------------------------------------------------------ between_groups --
@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, [2]),
        ({"blank_row_first": True}, [0, 2]),
    ],
)
def test_between_groups_blanks_transitions_only(kwargs, expected):
    """R: ``between_groups`` fences nothing -- only the transitions.

    Checked in R: ``[2]``, and ``[0, 2]`` with ``blank_row_first = TRUE``.
    """
    frame = rr.set_blank_rows(
        {"g": ["A", "A", "B", "B"], "v": [1, 2, 3, 4]},
        blank_rows="between_groups",
        **kwargs,
    )
    assert rr.rtftable(frame).blank_rows == expected


def test_between_groups_via_as_rtftables_matches_r():
    pages = rr.as_rtftables(
        {"g": ["A", "A", "B", "B"], "v": [1, 2, 3, 4]},
        blank_rows="between_groups",
        group_col="g",
    )
    assert pages[0].blank_rows == [2]


# --------------------------------------------------------- other R defaults --
@pytest.mark.parametrize(
    ("fn", "arg", "expected"),
    [
        ("as_rtftables", "cont_label", " (Cont.)"),
        ("as_rtftables", "min_group_rows", 2),
        ("as_rtftables", "stub_indent", 4),
        ("as_rtftables", "border", "tfl"),
        ("as_rtftables", "read_meta", True),
        ("as_rtftables", "split", "none"),
        ("as_rtftables", "stub_group_summary", "empty"),
        ("rtftable", "table_align", "left"),
        ("rtftable", "border", "tfl"),
        ("rtftable", "row_height_exact", False),
        ("generate_rtfreport", "overwrite", False),
        ("rtfplot", "align", "center"),
        ("rtf_replace_text", "backup", True),
        ("rtf_replace_text", "use_regex", False),
        ("blank_rows_by_rule", "where", "before"),
    ],
)
def test_scalar_defaults_match_r(fn, arg, expected):
    sig = inspect.signature(getattr(rr, fn))
    assert sig.parameters[arg].default == expected


def test_page_defaults_resolve_to_the_r_values():
    """`rtf_page()` uses a sentinel so options can win; the resolved values match R."""
    opts = rr.rtfreporter_options()
    assert opts["page.paper_size"] == "letter"
    assert opts["page.orientation"] == "landscape"
    for side in ("top", "bottom", "left", "right"):
        assert opts[f"page.margin_{side}_in"] == 0.75
    assert opts["font_size_half_points"] == 18
    assert opts["markup"] == "script"
    assert opts["title_format"] == "text"
    assert opts["footnote_format"] == "table"
