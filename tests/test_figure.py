"""Embedded PNG/JPEG figure parsing, DPI, and display sizing."""

import struct
import zlib

import pytest

import rtfreporter as rr
from rtfreporter.figure import (
    _read_jpeg_density,
    _read_jpeg_dims,
    _read_png_density,
    _read_png_dims,
)


def _png_bytes(width, height, phys=None):
    """Build a minimal but structurally valid PNG (optionally with pHYs)."""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(ctype, data):
        return (
            struct.pack(">I", len(data))
            + ctype
            + data
            + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    out = sig + chunk(b"IHDR", ihdr)
    if phys is not None:
        ppux, ppuy, unit = phys
        out += chunk(b"pHYs", struct.pack(">IIB", ppux, ppuy, unit))
    out += chunk(b"IDAT", zlib.compress(b"\x00" * (width * height)))
    out += chunk(b"IEND", b"")
    return out


def _jpeg_bytes(width, height, jfif_units=None):
    """Build minimal JPEG bytes: SOI, optional APP0/JFIF, SOF0, EOI."""
    out = b"\xff\xd8"  # SOI
    if jfif_units is not None:
        units, xd, yd = jfif_units
        app0 = b"JFIF\x00" + bytes([1, 1, units]) + struct.pack(">HH", xd, yd) + b"\x00\x00"
        out += b"\xff\xe0" + struct.pack(">H", len(app0) + 2) + app0
    # SOF0: len(17), precision, height, width, comps...
    sof = struct.pack(">BHHB", 8, height, width, 3) + b"\x01\x11\x00\x02\x11\x00\x03\x11\x00"
    out += b"\xff\xc0" + struct.pack(">H", len(sof) + 2) + sof
    out += b"\xff\xd9"  # EOI
    return out


# -- low-level readers --------------------------------------------------------


def test_read_png_dims():
    assert _read_png_dims(_png_bytes(120, 80)) == (120, 80)


def test_read_png_dims_rejects_non_png():
    with pytest.raises(ValueError, match="valid PNG"):
        _read_png_dims(b"not a png at all really")


def test_read_png_density_meter_unit():
    # 3780 pixels/metre ~= 96 dpi.
    dpi = _read_png_density(_png_bytes(10, 10, phys=(3780, 3780, 1)))
    assert dpi is not None
    assert dpi[0] == pytest.approx(96, abs=0.5)


def test_read_png_density_unknown_unit_is_none():
    assert _read_png_density(_png_bytes(10, 10, phys=(3780, 3780, 0))) is None


def test_read_png_density_absent_is_none():
    assert _read_png_density(_png_bytes(10, 10)) is None


def test_read_jpeg_dims():
    assert _read_jpeg_dims(_jpeg_bytes(200, 100)) == (200, 100)


def test_read_jpeg_density_dpi_units():
    dpi = _read_jpeg_density(_jpeg_bytes(10, 10, jfif_units=(1, 150, 150)))
    assert dpi == (150.0, 150.0)


def test_read_jpeg_density_dpcm_units_converted():
    dpi = _read_jpeg_density(_jpeg_bytes(10, 10, jfif_units=(2, 100, 100)))
    assert dpi[0] == pytest.approx(254.0)


def test_read_jpeg_density_no_units_is_none():
    assert _read_jpeg_density(_jpeg_bytes(10, 10, jfif_units=(0, 1, 1))) is None


def test_read_jpeg_dims_missing_sof_raises():
    with pytest.raises(ValueError, match="SOF"):
        _read_jpeg_dims(b"\xff\xd8\xff\xd9")


# -- Figure / rtfplot ---------------------------------------------------------


def test_rtfplot_png_native_size(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(_png_bytes(96, 48, phys=(3780, 3780, 1)))
    fig = rr.rtfplot(str(p))
    assert fig.img_type == "png"
    d = fig.display_twips()
    # 96 px at 96 dpi = 1 inch = 1440 twips.
    assert d["w"] == pytest.approx(1440, abs=10)
    assert d["h"] == pytest.approx(720, abs=10)


def test_rtfplot_jpeg_native_size(tmp_path):
    p = tmp_path / "a.jpg"
    p.write_bytes(_jpeg_bytes(48, 24, jfif_units=(1, 48, 48)))
    fig = rr.rtfplot(str(p))
    assert fig.img_type == "jpeg"
    d = fig.display_twips()
    assert d["w"] == pytest.approx(1440, abs=10)


def test_figure_explicit_width_derives_height(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(_png_bytes(100, 50))
    fig = rr.rtfplot(str(p), width_twips=2000)
    d = fig.display_twips()
    assert d["w"] == 2000
    assert d["h"] == 1000  # aspect ratio 2:1 preserved


def test_figure_explicit_height_derives_width(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(_png_bytes(100, 50))
    fig = rr.rtfplot(str(p), height_twips=1000)
    d = fig.display_twips()
    assert d["h"] == 1000
    assert d["w"] == 2000


def test_figure_default_dpi_when_absent(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(_png_bytes(96, 96))  # no pHYs -> 96 dpi default
    fig = rr.rtfplot(str(p))
    assert fig.dpi_x is None
    d = fig.display_twips()
    assert d["native_w"] == pytest.approx(1440, abs=10)


def test_figure_bad_align_raises(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(_png_bytes(10, 10))
    with pytest.raises(ValueError, match="align"):
        rr.rtfplot(str(p), align="middle")


def test_figure_non_image_raises(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(b"just some text, not an image \x00\x01")
    with pytest.raises(ValueError, match="PNG or JPEG"):
        rr.rtfplot(str(p))


def test_figure_align_left(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(_png_bytes(10, 10))
    assert rr.rtfplot(str(p), align="left").align == "left"
