"""Package-wide configurable defaults (the R ``rtfreporter.*`` options).

Ported from ``R/defaults.R``.  The single source of truth is
:data:`_FACTORY_DEFAULTS`; session overrides live in a module-level dict.  The
resolution order used throughout the package (highest wins) mirrors R:

1. an explicit function argument,
2. the option value (set via :func:`rtfreporter_options`), then
3. the factory default.

Because option values can change identical code's output, a validated run
should pin its configuration explicitly; :func:`rtfreporter_options` returns a
snapshot of the resolved values for the audit trail, and
:func:`rtfreporter_reset_defaults` restores the factory baseline.
"""

from __future__ import annotations

from typing import Any

# The factory baseline -- the ONLY place package default values are defined.
# Keys mirror R's ``rtfreporter.*`` options with the ``rtfreporter.`` prefix
# dropped (a ``None`` value means "inherit the font-aware / resource baseline").
_FACTORY_DEFAULTS: dict[str, Any] = {
    "page.paper_size": "letter",
    "page.orientation": "landscape",
    "page.margin_top_in": 0.75,
    "page.margin_bottom_in": 0.75,
    "page.margin_left_in": 0.75,
    "page.margin_right_in": 0.75,
    "font": "Courier",
    "font_size_half_points": 18,
    "row_height_twips": None,
    "cell_padding_left_twips": None,
    "cell_padding_right_twips": None,
    "markup": "script",
    "title_format": "text",
    "footnote_format": "table",
    "figure.default_dpi": 96,
}

# Session overrides.  Empty by default; set via ``rtfreporter_options(**kw)``.
_OPTIONS: dict[str, Any] = {}

# Sentinel marking "argument not supplied" so a caller-omitted argument can fall
# through to the option / factory default (the R ``missing()`` idiom).
_UNSET: Any = object()


def _opt(name: str) -> Any:
    """Resolve one default: the session override if set, else the factory value."""
    if name not in _FACTORY_DEFAULTS:
        raise KeyError(f"Unknown rtfreporter option {name!r}.")
    return _OPTIONS.get(name, _FACTORY_DEFAULTS[name])


def _resolve(value: Any, name: str) -> Any:
    """Return ``value`` when supplied, else the resolved option (``_opt``)."""
    return _opt(name) if value is _UNSET else value


def rtfreporter_options(**overrides: Any) -> dict[str, Any]:
    """Inspect or set the active rtfreporter defaults.

    Called with **no arguments**, returns a snapshot dict of the currently
    *resolved* default values (the session override where set, otherwise the
    factory baseline) -- useful to record the configuration a report was
    generated under.

    Called with keyword ``overrides`` (option name -> value), sets those session
    options and returns a dict of their **previous** resolved values (so the old
    state can be restored), mirroring base R's ``options()``.  Unknown option
    names raise :class:`KeyError`.

    Args:
        **overrides: Option name/value pairs to set (see the module's factory
            defaults for the valid names).

    Returns:
        A snapshot of resolved values (no-arg form) or the prior values of the
        changed options (setter form).
    """
    if not overrides:
        return {name: _opt(name) for name in _FACTORY_DEFAULTS}
    unknown = set(overrides) - set(_FACTORY_DEFAULTS)
    if unknown:
        raise KeyError(f"Unknown rtfreporter option(s): {sorted(unknown)}.")
    prior = {name: _opt(name) for name in overrides}
    _OPTIONS.update(overrides)
    return prior


def rtfreporter_reset_defaults() -> dict[str, Any]:
    """Restore the factory default options, discarding all session overrides.

    Returns:
        A copy of the factory default mapping that was restored.
    """
    _OPTIONS.clear()
    return dict(_FACTORY_DEFAULTS)
