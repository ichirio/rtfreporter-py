# Assemble two deliverables with the R package, for the port's differential
# test of assemble_rtf() (tests/test_assemble_vs_r.py).
#
# Usage (from the repo root, with the R release checked out beside it):
#   Rscript data-raw/xcheck/assemble_r.R [path/to/rtfreporter]
#
# Writes tests/xcheck_golden/assemble/*.rtf.

args <- commandArgs(trailingOnly = TRUE)
pkg  <- if (length(args) >= 1) args[[1]] else "C:/Yrepo/rtfreporter"
suppressMessages(devtools::load_all(pkg, quiet = TRUE))

out_dir <- file.path(getwd(), "tests", "xcheck_golden", "assemble")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
work <- tempfile("asm"); dir.create(work)

# Each deliverable reserves the book's page number in its footer.
one <- function(id, rows) {
  df <- data.frame(Item = paste0(id, "-", seq_len(rows)), N = as.character(seq_len(rows)))
  doc <- rtf_document() |>
    rtf_tables(as_rtftables(df)) |>
    rtf_titles(list(paste("Table", id))) |>
    rtf_section(page = 1, secinfo = list(
      header = rtf_header(rows = list(c(l = "Study X", r = "Page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}"))),
      footer = rtf_footer(rows = list(c(c = "{BOOK_PAGE}")))))
  path <- file.path(work, paste0(id, ".rtf"))
  generate_rtfreport(doc, path)
  path
}
inputs <- c(one("T1", 3), one("T2", 2))

assemble_rtf(inputs, file.path(out_dir, "book_page.rtf"), overwrite = TRUE,
             book_page = "Book page {AUTO_PAGE} of {AUTO_TOTAL_PAGES}")
assemble_rtf(inputs, file.path(out_dir, "book_page_none.rtf"), overwrite = TRUE)
cat("wrote", out_dir, "\n")
