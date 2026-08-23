"""Group detection modes and the ``between_groups`` blank-row shorthand.

Every expectation here was checked against the R package (``group_by`` maps to
R's ``.compute_group_info()`` / ``.detect_group_mode()``; the ``group_force``
page shapes were compared with ``as_rtftables()`` in R).
"""

from __future__ import annotations

import pandas as pd
import pytest

import rtfreporter as rr
from rtfreporter.adapters import _compute_group_keys, _detect_group_mode

NBSP = chr(0xA0)


# ---------------------------------------------------------------- detection --
def test_detect_indent_wins_over_everything():
    assert _detect_group_mode(["SOC", NBSP + "PT", NBSP + "PT2"]) == "indent"
    assert _detect_group_mode(["SOC", "    PT"]) == "indent"


def test_detect_filled_when_some_cells_are_empty():
    assert _detect_group_mode(["SOC", "", "", "SOC2", ""]) == "filled"


def test_detect_value_when_every_cell_is_filled_and_flush():
    assert _detect_group_mode(["A", "A", "B"]) == "value"


# ------------------------------------------------------------------- keys ----
def _keys(labels, mode):
    rows = [[label] for label in labels]
    return _compute_group_keys(rows, 0, mode)


def test_indent_mode_assigns_children_to_their_header():
    labels = ["SOC1", NBSP + "PT a", NBSP + "PT b", "SOC2", NBSP + "PT c"]
    assert _keys(labels, "indent") == ["SOC1", "SOC1", "SOC1", "SOC2", "SOC2"]


def test_filled_mode_treats_blank_cells_as_members():
    labels = ["G1", "", "", "G2", ""]
    assert _keys(labels, "filled") == ["G1", "G1", "G1", "G2", "G2"]


def test_value_mode_uses_the_raw_cell_values():
    assert _keys(["A", "A", "B"], "value") == ["A", "A", "B"]


def test_unknown_group_by_is_rejected():
    with pytest.raises(ValueError, match="group_by"):
        _keys(["A"], "sideways")


# ------------------------------------------------------- indent + paginate ---
def _indented_frame():
    """Two SOCs of three rows each (header + two indented children)."""
    labels = []
    for soc in ("SOC1", "SOC2"):
        labels += [soc, NBSP + f"{soc} PT a", NBSP + f"{soc} PT b"]
    return pd.DataFrame({"Event": labels, "n": list(range(6))})


def test_group_by_indent_keeps_a_soc_together_under_group_safe():
    pages = rr.as_rtftables(
        _indented_frame(), split="group_safe", group_col=0, group_by="indent", max_rows=4
    )
    assert [p.nrows for p in pages] == [3, 3]
    assert pages[1].rows[0][0] == "SOC2"


def test_group_by_indent_continues_a_split_soc_under_group_force():
    pages = rr.as_rtftables(
        _indented_frame(),
        split="group_force",
        group_col=0,
        group_by="indent",
        max_rows=2,
        min_group_rows=1,
        cont_label=" (Cont.)",
    )
    flat = [row[0] for page in pages for row in page.rows]
    assert any(str(cell).endswith("(Cont.)") for cell in flat)


# --------------------------------------------------------- between_groups ----
def test_between_groups_inserts_a_blank_at_each_transition():
    df = pd.DataFrame({"g": ["A", "A", "B", "B"], "v": [1, 2, 3, 4]})
    pages = rr.as_rtftables(df, blank_rows="between_groups", group_col="g")
    assert pages[0].blank_rows == [2]


def test_between_groups_defaults_to_the_first_column():
    df = pd.DataFrame({"g": ["A", "B", "B"], "v": [1, 2, 3]})
    pages = rr.as_rtftables(df, blank_rows="between_groups")
    assert pages[0].blank_rows == [1]


def test_between_groups_composes_inside_a_list():
    df = pd.DataFrame({"g": ["A", "A", "B"], "v": [1, 2, 3]})
    pages = rr.as_rtftables(
        df, blank_rows=["between_groups", rr.AFTER_LAST], group_col="g"
    )
    assert pages[0].blank_rows == [2, 3]


def test_unknown_blank_rows_string_is_rejected():
    with pytest.raises(ValueError, match="between_groups"):
        rr.as_rtftables({"g": ["A"]}, blank_rows="sometimes")
