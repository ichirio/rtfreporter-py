# Column-header features rendered with the R package, for the port's
# differential test (tests/test_header_vs_r.py): col_cell(pos = <selector>) /
# col_key(), set_col_header(values = ) and a named label row, and what
# header_map() reports.
#
# Usage (from the repo root, with the R release checked out beside it):
#   Rscript data-raw/xcheck/header_r.R [path/to/rtfreporter]
#
# Writes tests/xcheck_golden/header/.

args <- commandArgs(trailingOnly = TRUE)
pkg  <- if (length(args) >= 1) args[[1]] else "C:/Yrepo/rtfreporter"
if (requireNamespace("devtools", quietly = TRUE)) {
  suppressMessages(devtools::load_all(pkg, quiet = TRUE))
} else {
  # no devtools: the installed package (`R CMD INSTALL <pkg>` first)
  suppressMessages(library(rtfreporter))
}

out_dir <- file.path(getwd(), "tests", "xcheck_golden", "header")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
write_doc <- function(pages, id) {
  doc <- rtf_document() |> rtf_tables(pages, auto_title = TRUE)
  generate_rtfreport(doc, file.path(out_dir, paste0(id, ".rtf")), overwrite = TRUE)
}

wide <- data.frame(Param = c("Hgb", "ALT"),
                   `Placebo____Day 1` = c("13", "30"), `Placebo____Day 7` = c("12", "31"),
                   `Drug____Day 1` = c("14", "29"), `Drug____Day 7` = c("15", "28"),
                   check.names = FALSE, stringsAsFactors = FALSE)

# 1. a spanning row selected by a column-name segment
p1 <- as_rtftables(wide, header_sep = NULL) |>
  set_col_header(list(col_cell(1L, ""),
                      col_cell(col_key("Placebo"), "Placebo"),
                      col_cell(col_key("Drug"), "Drug")),
                 c("Param", "Day 1", "Day 7", "Day 1", "Day 7"))
write_doc(p1, "col_key")

# 2. per-page values for tokens in a shared header
long <- data.frame(Period = c("P1", "P1", "P2", "P2"),
                   Param = c("Hgb", "ALT", "Hgb", "ALT"),
                   Placebo = c("13", "30", "12", "31"),
                   Drug = c("14", "29", "15", "28"), stringsAsFactors = FALSE)
p2 <- as_rtftables(long, split = "by_value", group_col = "Period", drop_cols = "Period")
vals <- data.frame(group = c("P1", "P2"), n_pbo = c(120, 118), n_drug = c(121, 117))
p2 <- set_col_header(p2, c("Parameter", "Placebo\n(N={n_pbo})", "Drug\n(N={n_drug}) {{x}}"),
                     values = vals)
write_doc(p2, "values")
jsonlite::write_json(header_map(p2), file.path(out_dir, "header_map.json"),
                     auto_unbox = TRUE, digits = NA, pretty = TRUE)

# 3. a named label row: the columns it leaves out keep their own name
p3 <- as_rtftables(long[, -1]) |> set_col_header(c(Placebo = "PBO", Drug = "Active"))
write_doc(p3, "named_row")
cat("wrote", out_dir, "\n")
