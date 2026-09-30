"""rtf_figures(width_twips=, height_twips=, align=), compared byte-for-byte
with the R package (``data-raw/xcheck/figure_r.R`` writes
``tests/xcheck_golden/figure/``)."""

import struct
import zlib
from pathlib import Path

import pytest

import rtfreporter as rr

DIR = Path(__file__).parent / "xcheck_golden" / "figure"
PNG = DIR / "tiny.png"


def tiny_png() -> bytes:
    """A 4 x 2 RGB PNG, written by hand so no imaging library is needed."""
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    raw = b"".join(b"\x00" + bytes([200, 30, 30] * 4) for _ in range(2))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 2, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def test_the_committed_image_is_the_one_this_file_writes():
    assert PNG.read_bytes() == tiny_png()


@pytest.mark.parametrize("name, kw", [
    ("default", {}),
    ("sized_left", {"width_twips": 4320, "height_twips": 2160, "align": "left"}),
    ("width_only_right", {"width_twips": 5000, "align": "right"}),
])
def test_rtf_figures_matches_r(name, kw):
    doc = rr.rtf_figures(rr.rtf_document(), [str(PNG)], titles=["Figure 1"], **kw)
    expected = (DIR / f"{name}.rtf").read_text(encoding="ascii").replace("\r\n", "\n")
    assert doc.to_rtf() == expected
