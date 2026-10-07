# Record what the R package's number formatters and catx() return, for the
# Python port's differential test (tests/test_formatters_vs_r.py).
#
# Usage (from the repo root, with the R release checked out beside it):
#   Rscript data-raw/xcheck/formatters_r.R [path/to/rtfreporter]
#
# Writes tests/xcheck_golden/formatters.json.

args <- commandArgs(trailingOnly = TRUE)
pkg  <- if (length(args) >= 1) args[[1]] else "C:/Yrepo/rtfreporter"
if (requireNamespace("devtools", quietly = TRUE)) {
  suppressMessages(devtools::load_all(pkg, quiet = TRUE))
} else {
  # no devtools: the installed package (`R CMD INSTALL <pkg>` first)
  suppressMessages(library(rtfreporter))
}

x <- c(0, 10.2, 103.4, 20.333333, 23.4463, 23.445, 99.995, 999.95, 0.333333,
       0.0004567, 0.00998, 2.675, 2.5, -2.5, -0.5, 0.5, 12345.6, -0.0004567,
       1e-10, 1234567.891, 0.05, 0.15, 1.005, NA, Inf, -Inf, NaN)

cases <- list()
add <- function(fn, args, out) {
  cases[[length(cases) + 1L]] <<- list(fn = fn, args = args, out = out)
}
for (rounding in c("r", "sas")) {
  for (d in c(1L, 2L, 3L, 4L)) {
    for (small in c("signif", "fixed")) {
      add("fmt_signif", list(digits = d, rounding = rounding, small = small),
          fmt_signif(x, digits = d, rounding = rounding, small = small, na = "NA"))
    }
  }
  for (d in c(0L, 1L, 2L, 3L)) {
    add("fmt_round", list(digits = d, rounding = rounding),
        fmt_round(x, digits = d, rounding = rounding, na = "NA"))
  }
}

df <- data.frame(stat = c("n", "  Mean", "SD", "Median", "", "CV%"),
                 a = c(24, 902.3312, 230.1234, 0.0004567, NA, 23.445),
                 b = c(3, 1.5, 2.25, 100.05, NA, 99.995),
                 txt = c("x", "y", "z", "w", "", "v"),
                 stringsAsFactors = FALSE)
nm <- list(
  by = fmt_numeric(df, cols = c("a", "b", "txt"), by = "stat",
                   formats = list(n = list(digits = 0), Mean = list(signif = 4),
                                  SD = list(signif = 4, small = "fixed"),
                                  .default = list(digits = 1)),
                   rounding = "sas"),
  signif = fmt_numeric(df, cols = c("a", "b"), signif = 3),
  digits = fmt_numeric(df, cols = "b", digits = 2, na = "-")
)

cx <- list(
  catx(" / ", c("Headache", "Nausea", NA, " "), c("Mild", NA, "Severe", "x")),
  catx("-", 1, c(2.5, NA, 0.1 + 0.2)),
  catx(", ", c("a", ""), "b")
)

out <- list(
  x = lapply(x, function(v) if (is.na(v) && !is.nan(v)) NULL else
    if (is.nan(v)) "NaN" else if (is.infinite(v)) (if (v > 0) "Inf" else "-Inf") else v),
  cases = cases,
  fmt_numeric = lapply(nm, function(d) lapply(d, function(col) as.list(col))),
  catx = cx
)
path <- file.path(getwd(), "tests", "xcheck_golden", "formatters.json")
jsonlite::write_json(out, path, auto_unbox = TRUE, digits = NA, null = "null",
                     na = "null", pretty = TRUE)
cat("wrote", path, "\n")
