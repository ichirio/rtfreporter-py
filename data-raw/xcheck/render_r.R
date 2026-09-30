# Render every cross-check case with the R package.
#
# Usage (from the repo root, with the R package checked out beside it):
#   Rscript data-raw/xcheck/render_r.R [path/to/rtfreporter]
#
# The path should be a checkout of the R RELEASE the port tracks (a `git
# worktree add ../rtfreporter-v0.8.2 v0.8.2`), so the goldens say which R the
# port matches.  Writes one RTF per case into tests/xcheck_golden/, which is
# committed so the Python test suite can compare against R's output without
# needing R installed.

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
# `[[` rather than `$`: `$` partial-matches, so a {"rtf_border": ...} object
# would be mistaken for an index object.
pick <- function(v) if (is.list(v) && !is.null(v[["r"]])) v[["r"]] else v

as_df <- function(cols) {
  cols <- lapply(cols, function(v) unlist(v, use.names = FALSE))
  as.data.frame(cols, stringsAsFactors = FALSE, check.names = FALSE)
}

# A border written as JSON: {"all": true, "inside_h": "double", "top": false}
# -> rtf_border(...).  A side is TRUE / FALSE / a style name, or an object
# {"style": , "width": , "color": } -> rtf_border_side().
as_border <- function(b) {
  sides <- lapply(b, function(v) {
    if (is.list(v)) do.call(rtf_border_side, v) else v
  })
  do.call(rtf_border, sides)
}

# A title / footnote block: strings, or named rows {"l": , "c": , "r": }.
as_block <- function(rows) {
  lapply(rows, function(r) if (is.list(r)) unlist(r) else r)
}

# Block-level style for rtf_titles() / rtf_footnotes(): a border is written
# as JSON, everything else passes through.
as_style <- function(st) {
  if (!is.null(st$border)) st$border <- as_border(st$border)
  st
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
               "col_rel_width", "col_header")) {
    if (!is.null(a[[nm]])) a[[nm]] <- unlist(a[[nm]], use.names = FALSE)
  }
  # cell_styles: one entry per row, null or {"bold": [null, true], ...};
  # a null inside a vector is NA ("use the column's own").
  if (!is.null(a$cell_styles)) {
    a$cell_styles <- lapply(a$cell_styles, function(r) {
      if (is.null(r)) return(NULL)
      lapply(r, function(v) unlist(lapply(v, function(z) if (is.null(z)) NA else z)))
    })
  }
  # A whole-table border written as {"rtf_border": {...}}.
  if (is.list(a$border) && !is.null(a$border$rtf_border)) {
    a$border <- as_border(a$border$rtf_border)
  }

  pages <- do.call(as_rtftables, c(list(df), a))

  # Post-hoc zone borders, applied to every page.
  if (!is.null(case$style_zone)) {
    zones <- lapply(case$style_zone, as_border)
    pages <- do.call(style_zone, c(list(pages), zones))
  }

  doc_args <- list()
  if (!is.null(case$page)) {
    doc_args$page <- do.call(rtf_page, lapply(case$page, pick))
  }
  if (!is.null(case$default_format)) {
    doc_args$default_format <- do.call(rtf_default_format, case$default_format)
  }
  # The declared fonts, first = the default: a list of family names.
  if (!is.null(case$font_table)) {
    doc_args$font_table <- lapply(case$font_table, function(f) list(name = f))
  }
  # A watermark: a bare string, or {"text": , "angle": , ...} for rtf_watermark().
  if (!is.null(case$watermark)) {
    doc_args$watermark <- if (is.list(case$watermark))
      do.call(rtf_watermark, case$watermark) else case$watermark
  }
  doc <- do.call(rtf_document, doc_args)

  doc <- rtf_tables(doc, pages)
  if (!is.null(case$titles)) {
    doc <- do.call(rtf_titles, c(list(doc, list(as_block(case$titles))),
                                 as_style(case$titles_style)))
  }
  if (!is.null(case$footnotes)) {
    doc <- do.call(rtf_footnotes, c(list(doc, list(as_block(case$footnotes))),
                                    as_style(case$footnotes_style)))
  }

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
  # The run tokens: a fixed program and time, so R and the port agree.
  if (!is.null(case$run)) {
    old <- options(rtfreporter.render_time = as.POSIXct(case$run$render_time))
    generate_rtfreport(doc, path, program = case$run$program)
    options(old)
  } else {
    generate_rtfreport(doc, path)
  }
  written <- c(written, id)
  cat("  wrote", id, "\n")
}

cat("\n", length(written), "golden files written to", out_dir, "\n")
