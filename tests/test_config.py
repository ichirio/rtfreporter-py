"""Package options: resolution order, setter/snapshot, reset."""

import pytest

import rtfreporter as rr
from rtfreporter.config import _FACTORY_DEFAULTS, _UNSET, _opt, _resolve


@pytest.fixture(autouse=True)
def _reset():
    rr.rtfreporter_reset_defaults()
    yield
    rr.rtfreporter_reset_defaults()


def test_snapshot_returns_every_factory_key():
    snap = rr.rtfreporter_options()
    assert set(snap) == set(_FACTORY_DEFAULTS)


def test_setter_returns_prior_values_for_changed_keys_only():
    prior = rr.rtfreporter_options(font="Arial", font_size_half_points=24)
    assert prior == {"font": "Courier", "font_size_half_points": 18}


def test_setter_persists_until_reset():
    rr.rtfreporter_options(**{"page.orientation": "portrait"})
    assert rr.rtfreporter_options()["page.orientation"] == "portrait"
    rr.rtfreporter_reset_defaults()
    assert rr.rtfreporter_options()["page.orientation"] == "landscape"


def test_unknown_option_lists_offending_key():
    with pytest.raises(KeyError, match="bogus"):
        rr.rtfreporter_options(bogus=1)


def test_reset_returns_factory_copy_not_alias():
    restored = rr.rtfreporter_reset_defaults()
    restored["font"] = "MUTATED"
    assert _FACTORY_DEFAULTS["font"] == "Courier"


def test_opt_unknown_key_raises():
    with pytest.raises(KeyError, match="Unknown rtfreporter option"):
        _opt("nope.nope")


def test_opt_prefers_session_override():
    rr.rtfreporter_options(font="Arial")
    assert _opt("font") == "Arial"


def test_resolve_uses_value_when_supplied():
    assert _resolve("Explicit", "font") == "Explicit"


def test_resolve_falls_through_on_unset():
    rr.rtfreporter_options(font="Arial")
    assert _resolve(_UNSET, "font") == "Arial"
