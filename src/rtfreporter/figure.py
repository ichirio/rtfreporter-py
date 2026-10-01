"""Embedded PNG / JPEG figures.

Ported from ``R/rtfplot.R``.  Reads image dimensions and pixel density (PNG
``pHYs`` chunk, JPEG JFIF density) so a figure defaults to its native size at
its embedded DPI.
"""

from __future__ import annotations

import os
import struct
import tempfile
from dataclasses import dataclass

_DEFAULT_DPI = 96
_UNSET: float = object()  # type: ignore[assignment]


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
        # A missing DPI falls back to the `figure.default_dpi` option (R).
        from .config import _opt

        fallback = float(_opt("figure.default_dpi") or _DEFAULT_DPI)
        dpi_x = self.dpi_x if self.dpi_x and self.dpi_x > 0 else fallback
        dpi_y = self.dpi_y if self.dpi_y and self.dpi_y > 0 else fallback
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


# -- Drawing an in-memory plot ----------------------------------------------
#
# Every figure in a report is a plot object a moment before it is a file (R
# #394).  So draw the object here, into a PNG at `render_width` x
# `render_height` inches and `render_dpi`, and embed that.  The resolution is
# taken from `render_dpi` rather than read back from the file, so the figure
# lands at exactly the size asked for, whatever the backend wrote.
#
# Dispatch is by capability rather than by package, as in R: an object with
# `savefig()` (a matplotlib Figure, a seaborn grid) is saved at the size, an
# object with `save(filename, width, height, dpi)` (a plotnine ggplot) saves
# itself, and a function of no arguments draws onto a fresh matplotlib figure
# of the size.


def _rtfplot_is_object(x) -> bool:
    if isinstance(x, (str, os.PathLike)):
        return False
    if x is None or isinstance(x, (bool, int, float, bytes, list, tuple)):
        got = "None" if x is None else f"a {type(x).__name__}"
        raise ValueError(f"A figure is one file path, or one plot object; got {got}.")
    return True


def _rtfplot_render(x, width, height, dpi) -> str:
    for nm, v in (("render_width", width), ("render_height", height), ("render_dpi", dpi)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not v > 0:
            raise ValueError(f"`{nm}` must be a single positive number.")
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    ok = False
    try:
        if hasattr(x, "savefig"):
            fig = getattr(x, "figure", x)  # a seaborn grid holds its Figure
            old = fig.get_size_inches() if hasattr(fig, "get_size_inches") else None
            try:
                if old is not None:
                    fig.set_size_inches(width, height)
                x.savefig(path, dpi=dpi)
            finally:
                if old is not None:
                    fig.set_size_inches(*old)
        elif hasattr(x, "save") and callable(x.save):
            x.save(filename=path, width=width, height=height, dpi=dpi, units="in",
                   verbose=False)
        elif callable(x):
            import matplotlib.pyplot as plt

            fig = plt.figure(figsize=(width, height))
            try:
                x()
                fig.savefig(path, dpi=dpi)
            finally:
                plt.close(fig)
        else:
            raise ValueError(
                f"Cannot draw a {type(x).__name__}: a plot object needs a savefig() "
                "(matplotlib) or save() (plotnine) method, or is a function of no "
                "arguments that draws with matplotlib.  Save the figure yourself and "
                "pass the file path."
            )
        ok = True
    finally:
        if not ok:
            os.unlink(path)
    return path


def rtfplot(
    x,
    width_twips: int | None = None,
    height_twips: int | None = None,
    align: str = "center",
    render_width: float = _UNSET,
    render_height: float = _UNSET,
    render_dpi: float = _UNSET,
) -> Figure:
    """Create an embedded :class:`Figure` -- a PNG or JPEG file, or a plot
    object drawn here and then embedded.

    Args:
        x: A figure.  Either the path to a **PNG or JPEG** file, or a plot
            object to draw: a **matplotlib** ``Figure`` (or anything with a
            ``savefig()`` method, such as a seaborn grid), a **plotnine** plot
            (anything with ``save(filename, width, height, dpi)``), or a
            **function of no arguments** that draws with matplotlib -- it is
            called on a fresh figure of the render size.
        width_twips: Display width in twips.  ``None`` (default) uses the
            image's native size at its DPI; if only ``height_twips`` is given,
            the width is derived from the native aspect ratio.
        height_twips: Display height in twips (mirror of ``width_twips``).
        align: ``"center"`` (default), ``"left"``, or ``"right"``.
        render_width, render_height: Size **in inches** to draw a plot object
            at (default 6.5 x 4.5, which fits a portrait letter page).  This is
            also the size the figure takes on the page unless ``width_twips`` /
            ``height_twips`` say otherwise.  Refused for a file, which has its
            size already.
        render_dpi: Resolution to draw a plot object at (default 300).  It
            decides how sharp the figure is, **not** how big.

    A matplotlib figure is drawn at the render size and its own size is put
    back afterwards.  Drawing needs the plotting library itself
    (``pip install rtfreporter[plot]`` for matplotlib).
    """
    if _rtfplot_is_object(x):
        rw = 6.5 if render_width is _UNSET else render_width
        rh = 4.5 if render_height is _UNSET else render_height
        rd = 300 if render_dpi is _UNSET else render_dpi
        path = _rtfplot_render(x, rw, rh, rd)
        fig = Figure(path=path, width_twips=width_twips, height_twips=height_twips, align=align)
        # We drew it, so we know its resolution.
        fig.dpi_x = fig.dpi_y = float(rd)
        return fig
    if any(v is not _UNSET for v in (render_width, render_height, render_dpi)):
        raise ValueError(
            "`render_width`, `render_height` and `render_dpi` say how to draw a plot "
            "object; a file already has a size and a resolution."
        )
    return Figure(path=os.fspath(x), width_twips=width_twips, height_twips=height_twips,
                  align=align)
