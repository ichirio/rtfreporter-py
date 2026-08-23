"""Generate synthetic ADaM-shaped data, as a drop-in for :mod:`adam_data`.

Use this when you want to run the showcase examples without the bundled CSVs
-- for instance in a downstream project that cannot vendor the sample data.
It exposes the same ``load_adsl`` / ``load_adae`` / ``arm_counts`` /
``arm_labels`` interface, with the same column contract and the same derived
variables, so the showcase modules work unchanged::

    import adam_synthetic as adam_data   # instead of `import adam_data`

The generator is seeded, so a given ``seed`` always yields the same data.
**The numbers deliberately do NOT match the real dataset** -- this is invented
data for shape and plumbing, not a reproduction of the CDISC pilot study.  Use
:mod:`adam_data` when you want the figures in
``data-raw/R_reference_numbers.txt``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from adam_data import (  # noqa: F401  (re-exported so callers can swap modules)
    AGEGR_BINS,
    AGEGR_LABELS,
    ANY_AE,
    ARM_LEVELS,
    RACE_LABELS,
    RACE_LEVELS,
    SEX_LABELS,
    SEX_LEVELS,
    arm_counts,
    arm_labels,
)

DEFAULT_SEED = 20260823

#: Subjects per arm, in :data:`ARM_LEVELS` order.
DEFAULT_ARM_SIZES = (86, 96, 72)

#: A small MedDRA-shaped dictionary: system organ class -> preferred terms.
SOC_PT = {
    "CARDIAC DISORDERS": ["SINUS BRADYCARDIA", "MYOCARDIAL INFARCTION"],
    "GASTROINTESTINAL DISORDERS": ["DIARRHOEA", "NAUSEA", "VOMITING"],
    "GENERAL DISORDERS AND ADMINISTRATION SITE CONDITIONS": [
        "APPLICATION SITE PRURITUS",
        "APPLICATION SITE ERYTHEMA",
        "FATIGUE",
    ],
    "NERVOUS SYSTEM DISORDERS": ["DIZZINESS", "HEADACHE", "SOMNOLENCE"],
    "SKIN AND SUBCUTANEOUS TISSUE DISORDERS": ["PRURITUS", "ERYTHEMA", "RASH"],
}

#: Per-arm probability that a subject reports a given preferred term.  The
#: active arms are made more eventful so the table has a visible gradient.
_ARM_EVENT_RATE = (0.10, 0.18, 0.24)


def _ordered(values, levels, labels=None):
    cat = pd.Categorical(values, categories=levels, ordered=True)
    out = pd.Series(cat)
    if labels is not None:
        out = out.cat.rename_categories(labels)
    return out


def load_adsl(seed: int = DEFAULT_SEED, arm_sizes=DEFAULT_ARM_SIZES) -> pd.DataFrame:
    """Generate a synthetic subject-level dataset with the ADaM columns used here."""
    rng = np.random.default_rng(seed)
    usubjid, arms = [], []
    for arm, size in zip(ARM_LEVELS, arm_sizes, strict=True):
        start = len(usubjid) + 1
        usubjid += [f"SYNTH-{i:04d}" for i in range(start, start + size)]
        arms += [arm] * size
    n = len(usubjid)

    age = np.clip(rng.normal(75, 8, n).round(), 50, 92).astype(int)
    adsl = pd.DataFrame(
        {
            "USUBJID": usubjid,
            "TRT01A": arms,
            "AGE": age,
            "SEX": rng.choice(SEX_LEVELS, n, p=[0.4, 0.6]),
            "RACE": rng.choice(RACE_LEVELS, n, p=[0.86, 0.10, 0.02, 0.02]),
            "ETHNIC": "NOT HISPANIC OR LATINO",
            "SAFFL": "Y",
        }
    )
    adsl["TRT01A"] = _ordered(adsl["TRT01A"], ARM_LEVELS)
    adsl["SEX"] = _ordered(adsl["SEX"], SEX_LEVELS, SEX_LABELS)
    adsl["RACE"] = _ordered(adsl["RACE"], RACE_LEVELS, RACE_LABELS)
    adsl["AGEGR"] = pd.cut(
        adsl["AGE"], bins=AGEGR_BINS, labels=AGEGR_LABELS, right=False, ordered=True
    )
    return adsl


def load_adae(adsl: pd.DataFrame | None = None, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    """Generate synthetic treatment-emergent adverse events for ``adsl``."""
    if adsl is None:
        adsl = load_adsl(seed=seed)
    rng = np.random.default_rng(seed + 1)
    rate = dict(zip(ARM_LEVELS, _ARM_EVENT_RATE, strict=True))

    records = []
    for subject in adsl.itertuples(index=False):
        p = rate[str(subject.TRT01A)]
        for soc, pts in SOC_PT.items():
            for pt in pts:
                if rng.random() < p:
                    # A subject may report the same PT more than once.
                    for _ in range(1 + int(rng.random() < 0.25)):
                        records.append(
                            {
                                "USUBJID": subject.USUBJID,
                                "TRT01A": str(subject.TRT01A),
                                "AESOC": soc,
                                "AEDECOD": pt,
                                "TRTEMFL": "Y",
                            }
                        )
    adae = pd.DataFrame.from_records(
        records, columns=["USUBJID", "TRT01A", "AESOC", "AEDECOD", "TRTEMFL"]
    )
    adae["TRT01A"] = _ordered(adae["TRT01A"], ARM_LEVELS)
    return adae


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    adsl = load_adsl()
    adae = load_adae(adsl)
    print(f"synthetic adsl: {adsl.shape[0]} rows x {adsl.shape[1]} cols")
    print(f"synthetic adae: {adae.shape[0]} rows x {adae.shape[1]} cols")
    print(arm_counts(adsl).to_string())
