# Sections with auto_section rendered with the R package, for the port's
# differential test (tests/test_sections_vs_r.py): a running header kept as the
# template of the auto sections, with and without an explicit section on the
# page an auto section starts (R #548: the explicit section wins that page).
#
# Usage (from the repo root, with the R package checked out beside it):
#   Rscript data-raw/xcheck/sections_r.R [path/to/rtfreporter]
#
# Writes tests/xcheck_golden/sections/.

args <- commandArgs(trailingOnly = TRUE)
pkg  <- if (length(args) >= 1) args[[1]] else "C:/Yrepo/rtfreporter"
if (requireNamespace("devtools", quietly = TRUE)) {
  suppressMessages(devtools::load_all(pkg, quiet = TRUE))
} else {
  # no devtools: the installed package (`R CMD INSTALL <pkg>` first)
  suppressMessages(library(rtfreporter))
}

out_dir <- file.path(getwd(), "tests", "xcheck_golden", "sections")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

d <- data.frame(a = c("x", "y"), b = c(1L, 2L), stringsAsFactors = FALSE)
pages <- function() list(
  T1 = as_rtftables(d, col_rel_width = c(50, 50)),
  T2 = as_rtftables(d, col_rel_width = c(50, 50)))
hdr <- function(s) rtf_header(rows = list(c(l = s)))

write_doc <- function(doc, id) {
  generate_rtfreport(doc, file.path(out_dir, paste0(id, ".rtf")), overwrite = TRUE)
}

# 1. the running header alone: one auto section per named page
write_doc(rtf_document() |>
            rtf_section(page = NULL, secinfo = list(header = hdr("Study"))) |>
            rtf_tables(combine_sections(T1 = pages()$T1, T2 = pages()$T2),
                       auto_section = TRUE),
          "auto_only")

# 2. and 3. an explicit section on the first / second auto section's page
for (pg in 1:2) {
  write_doc(rtf_document() |>
              rtf_section(page = NULL, secinfo = list(header = hdr("Study"))) |>
              rtf_section(page = pg, secinfo = list(header = hdr("Explicit"))) |>
              rtf_tables(combine_sections(T1 = pages()$T1, T2 = pages()$T2),
                         auto_section = TRUE),
            paste0("explicit_page", pg))
}
cat("wrote", length(list.files(out_dir)), "files to", out_dir, "\n")
