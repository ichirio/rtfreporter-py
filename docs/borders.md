# Borders and rules

Clinical tables live and die by their rules: a top and bottom line around the
column header, a group underline beneath a spanning label, an occasional rule
under the last data row. `rtfreporter` gives three levels of control, from a
one-word preset down to a single cell.

The border objects are immutable records, so a border you build can be reused
across tables safely. The vocabulary is small:

- [`border_side(style, width, color)`](reference.md#rtfreporter.borders.border_side)
  — one **edge** (a line).
- [`border(top, bottom, left, right)`](reference.md#rtfreporter.borders.border)
  — the four edges of one **cell/row** ([`Border`][border]).
- [`TableBorder`][tableborder] — the per-**zone** borders of a whole table.

[border]: reference.md#rtfreporter.borders.Border
[tableborder]: reference.md#rtfreporter.borders.TableBorder

## Level 1 — a preset

The `border` argument of `rtftable()` (and `as_rtftables()`) accepts a shorthand
string:

```python
from rtfreporter import rtftable

tbl = rtftable({"Parameter": ["Age"], "Value": ["75.1"]}, border="tfl")
```

- `"tfl"` — the clinical preset: a rule on **top of the first** header row and
  **below the last** header row; a multi-column spanning cell gets an automatic
  group underline where the grouping changes below it; the data area has **no**
  borders. This is the default.
- `"none"` (or `None`) — no borders anywhere.

`"tfl"` is exactly [`border_tfl()`](reference.md#rtfreporter.borders.border_tfl).

## Level 2 — zones with `TableBorder`

When the preset is not enough, build the zones yourself. A table has five border
zones:

| Zone | Applies to |
|------|------------|
| `header` | the column-header label rows |
| `spanning` | the spanning-header rows |
| `body` | every data row |
| `first_row` | override merged on top of the first data row |
| `last_row` | override merged on top of the last data row |

```python
from rtfreporter import rtftable, TableBorder, Border, BorderSide

thin = BorderSide("single", 15)
tb = TableBorder(
    header=Border(top=thin, bottom=thin),
    last_row=Border(bottom=BorderSide("single", 20)),
)
tbl = rtftable({"Parameter": ["Age"], "Value": ["75.1"]}, border=tb)
```

`first_row` / `last_row` are *overrides* merged on top of `body`, so you can set
a body rule and still special-case the edges.

## Level 3 — one cell / column

A single `Border` passed as the `border` argument applies to the **header** zone
(a common shorthand). For per-column control, set the `border` field of a
`col_spec` entry, or use the [`style_zone`](styling.md) verb after construction:

```python
from rtfreporter import rtftable, style_zone, Border, BorderSide

tbl = rtftable({"A": [1], "B": [2]}, border="tfl")
tbl = style_zone(tbl, "last_row", Border(bottom=BorderSide("double", 20)))
```

## Side styles, widths and colours

A `BorderSide` has three fields:

- `style` — `"single"` (default), `"double"`, `"thick"`, `"dash"`, `"dot"`, or
  `"none"`;
- `width` — line weight in twips (default `15` ≈ 0.5 pt);
- `color` — `None` (black) or a 6-digit hex string such as `"#003366"`.

`style="none"` is an **explicit no-line** that *removes* an inherited border when
merged on top of another spec — distinct from `None`, which simply leaves the
side unset. Any colour you reference is automatically collected into the RTF
colour table.

```python
from rtfreporter import BorderSide, Border

navy_rule = Border(bottom=BorderSide("single", 20, "#003366"))
```

Convenience constructors cover the common shapes:
[`border_top`](reference.md#rtfreporter.borders.border_top),
[`border_bottom`](reference.md#rtfreporter.borders.border_bottom),
[`border_box`](reference.md#rtfreporter.borders.border_box),
[`border_none`](reference.md#rtfreporter.borders.border_none).
