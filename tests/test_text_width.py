"""Font-aware text width estimation and automatic column sizing."""

import rtfreporter as rr
from rtfreporter.text_width import _char_width_in, _max_line_nchar

# -- helpers ------------------------------------------------------------------


def test_char_width_arial_narrower_than_courier():
    assert _char_width_in("arial", 9) < _char_width_in("courier_new", 9)


def test_char_width_unknown_font_falls_back_to_courier():
    assert _char_width_in("wingdings", 9) == _char_width_in("courier_new", 9)


def test_max_line_nchar_multiline_takes_longest():
    assert _max_line_nchar("ab\nabcd\nx") == 4


def test_max_line_nchar_handles_crlf_and_cr():
    assert _max_line_nchar("aa\r\nbbbb\rc") == 4


def test_max_line_nchar_none_is_zero():
    assert _max_line_nchar(None) == 0


# -- text_width_in ------------------------------------------------------------


def test_text_width_single_string_returns_one_element():
    out = rr.text_width_in("abcd")
    assert len(out) == 1 and out[0] > 0


def test_text_width_empty_string_is_zero():
    assert rr.text_width_in("")[0] == 0.0


def test_text_width_arial_option():
    arial = rr.text_width_in("abcdef", font="arial")[0]
    courier = rr.text_width_in("abcdef", font="courier_new")[0]
    assert arial < courier


def test_text_width_unknown_font_treated_as_courier():
    assert rr.text_width_in("abc", font="nope")[0] == rr.text_width_in("abc")[0]


# -- auto_col_widths ----------------------------------------------------------


def test_auto_col_widths_wider_content_gets_more_width():
    widths = rr.auto_col_widths({"short": ["x"], "long": ["xxxxxxxxxxxxxxxxxxxx"]})
    assert widths[1] > widths[0]


def test_auto_col_widths_uses_header_when_wider_than_data():
    w_hdr = rr.auto_col_widths(
        {"c": ["x"]}, col_header=["a_very_long_header_label"]
    )
    w_plain = rr.auto_col_widths({"c": ["x"]}, col_header=["c"])
    assert w_hdr[0] > w_plain[0]


def test_auto_col_widths_pipe_header_string():
    widths = rr.auto_col_widths(
        {"a": ["1"], "b": ["2"]}, col_header="Alpha|Beta"
    )
    assert len(widths) == 2


def test_auto_col_widths_multirow_header_uses_first_row():
    widths = rr.auto_col_widths(
        {"a": ["1"], "b": ["2"]}, col_header=[["Alpha", "Beta"], ["x", "y"]]
    )
    assert len(widths) == 2


def test_auto_col_widths_short_header_padded():
    widths = rr.auto_col_widths({"a": ["1"], "b": ["2"]}, col_header=["only"])
    assert len(widths) == 2


def test_auto_col_widths_scale_down_sums_to_target():
    widths = rr.auto_col_widths(
        {"a": ["xxxxxxxxxx"], "b": ["yyyyyyyyyy"]}, table_width_twips=3000
    )
    assert sum(widths) == 3000


def test_auto_col_widths_protect_falls_back_when_impossible():
    # Protecting the wide column leaves too little for the rest, so protection
    # cannot be honoured: it falls through to uniform scaling and every column
    # is held at least at min width.
    widths = rr.auto_col_widths(
        {"wide": ["x" * 50], "a": ["1"], "b": ["2"]},
        table_width_twips=2200,
        protect_cols=[0],
        min_col_width_twips=720,
    )
    assert len(widths) == 3
    assert all(w >= 720 for w in widths)


def test_auto_col_widths_protect_out_of_range_ignored():
    widths = rr.auto_col_widths(
        {"a": ["xxxx"], "b": ["yyyy"]},
        table_width_twips=4000,
        protect_cols=[99],
    )
    assert sum(widths) == 4000


def test_auto_col_widths_no_target_returns_natural():
    widths = rr.auto_col_widths(
        {"a": ["x"], "b": ["yy"]}, min_col_width_twips=100, col_padding_twips=0
    )
    assert all(isinstance(w, int) for w in widths)
    # "yy" is wider than "x", so with no target the natural widths differ.
    assert widths[1] >= widths[0]
