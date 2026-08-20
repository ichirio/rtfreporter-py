# rtfreporter

**A Python toolkit for clinical RTF Tables, Listings and Figures (TLFs).**

`rtfreporter` composes a Rich Text Format (RTF) document — the format regulators
and medical writers still expect — directly from tabular data, with **no
third-party RTF engine**. It is a faithful, Pythonic port of the R package
[`rtfreporter`](https://github.com/ichirio/rtfreporter).

- Build tables with multi-row **spanning column headers**, per-column
  formatting, and the clinical **TFL border** convention.
- Turn a **pandas** / **polars** DataFrame or a **great_tables** `GT` object
  into paginated pages with one call (`as_rtftables`).
- Running **headers / footers** with automatic page-number fields
  (`{AUTO_PAGE}`, `{AUTO_TOTAL_PAGES}`).
- **Titles / footnotes**, blank separator rows, `(Cont.)` continuation markers.
- Embed **PNG / JPEG figures** at their native DPI.
- A fluent, chainable document builder plus a plain functional layer.

## Install

```bash
pip install rtfreporter          # core (no hard dependencies)
pip install "rtfreporter[all]"   # + pandas, polars, great_tables
```

## Quickstart

```python
from rtfreporter import RtfDocument, header, footer

doc = (
    RtfDocument()
    .add_section(
        header=rtf_header([{"l": "Protocol XYZ", "r": "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"}]),
        footer=rtf_footer([{"c": "CONFIDENTIAL"}]),
    )
    .add_table(
        {"Subject": ["001", "002", "003"], "Age": [34, 45, 28], "Sex": ["M", "F", "M"]},
        title=["Table 14.1", "", "Demographic Characteristics"],
        footnote=["Source: ADSL"],
    )
)

doc.save("demographics.rtf")
```

From a DataFrame with automatic pagination:

```python
import pandas as pd
from rtfreporter import RtfDocument, as_rtftables

df = pd.DataFrame({"Arm": ["A"] * 40 + ["B"] * 40, "Subject": range(80)})
pages = as_rtftables(df, split="group_force", group_col="Arm", max_rows=25)

doc = RtfDocument()
for page in pages:
    doc.add_table(page, title=["Listing 16.1"])
doc.save("listing.rtf")
```

## Documentation

Full documentation, including per-topic guides and the API reference, lives at
<https://ichirio.github.io/rtfreporter-py/>.

Runnable end-to-end examples are in [`examples/`](examples/):
`demographics.py`, `pagination.py`, and `styling.py`.

## License

Apache-2.0. See [LICENSE](LICENSE).
