"""rtf_watermark(): the document's, a section's own, and switching it off.
Byte parity with R is in the xcheck cases watermark_default / watermark_styled."""

import pytest

import rtfreporter as rr

SHAPE = r"{\shp{\*\shpinst"


def _two_sections(**section_kw):
    doc = rr.rtf_document(watermark="DRAFT")
    doc = rr.rtf_tables(doc, [rr.rtftable({"A": ["1"]}), rr.rtftable({"A": ["2"]})])
    doc = rr.rtf_section(doc, page=1, header=rr.rtf_header([{"l": "x"}]))
    return rr.rtf_section(doc, page=2, header=rr.rtf_header([{"l": "y"}]), **section_kw)


def test_document_watermark_on_every_section():
    assert _two_sections().to_rtf().count(SHAPE) == 2


def test_a_section_can_switch_it_off_or_change_it():
    assert _two_sections(watermark=None).to_rtf().count(SHAPE) == 1
    rtf = _two_sections(watermark=rr.rtf_watermark("FINAL", angle=0))
    assert "FINAL" in rtf.to_rtf() and "DRAFT" in rtf.to_rtf()


def test_rtf_config_sets_and_removes():
    doc = rr.rtf_tables(rr.rtf_document(), [rr.rtftable({"A": ["1"]})])
    on = rr.rtf_config(doc, watermark="COPY")
    assert "COPY" in on.to_rtf()
    assert SHAPE not in rr.rtf_config(on, watermark="").to_rtf()
    assert "COPY" in rr.rtf_config(on, page={"orientation": "portrait"}).to_rtf()


def test_watermark_is_validated():
    with pytest.raises(ValueError, match="RRGGBB"):
        rr.rtf_watermark("X", color="grey")
    with pytest.raises(ValueError, match="positive"):
        rr.rtf_watermark("X", width_in=0)
    with pytest.raises(ValueError, match="rtf_watermark object"):
        rr.rtf_document(watermark=3)
