"""End-to-end example: borders, spanning headers, and style verbs.

Demonstrates:

* a two-level spanning column header built with :func:`rtfreporter.col_cell`,
* the ``tfl`` clinical border preset plus a custom coloured zone border,
* the post-hoc styling verbs (:func:`style_body`, :func:`style_cols`,
  :func:`style_header`, :func:`style_zone`), and
* superscript / subscript markup in cell text.

Run::

    python examples/styling.py
"""

from __future__ import annotations

import os

from rtfreporter import (
    Border,
    BorderSide,
    RtfDocument,
    col_cell,
    rtftable,
    style_body,
    style_cols,
    style_header,
    style_zone,
)

DATA = {
    "Parameter": ["ALT (U/L)", "AST (U/L)", "Bilirubin^{2} (mg/dL)"],
    "Placebo n": ["42", "42", "41"],
    "Placebo Mean": ["24.1", "26.7", "0.6"],
    "Active n": ["45", "45", "44"],
    "Active Mean": ["23.4", "25.9", "0.7"],
}


def build_table():
    tbl = rtftable(
        DATA,
        # A spanning header row on top of the leaf labels.
        col_header=[
            [
                col_cell(0, ""),
                col_cell((1, 2), "Placebo (N=42)"),
                col_cell((3, 4), "Active (N=45)"),
            ],
            ["Parameter", "n", "Mean", "n", "Mean"],
        ],
        border="tfl",
    )

    # Numeric columns right-aligned; header centered and bold.
    tbl = style_cols(tbl, cols=[1, 2, 3, 4], align="right")
    tbl = style_header(tbl, align="center", bold=True)
    tbl = style_body(tbl, cols=0, bold=False, align="left")

    # A coloured rule under the whole body (custom zone border).
    tbl = style_zone(
        tbl,
        "last_row",
        Border(bottom=BorderSide(style="single", width=20, color="#003366")),
    )
    return tbl


def build() -> RtfDocument:
    return RtfDocument().add_table(
        build_table(),
        title=["Table 14.2", "", "Summary of Liver Function Tests"],
        footnote=["Values are arithmetic means.", "^{2} Total bilirubin."],
    )


def main() -> str:
    doc = build()
    rtf = doc.to_rtf()

    assert rtf.startswith("{\\rtf1"), "output must start with {\\rtf1"
    assert rtf.count("{") == rtf.count("}"), "RTF group braces must balance"
    assert "\\clbrdrb" in rtf, "a bottom border command should be present"
    assert "\\super " in rtf, "superscript markup should be rendered"
    # The custom colour is registered in the RTF colour table (as RGB, not hex).
    assert "\\red0\\green51\\blue102" in rtf, "custom border colour should be registered"

    out_path = os.path.join(os.path.dirname(__file__), "styling.rtf")
    doc.save(out_path)
    print(f"Wrote {out_path} ({len(rtf):,} bytes)")
    return out_path


if __name__ == "__main__":
    main()
