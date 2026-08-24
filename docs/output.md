# Rendering and post-processing

Turning a finished document into bytes, what those bytes contain, and the
last-mile edits you sometimes need on a rendered file.

## Rendering

`generate_rtfreport()` writes the document to a path and returns it:

```python
from rtfreporter import generate_rtfreport

generate_rtfreport(doc, "t_14_1_1_dm.rtf", overwrite=True)
```

Like the R package it **refuses to clobber an existing file** unless you ask:

```python
generate_rtfreport(doc, "report.rtf")                  # FileExistsError if present
generate_rtfreport(doc, "report.rtf", overwrite=True)  # replaces it
```

To keep the bytes in memory instead — to write them yourself, hash them, or diff
two runs — use `to_rtf()`:

```python
from rtfreporter import to_rtf

rtf = to_rtf(doc)
assert rtf.startswith("{" + chr(92) + "rtf1")
```

The fluent equivalents are `doc.save(path)` (which defaults to
`overwrite=True`) and `doc.to_rtf()`.

## What the output looks like

The rendered file is **plain ASCII**. Any character outside ASCII is emitted as
an RTF Unicode escape rather than raw bytes, so the file survives being moved
between systems, opened by old versions of Word, or committed to a repository
with strict encoding rules:

```python
rtf = to_rtf(doc)
assert all(ord(ch) < 128 for ch in rtf)
```

A few consequences worth knowing:

- **Non-breaking spaces**, which the count/percent aligners use for padding, are
  escaped rather than written literally.
- Superscripts, subscripts and the relational operators produced by the markup
  layer become RTF control words. See the markup notes in
  [Post-hoc styling](styling.md).
- Page-number fields (`{AUTO_PAGE}`, `{AUTO_TOTAL_PAGES}`) become **live RTF
  fields**, so Word recomputes them. They are not baked at render time. See
  [Headers and footers](headers-footers.md).

### Checking a file is well formed

RTF is a brace-nested format; a truncated or malformed file usually shows up as
unbalanced braces. This is the check the test suite uses:

```python
BS, OB, CB = chr(92), chr(123), chr(125)

def rtf_is_wellformed(text: str) -> bool:
    depth = lowest = i = 0
    while i < len(text):
        ch = text[i]
        if ch == BS and i + 1 < len(text) and text[i + 1] in (OB + CB + BS):
            i += 2          # an escaped literal brace, not structure
            continue
        if ch == OB:
            depth += 1
        elif ch == CB:
            depth -= 1
            lowest = min(lowest, depth)
        i += 1
    return depth == 0 and lowest >= 0
```

Note the escape handling: `\{` and `\}` are literal characters in the document
text and must not be counted as structure.

## Post-processing a rendered file

Sometimes a deliverable needs a change after rendering — a protocol number
corrected across a batch, a placeholder swapped for a run date, a sponsor name
updated. `rtf_replace_text()` edits the rendered bytes in place:

```python
from rtfreporter import rtf_replace_text

rtf_replace_text(
    "report.rtf",
    target="@RUN_DATE@",       # brace-free placeholder — see the warning below
    replacement="2026-08-23",
)
```

By default it **writes a backup** beside the original and edits in place. Give
`output_file` to write elsewhere and leave the input untouched:

```python
rtf_replace_text("draft.rtf", "DRAFT", "FINAL", output_file="final.rtf", backup=False)
```

Regular expressions and case-insensitive matching are available:

```python
rtf_replace_text("report.rtf", r"Page \d+ of \d+", "Page X of Y",
                 use_regex=True, case_insensitive=True)
```

!!! warning "You are editing RTF, not plain text"

    The file is RTF markup, so a search string can be split across control
    words, and replacing a brace or a backslash can corrupt the document.

    **Braces and backslashes are escaped in the output**, so a curly-brace
    placeholder never matches — it is written to the file with its braces
    escaped, and searching for the unescaped form silently replaces nothing:

    ```python
    rtf_replace_text("report.rtf", "{RUN_DATE}", "2026-08-23")   # matches nothing
    rtf_replace_text("report.rtf", "@RUN_DATE@", "2026-08-23")   # works
    ```

    Choose a **brace-free** placeholder such as `@RUN_DATE@` or a bare word, and
    re-check the result is well formed afterwards. (RTF's own page-number
    tokens like `{AUTO_PAGE}` are a different thing entirely — they are
    interpreted at render time and become live fields, not literal text.)

Prefer solving it upstream when you can: a token in a title, or a value threaded
through the header, is safer than a post-hoc edit.

## Combining several files

Rendering produces one file per report. To ship them as a single deliverable
with a table of contents, see [Assembling deliverables](assembling.md), which
covers `assemble_rtf()`, `assemble_files()`, `assemble_folder()` and the
`toc_*` helpers.

To structure **one** document into sections instead, see
[Splitting a report into sections](section-splitting.md).

## Where to next

- [Assembling deliverables](assembling.md) — many files into one, with a TOC.
- [Splitting a report into sections](section-splitting.md) — sections within a file.
- [Document API guide](document-api.md) — the calls that build `doc`.
