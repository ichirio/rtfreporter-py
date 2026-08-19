# Styling with the style verbs

The **style verbs** apply formatting to a table *after* it is built. Each verb
returns a **modified copy**, leaving the original untouched, so they compose
cleanly and can be chained. They are the Pythonic counterpart to editing a
`col_spec` by hand.

```python
from rtfreporter import rtftable, style_body, style_header

tbl = rtftable({"Parameter": ["Age"], "Placebo": ["75.1"], "Active": ["74.4"]})
tbl = style_header(style_body(tbl, cols=[1, 2], align="right"), bold=True)
```

## Selecting columns

Every verb takes a `cols` argument: a single index or name, a list of them, or
`None` for **all** columns. Names and 0-based indices are interchangeable.

```python
style_body(tbl, cols=0)          # first column
style_body(tbl, cols="Active")   # by name
style_body(tbl, cols=[1, 2])     # several
style_body(tbl, cols=None)       # every column
```

## The verbs

### `style_body` — body-cell formatting

Accepts `align`, `bold`, `italic`, `underline`, `indent_twips`, `color`, and a
per-column `border`.

```python
from rtfreporter import style_body

tbl = style_body(tbl, cols=[1, 2], align="right")
tbl = style_body(tbl, cols=0, bold=True, color="#003366")
```

### `style_header` — column-header formatting

Maps `align` / `bold` / `italic` onto the header fields, plus an optional header
`border`.

```python
from rtfreporter import style_header

tbl = style_header(tbl, align="center", bold=True)
```

### `style_cols` — body **and** header in one call

The general verb: accepts any body field *or* header field
(`header_align`, `header_bold`, `header_italic`).

```python
from rtfreporter import style_cols

tbl = style_cols(tbl, cols="Active", align="right", header_align="center")
```

### `style_zone` — a table border zone

Set one [`TableBorder`](reference.md#rtfreporter.borders.TableBorder) zone —
`"header"`, `"spanning"`, `"body"`, `"first_row"`, or `"last_row"` — to a
[`Border`](reference.md#rtfreporter.borders.Border) (or `None` to clear it). See
[Borders and rules](borders.md).

```python
from rtfreporter import style_zone, Border, BorderSide

tbl = style_zone(tbl, "last_row", Border(bottom=BorderSide("double", 20)))
```

## Cell-text markup

Independently of the verbs, cell text supports lightweight inline markup,
controlled by the document's `markup` setting (default `"script"`):

- `x^{2}` → superscript, `H_{2}O` → subscript (the `"script"` token);
- `>=` / `<=` → the ≥ / ≤ glyphs (the `"relational"` token).

```python
from rtfreporter import rtftable, DefaultFormat, RtfDocument

tbl = rtftable({"Term": ["C_{max}", "AUC^{0-t}"], "n": [42, 42]})
doc = RtfDocument(default_format=DefaultFormat(markup="all")).add_table(tbl)
```

Set `markup="none"` to treat text literally. All non-ASCII characters are always
emitted as RTF unicode escapes, so output stays ASCII-safe.
