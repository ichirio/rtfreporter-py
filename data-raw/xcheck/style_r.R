# Row / cell styling rendered with the R package, for the port's differential
# test (tests/test_style_vs_r.py): style_body(rows = ) and
# style_header(row = , cols = , label = , border = , underline = ).
#
# Usage (from the repo root, with the R release checked out beside it):
#   Rscript data-raw/xcheck/style_r.R [path/to/rtfreporter]
#
# Writes tests/xcheck_golden/style/.

args <- commandArgs(trailingOnly = TRUE)
pkg  <- if (length(args) >= 1) args[[1]] else "C:/Yrepo/rtfreporter"
if (requireNamespace("devtools", quietly = TRUE)) {
  suppressMessages(devtools::load_all(pkg, quiet = TRUE))
} else {
  # no devtools: the installed package (`R CMD INSTALL <pkg>` first)
  suppressMessages(library(rtfreporter))
}

out_dir <- file.path(getwd(), "tests", "xcheck_golden", "style")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
write_doc <- function(tbl, id) {
  doc <- rtf_document() |> rtf_tables(list(tbl))
  generate_rtfreport(doc, file.path(out_dir, paste0(id, ".rtf")), overwrite = TRUE)
}

df <- data.frame(Stat = c("n", "Mean", "SD", "Median"),
                 A = c("10", "5.1", "1.2", "5.0"),
                 B = c("12", "5.4", "1.1", "5.3"), stringsAsFactors = FALSE)

# 1. style_body by row: a predicate, a position list, a border on some cells
t1 <- rtftable(df) |>
  style_body(rows = ~ Stat == "Mean", bold = TRUE, background = "#FFFF00") |>
  style_body(rows = c(3L, 4L), cols = "B", color = "#FF0000", italic = TRUE,
             align = "right", indent_twips = 120L) |>
  style_body(rows = 1L, border = rtf_border(bottom = "double"))
write_doc(t1, "body_rows")

# 2. style_header on a two-row header: one cell's label, border and underline
t2 <- rtftable(df, col_header = list(c("", "Arm A", "Arm B"), c("Statistic", "Value", "Value"))) |>
  style_header(row = 2L, cols = "B", label = "Val.", border = rtf_border(bottom = "double"),
               underline = TRUE) |>
  style_header(row = 1L, cols = c("A", "B"), align = "right")
write_doc(t2, "header_cells")
cat("wrote", out_dir, "\n")
