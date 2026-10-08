"""API parity with the R package: every R export outside the ARD / plan layer
exists in Python under the same name.

``data-raw/r_api/r_exports.txt`` snapshots the R ``NAMESPACE`` (refresh it
with ``data-raw/r_api/api_parity.py``), so this runs without an R checkout.
"""

from __future__ import annotations

import re
from pathlib import Path

import rtfreporter as rr

SNAPSHOT = Path(__file__).resolve().parents[1] / "data-raw" / "r_api" / "r_exports.txt"

#: The R package's ARD / table-plan layer: it consumes cards / cardx analysis
#: results data, which exist only in R, so it is not ported (see
#: docs/relationship-to-r.md).  ``plan_header_tokens()`` is new since R v0.8.2.
OUT_OF_SCOPE = frozenset({
    # ARD
    "normalize_ard", "widen_ard", "pull_ard", "list_ard_keys", "cell_rows",
    "overall_row",
    # the table plan
    "table_plan", "plan_apply", "plan_layers", "plan_template",
    "plan_header_tokens", "plan_levels", "plan_labels", "plan_cells",
    "plan_digits", "plan_stub", "plan_cell_style", "plan_paginate_group",
    "plan_paginate_rows", "plan_paginate_cols", "plan_row_group", "plan_hide",
    "plan_sort", "plan_blanks", "plan_style", "plan_col_header", "plan_columns",
    "plan_listing", "plan_titles", "plan_footnotes", "plan_after",
})

#: In scope but deliberately not ported: the R package's AI-assistant manuals
#: describe the R API.
NOT_PORTED = frozenset({"rtfreporter_ai_manual"})


def _r_exports() -> list[str]:
    lines = SNAPSHOT.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]


def test_every_r_export_outside_ard_plan_is_in_python():
    missing = [n for n in _r_exports()
               if n not in rr.__all__ and n not in OUT_OF_SCOPE and n not in NOT_PORTED]
    assert not missing, f"R exports missing from rtfreporter.__all__: {missing}"


def test_the_out_of_scope_list_is_the_ard_plan_layer_only():
    names = set(_r_exports())
    assert OUT_OF_SCOPE <= names, sorted(OUT_OF_SCOPE - names)
    for n in OUT_OF_SCOPE:
        assert re.search(r"ard|^plan_|^table_plan$|^cell_rows$|^overall_row$", n), n
    # and none of it leaked into the Python API
    assert not OUT_OF_SCOPE & set(rr.__all__)


def test_parity_numbers():
    names = _r_exports()
    in_scope = [n for n in names if n not in OUT_OF_SCOPE]
    ported = [n for n in in_scope if n in rr.__all__]
    assert len(names) == 125 and len(in_scope) == 94 and len(ported) == 93
    assert sorted(set(in_scope) - set(ported)) == sorted(NOT_PORTED)


def test_the_exports_new_since_r_0_8_2_are_here():
    for n in ("rtf_border_line", "rtf_text_tokens"):
        assert n in rr.__all__ and callable(getattr(rr, n))
