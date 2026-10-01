# Figures

A figure is a content page like any other: one figure per page, its own titles
and footnotes, the section's running header and footer around it. What is
particular to a figure is **size** -- a table fills the width it is given,
while a figure has a size of its own and has to be told what to do about it.

This article is about that: getting a plot into the document, deciding how big
it is on the page, and knowing what the file underneath is.

## A plot object goes straight in

`rtf_figures()` takes the plot itself. There is no file to write first:

```python
import matplotlib.pyplot as plt
import numpy as np
from rtfreporter import rtf_document, rtf_figures

rng = np.random.default_rng(20260909)
weeks = np.arange(13)
fig, ax = plt.subplots()
ax.plot(weeks, np.linspace(0, 6, 13) + rng.normal(0, 0.2, 13), label="Placebo")
ax.plot(weeks, np.linspace(0, 11, 13) + rng.normal(0, 0.2, 13), label="Drug")
ax.set_xlabel("Study week")
ax.set_ylabel("Mean change from baseline")
ax.legend(frameon=False)

doc = rtf_figures(
    rtf_document(), [fig],
    titles=[["Figure 14.2.1", "Mean Change from Baseline by Week", "Full Analysis Set"]],
    footnotes=[["Error bars omitted for clarity."]],
)
```

`rtfplot()` is the same thing one step lower down, for when one figure in a
list of several needs settings of its own:

```python
>>> from rtfreporter import rtfplot
>>> f = rtfplot(fig)
>>> f.img_type, f.img_width, f.img_height, f.dpi_x
('png', 1950, 1350, 300.0)
```

Drawing needs the plotting library itself; `pip install rtfreporter[plot]`
brings matplotlib.

### What counts as a plot

Dispatch is by what the object can do, not by which package made it, so the
list is short and open-ended:

| what you pass | how it is drawn |
|---|---|
| a **matplotlib** `Figure`, or anything with a `savefig()` method (a seaborn grid) | saved at the render size; the figure's own size is put back afterwards |
| a **plotnine** plot, or anything with `save(filename, width, height, dpi)` | asked to save itself |
| a **function of no arguments** that draws with matplotlib | called on a fresh figure of the render size |
| a path to a **PNG or JPEG** file | read as it stands |

The function is the escape hatch, and the natural way to give pyplot-style code
-- which draws as a side effect and leaves no object to pass:

```python
def boxplot():
    data = [rng.normal(m, 2, 30) for m in (26, 20, 15)]
    plt.boxplot(data, tick_labels=["4", "6", "8"])
    plt.xlabel("Cylinders")
    plt.ylabel("MPG")

fig2 = rtfplot(boxplot)
```

## Size: inches on the page, pixels in the file

Two sizes are easy to confuse, so the arguments keep them apart.

**`render_width` / `render_height` (inches) say how big the figure is on the
page.** They default to 6.5 x 4.5 in, which fits a portrait letter page inside
one-inch margins.

**`render_dpi` says how sharp it is, and nothing else.** It multiplies the
pixels in the file; it does not change the inches:

```python
>>> for d in (150, 300, 600):
...     f = rtfplot(lambda: plt.plot(range(10)),
...                 render_width=4, render_height=3, render_dpi=d)
...     print(d, f"{f.img_width} x {f.img_height}",
...           f"{f.img_width / d:.1f} x {f.img_height / d:.1f} in")
150 600 x 450 4.0 x 3.0 in
300 1200 x 900 4.0 x 3.0 in
600 2400 x 1800 4.0 x 3.0 in
```

Three files of very different weight, one size on the page. Pick `render_dpi`
for the medium: 300 for something that will be printed, 150 for a review copy,
600 for a figure with fine hatching.

### Fitting the page

The native size is **not** capped to your page, because a figure's size is a
decision -- a plot squeezed to fit usually reads worse than one drawn at the
right size to begin with. So draw it at the size it should occupy:

```python
# A4 landscape is 11.69 x 8.27 in; the writable width is what the margins leave.
writable_in = 11.69 - 0.75 - 0.75     # 10.19

rtfplot(fig, render_width=writable_in, render_height=4.5)
```

To scale a figure you already have -- a file from someone else, or a plot you
do not want to redraw -- give `width_twips` instead. The height follows the
aspect ratio:

```python
rtfplot(fig, width_twips=int(writable_in * 1440))
```

`width_twips` and `height_twips` are display size in twips (1 in = 1440), the
unit the rest of the package uses; give both to set the box exactly (the aspect
ratio is then not kept). `align` puts the figure `"center"` (default),
`"left"` or `"right"` on the page.

## From a file

The path form is what you want when the graphic comes from somewhere else -- a
validated output from another system, a diagram someone drew:

```python
>>> f = rtfplot("visit.png")      # 2400 x 1500 px, saved at 300 dpi
>>> f.display_twips()
{'w': 11520, 'h': 7200, 'native_w': 11520, 'native_h': 7200}
```

A file carries its own resolution, so **its native size is what the file says
it is**: 2400 x 1500 px at 300 dpi is 8 x 5 in. That is read from the PNG's
`pHYs` chunk or the JPEG's JFIF density. A file recording none is assumed to
be at the `figure.default_dpi` option (factory `96`), which is worth knowing
when a figure comes out unexpectedly large:

```python
>>> from rtfreporter import rtfreporter_options
>>> rtfreporter_options()["figure.default_dpi"]
96
```

A drawn object has no such doubt -- the package drew it, so it carries the
`render_dpi` it was drawn at, whatever the backend recorded in the file.
`render_*` are refused for a file, which has its size already.

### Formats

**PNG and JPEG only.** RTF's picture keywords include `\emfblip`,
`\wmetafile`, `\dibitmap` and `\macpict`; `rtfreporter` emits `\pngblip` and
`\jpegblip`, and refuses the rest rather than embedding something a viewer may
not render:

```python
>>> rtfplot("figure.svg")
ValueError: 'figure.svg' is not a PNG or JPEG image.
```

For a clinical deliverable that is the right pair: PNG for anything with text
or lines (lossless, and the usual choice for a plot), JPEG for a photograph.

### Reading what was parsed

A `Figure` exposes what it read, which is handy for layout logic:

```python
f.img_type        # "png" or "jpeg"
f.img_width       # pixels
f.dpi_x           # DPI, or None when the file records none
f.display_twips() # {"w": ..., "h": ..., "native_w": ..., "native_h": ...}
```

## A report of figures and tables

They share the page model, so a document is a sequence of content pages:

```python
import pandas as pd
from rtfreporter import generate_rtfreport, rtf_header, rtf_section, rtf_tables

cars = pd.DataFrame({"mpg": [21.0, 22.8, 21.4], "cyl": [6, 4, 6], "hp": [110, 93, 110]})

report = rtf_document()
report = rtf_section(report, page=1, header=rtf_header(
    [{"l": "Protocol XYZ-123", "r": "Page {AUTO_PAGE}"}]))
report = rtf_tables(report, [cars], titles=[["Table 14.1.1", "Vehicle characteristics"]])
report = rtf_figures(report, [fig, lambda: plt.hist(cars["mpg"])],
                     titles=[["Figure 14.2.1", "Mean change by week"],
                             ["Figure 14.2.2", "Distribution of MPG"]])
generate_rtfreport(report, "figures.rtf", overwrite=True)
```

Three pages -- one table, two figures -- under one running header. The images
are embedded in the `.rtf` itself, so there is no folder of files to keep
beside it. An item `rtf_figures()` cannot draw is named by its position:
`figures[1]: A figure is one file path, or one plot object; got None.`

The fluent form takes the same inputs:
`RtfDocument().add_figure(fig, title=[...], footnote=[...])`.

## Where next

- [Adding tables and figures](adding-content.md) -- titles, footnotes and the page model
- [Headers and footers](headers-footers.md) -- the running header around a figure
- [Rendering and post-processing](output.md) -- writing the file
