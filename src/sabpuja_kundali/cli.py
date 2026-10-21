"""Offline JSON stdin -> stdout CLI. Never log birth details."""
import json
import sys
from .engine import calculate

def main() -> int:
    try:
        raw = sys.stdin.read(4097)
        if len(raw) > 4096:
            raise ValueError("Input exceeds 4 KB limit")
        result = calculate(json.loads(raw))
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        # Avoid printing raw input or stack traces containing personal data.
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
