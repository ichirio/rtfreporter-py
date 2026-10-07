"""Tokens of one's own (R #564), rtf_text_tokens() (R #529) and
rtf_header() / rtf_footer(drop_empty_rows=) (R #571)."""

import pytest

import rtfreporter as rr
from rtfreporter import _run_tokens
from rtfreporter.header_footer import hf_row_empty


def _doc(header_rows, tokens=None, drop=False, title=None):
    doc = rr.rtf_document(tokens=tokens)
    doc = rr.rtf_tables(doc, [rr.rtftable({"A": ["1"]})],
                        titles=[title] if title else None)
    hdr = rr.rtf_header(header_rows, drop_empty_rows=drop)
    return rr.rtf_section(doc, page=1, header=hdr)


@pytest.fixture
def no_tokens_option():
    old = rr.rtfreporter_options(tokens=None)
    yield
    rr.rtfreporter_options(**old)


def test_document_tokens_fill_headers_titles_and_footnotes(no_tokens_option):
    doc = _doc([{"l": "Study {STUDY}", "r": "Cut-off {CUTOFF}"}],
               tokens={"STUDY": "ABC-123", "CUTOFF": "01JUN2026"},
               title="Table 1 {STUDY}")
    doc = rr.rtf_footnotes(doc, ["Source: {STUDY}"])
    rtf = doc.to_rtf()
    assert "Study ABC-123" in rtf and "Cut-off 01JUN2026" in rtf
    assert "Table 1 ABC-123" in rtf and "Source: ABC-123" in rtf
    assert "{STUDY}" not in rtf


def test_values_are_rtf_escaped_and_numbers_are_text(no_tokens_option):
    rtf = _doc([{"l": "{A} {N} {F}"}],
               tokens={"A": "a{b}\\c", "N": 3, "F": 0.5}).to_rtf()
    assert r"a\{b\}\\c 3 0.5" in rtf


def test_the_option_sets_them_for_a_session_and_the_document_wins(no_tokens_option):
    rr.rtfreporter_options(tokens={"STUDY": "OPT", "SITE": "S01"})
    rtf = _doc([{"l": "{STUDY}/{SITE}"}], tokens={"STUDY": "DOC"}).to_rtf()
    assert "DOC/S01" in rtf


def test_an_unknown_token_is_left_as_written(no_tokens_option):
    assert r"\{OTHER\}" in _doc([{"l": "{OTHER}"}], tokens={"STUDY": "x"}).to_rtf()


@pytest.mark.parametrize("tokens, msg", [
    ("ABC", "dict of values"),
    ({"study": "x"}, "upper case"),
    ({"1ST": "x"}, "upper case"),
    ({"PAGE": "x"}, "rtfreporter's own token"),
    ({"PROGRAM_FULL": "x"}, "rtfreporter's own token"),
    ({"STUDY": ["a", "b"]}, "one value"),
    ({"STUDY": None}, "one value"),
    ({"STUDY": float("nan")}, "one value"),
    ({"": "x"}, "every token has a name"),
])
def test_tokens_are_checked(tokens, msg):
    with pytest.raises(ValueError, match=msg):
        rr.rtf_document(tokens=tokens)


def test_the_option_is_checked_when_used(no_tokens_option):
    rr.rtfreporter_options(tokens={"bad": "x"})
    with pytest.raises(ValueError, match=r"rtfreporter_options\(tokens=\)"):
        _doc([{"l": "x"}]).to_rtf()


def test_logical_value_reads_as_r_writes_it(no_tokens_option):
    assert "TRUE" in _doc([{"l": "{FLAG}"}], tokens={"FLAG": True}).to_rtf()


# -- rtf_text_tokens() ---------------------------------------------------------


def test_rtf_text_tokens_lists_every_token(no_tokens_option):
    rows = rr.rtf_text_tokens()
    assert [r["token"] for r in rows] == [
        "{PAGE}", "{TOTAL_PAGES}", "{AUTO_PAGE}", "{AUTO_TOTAL_PAGES}", "{BOOK_PAGE}",
        "{PROGRAM}", "{PROGRAM_FULL}", "{PROGRAM_NAME}", "{PROGRAM_DIR}", "{DATETIME}"]
    assert set(rows[0]) == {"token", "kind", "when", "description", "example"}
    assert {r["kind"] for r in rows} == {"page", "run"}
    assert {r["when"] for r in rows} == {"render", "viewer", "assemble"}
    # every listed token is one the renderer knows
    for r in rows:
        assert r["token"][1:-1] in _run_tokens.RENDER_TOKENS


def test_rtf_text_tokens_every_listed_token_is_replaced(no_tokens_option):
    old = rr.rtfreporter_options(render_time="2026-10-04 10:05:00")
    try:
        line = " ".join(r["token"] for r in rr.rtf_text_tokens())
        rtf = _doc([{"l": line}]).to_rtf(program="p/t.py")
    finally:
        rr.rtfreporter_options(**old)
    for r in rr.rtf_text_tokens():
        assert "\\" + r["token"][:-1] + "\\}" not in rtf, r["token"]


def test_rtf_text_tokens_own_tokens(no_tokens_option):
    rr.rtfreporter_options(tokens={"SITE": "S01"})
    doc = rr.rtf_document(tokens={"STUDY": "ABC"})
    own = [r for r in rr.rtf_text_tokens(doc) if r["kind"] == "own"]
    assert [(r["token"], r["example"], r["when"]) for r in own] == [
        ("{SITE}", "S01", "render"), ("{STUDY}", "ABC", "render")]
    assert [r["token"] for r in rr.rtf_text_tokens() if r["kind"] == "own"] == ["{SITE}"]
    with pytest.raises(TypeError, match="RtfDocument"):
        rr.rtf_text_tokens("doc")


# -- drop_empty_rows -----------------------------------------------------------


def test_drop_empty_rows_leaves_out_a_row_whose_own_tokens_are_empty(no_tokens_option):
    rows = [{"l": "Protocol {STUDY}", "r": "Page {PAGE}"},
            {"l": "<{POPULATION}>"},
            {"c": "Draft"}]
    toks = {"STUDY": "ABC", "POPULATION": ""}
    kept = _doc(rows, toks, drop=True).to_rtf()
    assert "&lt;" not in kept and "<>" not in kept
    assert kept.count(r"\trowd") == _doc(rows, toks).to_rtf().count(r"\trowd") - 1
    # with a value, the row is written
    full = _doc(rows, {"STUDY": "ABC", "POPULATION": "Safety"}, drop=True).to_rtf()
    assert "<Safety>" in full


def test_drop_empty_rows_default_writes_every_row(no_tokens_option):
    rtf = _doc([{"l": "<{POPULATION}>"}], {"POPULATION": ""}).to_rtf()
    assert "<>" in rtf


def test_a_band_with_every_row_dropped_is_no_band(no_tokens_option):
    rtf = _doc([{"l": "{POPULATION}"}], {"POPULATION": " "}, drop=True).to_rtf()
    assert r"{\header" not in rtf


@pytest.mark.parametrize("row, empty", [
    ({"l": "{A}"}, True),
    ({"l": "({A}) [{B}]", "r": " - {A}; "}, True),
    ({"l": "{A}", "r": "x"}, False),        # says something else
    ({"l": "{A} {C}"}, False),             # C has a value
    ({"l": "{A} {PAGE}"}, False),          # rtfreporter's own
    ({"l": "{A} {UNKNOWN}"}, False),       # an unknown one
    ({"l": "plain"}, False),               # no token
    ({"l": "{lower}"}, False),
])
def test_hf_row_empty(row, empty):
    assert hf_row_empty(row, {"A": "", "B": "  ", "C": "c"}) is empty


def test_drop_empty_rows_is_checked_and_kept_by_auto_sections(no_tokens_option):
    with pytest.raises(ValueError, match="drop_empty_rows"):
        rr.rtf_footer([{"l": "x"}], drop_empty_rows="yes")
    hdr = rr.rtf_header([{"l": "<{POP}>"}], drop_empty_rows=True)
    doc = rr.rtf_section(rr.rtf_document(tokens={"POP": ""}), header=hdr)
    t = rr.as_rtftables({"G": ["a", "b"], "V": ["1", "2"]}, split="by_value", group_col="G",
                        drop_cols="G")
    rtf = rr.rtf_tables(doc, t, auto_section=True).to_rtf()
    assert "<>" not in rtf and "a" in rtf
