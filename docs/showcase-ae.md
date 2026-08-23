# Showcase: adverse events by SOC and preferred term

A multi-page adverse-events table with group-aware pagination, built from real
ADaM data. It is the companion to the [demographics
showcase](showcase-dm.md); the data loading and shared furniture are explained
there.

Run it:

```bash
python examples/showcase_ae.py
```

## The table's rules

These are clinical reporting conventions, not rtfreporter details, but they
drive every design decision below:

* an **“Subjects with any adverse event”** row on top;
* **each SOC row carries its own independent distinct-subject count** — never
  the sum of the preferred terms printed beneath it;
* a preferred term appears only if it reaches **≥ 3% in any arm**;
* SOCs alphabetically; PTs within a SOC by total distinct-subject count
  descending, ties A→Z;
* zero cells written out as an aligned `0 (0.0%)`;
* PTs indented under their SOC.

### Why a SOC row is not a column sum

A subject who reports both *Diarrhoea* and *Nausea* is **one** subject with a
gastrointestinal event, but appears on two PT rows. Adding the PT rows up
would double-count them. Each level is therefore counted independently over
distinct `USUBJID`:

```python
def _distinct_counts(frame, *keys):
    return (frame.drop_duplicates(["USUBJID", "TRT01A", *keys])
                 .groupby(["TRT01A", *keys], observed=True)
                 .size().rename("n").reset_index())
```

For this dataset the gastrointestinal SOC is 17 / 15 / 19 subjects, while its
printed PTs sum to considerably more. `tests/test_showcase.py` asserts the two
differ, so a refactor cannot quietly turn the SOC row into a sum.

## Zeros that align

The built-in [`format_count_pct`][rtfreporter.format_count_pct.format_count_pct] collapses a
zero to a padded bare `0` — correct, and what R does. For this table we want
the zeros written out so the column stays visually flush, exactly as the R
article does with its own `fmt_ae()`:

```python
def fmt_ae(n: int, denom: int) -> str:
    pct = 100.0 * n / denom if denom else 0.0
    if n == 0:
        body = f"{n:>3}{NBSP * 2}(0.0%)"
    elif pct < 10:
        body = f"{n:>3}{NBSP * 2}({pct:>3.1f}%)"
    else:
        body = f"{n:>3}{NBSP}({pct:>4.1f}%)"
    return body.replace(" ", NBSP)
```

Every branch is 11 characters wide, so the closing parenthesis lines up. A
test asserts that every cell in the table is exactly 11 characters — a ragged
column fails the build.

## Indentation *is* the group structure

The preferred terms are indented with four non-breaking spaces, and that
indent is what rtfreporter uses to find group boundaries:

```python
pages = as_rtftables(
    body,
    group_col=0,
    group_by="indent",
    split="group_force",
    max_rows=16,
    min_group_rows=2,
    cont_label=" (Cont.)",
    col_header=ae_col_header(adsl),
    col_rel_width=[46, 18, 18, 18],
)
```

`group_by` chooses **how** a boundary is detected, independently of **which**
column carries it:

| mode | a new group starts when… |
|------|--------------------------|
| `"value"` | the cell value changes (run-length) |
| `"indent"` | the cell is **not** indented (flush-left rows are headers) |
| `"filled"` | the cell is non-empty (blank cells are members) |
| `"auto"` | detected from the column: indent → filled → value |

Group on a **printed** column. Under `group_force` the `(Cont.)` marker is
written into the grouping column's cell, so hiding that column via `drop_cols`
would take the marker with it.

## Pagination and continuation

`split="group_force"` cuts on **every** `max_rows` and, when the cut lands
inside a SOC, repeats that SOC's header on the next page with `(Cont.)`
appended:

```
Page 1   … Skin And Subcutaneous Tissue Disorders
             Pruritus            8 (9.3%)   21 (21.9%)   25 (34.7%)
Page 2   Skin And Subcutaneous Tissue Disorders (Cont.)
             Erythema            8 (9.3%)   14 (14.6%)   14 (19.4%)
```

`min_group_rows=2` is widow/orphan control: a group that would show only one
row before the break is pushed to the next page, and a cut that would leave a
single trailing row is pulled back.

Contrast with `split="group_safe"`, which never splits a group — it fills up
to `max_rows` and moves a whole group down instead, so no continuation marker
is ever produced.

## Validation against R

`tests/test_showcase.py` checks these figures against
`data-raw/R_reference_numbers.txt`:

| Row | Placebo | Xanomeline Low Dose | Xanomeline High Dose |
|-----|--------:|--------------------:|---------------------:|
| Subjects with any adverse event | 65 | 84 | 68 |
| Cardiac disorders | 12 | 14 | 14 |
| Gastrointestinal disorders | 17 | 15 | 19 |
| General disorders and administration site conditions | 21 | 51 | 36 |

Also asserted: exactly **32** preferred terms pass the 3% filter; the PT order
starts Pruritus → Application Site Pruritus → Erythema; SOCs are alphabetical;
the rendered RTF is well-formed, ASCII-safe, spans more than one page, and
contains a `(Cont.)` marker.
