# Render every cross-check case with the R package.
#
# Usage (from the repo root, with the R package checked out beside it):
#   Rscript data-raw/xcheck/render_r.R [path/to/rtfreporter]
#
# Writes one RTF per case into tests/xcheck_golden/, which is committed so the
# Python test suite can compare against R's output without needing R installed.

args <- commandArgs(trailingOnly = TRUE)
pkg  <- if (length(args) >= 1) args[[1]] else "C:/Yrepo/rtfreporter"
suppressMessages(devtools::load_all(pkg, quiet = TRUE))

if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("jsonlite is required: install.packages('jsonlite')")
}

here    <- file.path(getwd(), "data-raw", "xcheck")
out_dir <- file.path(getwd(), "tests", "xcheck_golden")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

spec  <- jsonlite::fromJSON(file.path(here, "cases.json"), simplifyVector = FALSE)
cases <- spec$cases

# An index may be given as {"r": 1, "py": 0}; take the R side.
pick <- function(v) if (is.list(v) && !is.null(v$r)) v$r else v

as_df <- function(cols) {
  cols <- lapply(cols, function(v) unlist(v, use.names = FALSE))
  as.data.frame(cols, stringsAsFactors = FALSE, check.names = FALSE)
}

written <- character(0)

for (case in cases) {
  id <- case$id
  df <- as_df(case$data)

  a <- lapply(case$as_rtftables, pick)

  # blank_rows_by_change is expressed as the column to watch.
  if (!is.null(a$blank_rows_by_change)) {
    a$blank_rows <- blank_rows_by_change(unlist(a$blank_rows_by_change))
    a$blank_rows_by_change <- NULL
  }
  for (nm in c("stub_vars", "sort_by", "drop_cols", "collapse_repeats",
               "col_rel_width")) {
    if (!is.null(a[[nm]])) a[[nm]] <- unlist(a[[nm]], use.names = FALSE)
  }

  pages <- do.call(as_rtftables, c(list(df), a))

  doc <- if (!is.null(case$page)) {
    rtf_document(page = do.call(rtf_page, lapply(case$page, pick)))
  } else {
    rtf_document()
  }

  tbl_args <- list(doc, pages)
  if (!is.null(case$titles)) {
    tbl_args$titles <- list(unlist(case$titles, use.names = FALSE))
  }
  if (!is.null(case$footnotes)) {
    tbl_args$footnotes <- list(unlist(case$footnotes, use.names = FALSE))
  }
  doc <- do.call(rtf_tables, tbl_args)

  if (!is.null(case$header) || !is.null(case$footer)) {
    to_rows <- function(rows) lapply(rows, function(r) unlist(r))
    sec <- list()
    if (!is.null(case$header)) sec$header <- rtf_header(rows = to_rows(case$header))
    if (!is.null(case$footer)) {
      if (identical(case$footer_border, "none")) {
        sec$footer <- rtf_footer(rows = to_rows(case$footer), border = NULL)
      } else {
        sec$footer <- rtf_footer(rows = to_rows(case$footer))
      }
    }
    doc <- rtf_section(doc, page = 1, secinfo = sec)
  }

  path <- file.path(out_dir, paste0(id, ".rtf"))
  if (file.exists(path)) file.remove(path)
  generate_rtfreport(doc, path)
  written <- c(written, id)
  cat("  wrote", id, "\n")
}

cat("\n", length(written), "golden files written to", out_dir, "\n")
