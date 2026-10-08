"""Snapshot the R package's exports and report the port's API parity.

Usage (from the repo root, the R package checked out beside it)::

    python data-raw/r_api/api_parity.py ../rtfreporter          # report
    python data-raw/r_api/api_parity.py ../rtfreporter --write  # refresh the snapshot

The snapshot, ``data-raw/r_api/r_exports.txt``, is what
``tests/test_api_parity.py`` checks the Python ``__all__`` against, so CI
needs no R checkout.  An R export that is neither in ``rtfreporter.__all__``
nor listed as out of scope in that test fails it.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAPSHOT = HERE / "r_exports.txt"


def r_exports(r_repo: Path) -> list[str]:
    ns = (r_repo / "NAMESPACE").read_text(encoding="utf-8")
    return re.findall(r"^export\(([^)]+)\)", ns, flags=re.M)


def r_version(r_repo: Path) -> str:
    desc = (r_repo / "DESCRIPTION").read_text(encoding="utf-8")
    version = re.search(r"^Version:\s*(\S+)", desc, flags=re.M).group(1)
    try:
        sha = subprocess.run(["git", "-C", str(r_repo), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sha = "unknown"
    return f"{version} ({sha})"


def main(argv: list[str]) -> int:
    r_repo = Path(argv[1]) if len(argv) > 1 else HERE.parents[1].parent / "rtfreporter"
    names = r_exports(r_repo)
    if "--write" in argv:
        SNAPSHOT.write_text(
            f"# R rtfreporter {r_version(r_repo)}: export() lines of NAMESPACE, in order.\n"
            "# Regenerate with data-raw/r_api/api_parity.py <R checkout> --write\n"
            + "\n".join(names) + "\n", encoding="utf-8")
        print(f"wrote {SNAPSHOT} ({len(names)} exports)")
    sys.path.insert(0, str(HERE.parents[1] / "tests"))
    sys.path.insert(0, str(HERE.parents[1] / "src"))
    import rtfreporter as rr
    from test_api_parity import NOT_PORTED, OUT_OF_SCOPE

    ported = [n for n in names if n in rr.__all__]
    skipped = [n for n in names if n in OUT_OF_SCOPE]
    missing = [n for n in names if n not in rr.__all__ and n not in OUT_OF_SCOPE
               and n not in NOT_PORTED]
    in_scope = len(names) - len(skipped)
    print(f"R exports: {len(names)}; ARD / plan (out of scope): {len(skipped)}; "
          f"in scope: {in_scope}; in Python: {len(ported)}; not ported on purpose: "
          f"{', '.join(sorted(NOT_PORTED))}")
    if missing:
        print("MISSING from the port: " + ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
