# Sample ADaM data

`adsl.csv` and `adae.csv` are a trimmed copy of the `adsl` and `adae` datasets
from **[pharmaverseadam](https://pharmaverse.github.io/pharmaverseadam/)**
(© the pharmaverse authors, released under the **Apache License 2.0**), which
are themselves derived from the CDISC pilot study. They are vendored here so
every example in this repository runs with **no R installation and no network
access**.

## What was changed

Both files are subsets, not modifications — no value was altered:

| File | Rows | Columns kept | Filter applied |
|------|-----:|--------------|----------------|
| `adsl.csv` | 254 | `USUBJID`, `TRT01A`, `AGE`, `SEX`, `RACE`, `ETHNIC`, `SAFFL` | the three randomised arms only |
| `adae.csv` | 1122 | `USUBJID`, `TRT01A`, `AESOC`, `AEDECOD`, `TRTEMFL` | same three arms, and treatment-emergent events only (`TRTEMFL == "Y"`) |

## Reproducing them

`../../data-raw/export_pharmaverseadam.R` regenerates both CSVs from the R
package, and also writes `../../data-raw/R_reference_numbers.txt` — the figures
the R implementation produces, which `tests/test_showcase.py` checks the Python
showcase against.

```r
Rscript data-raw/export_pharmaverseadam.R
```

## Note on reading R data from Python

`pharmaverseadam` ships its datasets as an R *lazy-load database*
(`Rdata.rdb` / `Rdata.rdx`), not as standalone `.rda` files. `pyreadr` reads
standalone `.rds` / `.RData` files but **cannot** read that lazy-load database,
and the package bundles no CSV, Parquet or XPT. Converting through R once, as
the script above does, is therefore the practical route. (For SAS transport
files, `pandas.read_sas(..., format="xport")` works with no extra dependency.)

## If you would rather not use this data

`examples/adam_synthetic.py` generates seeded, reproducible ADaM-shaped data
with the same column contract and can be swapped in for `examples/adam_data.py`.
Its numbers are invented and do not match the figures above.
