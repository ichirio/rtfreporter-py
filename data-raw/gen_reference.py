"""Generate docs/reference.md: R-style grouped API reference with descriptions.

Mirrors the grouping of the R package's pkgdown reference index so the two
sites correspond section for section.  Fails loudly if a public symbol is
missing from the spec, so the page can never silently fall behind the API.
"""

from __future__ import annotations

import rtfreporter as rr

GROUPS: list[tuple[str, str, list[str]]] = [
    (
        "Document and rendering",
        "The entry point and the final render call.  Build a document by passing "
        "`rtf_document()` through the section and content calls below, then render "
        "it with `generate_rtfreport()`.  Every builder returns a **new** document; "
        "the one passed in is left unchanged, as in R.",
        ["RtfDocument", "rtf_document", "rtf_config", "rtf_page", "DefaultFormat",
         "rtf_default_format", "Page", "generate_rtfreport", "to_rtf", "save"],
    ),
    (
        "Package defaults",
        "Inspect and reset the configurable `rtfreporter.*` defaults (paper size, "
        "orientation, margins, font, font size).  Resolution order: an explicit "
        "argument, then an option, then the factory value.",
        ["rtfreporter_options", "rtfreporter_reset_defaults"],
    ),
    (
        "Sections: headers and footers",
        "A section applies a running header and footer to a range of pages.  The "
        "bands are themselves small tables whose rows you build with `rtf_header()` "
        "/ `rtf_footer()` and edit with the `update_*_row()` helpers.",
        ["rtf_section", "rtf_header", "rtf_footer", "HeaderFooter",
         "update_header_row", "update_footer_row"],
    ),
    (
        "Page content: tables and figures",
        "Add one content item per page with `rtf_tables()` / `rtf_figures()`, and "
        "attach per-page titles and footnotes.  For finer control build the content "
        "object yourself with `rtftable()` / `rtfplot()` and pass it in.",
        ["rtf_tables", "rtf_figures", "rtf_titles", "rtf_footnotes",
         "rtftable", "RtfTable", "ColSpec", "rtfplot", "Figure"],
    ),
    (
        "Importing tables",
        "Convert a pandas or polars DataFrame, a `great_tables` GT object, or a "
        "plain dict/records structure into `RtfTable` pages, reading the source's "
        "metadata and paginating in one call.  `as_rtftables()` returns one table "
        "**per page**; `as_rtftable()` is the single-page form.  `stub_cols()` "
        "finishes a tidy frame beforehand by merging hierarchy columns into one "
        "indented stub.",
        ["as_rtftables", "as_rtftable", "combine_sections", "stub_cols"],
    ),
    (
        "Column headers",
        "Multi-row column headers with optional spanning cells, addressed by "
        "position (`cols=1`, `cols=(1, 3)`) or by column name.  Ranges are "
        "**inclusive and 0-based**.  `set_col_header()` configures the header of a "
        "finished table against its final printed columns; `rtf_columns()` lists "
        "those columns; `rtf_header_source()` deparses the current header back to "
        "editable source.",
        ["rtf_col_header", "col_cell", "SpanCell", "HeaderRow",
         "col_header_from_names", "add_col_header_row", "set_col_header",
         "set_header_cell", "rtf_columns", "rtf_header_source"],
    ),
    (
        "Post-hoc styling verbs",
        "Restyle an already-built table -- or every page of an `as_rtftables()` "
        "list at once -- addressing header rows, body rows and columns by position. "
        "Each verb returns a modified copy; last writer wins, per side and per "
        "field.  `collapse_repeats()` blanks repeated group values.",
        ["style_header", "style_body", "style_cols", "style_zone",
         "add_header_row", "collapse_repeats"],
    ),
    (
        "Cell-format functions",
        "Ready-made cell re-formatters for the `cell_format` argument of "
        "`rtftable()` / `as_rtftables()`, notably monospaced count/percent "
        "alignment.  You can also write your own, following the same "
        "one-column-in / one-column-out contract.",
        ["format_count_pct", "realign_count_pct", "fmt_count_paren",
         "fmt_count_paren_bare", "fmt_right_align"],
    ),
    (
        "Blank rows",
        "Insert blank separator rows by position, by value change, or by rule.  "
        "Positions are 0-based; the two R sentinels (`0` and `-1`) are the named "
        "constants `BEFORE_FIRST` and `AFTER_LAST`.",
        ["set_blank_rows", "blank_rows_by_change", "blank_rows_by_rule",
         "BlankRowsByChange", "BlankRowsByRule", "BEFORE_FIRST", "AFTER_LAST"],
    ),
    (
        "Pagination strategies and helpers",
        "Built-in page-split strategies as reusable callables for the `split=` "
        "argument of `as_rtftables()`, plus the helpers for writing your own.  "
        "`group_force` cuts on every `max_rows` and repeats the group header with "
        "a continuation label; `group_safe` never splits a group.",
        ["paginate", "Frame", "PaginationError", "add_cont_label",
         "page_split_none", "page_split_rows", "page_split_by_value",
         "page_split_group_safe", "page_split_group_force"],
    ),
    (
        "Borders",
        "Border specifications.  Borders apply to content-table zones, to header "
        "and footer rows, and to individual columns and cells, so the same builders "
        "are reused throughout a report.",
        ["rtf_border_side", "rtf_border", "rtf_border_with", "rtf_border_none",
         "rtf_border_top", "rtf_border_bottom", "rtf_border_box",
         "rtf_table_border", "rtf_border_tfl", "Border", "BorderSide",
         "TableBorder"],
    ),
    (
        "Shared table styles",
        "Bundle border, padding and row-height defaults into a reusable style and "
        "share it across many tables.  Snapshot semantics: a table captures the "
        "style's state at construction.",
        ["rtf_table_style", "rtf_table_style_with", "rtf_table_style_tfl",
         "TableStyle"],
    ),
    (
        "Column-width utilities",
        "Measure rendered text and propose column widths.",
        ["text_width_in", "auto_col_widths"],
    ),
    (
        "Assembling multiple RTF files",
        "Combine several rendered RTF files into one deliverable with a table of "
        "contents -- for example a TLF shell catalogue.",
        ["assemble_rtf", "assemble_files", "assemble_folder", "assemble_spec",
         "assemble_from_spec", "assemble_toc", "toc_heading", "toc_entry"],
    ),
    (
        "Post-processing",
        "Last-mile edits to an already-rendered RTF file, such as a one-off "
        "find-and-replace on the generated bytes.",
        ["rtf_replace_text"],
    ),
    (
        "Markup",
        "Inline text markup: superscripts, subscripts and relational operators, "
        "resolved into RTF control words at render time.",
        ["resolve_markup"],
    ),
]

HEADER = """# API reference

Every symbol below is importable directly from the top-level `rtfreporter`
package, and follows the R package's name, arguments and defaults.

!!! note "Two deliberate divergences from R"

    **All index-taking arguments are 0-based** (R is 1-based), and the
    `blank_rows` sentinels are the named constants `BEFORE_FIRST` /
    `AFTER_LAST` rather than the magic integers `0` and `-1`.
    See [Differences from the R package](r-differences.md).

## Contents

"""


def anchor(module: str, name: str) -> str:
    return f"#{module}.{name}"


def main() -> None:
    public = [n for n in rr.__all__ if not n.startswith("__")]
    spec = [n for _, _, names in GROUPS for n in names]

    missing = sorted(set(public) - set(spec))
    extra = sorted(set(spec) - set(public))
    if missing:
        raise SystemExit(f"Symbols missing from the reference spec: {missing}")
    if extra:
        raise SystemExit(f"Spec names that are not public: {extra}")
    dupes = sorted({n for n in spec if spec.count(n) > 1})
    if dupes:
        raise SystemExit(f"Symbols listed in more than one group: {dupes}")

    out = [HEADER]

    # Index table: one row per group, symbols linked to their anchors.
    out.append("| Group | Symbols |\n|---|---|\n")
    for title, _desc, names in GROUPS:
        slug = title.lower().replace(" ", "-").replace(":", "").replace(",", "")
        links = ", ".join(f"`{n}`" for n in names)
        out.append(f"| [{title}](#{slug}) | {links} |\n")
    out.append("\n")

    for title, desc, names in GROUPS:
        out.append(f"\n## {title}\n\n{desc}\n\n")
        for name in names:
            module = getattr(rr, name).__module__ if hasattr(getattr(rr, name), "__module__") else None
            if module is None:  # constants such as BEFORE_FIRST
                module = "rtfreporter.blank_rows"
            out.append(f"::: {module}.{name}\n\n")

    open("docs/reference.md", "w", encoding="utf-8", newline="\n").write("".join(out))
    print(f"wrote docs/reference.md: {len(GROUPS)} groups, {len(spec)} symbols")


if __name__ == "__main__":
    main()
