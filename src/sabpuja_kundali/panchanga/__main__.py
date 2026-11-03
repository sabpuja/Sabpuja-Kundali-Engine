"""Minimal offline Panchanga CLI: one chart request as JSON on stdin -> `sabpuja-panchanga/1` on stdout.

Same input contract, 4 KB limit and error contract as the chart CLI
(`sabpuja_kundali.cli`): a typed refusal prints {"error": "<CODE>: <fixed text>"}
to stderr and exits 2, with no traceback and no input echoed. Never logs birth details.
Run as `python -m sabpuja_kundali.panchanga`.
"""
import json
import sys

from ..engine import InputRefusalError
from .contract import EXPECTED_ERRORS, calculate


def main() -> int:
    try:
        data = sys.stdin.buffer.read(4097)
        if len(data) > 4096:
            raise InputRefusalError("REQUEST_INVALID", "Input exceeds 4 KB limit")
        try:
            raw = data.decode("utf-8")
        except UnicodeDecodeError:
            raise InputRefusalError("REQUEST_INVALID", "input must be UTF-8 text") from None
        try:
            request = json.loads(raw)
        except (ValueError, RecursionError):
            raise InputRefusalError("REQUEST_INVALID", "input must be one JSON object") from None
        result = calculate(request)
    except EXPECTED_ERRORS as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
