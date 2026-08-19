"""Figure parsing and rendering (rtfplot, plot)."""

import struct
import zlib

import pytest

from helpers import assert_valid_rtf
from rtfreporter import RtfDocument, rtfplot
from rtfreporter.render import render_rtfplot


def _png(path, width, height, dpi=None):
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    out = sig + chunk(b"IHDR", ihdr)
    if dpi:
        ppm = int(round(dpi / 0.0254))
        out += chunk(b"pHYs", struct.pack(">IIB", ppm, ppm, 1))
    raw = b"\x00" + b"\x00\x00\x00" * width
    out += chunk(b"IDAT", zlib.compress(raw * height))
    out += chunk(b"IEND", b"")
    path.write_bytes(out)


def _jpeg(path, width, height):
    # Minimal JFIF: SOI + APP0 + SOF0 + EOI
    soi = b"\xff\xd8"
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x01\x01" + b"\x00" \
        + struct.pack(">HH", 72, 72) + b"\x00\x00"
    sof = b"\xff\xc0" + struct.pack(">H", 17) + b"\x08" + struct.pack(">HH", height, width) \
        + b"\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
    eoi = b"\xff\xd9"
    path.write_bytes(soi + app0 + sof + eoi)


def test_png_dimensions(tmp_path):
    p = tmp_path / "f.png"
    _png(p, 300, 150, dpi=150)
    fig = rtfplot(str(p))
    assert fig.img_type == "png"
    assert fig.img_width == 300 and fig.img_height == 150


def test_png_density(tmp_path):
    p = tmp_path / "f.png"
    _png(p, 100, 100, dpi=150)
    fig = rtfplot(str(p))
    assert round(fig.dpi_x) == 150


def test_png_native_display_twips(tmp_path):
    p = tmp_path / "f.png"
    _png(p, 300, 150, dpi=150)
    disp = rtfplot(str(p)).display_twips()
    assert disp["w"] == int(round(300 / 150 * 1440))  # 2 inches


def test_png_no_density_defaults_96(tmp_path):
    p = tmp_path / "f.png"
    _png(p, 96, 96)
    disp = rtfplot(str(p)).display_twips()
    assert disp["w"] == 1440  # 96px / 96dpi = 1 inch


def test_explicit_width(tmp_path):
    p = tmp_path / "f.png"
    _png(p, 300, 150)
    assert rtfplot(str(p), width_twips=7200).display_twips()["w"] == 7200


def test_explicit_height_derives_width(tmp_path):
    p = tmp_path / "f.png"
    _png(p, 300, 150)
    disp = rtfplot(str(p), height_twips=1500).display_twips()
    assert disp["h"] == 1500
    assert disp["w"] == int(round(1500 * 300 / 150))


def test_both_dimensions_exact(tmp_path):
    p = tmp_path / "f.png"
    _png(p, 300, 150)
    disp = rtfplot(str(p), width_twips=4320, height_twips=2880).display_twips()
    assert disp["w"] == 4320 and disp["h"] == 2880


def test_align_default_center(tmp_path):
    p = tmp_path / "f.png"
    _png(p, 10, 10)
    assert rtfplot(str(p)).align == "center"


def test_bad_align_raises(tmp_path):
    p = tmp_path / "f.png"
    _png(p, 10, 10)
    with pytest.raises(ValueError):
        rtfplot(str(p), align="up")


def test_render_pngblip(tmp_path):
    p = tmp_path / "f.png"
    _png(p, 20, 20, dpi=96)
    out = render_rtfplot(rtfplot(str(p)), 12000)
    assert "\\pngblip" in out
    assert "\\picwgoal" in out


def test_render_alignment_command(tmp_path):
    p = tmp_path / "f.png"
    _png(p, 20, 20)
    out = render_rtfplot(rtfplot(str(p), align="left"), 12000)
    assert "\\ql" in out


def test_jpeg_dimensions(tmp_path):
    p = tmp_path / "f.jpg"
    _jpeg(p, 200, 120)
    fig = rtfplot(str(p))
    assert fig.img_type == "jpeg"
    assert fig.img_width == 200 and fig.img_height == 120


def test_jpeg_render_jpegblip(tmp_path):
    p = tmp_path / "f.jpg"
    _jpeg(p, 50, 50)
    out = render_rtfplot(rtfplot(str(p)), 12000)
    assert "\\jpegblip" in out


def test_not_an_image_raises(tmp_path):
    p = tmp_path / "f.png"
    p.write_bytes(b"not an image at all")
    with pytest.raises(ValueError):
        rtfplot(str(p))


def test_figure_embedded_in_document(tmp_path):
    p = tmp_path / "f.png"
    _png(p, 100, 100, dpi=96)
    doc = RtfDocument().add_figure(str(p), width_twips=5000, title=["Figure 1"])
    rtf = doc.to_rtf()
    assert "\\pngblip" in rtf
    assert_valid_rtf(rtf)
