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
    monkeypatch.setattr(_run_tokens, "_find_program", lambda: None)
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


# -- {PROGRAM_FULL} (R #560) ---------------------------------------------------


def test_program_full_is_absolute_from_the_working_folder(fixed_time, tmp_path, monkeypatch):
    (tmp_path / "programs").mkdir()
    (tmp_path / "programs" / "t_dm.py").write_text("")
    monkeypatch.chdir(tmp_path)
    rtf = _doc("{PROGRAM_FULL}|{PROGRAM}", program="programs/t_dm.py").to_rtf()
    full = str((tmp_path / "programs" / "t_dm.py").resolve())
    assert f"{full}|programs/t_dm.py" in rtf


def test_program_full_of_a_path_that_does_not_exist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base = str(tmp_path.resolve())
    full = _run_tokens._full_path
    assert full("new/./sub/../t.py") == f"{base}/new/t.py"
    assert full("../t.py") == f"{str(tmp_path.parent.resolve())}/t.py"
    assert full(".") == base
    assert full(str(tmp_path / "x" / "y.py")) == f"{base}/x/y.py"


def test_program_full_is_listed_as_a_render_token():
    from rtfreporter.post_hoc import _RENDER_TOKENS

    assert "PROGRAM_FULL" in _RENDER_TOKENS
    assert "DATE" not in _RENDER_TOKENS  # R #532: never a token


def test_date_is_not_left_for_the_renderer():
    # R #532: `{DATE}` in a column header is an unfilled token now.
    from rtfreporter.post_hoc import _fill_text_tokens

    with pytest.raises(ValueError, match=r"no value for `\{DATE\}`"):
        _fill_text_tokens("{DATE}", {"x": 1}, "set_col_header()")
    assert _fill_text_tokens("{PROGRAM_FULL}", {}, "w") == "{PROGRAM_FULL}"


# -- finding the program (R #562) ---------------------------------------------


def test_a_program_found_is_said_in_a_message(fixed_time, tmp_path, monkeypatch, capsys):
    script = tmp_path / "t_ae.py"
    script.write_text("")
    monkeypatch.setattr(_run_tokens, "_program_from_script", lambda: str(script))
    rtf = _doc("{PROGRAM_NAME}").to_rtf()
    assert "t_ae.py" in rtf
    err = capsys.readouterr().err
    assert "{PROGRAM} is" in err and "the script Python runs" in err


def test_a_program_said_is_quiet_and_not_searched(fixed_time, monkeypatch, capsys):
    def boom():
        raise AssertionError("searched")

    monkeypatch.setattr(_run_tokens, "_find_program", boom)
    _doc("{PROGRAM}", program="a.py").to_rtf()
    assert capsys.readouterr().err == ""
    # a file with no {PROGRAM...} token searches for nothing
    _doc("{DATETIME}").to_rtf()


def test_the_program_is_found_once_per_file(fixed_time, monkeypatch, capsys):
    calls = []

    def found():
        calls.append(1)
        return ("x.py", "the script Python runs")

    monkeypatch.setattr(_run_tokens, "_find_program", found)
    doc = rr.rtf_document()
    doc = rr.rtf_tables(doc, [rr.rtftable({"A": ["1"]})] * 2,
                        titles=["{PROGRAM}", "{PROGRAM_NAME}"])
    doc = rr.rtf_section(doc, page=1, footer=rr.rtf_footer([{"l": "{PROGRAM}"}]))
    doc.to_rtf()
    assert len(calls) == 1
    assert capsys.readouterr().err.count("rtfreporter:") == 1


def test_program_from_script(monkeypatch, tmp_path):
    import sys

    import __main__

    monkeypatch.delitem(sys.modules, "ipykernel", raising=False)
    monkeypatch.setattr(__main__, "__file__", "/work/t_lb.py", raising=False)
    assert _run_tokens._program_from_script() == "/work/t_lb.py"
    monkeypatch.delattr(__main__, "__file__")
    f = tmp_path / "run.py"
    f.write_text("")
    monkeypatch.setattr(sys, "argv", [str(f)])
    assert _run_tokens._program_from_script() == str(f)
    monkeypatch.setattr(sys, "argv", ["-c"])
    assert _run_tokens._program_from_script() is None
    # inside a Jupyter kernel the script is the kernel launcher: not a program
    monkeypatch.setitem(sys.modules, "ipykernel", object())
    monkeypatch.setattr(__main__, "__file__", "/x/ipykernel_launcher.py", raising=False)
    assert _run_tokens._program_from_script() is None


def test_program_from_notebook(monkeypatch):
    import sys

    import __main__

    monkeypatch.delitem(sys.modules, "ipykernel", raising=False)
    monkeypatch.setenv("JPY_SESSION_NAME", "/nb/t_vs.ipynb")
    assert _run_tokens._program_from_notebook() is None  # not a kernel
    monkeypatch.setitem(sys.modules, "ipykernel", object())
    assert _run_tokens._program_from_notebook() == "/nb/t_vs.ipynb"
    monkeypatch.setattr(__main__, "__vsc_ipynb_file__", "/vs/t_eg.ipynb", raising=False)
    assert _run_tokens._program_from_notebook() == "/vs/t_eg.ipynb"
    monkeypatch.delattr(__main__, "__vsc_ipynb_file__")
    monkeypatch.delenv("JPY_SESSION_NAME")
    assert _run_tokens._program_from_notebook() is None
    # the order: a script first, then a notebook
    monkeypatch.setattr(_run_tokens, "_program_from_script", lambda: None)
    monkeypatch.setattr(_run_tokens, "_program_from_notebook", lambda: "n.ipynb")
    assert _run_tokens._find_program() == ("n.ipynb", "the notebook Jupyter runs")


def test_complete_program(tmp_path):
    (tmp_path / "T_DM.PY").write_text("")
    (tmp_path / "t_ae.ipynb").write_text("")
    d = str(tmp_path)
    cp = _run_tokens._complete_program
    # a file that is there keeps its real case (only where the file system
    # matches names case-insensitively does a different case find it)
    assert cp(f"{d}/T_DM.PY") == f"{d}/T_DM.PY"
    # no extension: the program of that name in the folder, any case
    assert cp(f"{d}/t_dm") == f"{d}/T_DM.PY"
    assert cp(f"{d}/t_ae") == f"{d}/t_ae.ipynb"
    # else ".py"; a name with an extension that is not there, as it is
    assert cp(f"{d}/t_lb") == f"{d}/t_lb.py"
    assert cp(f"{d}/t_lb.R") == f"{d}/t_lb.R"
    assert cp("no/such/folder/t_x") == "no/such/folder/t_x.py"


def test_program_is_completed_when_said(fixed_time, tmp_path):
    (tmp_path / "t_dm.py").write_text("")
    rtf = _doc("{PROGRAM_NAME}", program=str(tmp_path / "t_dm")).to_rtf()
    assert "t_dm.py" in rtf


def test_program_must_be_a_string():
    with pytest.raises(ValueError, match="`program` must be a single string"):
        rr.rtf_document(program=3)
    with pytest.raises(ValueError, match="`program_fallback` must be a single string"):
        rr.rtf_document(program_fallback=["a", "b"])


# -- program_fallback (R #566) -------------------------------------------------


def test_program_fallback_is_the_last_resort(fixed_time, monkeypatch, capsys):
    monkeypatch.setattr(_run_tokens, "_find_program", lambda: None)
    doc = rr.rtf_document(program_fallback="t_fb")
    doc = rr.rtf_tables(doc, [rr.rtftable({"A": ["1"]})])
    doc = rr.rtf_section(doc, page=1, footer=rr.rtf_footer([{"l": "{PROGRAM}"}]))
    assert "t_fb.py" in doc.to_rtf()
    assert "no file name was found: program_fallback" in capsys.readouterr().err
    # generate_rtfreport(program_fallback=) overrides the document's
    assert "other.py" in doc.to_rtf(program_fallback="other.py")
    # a program found wins over the fallback
    monkeypatch.setattr(_run_tokens, "_find_program", lambda: ("found.py", "x"))
    assert "found.py" in doc.to_rtf()
    # and one said wins over both, quietly
    capsys.readouterr()
    assert "said.py" in doc.to_rtf(program="said.py")
    assert capsys.readouterr().err == ""


def test_generate_rtfreport_takes_program_fallback(fixed_time, tmp_path, monkeypatch):
    monkeypatch.setattr(_run_tokens, "_find_program", lambda: None)
    out = tmp_path / "o.rtf"
    rr.generate_rtfreport(_doc("{PROGRAM_NAME}"), str(out), program_fallback="fb.py")
    assert "fb.py" in out.read_text()


def test_program_fallback_survives_the_builders():
    doc = rr.rtf_document(program_fallback="fb.py", tokens={"STUDY": "S1"})
    doc = rr.rtf_config(rr.rtf_tables(doc, [rr.rtftable({"A": ["1"]})]), page={})
    assert doc.program_fallback == "fb.py"
    assert doc.tokens == {"STUDY": "S1"}


def test_substitution_outside_a_render(monkeypatch):
    # the escape layer works on its own too (a context is set for the call)
    from rtfreporter._escape import render_tokens

    monkeypatch.setattr(_run_tokens, "_find_program", lambda: None)
    old = rr.rtfreporter_options(program="opt.py", tokens={"STUDY": "S9"})
    try:
        assert render_tokens("{PROGRAM} {STUDY}") == "opt.py S9"
    finally:
        rr.rtfreporter_options(**old)
