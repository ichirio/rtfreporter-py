# Figures placed with the R package, for the port's differential test
# (tests/test_figure_vs_r.py): rtf_figures(width_twips = , height_twips = ,
# align = ) on an image path.  The image is tests/xcheck_golden/figure/tiny.png
# (written by the Python test's helper; committed).
#
# Usage (from the repo root, with the R release checked out beside it):
#   Rscript data-raw/xcheck/figure_r.R [path/to/rtfreporter]

args <- commandArgs(trailingOnly = TRUE)
pkg  <- if (length(args) >= 1) args[[1]] else "C:/Yrepo/rtfreporter"
if (requireNamespace("devtools", quietly = TRUE)) {
  suppressMessages(devtools::load_all(pkg, quiet = TRUE))
} else {
  # no devtools: the installed package (`R CMD INSTALL <pkg>` first)
  suppressMessages(library(rtfreporter))
}

dir <- file.path(getwd(), "tests", "xcheck_golden", "figure")
png <- file.path(dir, "tiny.png")
one <- function(id, ...) {
  doc <- rtf_document() |> rtf_figures(list(png), ..., titles = list("Figure 1"))
  generate_rtfreport(doc, file.path(dir, paste0(id, ".rtf")), overwrite = TRUE)
}
one("default")
one("sized_left", width_twips = 4320L, height_twips = 2160L, align = "left")
one("width_only_right", width_twips = 5000L, align = "right")
cat("wrote", dir, "\n")
