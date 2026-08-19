"""Embedded PNG / JPEG figures.

Ported from ``R/rtfplot.R``.  Reads image dimensions and pixel density (PNG
``pHYs`` chunk, JPEG JFIF density) so a figure defaults to its native size at
its embedded DPI.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

_DEFAULT_DPI = 96


def _read_png_dims(raw: bytes) -> tuple[int, int]:
    if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a valid PNG file.")
    width, height = struct.unpack(">II", raw[16:24])
    return width, height


def _read_png_density(raw: bytes):
    """Return ``(dpi_x, dpi_y)`` from the PNG ``pHYs`` chunk, or ``None``."""
    i = 8
    n = len(raw)
    while i + 8 <= n:
        (length,) = struct.unpack(">I", raw[i : i + 4])
        ctype = raw[i + 4 : i + 8]
        if ctype == b"pHYs":
            d = raw[i + 8 : i + 8 + 9]
            if len(d) < 9:
                return None
            ppux, ppuy = struct.unpack(">II", d[0:8])
            unit = d[8]
            if unit == 1 and ppux > 0 and ppuy > 0:
                return ppux * 0.0254, ppuy * 0.0254
            return None
        if ctype in (b"IDAT", b"IEND"):
            break
        i += 12 + length  # 4 len + 4 type + data + 4 CRC
    return None


def _read_jpeg_dims(raw: bytes) -> tuple[int, int]:
    n = len(raw)
    i = 2
    while i < n - 4:
        if raw[i] == 0xFF:
            marker = raw[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                height = (raw[i + 5] << 8) + raw[i + 6]
                width = (raw[i + 7] << 8) + raw[i + 8]
                return width, height
            seg_len = (raw[i + 2] << 8) + raw[i + 3]
            i += seg_len + 2
        else:
            i += 1
    raise ValueError("Could not locate the JPEG SOF marker.")


def _read_jpeg_density(raw: bytes):
    n = len(raw)
    i = 2
    while i < n - 4:
        if raw[i] != 0xFF:
            i += 1
            continue
        marker = raw[i + 1]
        if marker == 0xE0 and i + 16 <= n and raw[i + 4 : i + 8] == b"JFIF":
            units = raw[i + 11]
            xd = (raw[i + 12] << 8) + raw[i + 13]
            yd = (raw[i + 14] << 8) + raw[i + 15]
            if units == 1 and xd > 0 and yd > 0:
                return float(xd), float(yd)
            if units == 2 and xd > 0 and yd > 0:
                return xd * 2.54, yd * 2.54
            return None
        if marker in (0xD8, 0xD9, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
        else:
            seg_len = (raw[i + 2] << 8) + raw[i + 3]
            i += 2 + seg_len
    return None


@dataclass
class Figure:
    """An embedded PNG or JPEG figure.

    Args:
        path: Path to a PNG or JPEG file.
        width_twips: Display width in twips.  ``None`` uses the native size at
            the image's DPI; if only ``height_twips`` is given, the width is
            derived from the aspect ratio.
        height_twips: Display height in twips (mirror of ``width_twips``).
        align: ``"center"`` (default), ``"left"``, or ``"right"``.
    """

    path: str
    width_twips: int | None = None
    height_twips: int | None = None
    align: str = "center"
    img_type: str = ""
    img_width: int = 0
    img_height: int = 0
    dpi_x: float | None = None
    dpi_y: float | None = None
    _raw: bytes = b""

    def __post_init__(self) -> None:
        with open(self.path, "rb") as fh:
            raw = fh.read()
        self._raw = raw
        if raw[:8] == b"\x89PNG\r\n\x1a\n":
            self.img_type = "png"
            self.img_width, self.img_height = _read_png_dims(raw)
            density = _read_png_density(raw)
        elif raw[:2] == b"\xff\xd8":
            self.img_type = "jpeg"
            self.img_width, self.img_height = _read_jpeg_dims(raw)
            density = _read_jpeg_density(raw)
        else:
            raise ValueError(f"{self.path!r} is not a PNG or JPEG image.")
        if density is not None:
            self.dpi_x, self.dpi_y = density
        if self.align not in ("left", "center", "right"):
            raise ValueError('`align` must be "left", "center", or "right".')

    def display_twips(self) -> dict:
        """Resolve the display size (twips), honouring explicit width/height."""
        dpi_x = self.dpi_x if self.dpi_x and self.dpi_x > 0 else _DEFAULT_DPI
        dpi_y = self.dpi_y if self.dpi_y and self.dpi_y > 0 else _DEFAULT_DPI
        native_w = int(round(self.img_width / dpi_x * 1440))
        native_h = int(round(self.img_height / dpi_y * 1440))
        uw, uh = self.width_twips, self.height_twips
        if uw is not None:
            w = int(uw)
        elif uh is not None:
            w = int(round(uh * self.img_width / self.img_height))
        else:
            w = native_w
        if uh is not None:
            h = int(uh)
        elif uw is not None:
            h = int(round(uw * self.img_height / self.img_width))
        else:
            h = native_h
        return {"w": w, "h": h, "native_w": native_w, "native_h": native_h}


def rtfplot(
    path: str,
    width_twips: int | None = None,
    height_twips: int | None = None,
    align: str = "center",
) -> Figure:
    """Create an embedded :class:`Figure` from a PNG or JPEG file."""
    return Figure(path=path, width_twips=width_twips, height_twips=height_twips, align=align)
