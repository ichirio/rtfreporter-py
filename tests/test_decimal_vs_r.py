"""set_decimal_split(), compared byte-for-byte with the R package
(``data-raw/xcheck/decimal_r.R`` writes ``tests/xcheck_golden/decimal/``)."""

from pathlib import Path

import pytest

import rtfreporter as rr

GOLDEN = Path(__file__).parent / "xcheck_golden" / "decimal"
DF = {"Stat": ["n", "Mean", "SD", "Min, Max", "p-value", "Median", "CV"],
      "A": ["12", "3.45", "0.123", "1.0, 9.9", "<0.001", None, ".5"],
      "B": ["100", "12.3 (4.56)", "7.1", "n/a", "0.045", "15", "2.25"]}


def _rtf(tbl):
    return rr.rtf_tables(rr.rtf_document(), [tbl]).to_rtf()


def _golden(name):
    return (GOLDEN / f"{name}.rtf").read_text(encoding="ascii").replace("\r\n", "\n")


def test_default_matches_r():
    assert _rtf(rr.set_decimal_split(rr.rtftable(DF), cols=["A", "B"])) == _golden("default")


def test_ratio_compound_box_matches_r():
    t = rr.rtftable(DF, border=rr.rtf_border(all=True))
    t = rr.set_decimal_split(t, cols="B", ratio=0.3, include_compound=True)
    assert _rtf(t) == _golden("ratio_compound_box")


def test_styles_and_size_match_r():
    t = rr.rtftable(DF, font_size_half_points=20, cell_styles=[
        None, {"bold": [None, True, None]}, None, None, None, None,
        {"color": [None, "#FF0000", None]}])
    t = rr.set_decimal_split(t, cols=1, pad_chars=(0, 0), min_chars=(0, 0))
    assert _rtf(t) == _golden("styles_size")


def test_arguments_are_checked():
    t = rr.rtftable(DF)
    with pytest.raises(ValueError, match="`cols` is required"):
        rr.set_decimal_split(t)
    with pytest.raises(ValueError, match="strictly between"):
        rr.set_decimal_split(t, cols="A", ratio=1)
    with pytest.raises(ValueError, match="two non-negative"):
        rr.set_decimal_split(t, cols="A", pad_chars=(1,))
    cleared = rr.set_decimal_split(rr.set_decimal_split(t, cols="A"), cols=None)
    assert cleared.decimal_split is None
    # an integer-only column is left alone
    ints = rr.set_decimal_split(rr.rtftable({"A": ["1", "2"]}), cols="A")
    assert _rtf(ints) == _rtf(rr.rtftable({"A": ["1", "2"]}))
