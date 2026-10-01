# The four recipes of ?`rtfreporter-recipes` (DM, AE, PK, LB) rendered with the
# R package, for the port's differential test (tests/test_recipes_vs_r.py);
# docs/recipes.md shows the same four programs in Python.  The data and the
# calls are the R help page's, written with `stub = stub_spec()` where the help
# page still uses the superseded `stub_vars`.
#
# Usage (from the repo root, with the R release checked out beside it):
#   Rscript data-raw/xcheck/recipes_r.R [path/to/rtfreporter]
#
# Writes tests/xcheck_golden/recipes/.

args <- commandArgs(trailingOnly = TRUE)
pkg  <- if (length(args) >= 1) args[[1]] else "C:/Yrepo/rtfreporter"
suppressMessages(devtools::load_all(pkg, quiet = TRUE))

out_dir <- file.path(getwd(), "tests", "xcheck_golden", "recipes")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
out <- function(id) file.path(out_dir, paste0(id, ".rtf"))

# 1. DM -- demographics.  Flat table, grouped by characteristic.
dm <- data.frame(
  Characteristic = c("Age (years)", "Age (years)", "Age (years)", "Sex", "Sex"),
  Statistic      = c("n", "Mean (SD)", "Median", "Male, n (%)", "Female, n (%)"),
  `Drug A`       = c("60", "54.2 (11.3)", "55.0", "31 (51.7%)", "29 (48.3%)"),
  `Drug B`       = c("58", "56.8 (10.1)", "57.5", "27 (46.6%)", "31 (53.4%)"),
  check.names = FALSE, stringsAsFactors = FALSE
)
dm_doc <- rtf_document(page = rtf_page(orientation = "landscape")) |>
  rtf_tables(
    as_rtftables(dm, group_col = "Characteristic", split = "group_safe",
                 max_rows = 20, border = "tfl"),
    titles = list(c("Table 14.1.1", "Demographic and Baseline Characteristics",
                    "<Safety Analysis Set>"))
  )
generate_rtfreport(dm_doc, out("dm"), overwrite = TRUE)

# 2. AE -- adverse events.  SOC / PT hierarchy folded into one stub column.
ae <- data.frame(
  SOC = c(rep("Cardiac disorders", 2), rep("Gastrointestinal disorders", 3)),
  PT  = c("Atrial fibrillation", "Bradycardia", "Nausea", "Vomiting", "Diarrhoea"),
  `Drug A` = c("3 (5.0%)", "1 (1.7%)", "8 (13.3%)", "4 (6.7%)", "2 (3.3%)"),
  `Drug B` = c("2 (3.4%)", "0", "6 (10.3%)", "3 (5.2%)", "5 (8.6%)"),
  check.names = FALSE, stringsAsFactors = FALSE
)
ae_doc <- rtf_document(page = rtf_page(orientation = "landscape")) |>
  rtf_tables(
    as_rtftables(ae, stub = stub_spec(c("SOC", "PT")), group_by = "indent",
                 blank_rows = "between_groups", split = "group_safe",
                 max_rows = 20, border = "tfl"),
    titles = list(c("Table 14.3.1",
                    "Adverse Events by System Organ Class and Preferred Term",
                    "<Safety Analysis Set>")),
    footnotes = list("Percentages use the number of treated subjects.")
  )
generate_rtfreport(ae_doc, out("ae"), overwrite = TRUE)

# 3. PK -- concentrations.  Decimal alignment and a table wider than a page.
pk <- data.frame(
  Time      = c(rep("1 h", 3), rep("2 h", 3)),
  Statistic = rep(c("n", "Mean", "SD"), 2),
  `Day 1`   = c("24", "1104.5", "233.41"),
  `Day 7`   = c("24", "88.012", "19.223"),
  `Day 14`  = c("24", "9.0125", "2.1044"),
  `Day 28`  = c("24", "1234.5", "301.22"),
  check.names = FALSE, stringsAsFactors = FALSE
)
pk_pages <- as_rtftables(pk, stub = stub_spec(c("Time", "Statistic")),
                         group_by = "indent", blank_rows = "between_groups",
                         column_widths_twips = c(2000L, rep(1800L, 4)),
                         border = "tfl")
pk_pages <- pk_pages |>
  set_decimal_split(cols = 2:5) |>
  paginate_cols(at = 4L, carry = 1L)
pk_doc <- rtf_document(page = rtf_page(orientation = "landscape"))
for (p in pk_pages) pk_doc <- rtf_tables(pk_doc, p)
generate_rtfreport(pk_doc, out("pk"), overwrite = TRUE)

# 4. LB -- laboratory shift, grouped by a column that is never printed.
lb <- data.frame(
  PARAMCD   = c(rep("ALT", 3), rep("AST", 3)),
  Baseline  = rep(c("Normal", "Grade 1", "Grade 2"), 2),
  Normal    = c("40", "5", "1", "38", "6", "2"),
  `Grade 1` = c("8", "12", "3", "9", "11", "4"),
  `Grade 2` = c("1", "4", "7", "2", "3", "6"),
  check.names = FALSE, stringsAsFactors = FALSE
)
lb_doc <- rtf_document(page = rtf_page(orientation = "landscape")) |>
  rtf_tables(
    as_rtftables(lb, group_col = "PARAMCD", drop_cols = "PARAMCD",
                 blank_rows = "between_groups", border = "tfl"),
    titles = list(c("Table 14.4.1", "Shift from Baseline in Laboratory Grade",
                    "<Safety Analysis Set>"))
  )
generate_rtfreport(lb_doc, out("lb"), overwrite = TRUE)
cat("wrote", out_dir, "\n")
