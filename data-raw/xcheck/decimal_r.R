# Decimal-point alignment rendered with the R package, for the port's
# differential test (tests/test_decimal_vs_r.py): set_decimal_split().
#
# Usage (from the repo root, with the R release checked out beside it):
#   Rscript data-raw/xcheck/decimal_r.R [path/to/rtfreporter]
#
# Writes tests/xcheck_golden/decimal/.

args <- commandArgs(trailingOnly = TRUE)
pkg  <- if (length(args) >= 1) args[[1]] else "C:/Yrepo/rtfreporter"
suppressMessages(devtools::load_all(pkg, quiet = TRUE))

out_dir <- file.path(getwd(), "tests", "xcheck_golden", "decimal")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
write_doc <- function(tbl, id) {
  doc <- rtf_document() |> rtf_tables(list(tbl))
  generate_rtfreport(doc, file.path(out_dir, paste0(id, ".rtf")), overwrite = TRUE)
}

df <- data.frame(Stat = c("n", "Mean", "SD", "Min, Max", "p-value", "Median", "CV"),
                 A = c("12", "3.45", "0.123", "1.0, 9.9", "<0.001", NA, ".5"),
                 B = c("100", "12.3 (4.56)", "7.1", "n/a", "0.045", "15", "2.25"),
                 stringsAsFactors = FALSE)

write_doc(rtftable(df) |> set_decimal_split(cols = c("A", "B")), "default")
write_doc(rtftable(df, border = rtf_border(all = TRUE)) |>
            set_decimal_split(cols = "B", ratio = 0.3, include_compound = TRUE),
          "ratio_compound_box")
write_doc(rtftable(df, font_size_half_points = 20, cell_styles = list(
            NULL, list(bold = c(NA, TRUE, NA)), NULL, NULL, NULL, NULL,
            list(color = c(NA, "#FF0000", NA)))) |>
            set_decimal_split(cols = 2L, pad_chars = c(0, 0), min_chars = c(0, 0)),
          "styles_size")
# A split row keeps the table's font and the cell fill (R #509, fixed in
# 0.8.2.9003 -- render this script with R main from that fix on; see
# "Which R the golden files come from" in data-raw/xcheck/README.md).
write_doc(rtftable(df, font = "Arial") |>
            style_cols(cols = "A", background = "#EFEFEF") |>
            style_body(rows = 2L, cols = "A", background = "#F8D7DA") |>
            set_decimal_split(cols = "A"),
          "font_fill")
cat("wrote", out_dir, "\n")
