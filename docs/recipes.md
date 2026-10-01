# Four complete recipes: DM, AE, PK and LB

Copy-and-run programs for the four table shapes a clinical report is mostly
made of. Each builds its data, its table and its document, and ends in a
rendered RTF. They are deliberately shown together because **their arguments
barely overlap** -- what a demographics table needs, an adverse events table
does not, and vice versa.

!!! success "Checked against R"

    These are the R package's recipes (`` ?`rtfreporter-recipes` ``), and each
    program below writes **byte-for-byte the same RTF** as the R version
    (`tests/test_recipes_vs_r.py`).

## Which arguments each shape actually uses

| Setting | DM | AE | PK | LB |
|---|:-:|:-:|:-:|:-:|
| `stub=stub_spec(...)` (hierarchy) | -- | yes | yes | -- |
| `group_col` / `group_by` | yes | yes | yes | yes |
| `blank_rows` | -- | yes | yes | yes |
| `split` / `max_rows` | yes | yes | yes | -- |
| `drop_cols` (hidden carrier) | -- | -- | -- | yes |
| `set_decimal_split()` | -- | -- | yes | -- |
| `paginate_cols()` (too wide) | -- | -- | yes | -- |
| `fmt_*()` before building | -- | yes | yes | yes |

The single most common mistake is reaching for a stub on a table that has no
hierarchy (DM), or omitting it on one that does (AE, PK).

All four start from:

```python
from rtfreporter import (
    as_rtftables, generate_rtfreport, paginate_cols, rtf_document, rtf_page,
    rtf_tables, set_decimal_split, stub_spec,
)
```

## 1. DM -- demographics

A flat table, grouped by characteristic so a characteristic is never split
across pages.

```python
dm = {
    "Characteristic": ["Age (years)", "Age (years)", "Age (years)", "Sex", "Sex"],
    "Statistic": ["n", "Mean (SD)", "Median", "Male, n (%)", "Female, n (%)"],
    "Drug A": ["60", "54.2 (11.3)", "55.0", "31 (51.7%)", "29 (48.3%)"],
    "Drug B": ["58", "56.8 (10.1)", "57.5", "27 (46.6%)", "31 (53.4%)"],
}

dm_doc = rtf_tables(
    rtf_document(page=rtf_page(orientation="landscape")),
    as_rtftables(dm,
                 group_col="Characteristic",   # keep a characteristic whole
                 split="group_safe",
                 max_rows=20,
                 border="tfl"),
    titles=[["Table 14.1.1", "Demographic and Baseline Characteristics",
             "<Safety Analysis Set>"]],
)
generate_rtfreport(dm_doc, "t-14-1-1.rtf", overwrite=True)
```

## 2. AE -- adverse events

The SOC / PT hierarchy folded into one indented stub column.

```python
ae = {
    "SOC": ["Cardiac disorders"] * 2 + ["Gastrointestinal disorders"] * 3,
    "PT": ["Atrial fibrillation", "Bradycardia", "Nausea", "Vomiting", "Diarrhoea"],
    "Drug A": ["3 (5.0%)", "1 (1.7%)", "8 (13.3%)", "4 (6.7%)", "2 (3.3%)"],
    "Drug B": ["2 (3.4%)", "0", "6 (10.3%)", "3 (5.2%)", "5 (8.6%)"],
}

ae_doc = rtf_tables(
    rtf_document(page=rtf_page(orientation="landscape")),
    as_rtftables(ae,
                 stub=stub_spec(["SOC", "PT"]),  # the hierarchy DM does not have
                 group_by="indent",              # groups are found by indentation
                 blank_rows="between_groups",
                 split="group_safe",
                 max_rows=20,
                 border="tfl"),
    titles=[["Table 14.3.1",
             "Adverse Events by System Organ Class and Preferred Term",
             "<Safety Analysis Set>"]],
    footnotes=[["Percentages use the number of treated subjects."]],
)
generate_rtfreport(ae_doc, "t-14-3-1.rtf", overwrite=True)
```

## 3. PK -- concentrations

Decimal alignment, and a table wider than a page.

```python
pk = {
    "Time": ["1 h"] * 3 + ["2 h"] * 3,
    "Statistic": ["n", "Mean", "SD"] * 2,
    "Day 1": ["24", "1104.5", "233.41"] * 2,
    "Day 7": ["24", "88.012", "19.223"] * 2,
    "Day 14": ["24", "9.0125", "2.1044"] * 2,
    "Day 28": ["24", "1234.5", "301.22"] * 2,
}

pk_pages = as_rtftables(
    pk,
    stub=stub_spec(["Time", "Statistic"]),
    group_by="indent",
    blank_rows="between_groups",
    # ABSOLUTE widths: relative ones are normalised to the page, so the table
    # could never be too wide and paginate_cols() would have nothing to do
    column_widths_twips=[2000] + [1800] * 4,
    border="tfl",
)
pk_pages = set_decimal_split(pk_pages, cols=["Day 1", "Day 7", "Day 14", "Day 28"])
pk_pages = paginate_cols(pk_pages, at=3, carry=0)   # split by COLUMN, repeat the stub

pk_doc = rtf_document(page=rtf_page(orientation="landscape"))
for p in pk_pages:
    pk_doc = rtf_tables(pk_doc, p)
generate_rtfreport(pk_doc, "t-14-2-1.rtf", overwrite=True)
```

`at=3` and `carry=0` are 0-based column positions (R's `at = 4L`,
`carry = 1L`): the second page starts at the fourth column, and the stub is
carried onto it.

## 4. LB -- laboratory shift

Grouped by a column that is never printed.

```python
lb = {
    "PARAMCD": ["ALT"] * 3 + ["AST"] * 3,          # carrier: groups, not printed
    "Baseline": ["Normal", "Grade 1", "Grade 2"] * 2,
    "Normal": ["40", "5", "1", "38", "6", "2"],
    "Grade 1": ["8", "12", "3", "9", "11", "4"],
    "Grade 2": ["1", "4", "7", "2", "3", "6"],
}

lb_doc = rtf_tables(
    rtf_document(page=rtf_page(orientation="landscape")),
    as_rtftables(lb,
                 group_col="PARAMCD",    # group by it ...
                 drop_cols="PARAMCD",    # ... but never print it
                 blank_rows="between_groups",
                 border="tfl"),
    titles=[["Table 14.4.1", "Shift from Baseline in Laboratory Grade",
             "<Safety Analysis Set>"]],
)
generate_rtfreport(lb_doc, "t-14-4-1.rtf", overwrite=True)
```

## Where next

- [Get started](getting-started.md) walks through one report slowly.
- [Importing tables](importing-tables.md) for the conversion,
  [Adding tables and figures](adding-content.md) for placement,
  [Rendering and post-processing](output.md) to render.
- [Listings](listings.md) for the fifth shape, which is built from source data.
