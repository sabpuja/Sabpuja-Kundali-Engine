"""Compare the PAN-REF-PHASE-2026 fixture with re-read publisher values.

Usage:
    python3 -I compare_phase_sources.py FIXTURE.json USNO.txt NASA.txt

Each publisher file has one event per line: ``MM-DD <Phase name> HH:MM [marker]``,
with phase names New Moon, First Quarter, Full Moon, Last Quarter.

Exit status:
    0  every check passed
    1  at least one discrepancy (details printed, one ``ERROR`` line each)
    2  unreadable or malformed input

Checks: fixture case count, publisher file event counts, malformed or duplicate
lines, duplicate fixture keys, fixture values absent from a publisher file,
publisher events absent from the fixture, minute mismatches, eclipse-marker
mismatches (NASA), and the fixture's recorded inter-source difference.

Documentation evidence only. It reads published minutes; it runs no engine and
no Swiss Ephemeris calculation.
"""

import json
import sys

PHASES = ("New Moon", "First Quarter", "Full Moon", "Last Quarter")
SOURCES = ("SRC-USNO-PHASES", "SRC-NASA-PHASES")
EXPECTED_EVENTS = 50


class InputError(Exception):
    pass


def _is_hhmm(s):
    return len(s) == 5 and s[2] == ":" and s[:2].isdigit() and s[3:].isdigit()


def load_publisher(path, errors):
    events = {}
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            tokens = raw.split()
            if not tokens:
                continue
            if len(tokens) not in (4, 5):
                raise InputError(f"{path}:{lineno}: expected 'MM-DD Phase Name HH:MM [marker]'")
            md, phase, hhmm = tokens[0], " ".join(tokens[1:3]), tokens[3]
            marker = tokens[4] if len(tokens) == 5 else None
            if phase not in PHASES or not _is_hhmm(hhmm) or len(md) != 5 or md[2] != "-":
                raise InputError(f"{path}:{lineno}: malformed line {raw.strip()!r}")
            key = (md, phase)
            if key in events:
                errors.append(f"duplicate publisher event {key} in {path}")
                continue
            events[key] = (hhmm, marker)
    return events


def fixture_marker(pv):
    m = pv.get("source_markers")
    return m.split()[0] if m else None


def compare(fixture_path, usno_path, nasa_path):
    errors = []
    rows = []
    try:
        with open(fixture_path, encoding="utf-8") as fh:
            fixture = json.load(fh)
        live = {"SRC-USNO-PHASES": load_publisher(usno_path, errors),
                "SRC-NASA-PHASES": load_publisher(nasa_path, errors)}
        cases = fixture["cases"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise InputError(str(exc)) from exc

    if len(cases) != EXPECTED_EVENTS:
        errors.append(f"fixture has {len(cases)} cases, expected {EXPECTED_EVENTS}")
    for src, events in live.items():
        if len(events) != EXPECTED_EVENTS:
            errors.append(f"{src} file has {len(events)} events, expected {EXPECTED_EVENTS}")

    seen = {src: set() for src in SOURCES}
    for case in cases:
        try:
            cid = case["case_id"]
            phase = case["event"]["published_phase_name"]
            values = case["published_values"]
        except (KeyError, TypeError) as exc:
            raise InputError(f"malformed fixture case: {exc}") from exc
        by_src = {}
        for pv in values:
            src = pv.get("source_id")
            v = pv.get("value_utc_minute", "")
            if src not in SOURCES or len(v) != 17 or not v.endswith("Z"):
                raise InputError(f"{cid}: malformed published value {pv!r}")
            key = (v[5:10], phase)
            if key in seen[src]:
                errors.append(f"{cid}: duplicate fixture key {key} for {src}")
            seen[src].add(key)
            by_src[src] = v[11:16]
            got = live[src].get(key)
            if got is None:
                status = "ABSENT"
                errors.append(f"{cid} {src} {key}: not found in publisher file")
            elif got[0] != v[11:16]:
                status = "MISMATCH"
                errors.append(f"{cid} {src} {key}: fixture {v[11:16]} vs publisher {got[0]}")
            else:
                status = "MATCH"
            if src == "SRC-NASA-PHASES" and got is not None and got[1] != fixture_marker(pv):
                errors.append(f"{cid} {src} {key}: marker fixture {fixture_marker(pv)!r} vs publisher {got[1]!r}")
                status += "+MARKER_MISMATCH"
            if src == "SRC-USNO-PHASES" and got is not None and got[1] is not None:
                errors.append(f"{cid} {src} {key}: unexpected marker {got[1]!r} in USNO file")
            rows.append((cid, phase, src, v[11:16], got[0] if got else None,
                         got[1] if got else None, status, pv.get("source_markers")))
        if set(by_src) != set(SOURCES):
            errors.append(f"{cid}: expected one value from each of {SOURCES}, got {sorted(by_src)}")
        elif "inter_source_difference_minutes" in case:
            u, n = (int(by_src[s][:2]) * 60 + int(by_src[s][3:]) for s in SOURCES)
            if abs(n - u) != case["inter_source_difference_minutes"]:
                errors.append(f"{cid}: recorded inter-source difference "
                              f"{case['inter_source_difference_minutes']} != {abs(n - u)}")

    for src in SOURCES:
        for key in sorted(set(live[src]) - seen[src]):
            errors.append(f"{src} {key}: publisher event absent from fixture")

    diffs = [(k, live["SRC-USNO-PHASES"][k][0], live["SRC-NASA-PHASES"][k][0])
             for k in live["SRC-USNO-PHASES"]
             if k in live["SRC-NASA-PHASES"]
             and live["SRC-USNO-PHASES"][k][0] != live["SRC-NASA-PHASES"][k][0]]
    return rows, errors, live, diffs


def main(argv):
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        rows, errors, live, diffs = compare(argv[1], argv[2], argv[3])
    except InputError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    for r in rows:
        print("\t".join(str(x) for x in r))
    mism = sum(1 for r in rows if r[6] != "MATCH")
    print("values", len(rows), "mismatches", mism)
    print("live usno entries", len(live["SRC-USNO-PHASES"]),
          "live nasa entries", len(live["SRC-NASA-PHASES"]))
    print("live inter-source differences", len(diffs))
    for d in diffs:
        print(" ", d)
    for e in errors:
        print("ERROR", e)
    print("RESULT", "PASS" if not errors else f"FAIL ({len(errors)} errors)")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
