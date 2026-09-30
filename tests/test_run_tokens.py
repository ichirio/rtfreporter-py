"""The run tokens ({PROGRAM} / {PROGRAM_NAME} / {PROGRAM_DIR} / {DATETIME})
and the {BOOK_PAGE} slot (R #413); byte parity is in the xcheck case run_tokens."""

import datetime as dt

import pytest

import rtfreporter as rr
from rtfreporter import _run_tokens


def _doc(text, program=None):
    doc = rr.rtf_document(program=program)
    doc = rr.rtf_tables(doc, [rr.rtftable({"A": ["1"]})])
    footer = rr.rtf_footer([{"l": text}])
    return rr.rtf_section(doc, page=1, footer=footer)


@pytest.fixture
def fixed_time():
    old = rr.rtfreporter_options(render_time="2026-09-07 09:05:00")
    yield
    rr.rtfreporter_options(**old)


def test_program_from_document_argument_and_option(fixed_time):
    assert "prog/a.py" in _doc("{PROGRAM}", program="prog/a.py").to_rtf()
    # an explicit program wins over the document's
    assert "b.py" in _doc("{PROGRAM_NAME}", program="prog/a.py").to_rtf(program="x/b.py")
    old = rr.rtfreporter_options(program="opt/c.py")
    try:
        rtf = _doc("{PROGRAM_DIR}|{PROGRAM_NAME}").to_rtf()
    finally:
        rr.rtfreporter_options(**old)
    assert "opt|c.py" in rtf


def test_no_program_known_is_an_error(fixed_time, monkeypatch):
    monkeypatch.setattr(_run_tokens, "_resolve_program", lambda program=None: program)
    with pytest.raises(ValueError, match="no program is known"):
        _doc("{PROGRAM}").to_rtf()


def test_datetime_default_and_format(fixed_time):
    rtf = _doc("{DATETIME}|{DATETIME:%Y-%m-%d %b %a}").to_rtf()
    assert "07Sep2026  09:05|2026-09-07 Sep Mon" in rtf


def test_datetime_is_one_time_for_the_whole_render():
    t = dt.datetime(2026, 1, 2, 3, 4)
    assert _run_tokens.format_run_time(t, "%d%b%Y %%b") == "02Jan2026 %b"


def test_book_page_is_an_empty_slot():
    assert r"{\*\rtfreporterbookpage}" in _doc("p {BOOK_PAGE}").to_rtf()
