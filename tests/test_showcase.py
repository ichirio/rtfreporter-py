"""Validate the showcase examples against the R implementation.

Every expected figure here comes from ``data-raw/R_reference_numbers.txt``,
produced by running the equivalent computation in R against the same
``pharmaverseadam`` subset.  If a number here disagrees, the Python side is
wrong -- these are not free-floating expectations.
"""

from __future__ import annotations

import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(REPO, "examples")
if EXAMPLES not in sys.path:
    sys.path.insert(0, EXAMPLES)

pytest.importorskip("pandas")

import adam_data  # noqa: E402
import showcase_ae  # noqa: E402
import showcase_dm  # noqa: E402

BS, OB, CB = chr(92), chr(123), chr(125)
NBSP = chr(0xA0)


@pytest.fixture(scope="module")
def adsl():
    return adam_data.load_adsl()


@pytest.fixture(scope="module")
def adae():
    return adam_data.load_adae()


# ------------------------------------------------------------------ shapes --
def test_bundled_data_shapes(adsl, adae):
    assert adsl.shape[0] == 254
    assert adae.shape[0] == 1122


def test_arm_denominators(adsl):
    """R: Placebo 86, Xanomeline Low Dose 96, Xanomeline High Dose 72."""
    n = adam_data.arm_counts(adsl)
    assert [int(n[a]) for a in adam_data.ARM_LEVELS] == [86, 96, 72]


# ------------------------------------------------------------ demographics --
def _dm_cell(body, characteristic, statistic):
    row = body[(body["Characteristic"] == characteristic) & (body["Statistic"] == statistic)]
    assert len(row) == 1, f"no unique row for {characteristic} / {statistic}"
    return [row.iloc[0][a] for a in adam_data.ARM_LEVELS]


@pytest.fixture(scope="module")
def dm_body(adsl):
    return showcase_dm.build_body(adsl)


def test_age_summary_matches_r(dm_body):
    assert _dm_cell(dm_body, "Age (years)", "n") == ["86", "96", "72"]
    assert _dm_cell(dm_body, "Age (years)", "Mean (SD)") == [
        "75.2 (8.59)", "76.0 (8.11)", "73.8 (7.94)"
    ]
    assert _dm_cell(dm_body, "Age (years)", "Median") == ["76.0", "78.0", "75.5"]
    assert _dm_cell(dm_body, "Age (years)", "Min, Max") == ["52, 89", "51, 88", "56, 88"]


def _counts(cells):
    """Pull the leading integer out of each ``n (xx.x)`` cell."""
    return [int(str(c).replace(NBSP, " ").strip().split(" ")[0]) for c in cells]


@pytest.mark.parametrize(
    ("characteristic", "level", "expected"),
    [
        ("Age group, n (%)", "<65", [14, 8, 11]),
        ("Age group, n (%)", "65 - 80", [42, 53, 49]),
        ("Age group, n (%)", ">80", [30, 35, 12]),
        ("Sex, n (%)", "Male", [33, 41, 37]),
        ("Sex, n (%)", "Female", [53, 55, 35]),
        ("Race, n (%)", "White", [78, 90, 62]),
        ("Race, n (%)", "Black or African American", [8, 6, 9]),
        ("Race, n (%)", "Asian", [0, 0, 0]),
        ("Race, n (%)", "American Indian or Alaska Native", [0, 0, 1]),
    ],
)
def test_categorical_counts_match_r(dm_body, characteristic, level, expected):
    assert _counts(_dm_cell(dm_body, characteristic, level)) == expected


def test_zero_count_race_levels_are_kept(dm_body):
    """Asian has no subjects, but the level must still appear in the table."""
    assert "Asian" in set(dm_body["Statistic"])


# --------------------------------------------------------- adverse events ---
@pytest.fixture(scope="module")
def ae_body(adsl, adae):
    return showcase_ae.build_body(adsl, adae)


def test_any_ae_counts_match_r(ae_body):
    """R: 65 / 84 / 68 distinct subjects with any TEAE."""
    row = ae_body[ae_body["Adverse Event"] == adam_data.ANY_AE]
    assert len(row) == 1
    assert _counts([row.iloc[0][a] for a in adam_data.ARM_LEVELS]) == [65, 84, 68]


@pytest.mark.parametrize(
    ("soc", "expected"),
    [
        ("Cardiac Disorders", [12, 14, 14]),
        ("Gastrointestinal Disorders", [17, 15, 19]),
        ("General Disorders And Administration Site Conditions", [21, 51, 36]),
    ],
)
def test_soc_counts_match_r(ae_body, soc, expected):
    """SOC rows carry an independent distinct-subject count, not a PT sum."""
    row = ae_body[ae_body["Adverse Event"] == soc]
    assert len(row) == 1
    assert _counts([row.iloc[0][a] for a in adam_data.ARM_LEVELS]) == expected


def test_soc_row_is_not_the_sum_of_its_preferred_terms(ae_body):
    """Guards the rule above: a subject with two PTs is counted once."""
    labels = ae_body["Adverse Event"].tolist()
    i = labels.index("Gastrointestinal Disorders")
    soc_n = _counts([ae_body.iloc[i][a] for a in adam_data.ARM_LEVELS])
    pt_total = [0, 0, 0]
    for j in range(i + 1, len(labels)):
        if not labels[j].startswith(showcase_ae.INDENT):
            break
        for k, arm in enumerate(adam_data.ARM_LEVELS):
            pt_total[k] += _counts([ae_body.iloc[j][arm]])[0]
    assert soc_n != pt_total


def test_exactly_32_preferred_terms_pass_the_3pct_filter(adsl, adae):
    kept = showcase_ae.kept_preferred_terms(adae, adam_data.arm_counts(adsl))
    assert len(kept) == 32


def test_preferred_term_order_matches_r(adae):
    """R: Pruritus, Application Site Pruritus, Erythema, ... (count desc, ties A-Z)."""
    order = showcase_ae.preferred_term_order(adae)
    assert order[:5] == [
        "PRURITUS",
        "APPLICATION SITE PRURITUS",
        "ERYTHEMA",
        "APPLICATION SITE ERYTHEMA",
        "RASH",
    ]


def test_socs_are_alphabetical_and_pts_are_indented(ae_body):
    labels = ae_body["Adverse Event"].tolist()[1:]  # skip the any-AE row
    socs = [lab for lab in labels if not lab.startswith(showcase_ae.INDENT)]
    assert socs == sorted(socs)
    assert any(lab.startswith(showcase_ae.INDENT) for lab in labels)


def test_zero_cells_are_expanded_and_aligned(ae_body):
    widths = {
        len(str(ae_body.iloc[i][arm]))
        for i in range(len(ae_body))
        for arm in adam_data.ARM_LEVELS
    }
    assert widths == {11}, f"ragged count column: {widths}"
    assert showcase_ae.fmt_ae(0, 86).replace(NBSP, " ").strip() == "0  (0.0%)"


# ------------------------------------------------------------------- RTF ----
def _rtf_is_wellformed(text: str) -> bool:
    depth = lowest = i = 0
    while i < len(text):
        ch = text[i]
        if ch == BS and i + 1 < len(text) and text[i + 1] in (OB + CB + BS):
            i += 2
            continue
        if ch == OB:
            depth += 1
        elif ch == CB:
            depth -= 1
            lowest = min(lowest, depth)
        i += 1
    return depth == 0 and lowest >= 0


def _render(build, tmp_path, name):
    import rtfreporter as rr

    path = os.path.join(str(tmp_path), name)
    rr.generate_rtfreport(build, path, overwrite=True)
    return open(path, "rb").read().decode("ascii", errors="replace")


def test_demographics_rtf_is_valid(adsl, dm_body, tmp_path):
    text = _render(showcase_dm.build_document(adsl, dm_body), tmp_path, "dm.rtf")
    assert text.startswith(OB + BS + "rtf1")
    assert _rtf_is_wellformed(text)


def test_demographics_via_great_tables_is_valid(adsl, dm_body, tmp_path):
    pytest.importorskip("great_tables")
    text = _render(showcase_dm.build_document_via_gt(adsl, dm_body), tmp_path, "dm_gt.rtf")
    assert text.startswith(OB + BS + "rtf1")
    assert _rtf_is_wellformed(text)


def test_adverse_events_rtf_spans_pages_with_a_continuation(adsl, ae_body, tmp_path):
    doc, pages = showcase_ae.build_document(adsl, ae_body)
    assert len(pages) > 1, "the AE table should not fit on one page"
    text = _render(doc, tmp_path, "ae.rtf")
    assert _rtf_is_wellformed(text)
    assert text.count(BS + "page") >= 1
    assert "(Cont.)" in text


def test_showcase_rtf_is_ascii_safe(adsl, ae_body, tmp_path):
    doc, _ = showcase_ae.build_document(adsl, ae_body)
    path = os.path.join(str(tmp_path), "ae_ascii.rtf")
    import rtfreporter as rr

    rr.generate_rtfreport(doc, path, overwrite=True)
    raw = open(path, "rb").read()
    assert all(byte < 128 for byte in raw), "RTF output must stay ASCII-safe"
