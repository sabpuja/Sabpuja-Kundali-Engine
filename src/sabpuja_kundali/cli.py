"""Offline JSON stdin -> stdout CLI. Never log birth details."""
import json
import sys
from .engine import InputRefusalError, calculate

def main() -> int:
    try:
        # The 4 KB limit counts bytes, before decoding (P5-QA-01).
        data = sys.stdin.buffer.read(4097)
        if len(data) > 4096:
            raise InputRefusalError("REQUEST_INVALID", "Input exceeds 4 KB limit")
        try:
            raw = data.decode("utf-8")
        except UnicodeDecodeError:
            raise InputRefusalError("REQUEST_INVALID", "input must be UTF-8 text") from None
        try:
            request = json.loads(raw)
        except ValueError:
            # Covers JSONDecodeError; its position text is replaced so nothing of the input is echoed.
            raise InputRefusalError("REQUEST_INVALID", "input must be one JSON object") from None
        result = calculate(request)
    except (ValueError, RuntimeError) as exc:
        # Avoid printing raw input or stack traces containing personal data.
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
