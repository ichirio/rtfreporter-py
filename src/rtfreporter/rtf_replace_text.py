"""Post-processing text replacement in a rendered RTF file.

Ported from ``R/rtf_replace_text.R``.  Replaces one or more target strings in a
finished ``.rtf`` file -- e.g. swapping a ``"DRAFT"`` watermark for ``"FINAL"``
or bumping a version string -- writing either in place (with a ``.bak`` backup)
or to a new file.
"""

from __future__ import annotations

import os
import re
import shutil


def rtf_replace_text(
    input_file: str,
    target,
    replacement,
    output_file: str | None = None,
    encoding: str = "utf-8",
    use_regex: bool = False,
    case_insensitive: bool = False,
    backup: bool = True,
) -> str:
    """Replace target text in an RTF file, writing in place or to a new file.

    Args:
        input_file: Path to the source ``.rtf`` file.
        target: A single string or a list of strings to replace.
        replacement: A single string, or a list matching ``target`` (or length 1,
            applied to all targets).
        output_file: Destination path.  ``None`` (default) rewrites
            ``input_file`` in place (keeping a ``.bak`` copy when ``backup``).
        encoding: File encoding used to read and write (default ``"utf-8"``).
        use_regex: Treat ``target`` entries as regular expressions.
        case_insensitive: Match case-insensitively.
        backup: When writing in place, keep an ``input_file + ".bak"`` copy.

    Returns:
        The absolute path written.
    """
    if not isinstance(input_file, str):
        raise TypeError("`input_file` must be a single file path.")
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"`input_file` not found: {input_file}")

    targets = [target] if isinstance(target, str) else list(target)
    reps = [replacement] if isinstance(replacement, str) else list(replacement)
    if len(targets) == 0:
        raise ValueError("`target` is empty.")
    if not (len(reps) == len(targets) or len(reps) == 1):
        raise ValueError("`replacement` must be the same length as `target`, or length 1.")
    if len(reps) == 1 and len(targets) > 1:
        reps = reps * len(targets)

    with open(input_file, encoding=encoding) as fh:
        text = fh.read()

    flags = re.IGNORECASE if case_insensitive else 0
    for pat, rep in zip(targets, reps, strict=False):
        if use_regex or case_insensitive:
            regex = pat if use_regex else re.escape(pat)
            # A function replacement keeps `rep` literal (no group-ref expansion).
            text = re.sub(regex, lambda _m, r=rep: r, text, flags=flags)
        else:
            text = text.replace(pat, rep)

    if output_file is None:
        output_file = input_file
        if backup:
            shutil.copyfile(input_file, input_file + ".bak")

    with open(output_file, "w", encoding=encoding) as fh:
        fh.write(text)
    return os.path.abspath(output_file)
