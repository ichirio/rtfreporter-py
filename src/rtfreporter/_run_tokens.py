"""``{PROGRAM}`` / ``{PROGRAM_FULL}`` / ``{PROGRAM_NAME}`` / ``{PROGRAM_DIR}`` /
``{DATETIME}``, and tokens of one's own (``{STUDY}``).

Ported from ``R/generate_rtfreport.R`` and ``R/user_tokens.R``.  What a footer
says about the run: which program wrote the file and when.  They are filled
while the file is RENDERED -- so "Generated on" is the time the file was
generated, not the time a footer was built -- from a context
:func:`run_context` sets for the length of one render.  Every page of a file
therefore shows the same time.  The text reaching
:func:`substitute_run_tokens` is already RTF-escaped, so a token reads
``\\{PROGRAM\\}``.

The program is *said* (``generate_rtfreport(program=)``, then
``rtf_document(program=)``, then the ``program`` option) or, when a
``{PROGRAM...}`` token first needs it, *found*: the script Python runs
(``__main__.__file__`` / ``sys.argv[0]``), then the notebook Jupyter runs
(VS Code's ``__vsc_ipynb_file__``, Jupyter's ``JPY_SESSION_NAME``), then
``program_fallback``.  A program found is said in a message on stderr (R's
``message()``); one said is not.
"""

from __future__ import annotations

import datetime as _dt
import ntpath
import os
import posixpath
import re
import sys
from contextlib import contextmanager

from .config import _opt

_CTX: dict = {"program": None, "program_fallback": None, "program_done": False,
              "time": None, "tokens": None, "active": False}

#: The tokens the RENDERER fills (R ``.RENDER_TOKENS``): a column header's
#: ``set_col_header(values=)`` leaves them alone, and a token of one's own may
#: not take one of these names.
RENDER_TOKENS = ("PAGE", "TOTAL_PAGES", "BOOK_PAGE", "AUTO_PAGE", "AUTO_TOTAL_PAGES",
                 "SECTION_PAGES", "PROGRAM", "PROGRAM_FULL", "PROGRAM_NAME",
                 "PROGRAM_DIR", "DATETIME")

# strftime in the C locale, so %b is "Sep" wherever the file is written.
_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]
_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _check_program(program, arg: str = "program"):
    if program is not None and not isinstance(program, str):
        raise ValueError(
            f"`{arg}` must be a single string: the path of the program that "
            "writes the file."
        )
    return program


def _resolve_program(program=None):
    """The program SAID: an argument, else the option (quietly)."""
    if program is None:
        program = _opt("program")
    return _check_program(program)


def _program_from_script():
    """The script Python runs: ``__main__.__file__``, else ``sys.argv[0]``
    when it is a file.  Not inside a Jupyter kernel, whose script is the
    kernel launcher."""
    if "ipykernel" in sys.modules:
        return None
    import __main__

    f = getattr(__main__, "__file__", None)
    if isinstance(f, str) and f:
        return f
    a = sys.argv[0] if sys.argv else ""
    if isinstance(a, str) and a and os.path.isfile(a):
        return a
    return None


def _program_from_notebook():
    """The notebook a Jupyter kernel runs, when it is cheaply known: VS Code
    puts it in ``__vsc_ipynb_file__``, Jupyter Server 2 in the kernel's
    ``JPY_SESSION_NAME``."""
    if "ipykernel" not in sys.modules:
        return None
    import __main__

    f = getattr(__main__, "__vsc_ipynb_file__", None) or os.environ.get("JPY_SESSION_NAME")
    if isinstance(f, str) and f:
        return f
    return None


def _find_program():
    ways = (("the script Python runs", _program_from_script),
            ("the notebook Jupyter runs", _program_from_notebook))
    for how, fn in ways:
        f = fn()
        if f is not None:
            return f, how
    return None


#: The extensions a program name with none is completed with, in order.
_PROGRAM_EXTS = (".py", ".ipynb")


def _complete_program(path: str) -> str:
    """A program's file name as it is on disk: the real case of a file that is
    there (``t_dm.py`` that is ``T_DM.PY`` on Windows); with no extension, the
    program of that name in the folder (``.py``, ``.ipynb``), else ``.py``
    added; a name with an extension that is not there, as it is."""
    stem = _basename(path)
    lead = path[: len(path) - len(stem)]
    folder = _dirname(path)
    try:
        here = sorted(os.listdir(folder))
    except OSError:
        here = []

    def pick(name):
        if name in here:
            return name
        m = [h for h in here if h.lower() == name.lower()]
        return m[0] if m else None

    if os.path.isfile(path):
        real = pick(stem)
        return path if real is None else lead + real
    if re.search(r"\.[A-Za-z0-9]+$", stem):
        return path
    for ext in _PROGRAM_EXTS:
        real = pick(stem + ext)
        if real is not None:
            return lead + real
    return path + ".py"


def _message(text: str) -> None:
    print(text, file=sys.stderr)


def _program_now():
    """The program for this file: said, else found (once per file, with a
    message), else ``program_fallback``; ``None`` when there is none."""
    if not _CTX["program_done"]:
        p = _CTX["program"]
        if p is None:
            found = _find_program()
            if found is not None:
                p = found[0]
                _message(f"rtfreporter: {{PROGRAM}} is {_complete_program(p)} ({found[1]}); "
                         "rtf_document(program=) says it for sure.")
            elif _CTX["program_fallback"] is not None:
                # the last resort: no file name was found
                p = _CTX["program_fallback"]
                _message(f"rtfreporter: {{PROGRAM}} is {_complete_program(p)} "
                         "(no file name was found: program_fallback); "
                         "rtf_document(program=) says it for sure.")
        _CTX["program"] = _complete_program(p) if p is not None else None
        _CTX["program_done"] = True
    return _CTX["program"]


def _full_path(path: str) -> str:
    """``{PROGRAM_FULL}``: the program's path made absolute, with the system's
    own separator.  The nearest folder that exists is resolved
    (``os.path.realpath``, R's ``normalizePath()``), and the rest of the path,
    which need not exist yet, is joined to it."""
    p = path
    if not re.match(r"^([A-Za-z]:)?[/\\]", p):
        p = os.path.join(os.getcwd(), p)
    rest: list[str] = []
    d = p
    while not os.path.exists(d) and os.path.dirname(d) != d:
        rest.insert(0, os.path.basename(d))
        d = os.path.dirname(d)
    base = os.path.realpath(d)
    # "." and ".." in the part that does not exist
    parts: list[str] = []
    for x in rest:
        if x in (".", ""):
            continue
        if x == "..":
            if parts:
                parts.pop()
            else:
                base = os.path.dirname(base)
            continue
        parts.append(x)
    if not parts:
        return base
    return os.sep.join([base.rstrip("/\\")] + parts)


# -- tokens of one's own (R/user_tokens.R) -----------------------------------

_USER_TOKEN_RX = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _check_user_tokens(x, where: str = "`tokens`"):
    """The tokens of one's own as a ``{name: text}`` dict (``None``: none)."""
    if x is None or (hasattr(x, "__len__") and len(x) == 0):
        return None
    if not isinstance(x, dict):
        raise ValueError(f'{where} is a dict of values, e.g. {{"STUDY": "ABC-123"}}.')
    names = list(x)
    if any(not isinstance(n, str) or not n for n in names):
        raise ValueError(f'{where}: every token has a name, e.g. {{"STUDY": "ABC-123"}}.')
    bad = [n for n in names if not _USER_TOKEN_RX.match(n)]
    if bad:
        raise ValueError(
            f"{where}: a token's name is upper case -- a letter, then letters, "
            "digits or _ (STUDY, DATA_CUTOFF): not "
            + ", ".join(f"`{b}`" for b in bad) + "."
        )
    own = [n for n in names if n in RENDER_TOKENS]
    if own:
        raise ValueError(
            f"{where}: " + ", ".join(f"{{{n}}}" for n in own)
            + " is rtfreporter's own token; give yours another name."
        )
    out = {}
    for n, v in x.items():
        ok = isinstance(v, (str, int, float)) and not (isinstance(v, float) and v != v)
        if not ok:
            raise ValueError(f"{where}: `{n}` is one value (a string or a number).")
        out[n] = _token_text(v)
    return out


def _token_text(v) -> str:
    """A value as R's ``as.character()`` writes it."""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float):
        from .catx import _as_text

        return _as_text(v)
    return str(v)


def _user_tokens(doc_tokens=None):
    """The session's tokens and the document's, the document's winning."""
    opt = _check_user_tokens(_opt("tokens"), "rtfreporter_options(tokens=)")
    doc = _check_user_tokens(doc_tokens)
    out = dict(opt or {})
    out.update(doc or {})
    return out or None


def current_tokens():
    """The tokens of one's own of the file being written (outside a render:
    the session's)."""
    return _CTX["tokens"] if _CTX["active"] else _user_tokens()


def _substitute_user_tokens(out: str, tokens=None) -> str:
    """Fill them in text that is already RTF-escaped (a token reads ``\\{STUDY\\}``)."""
    from ._escape import escape

    for nm, val in (tokens or {}).items():
        tok = "\\{" + nm + "\\}"
        if tok in out:
            out = out.replace(tok, escape(val))
    return out


def _resolve_render_time() -> _dt.datetime:
    t = _opt("render_time")
    if t is None:
        return _dt.datetime.now()
    if isinstance(t, _dt.datetime):
        return t
    return _dt.datetime.fromisoformat(str(t))


@contextmanager
def run_context(program=None, program_fallback=None, tokens=None):
    """Fix the program, the time and the tokens of one's own for one render
    (R's ``.run_ctx``).  The program is only looked for when a
    ``{PROGRAM...}`` token needs it."""
    if _CTX["active"]:  # a render inside a render keeps the outer one's
        yield
        return
    _CTX.update(program=_resolve_program(program),
                program_fallback=_check_program(program_fallback, "program_fallback"),
                program_done=False, time=_resolve_render_time(),
                tokens=_user_tokens(tokens), active=True)
    try:
        yield
    finally:
        _CTX.update(program=None, program_fallback=None, program_done=False,
                    time=None, tokens=None, active=False)


def format_run_time(time: _dt.datetime, fmt: str) -> str:
    """``time`` formatted with strftime directives, month and day names in
    English whatever the locale (R formats in the C locale)."""
    def sub(m):
        d = m.group(1)
        if d == "b":
            return _MONTHS[time.month - 1][:3]
        if d == "B":
            return _MONTHS[time.month - 1]
        if d == "a":
            return _DAYS[time.weekday()][:3]
        if d == "A":
            return _DAYS[time.weekday()]
        if d == "p":
            return "AM" if time.hour < 12 else "PM"
        return m.group(0)

    # A literal "%%" is kept out of the directive handling part by part.
    parts = fmt.split("%%")
    return "%".join(time.strftime(re.sub(r"%([bBaAp])", sub, p)) if p else ""
                    for p in parts)


def _dirname(path: str) -> str:
    d = ntpath.dirname(path) if "\\" in path else posixpath.dirname(path)
    return d or "."


def _basename(path: str) -> str:
    return ntpath.basename(path) if "\\" in path else posixpath.basename(path)


def substitute_run_tokens(out: str) -> str:
    """Fill the run tokens, then the tokens of one's own, in ALREADY-escaped text."""
    if not _CTX["active"]:
        with run_context():
            return substitute_run_tokens(out)
    from ._escape import escape

    if r"\{PROGRAM" in out:
        prog = _program_now()
        if prog is None:
            raise ValueError(
                "A header, footer, title or footnote uses {PROGRAM}, "
                "{PROGRAM_FULL}, {PROGRAM_NAME} or {PROGRAM_DIR}, but no program "
                "is known.\n"
                '  Say which with rtf_document(program="path/to/prog.py"), or run '
                "the program as a script (python prog.py)."
            )
        # the longer tokens first: {PROGRAM_FULL} is never read as {PROGRAM}
        out = out.replace(r"\{PROGRAM_FULL\}", escape(_full_path(prog)))
        out = out.replace(r"\{PROGRAM_NAME\}", escape(_basename(prog)))
        out = out.replace(r"\{PROGRAM_DIR\}", escape(_dirname(prog)))
        out = out.replace(r"\{PROGRAM\}", escape(prog))
    if r"\{DATETIME" in out:
        time = _CTX["time"]
        dflt = _opt("datetime_format")
        # `\{DATETIME\}` or `\{DATETIME:<format>\}`, the format up to the `\}`
        for h in dict.fromkeys(re.findall(r"\\\{DATETIME(?::.*?)?\\\}", out)):
            fmt = h[len(r"\{DATETIME"):-2]
            fmt = fmt[1:] if fmt.startswith(":") else fmt
            out = out.replace(h, escape(format_run_time(time, fmt or dflt)))
    # tokens of one's own (rtf_document(tokens=), the option)
    return _substitute_user_tokens(out, _CTX["tokens"])
