"""Load the bundled ADaM sample data used by the showcase examples.

The two CSVs in ``examples/data`` are a trimmed copy of the ``adsl`` and ``adae``
datasets from `pharmaverseadam <https://pharmaverse.github.io/pharmaverseadam/>`_
(Apache-2.0), which are themselves derived from the CDISC pilot study.  They are
committed so every example runs with **no R and no network**; the R script that
produced them is ``data-raw/export_pharmaverseadam.R``.

Both files are already restricted to the three randomised arms, and ``adae`` is
already restricted to treatment-emergent events (``TRTEMFL == "Y"``).  The
derivations applied here mirror the R package's showcase articles so the numbers
match ``data-raw/R_reference_numbers.txt``.

For a data-free alternative see :mod:`adam_synthetic`, which exposes the same
``load_adsl`` / ``load_adae`` interface.
"""

from __future__ import annotations

import os

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

#: Treatment arms, in the display order used by every showcase table.
ARM_LEVELS = [
    "Placebo",
    "Xanomeline Low Dose",
    "Xanomeline High Dose",
]

#: Age-group cut points and labels (``right=False`` half-open bins, as in R).
AGEGR_BINS = [float("-inf"), 65, 81, float("inf")]
AGEGR_LABELS = ["<65", "65 - 80", ">80"]

#: All race levels are declared, so a level with zero subjects still renders as
#: ``0 (0.0%)`` instead of vanishing from the table.
RACE_LEVELS = [
    "WHITE",
    "BLACK OR AFRICAN AMERICAN",
    "ASIAN",
    "AMERICAN INDIAN OR ALASKA NATIVE",
]
RACE_LABELS = [
    "White",
    "Black or African American",
    "Asian",
    "American Indian or Alaska Native",
]

SEX_LEVELS = ["M", "F"]
SEX_LABELS = ["Male", "Female"]

#: Label for the "any event" row on top of the adverse-event table.
ANY_AE = "Subjects with any adverse event"


def _ordered(values: pd.Series, levels: list[str], labels: list[str] | None = None):
    """Return ``values`` as an ordered categorical over ``levels``.

    Declaring every level keeps zero-count categories in the output, which is
    what a production TFL needs.
    """
    cat = pd.Categorical(values, categories=levels, ordered=True)
    out = pd.Series(cat, index=values.index)
    if labels is not None:
        out = out.cat.rename_categories(labels)
    return out


def load_adsl(path: str | None = None) -> pd.DataFrame:
    """Load ``adsl`` with the showcase derivations applied.

    Adds ``AGEGR`` (age category) and converts ``TRT01A``, ``SEX`` and ``RACE``
    to ordered categoricals so downstream ``groupby`` results keep a stable,
    clinically meaningful row order.
    """
    adsl = pd.read_csv(path or os.path.join(DATA_DIR, "adsl.csv"))
    adsl["TRT01A"] = _ordered(adsl["TRT01A"], ARM_LEVELS)
    adsl["SEX"] = _ordered(adsl["SEX"], SEX_LEVELS, SEX_LABELS)
    adsl["RACE"] = _ordered(adsl["RACE"], RACE_LEVELS, RACE_LABELS)
    adsl["AGEGR"] = pd.cut(
        adsl["AGE"], bins=AGEGR_BINS, labels=AGEGR_LABELS, right=False, ordered=True
    )
    return adsl


def load_adae(path: str | None = None) -> pd.DataFrame:
    """Load ``adae`` (treatment-emergent events only) with ordered arms."""
    adae = pd.read_csv(path or os.path.join(DATA_DIR, "adae.csv"))
    adae["TRT01A"] = _ordered(adae["TRT01A"], ARM_LEVELS)
    return adae


def arm_counts(adsl: pd.DataFrame) -> pd.Series:
    """Per-arm subject counts -- the denominators for every percentage."""
    return adsl["TRT01A"].value_counts().reindex(ARM_LEVELS).astype(int)


def arm_labels(adsl: pd.DataFrame) -> list[str]:
    """Column labels carrying the arm N, e.g. ``Placebo (N=86)``."""
    n = arm_counts(adsl)
    return [f"{arm} (N={n[arm]})" for arm in ARM_LEVELS]


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    adsl = load_adsl()
    adae = load_adae()
    print(f"adsl: {adsl.shape[0]} rows x {adsl.shape[1]} cols")
    print(f"adae: {adae.shape[0]} rows x {adae.shape[1]} cols")
    print("arm denominators:")
    print(arm_counts(adsl).to_string())
