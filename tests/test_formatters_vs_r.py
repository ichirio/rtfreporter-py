"""fmt_signif / fmt_round / fmt_numeric / catx, compared with the R package.

The expected values are what R v0.8.2 returned for the same input
(``data-raw/xcheck/formatters_r.R`` writes ``tests/xcheck_golden/formatters.json``).
"""

import json
import math
from pathlib import Path

import pytest

import rtfreporter as rr

GOLDEN = json.loads(
    (Path(__file__).parent / "xcheck_golden" / "formatters.json").read_text(encoding="utf-8")
)


def _x():
    out = []
    for v in GOLDEN["x"]:
        if v is None:
            out.append(None)
        elif v == "NaN":
            out.append(math.nan)
        elif v in ("Inf", "-Inf"):
            out.append(math.inf if v == "Inf" else -math.inf)
        else:
            out.append(float(v))
    return out


@pytest.mark.parametrize(
    "case", GOLDEN["cases"],
    ids=lambda c: f"{c['fn']}-" + "-".join(str(v) for v in c["args"].values()),
)
def test_number_formatters_match_r(case):
    fn = getattr(rr, case["fn"])
    assert fn(_x(), na="NA", **case["args"]) == case["out"]


def _df():
    return {
        "stat": ["n", "  Mean", "SD", "Median", "", "CV%"],
        "a": [24, 902.3312, 230.1234, 0.0004567, None, 23.445],
        "b": [3, 1.5, 2.25, 100.05, None, 99.995],
        "txt": ["x", "y", "z", "w", "", "v"],
    }


def test_fmt_numeric_by_carrier_matches_r():
    got = rr.fmt_numeric(
        _df(), cols=["a", "b", "txt"], by="stat",
        formats={"n": {"digits": 0}, "Mean": {"signif": 4},
                 "SD": {"signif": 4, "small": "fixed"}, ".default": {"digits": 1}},
        rounding="sas",
    )
    assert got == GOLDEN["fmt_numeric"]["by"]


def test_fmt_numeric_one_rule_matches_r():
    assert rr.fmt_numeric(_df(), cols=["a", "b"], signif=3) == GOLDEN["fmt_numeric"]["signif"]
    assert rr.fmt_numeric(_df(), cols="b", digits=2, na="-") == GOLDEN["fmt_numeric"]["digits"]


def test_fmt_numeric_keeps_the_frame_kind():
    pd = pytest.importorskip("pandas")
    got = rr.fmt_numeric(pd.DataFrame(_df()), cols=["a"], signif=3)
    assert isinstance(got, pd.DataFrame)
    assert got["a"].tolist() == GOLDEN["fmt_numeric"]["signif"]["a"]


def test_fmt_numeric_refuses_an_unmatched_key():
    with pytest.raises(ValueError, match="no format for 'SD'"):
        rr.fmt_numeric(_df(), cols="a", by="stat",
                       formats={"n": {"digits": 0}, "Mean": {"signif": 4},
                                "Median": {"digits": 1}, "CV%": {"digits": 1}})


def test_formatters_refuse_text_and_bad_digits():
    with pytest.raises(TypeError, match="already formatted"):
        rr.fmt_signif(["1.2"])
    with pytest.raises(ValueError, match="non-negative integer"):
        rr.fmt_round([1.2], digits=-1)
    assert rr.fmt_signif(23.445, 4, rounding="sas") == "23.45"


def test_catx_matches_r():
    exp = GOLDEN["catx"]
    assert rr.catx(" / ", ["Headache", "Nausea", None, " "], ["Mild", None, "Severe", "x"]) == exp[0]
    assert rr.catx("-", 1, [2.5, None, 0.1 + 0.2]) == exp[1]
    assert rr.catx(", ", ["a", ""], "b") == exp[2]
    with pytest.raises(ValueError, match="same length"):
        rr.catx("-", [1, 2], [1, 2, 3])
