"""``{PROGRAM}`` / ``{PROGRAM_NAME}`` / ``{PROGRAM_DIR}`` / ``{DATETIME}``.

Ported from ``R/generate_rtfreport.R``.  What a footer says about the run:
which program wrote the file and when.  They are filled while the file is
RENDERED -- so "Generated on" is the time the file was generated, not the
time a footer was built -- from a context :func:`run_context` sets for the
length of one render.  Every page of a file therefore shows the same time.
The text reaching :func:`substitute_run_tokens` is already RTF-escaped, so a
token reads ``\\{PROGRAM\\}``.
"""

from __future__ import annotations

import datetime as _dt
import ntpath
import posixpath
import re
from contextlib import contextmanager

from .config import _opt

_CTX: dict = {"program": None, "time": None, "active": False}

# strftime in the C locale, so %b is "Sep" wherever the file is written.
_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]
_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _resolve_program(program=None):
    """The program: an argument, else the option, else the script Python runs."""
    if program is None:
        program = _opt("program")
    if program is None:
        import __main__

        f = getattr(__main__, "__file__", None)
        if isinstance(f, str) and f:
            program = f
    if program is not None and not isinstance(program, str):
        raise ValueError(
            "`program` must be a single string: the path of the program that "
            "writes the file."
        )
    return program


def _resolve_render_time() -> _dt.datetime:
    t = _opt("render_time")
    if t is None:
        return _dt.datetime.now()
    if isinstance(t, _dt.datetime):
        return t
    return _dt.datetime.fromisoformat(str(t))


@contextmanager
def run_context(program=None):
    """Fix the program and the time for one render (R's ``.run_ctx``)."""
    if _CTX["active"]:  # a render inside a render keeps the outer one's
        yield
        return
    _CTX.update(program=_resolve_program(program), time=_resolve_render_time(), active=True)
    try:
        yield
    finally:
        _CTX.update(program=None, time=None, active=False)


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
    """Fill the run tokens in ALREADY-escaped text."""
    from ._escape import escape

    if r"\{PROGRAM" in out:
        prog = _CTX["program"] if _CTX["active"] else _resolve_program()
        if prog is None:
            raise ValueError(
                "A header, footer, title or footnote uses {PROGRAM}, "
                "{PROGRAM_NAME} or {PROGRAM_DIR}, but no program is known.\n"
                '  Say which: generate_rtfreport(..., program="path/to/prog.py") '
                "or rtfreporter_options(program=...)."
            )
        out = out.replace(r"\{PROGRAM_NAME\}", escape(_basename(prog)))
        out = out.replace(r"\{PROGRAM_DIR\}", escape(_dirname(prog)))
        out = out.replace(r"\{PROGRAM\}", escape(prog))
    if r"\{DATETIME" in out:
        time = _CTX["time"] if _CTX["active"] else _resolve_render_time()
        dflt = _opt("datetime_format")
        # `\{DATETIME\}` or `\{DATETIME:<format>\}`, the format up to the `\}`
        for h in dict.fromkeys(re.findall(r"\\\{DATETIME(?::.*?)?\\\}", out)):
            fmt = h[len(r"\{DATETIME"):-2]
            fmt = fmt[1:] if fmt.startswith(":") else fmt
            out = out.replace(h, escape(format_run_time(time, fmt or dflt)))
    return out
