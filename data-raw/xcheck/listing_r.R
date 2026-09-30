# Listings built with the R package, for the port's differential test
# (tests/test_listing_vs_r.py): build_listing(), as_rtftables(listing = ),
# fit_listing_widths() and listing_wrap().
#
# Usage (from the repo root, with the R release checked out beside it):
#   Rscript data-raw/xcheck/listing_r.R [path/to/rtfreporter]
#
# Writes tests/xcheck_golden/listing/.

args <- commandArgs(trailingOnly = TRUE)
pkg  <- if (length(args) >= 1) args[[1]] else "C:/Yrepo/rtfreporter"
suppressMessages(devtools::load_all(pkg, quiet = TRUE))

out_dir <- file.path(getwd(), "tests", "xcheck_golden", "listing")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

ae <- jsonlite::fromJSON(file.path(getwd(), "data-raw", "xcheck", "listing_data.json"))
ae <- as.data.frame(ae, stringsAsFactors = FALSE)

write_doc <- function(pages, id) {
  doc <- rtf_document() |> rtf_tables(pages)
  generate_rtfreport(doc, file.path(out_dir, paste0(id, ".rtf")), overwrite = TRUE)
}

spec1 <- listing_spec(list(
  listing_col("USUBJID", width = 11, collapse_repeats = TRUE, label = "Subject"),
  listing_col(c("AETERM", "AEDECOD"), width = 20),
  listing_col(c("ASTDT", "AENDT"), width = 10, label = c("Start /", "End")),
  listing_col("AESEV", width = 8, align = "center")))
write_doc(as_rtftables(ae, listing = spec1, max_rows = 12), "multiline")

spec2 <- listing_spec(list(
  listing_col(c("USUBJID", "AGE", "SEX"), width = 16, sep = " / "),
  listing_col(c("AETERM", "AEDECOD"), width = 24, layout = "flow"),
  "AESEV"), spacer = FALSE, blank_row = FALSE, record = FALSE, align = "right")
write_doc(as_rtftables(ae, listing = spec2), "flow_no_spacer")

body <- build_listing(ae, spec1)
spec3 <- fit_listing_widths(ae, listing_spec(list(
  listing_col("USUBJID"), listing_col(c("AETERM", "AEDECOD")),
  listing_col(c("ASTDT", "AENDT"), width = 12), "AESEV")),
  labels = c(AETERM = "Reported Term", AEDECOD = "Preferred Term"))

corpus <- c("Headache/Mild/Resolved after two weeks of treatment",
            "Supercalifragilisticexpialidocious-term, long", "", "a/b/c",
            "Line one\nLine two/three", "\u982d\u75db/\u8efd\u5ea6\u306e\u982d\u75db\u304c\u7d9a\u304f")
wraps <- lapply(c(6, 10, 15), function(w) list(
  stack = lapply(corpus, listing_wrap, width = w, sep = "/", layout = "stack"),
  flow  = lapply(corpus, listing_wrap, width = w, sep = "/", layout = "flow")))

jsonlite::write_json(list(
  body = lapply(body, function(v) as.list(v)),
  body_names = names(body),
  fit = lapply(spec3$cols, function(cl) list(name = cl$name, width = cl$width,
                                              rel_width = cl$rel_width, label = cl$label)),
  wraps = wraps),
  file.path(out_dir, "listing.json"), auto_unbox = TRUE, digits = NA, pretty = TRUE)
cat("wrote", out_dir, "\n")
