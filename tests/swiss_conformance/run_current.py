"""CLI: python -m tests.swiss_conformance.run_current --swetest PATH --receipt RECEIPT.json --ephe DIR --report-dir reports/

Runs the KUN-03 current profile, the test-only historical-numerics supplement
and the unchanged archival PR #18 profile, and reconciles them.
Exit 0 SWISS-CONFORMANCE PASS, 1 FAIL, 2 BLOCKED.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import os
import sys

from .conformance import REPO_ROOT
from .current import run_all, to_markdown, write_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Swiss-conformance reconciliation: KUN-03 profile vs official swetest")
    parser.add_argument("--swetest", default=os.environ.get("SABPUJA_TEST_SWETEST"))
    parser.add_argument("--receipt", default=os.environ.get("SABPUJA_TEST_SWETEST_RECEIPT"))
    parser.add_argument("--ephe", default=os.environ.get("SABPUJA_EPHE_PATH"))
    parser.add_argument("--report-dir", type=Path, default=REPO_ROOT / "reports")
    args = parser.parse_args(argv)
    report = run_all(args.swetest, args.ephe, args.receipt)
    paths = write_reports(report, args.report_dir)
    print(to_markdown(report))
    print("Reports: " + ", ".join(p.name for p in paths))
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
