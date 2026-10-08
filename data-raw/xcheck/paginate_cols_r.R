# Column pagination rendered with the R package, for the port's differential
# test (tests/test_paginate_cols_vs_r.py): paginate_cols().
#
# Usage (from the repo root, with the R release checked out beside it):
#   Rscript data-raw/xcheck/paginate_cols_r.R [path/to/rtfreporter]
#
# Writes tests/xcheck_golden/paginate_cols/.

args <- commandArgs(trailingOnly = TRUE)
pkg  <- if (length(args) >= 1) args[[1]] else "C:/Yrepo/rtfreporter"
if (requireNamespace("devtools", quietly = TRUE)) {
  suppressMessages(devtools::load_all(pkg, quiet = TRUE))
} else {
  # no devtools: the installed package (`R CMD INSTALL <pkg>` first)
  suppressMessages(library(rtfreporter))
}

out_dir <- file.path(getwd(), "tests", "xcheck_golden", "paginate_cols")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
write_doc <- function(pages, id, ...) {
  doc <- rtf_document() |> rtf_tables(pages, ...)
  generate_rtfreport(doc, file.path(out_dir, paste0(id, ".rtf")), overwrite = TRUE)
}

wide <- data.frame(Param = c("Hgb", "ALT", "AST", "Bili"),
                   `Placebo____Day 1` = c("13", "30", "25", "0.5"),
                   `Placebo____Day 7` = c("12", "31", "26", "0.6"),
                   `Drug____Day 1` = c("14", "29", "24", "0.4"),
                   `Drug____Day 7` = c("15", "28", "23", "0.7"),
                   check.names = FALSE, stringsAsFactors = FALSE)

# 1. cut before a column; two row pages; across and down
rows2 <- as_rtftables(wide, header_sep = NULL, split = "rows", split_rows = 3L)
write_doc(paginate_cols(rows2, at = "Drug____Day 1"), "at_across")
write_doc(paginate_cols(rows2, at = "Drug____Day 1", page_order = "down"), "at_down")

# 2. by the name separator, the two-level header from the names, groups outer
long <- rbind(cbind(Arm = "Low", wide), cbind(Arm = "High", wide))
grp <- as_rtftables(long, header_sep = NULL, split = "by_value", group_col = "Arm",
                    drop_cols = "Arm")
write_doc(paginate_cols(grp, by = "____", col_header = "names", page_order = "down"),
          "by_names_groups", auto_title = TRUE)

# 3. relative widths, fill vs keep; per-cell styles and a decimal split go along
t3 <- rtftable(wide, col_rel_width = c(2, 1, 1, 1.5, 1.5),
               cell_styles = list(NULL, list(bold = c(NA, NA, TRUE, NA, TRUE)), NULL, NULL)) |>
  set_decimal_split(cols = c(2L, 4L))
write_doc(paginate_cols(t3, cols = list(c("Placebo____Day 1", "Placebo____Day 7"),
                                        c("Drug____Day 1"), c("Drug____Day 7"))),
          "widths_fill")
write_doc(paginate_cols(t3, at = c("Placebo____Day 7", "Drug____Day 1"), width = "keep"),
          "widths_keep")

# 4. a whole-table header with spanning cells, sliced per page
hdr <- list(list(col_cell(1L, ""), col_cell(c(2L, 3L), "Placebo"), col_cell(c(4L, 5L), "Drug")),
            c("Parameter", "D1", "D7", "D1", "D7"))
write_doc(paginate_cols(rtftable(wide), at = "Placebo____Day 7", col_header = hdr),
          "sliced_header")
cat("wrote", out_dir, "\n")
