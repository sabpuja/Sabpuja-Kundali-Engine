"""Capture official swetest receipts for every chart fixture of matrix.json.

    python -m tests.sci_gold.capture --swetest PATH --ephe DIR      (from the repository root)

Writes receipts/<id>.txt and receipts/SHA256SUMS. Refuses to run with
SE_EPHE_PATH set. Deterministic: a second run must reproduce every byte.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import swiss_reference as sr


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--swetest", default=os.environ.get("SABPUJA_TEST_SWETEST"))
    ap.add_argument("--ephe", default=os.environ.get("SABPUJA_TEST_EPHE_PATH"))
    ap.add_argument("--out", default=str(sr.RECEIPTS))
    args = ap.parse_args(argv)
    if os.environ.get("SE_EPHE_PATH"):
        print("SE_EPHE_PATH must not be set", file=sys.stderr)
        return 2
    matrix = json.loads((sr.HERE / "matrix.json").read_text(encoding="utf-8"))
    os.makedirs(args.out, exist_ok=True)
    sums = []
    for fx in matrix["fixtures"]:
        if fx["expect"]["kind"] != "chart":
            continue
        text = sr.capture(fx, args.swetest, args.ephe)
        sr.parse(text)  # refuse to write a malformed receipt
        with open(os.path.join(args.out, fx["id"] + ".txt"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        sums.append(f"{sr.sha256_text(text)}  {fx['id']}.txt")
    with open(os.path.join(args.out, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(sums) + "\n")
    print(f"{len(sums)} receipts written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
