"""Tests for the border model and its RTF emission."""

import pytest

from rtfreporter import Border, BorderSide, rtf_border_side, rtf_border_tfl
from rtfreporter.render import build_border_commands


def test_border_side_defaults():
    s = BorderSide()
    assert s.style == "single" and s.width == 15 and s.color is None


def test_border_side_invalid_style():
    with pytest.raises(ValueError):
        BorderSide(style="wiggly")


def test_none_side_omits_command():
    b = Border(top=BorderSide("none"), bottom=BorderSide())
    cmds = build_border_commands(b)
    assert r"\clbrdrt" not in cmds  # "none" side omitted
    assert r"\clbrdrb\brdrs\brdrw15" in cmds


def test_none_border_object_empty_string():
    assert build_border_commands(None) == ""


def test_single_bottom_border_command():
    b = Border(bottom=BorderSide("single", 20))
    assert build_border_commands(b) == r"\clbrdrb\brdrs\brdrw20"


def test_double_style_command():
    b = Border(top=BorderSide("double"))
    assert r"\brdrdb" in build_border_commands(b)


def test_border_color_command_with_map():
    b = Border(bottom=BorderSide(color="#003366"))
    out = build_border_commands(b, {"#003366": 3})
    assert r"\brdrcf3" in out


def test_border_tfl_preset():
    tb = rtf_border_tfl()
    assert tb.header is not None
    assert tb.header.top is not None and tb.header.bottom is not None
    assert tb.body is None and tb.last_row is None


def test_border_side_functional_alias():
    assert rtf_border_side("thick", 40) == BorderSide("thick", 40)
