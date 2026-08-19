# Figures

`rtfreporter` can embed **PNG** and **JPEG** images directly into an RTF
document — no external tools. A figure occupies its own content page, with the
same title/footnote support as a table.

## Embedding an image

Pass a path to
[`add_figure`](reference.md#rtfreporter.document.RtfDocument.add_figure):

```python
from rtfreporter import RtfDocument

doc = RtfDocument().add_figure(
    "kaplan_meier.png",
    title=["Figure 14.1", "", "Kaplan-Meier Estimate of Overall Survival"],
    footnote=["Shaded band: 95% confidence interval."],
)
doc.save("figure.rtf")
```

You can also build the [`Figure`](reference.md#rtfreporter.figure.Figure) object
yourself with [`rtfplot`](reference.md#rtfreporter.figure.rtfplot) and add it:

```python
from rtfreporter import rtfplot, RtfDocument

fig = rtfplot("forest.png", width_twips=7200, align="center")
RtfDocument().add_figure(fig).save("forest.rtf")
```

## Sizing

By default a figure renders at its **native size** computed from the pixel
dimensions and the embedded DPI (the PNG `pHYs` chunk or the JPEG JFIF density).
When no density is stored, 96 DPI is assumed.

- Give **`width_twips`** or **`height_twips`** to set an explicit size; the other
  dimension is derived from the aspect ratio.
- Give **both** to set the box exactly (aspect ratio not preserved).
- There are **1440 twips per inch**, so a 2-inch-wide figure is `width_twips=2880`.

```python
rtfplot("plot.png", width_twips=2880)                 # 2 inches wide
rtfplot("plot.png", height_twips=1440)                # 1 inch tall, width from AR
rtfplot("plot.png", width_twips=4320, height_twips=2880)  # exact 3 x 2 inch box
```

## Alignment

`align` is `"center"` (default), `"left"`, or `"right"`.

## Reading dimensions without rendering

A `Figure` exposes what it parsed, which is handy for layout logic:

```python
fig = rtfplot("plot.png")
fig.img_type        # "png" or "jpeg"
fig.img_width       # pixels
fig.dpi_x           # embedded DPI, or None
fig.display_twips() # {"w": ..., "h": ..., "native_w": ..., "native_h": ...}
```
