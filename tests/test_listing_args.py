"""listing_col() / listing_spec() / build_listing() / fit_listing_widths()
argument checks and small behaviours (parity is in test_listing_vs_r.py)."""

import math

import pytest

import rtfreporter as rr

DATA = {"ID": ["1", "2"], "T": ["a b", "c"], "U": ["x", "y"]}


@pytest.mark.parametrize("kw, msg", [
    ({"vars": []}, "vars"),
    ({"vars": "ID", "sep": 3}, "sep"),
    ({"vars": "ID", "width": 0}, "width"),
    ({"vars": "ID", "rel_width": -1}, "rel_width"),
    ({"vars": "ID", "label": 5}, "label"),
    ({"vars": "ID", "name": ""}, "name"),
    ({"vars": "ID", "align": "middle"}, "align"),
    ({"vars": "ID", "layout": "wide"}, "layout"),
    ({"vars": "ID", "collapse_repeats": "yes"}, "collapse_repeats"),
])
def test_listing_col_checks(kw, msg):
    with pytest.raises(ValueError, match=msg):
        rr.listing_col(**kw)


@pytest.mark.parametrize("kw, msg", [
    ({"cols": None}, "required"),
    ({"cols": []}, "non-empty"),
    ({"cols": ["ID"], "type": "grid"}, "Unknown listing type"),
    ({"cols": ["ID"], "spacer": 1}, "spacer"),
    ({"cols": ["ID"], "spacer_rel_width": 0}, "spacer_rel_width"),
    ({"cols": ["ID"], "align": "x"}, "align"),
    ({"cols": ["ID"], "layout": "x"}, "layout"),
    ({"cols": ["ID"], "wrap": 3}, "wrap"),
    ({"cols": ["ID"], "wrap": lambda a, b: a}, "four arguments"),
    ({"cols": ["ID"], "record": 3}, "record"),
    ({"cols": [3]}, "cols"),
])
def test_listing_spec_checks(kw, msg):
    with pytest.raises(ValueError, match=msg):
        rr.listing_spec(**kw)


def test_duplicate_names_are_made_unique_and_record_named():
    spec = rr.listing_spec(["ID", "ID", rr.listing_col(["T", "U"])], record="REC")
    assert [c.name for c in spec.cols] == ["ID", "ID_1", "T"]
    body = rr.build_listing(DATA, spec)
    assert body.column_names[-1] == "REC"
    with pytest.raises(ValueError, match="already been through"):
        rr.build_listing(body, spec)
    with pytest.raises(ValueError, match="not in `data`"):
        rr.build_listing(DATA, rr.listing_spec(["ZZ"]))


def test_custom_wrap_and_bad_wrap_result():
    spec = rr.listing_spec([rr.listing_col("T", width=2)],
                           wrap=lambda text, width, sep, layout: [text.upper()])
    assert rr.build_listing(DATA, spec).rows[0][0] == "A B"
    assert "custom `wrap`" in rr.listing_code(spec)
    bad = rr.listing_spec([rr.listing_col("T", width=2)],
                          wrap=lambda text, width, sep, layout: [])
    with pytest.raises(ValueError, match="non-empty list"):
        rr.build_listing(DATA, bad)


def test_listing_arg_conflicts():
    body = rr.build_listing(DATA, rr.listing_spec(["ID"]))
    with pytest.raises(ValueError, match="already built"):
        rr.as_rtftables(body, listing=rr.listing_spec(["ID"]))
    with pytest.raises(ValueError, match="listing_spec"):
        rr.as_rtftables(DATA, listing="x")
    pages = rr.as_rtftables(body)
    assert pages[0].column_names[0] == "ID"


def test_fit_checks_and_infinite_header():
    spec = rr.listing_spec(["ID", "T"])
    with pytest.raises(ValueError, match="min_width"):
        rr.fit_listing_widths(DATA, spec, min_width=0)
    with pytest.raises(ValueError, match="probs"):
        rr.fit_listing_widths(DATA, spec, probs=2)
    with pytest.raises(ValueError, match="header_lines"):
        rr.fit_listing_widths(DATA, spec, header_lines=0)
    with pytest.raises(ValueError, match="cannot each be"):
        rr.fit_listing_widths(DATA, spec, total_width=5)
    with pytest.raises(ValueError, match="labels"):
        rr.fit_listing_widths(DATA, spec, labels=[1])
    fitted = rr.fit_listing_widths(DATA, spec, header_lines=math.inf, total_width=40)
    assert sum(c.width for c in fitted.cols) + fitted.fit["gutter"] == 40
    assert "listing_col('ID'" in rr.listing_code(fitted)


def test_wrap_helpers():
    assert rr.listing_disp_width(["ab", "頭"]) == [2, 2]
    assert rr.listing_take("abcdef", 3) == "abc"
    assert rr.listing_split_after("a/b", None) == ["a/b"]
    assert rr.listing_wrap("a/b", None) == ["a/b"]
    assert rr.listing_wrap(["a", "b"], 5) == [["a"], ["b"]]
    with pytest.raises(ValueError):
        rr.listing_wrap("a", 5, layout="x")
    with pytest.raises(ValueError):
        rr.listing_wrap_code("1bad")
