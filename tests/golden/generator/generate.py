"""Reference generator placeholder (KUN-01-WP2, not authorized yet).

WP1 ships only the isolation guard. Generating expected values needs the
owner's SCI decisions, frozen tolerances and QA review first, so this entry
point always refuses with exit code 2 (BLOCKED).
"""
from __future__ import annotations

import sys

from .isolation import import_guard


def main() -> int:
    with import_guard():
        print("BLOCKED: reference generator not implemented (KUN-01-WP2 not authorized); "
              "no expected values were produced", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
