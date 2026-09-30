# gt tables rendered with the R package, for the port's differential test
# (tests/test_gt_vs_r.py): the source column names kept verbatim (#458), and
# the gt metadata (alignment, widths, cell styles, labels, spanners) following
# its columns through `drop_cols` and `stub`.  The Python side builds the same
# tables with great_tables.
#
# Usage (from the repo root, with the R release checked out beside it):
#   Rscript data-raw/xcheck/gt_r.R [path/to/rtfreporter]
#
# Writes tests/xcheck_golden/gt/.

args <- commandArgs(trailingOnly = TRUE)
pkg  <- if (length(args) >= 1) args[[1]] else "C:/Yrepo/rtfreporter"
suppressMessages(devtools::load_all(pkg, quiet = TRUE))
library(gt)

out_dir <- file.path(getwd(), "tests", "xcheck_golden", "gt")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
write_doc <- function(pages, id) {
  doc <- rtf_document() |> rtf_tables(pages)
  generate_rtfreport(doc, file.path(out_dir, paste0(id, ".rtf")), overwrite = TRUE)
}

src <- data.frame(
  Characteristic  = c("Age, Mean (SD)", "Sex, n (%)", "Weight, kg"),
  `Drug A (N=60)` = c("54.2 (11.3)", "31 (51.7)", "70.1"),
  `2024 total`    = c("112", "58", "69.8"),
  check.names = FALSE, stringsAsFactors = FALSE)

# 1. non-syntactic names kept; a column addressed by its own name
g1 <- gt(src)
p1 <- as_rtftables(g1) |> set_col_header(c(`Drug A (N=60)` = "Drug A"))
write_doc(p1, "names_verbatim")
writeLines(names(p1[[1]]$data), file.path(out_dir, "names_verbatim.txt"))

# 2. drop_cols by name: alignment, widths and a user width follow the columns
g2 <- gt(src) |>
  cols_align("center", columns = `Drug A (N=60)`) |>
  cols_align("right", columns = `2024 total`) |>
  cols_width(Characteristic ~ pct(50), `Drug A (N=60)` ~ pct(30),
             `2024 total` ~ pct(20))
write_doc(as_rtftables(g2, drop_cols = "Drug A (N=60)"), "drop_align_width")

# 3. drop_cols with body cell styles and a spanner over the kept columns
g3 <- gt(src) |>
  tab_spanner("Treatment", columns = c(`Drug A (N=60)`, `2024 total`)) |>
  tab_style(cell_fill("#FFFF00"), cells_body(columns = `2024 total`, rows = 1)) |>
  tab_style(cell_text(weight = "bold"), cells_body(columns = Characteristic, rows = 2))
write_doc(as_rtftables(g3, drop_cols = "Drug A (N=60)"), "drop_styles_spanner")

# 4. stub on a gt table: labels, alignment and cell styles follow the stub
src4 <- data.frame(SOC = c("Cardiac", "Cardiac", "Skin"),
                   PT  = c("Palpitations", "Tachycardia", "Rash"),
                   n   = c("3", "1", "5"), stringsAsFactors = FALSE)
g4 <- gt(src4) |>
  cols_label(n = "Count") |>
  cols_align("center", columns = n) |>
  tab_style(cell_text(style = "italic"), cells_body(columns = n, rows = 2))
write_doc(as_rtftables(g4, stub = stub_spec(c("SOC", "PT"))), "stub_labels_styles")

# 5. stub + drop_cols together
src5 <- cbind(src4, ord = c("1", "2", "3"))
g5 <- gt(src5) |> cols_align("right", columns = n)
write_doc(as_rtftables(g5, stub = stub_spec(c("SOC", "PT")), drop_cols = "ord"),
          "stub_and_drop")

# 6. by_value + stub: each group's page keeps the gt labels and alignment
write_doc(as_rtftables(g4, split = "by_value", group_col = "SOC",
                       stub = stub_spec(c("SOC", "PT"))), "by_value_stub")
cat("wrote", out_dir, "\n")
