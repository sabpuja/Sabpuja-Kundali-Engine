"""Check proposed golden-fixture civil inputs against IANA tz rules (stdlib only).

Research evidence for docs/accuracy/golden-chart-spec.md. It applies the same
round-trip rule as the engine's _parse_birth (local -> zone -> local and offset
unchanged) using Python zoneinfo, but does not import the engine. It verifies
that each proposed input is valid or invalid under the tzdata in use; it does
not compute any astronomy and is not a reference value.

Usage: python -I fixture_input_check.py
"""
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CASES = [
    ("GC-01", "2000-01-01T17:30:00+05:30", "Asia/Kolkata"),
    ("GC-02", "1956-03-21T05:30:00+05:30", "Asia/Kolkata"),
    ("GC-03", "1975-08-15T06:10:00+05:30", "Asia/Kolkata"),
    ("GC-04", "2026-10-21T14:45:00+05:30", "Asia/Kolkata"),
    ("GC-05", "2050-06-15T23:55:00+05:30", "Asia/Kolkata"),
    ("GC-06", "2099-12-31T20:00:00+05:30", "Asia/Kolkata"),
    ("GC-07", "2024-02-29T08:15:00+11:00", "Australia/Sydney"),
    ("GC-08", "1985-07-10T21:45:00-03:00", "America/Argentina/Buenos_Aires"),
    ("GC-09", "1966-01-20T03:05:00+00:00", "Europe/London"),
    ("GC-10", "1919-11-11T11:00:00-05:00", "America/New_York"),
    ("GC-11", "1937-04-01T12:00:00+02:00", "Africa/Johannesburg"),
    ("GC-12", "2010-09-23T00:00:00-05:00", "America/Guayaquil"),
    ("GC-13", "2015-06-21T12:00:00+00:00", "Atlantic/Reykjavik"),
    ("GC-14", "1990-05-05T06:00:00+05:45", "Asia/Kathmandu"),
    ("GC-15", "1981-12-31T23:00:00+07:30", "Asia/Singapore"),
    ("GC-16", "1905-06-01T09:00:00+05:21:10", "Asia/Kolkata"),
    ("GC-17", "1943-06-15T10:00:00+06:30", "Asia/Kolkata"),
    ("GC-18", "1900-01-01T00:00:00+05:21:10", "Asia/Kolkata"),
    ("GC-19", "2100-12-31T23:59:00+14:00", "Pacific/Kiritimati"),
    ("GC-20", "2100-12-31T23:59:00-08:00", "America/Los_Angeles"),
    ("TZ-01", "2021-03-14T02:30:00-05:00", "America/New_York"),
    ("TZ-02a", "2021-11-07T01:30:00-04:00", "America/New_York"),
    ("TZ-02b", "2021-11-07T01:30:00-05:00", "America/New_York"),
    ("TZ-03a", "2023-04-02T02:30:00+10:30", "Australia/Adelaide"),
    ("TZ-03b", "2023-04-02T02:30:00+09:30", "Australia/Adelaide"),
    ("TZ-03c", "2023-10-01T02:30:00+09:30", "Australia/Adelaide"),
    ("TZ-04", "2023-10-01T02:15:00+10:30", "Australia/Lord_Howe"),
    ("TZ-05", "2024-01-10T12:00:00+13:45", "Pacific/Chatham"),
    ("TZ-06", "1995-07-01T12:00:00-02:30", "America/St_Johns"),
    ("TZ-07", "2000-01-01T17:30:00+05:00", "Asia/Kolkata"),
    ("TZ-08a", "2000-02-29T12:00:00+05:30", "Asia/Kolkata"),
    ("TZ-08b", "2024-02-29T12:00:00+05:30", "Asia/Kolkata"),
    ("TZ-09a", "2000-03-01T02:00:00+05:30", "Asia/Kolkata"),
    ("TZ-09b", "2000-02-28T20:00:00-08:00", "America/Los_Angeles"),
    ("TZ-10a", "1930-01-15T10:00:00+04:51", "Asia/Kolkata"),
    ("TZ-10b", "1930-01-15T10:00:00+05:30", "Asia/Kolkata"),
    ("TZ-11a", "1945-10-14T23:30:00+06:30", "Asia/Kolkata"),
    ("TZ-11b", "1945-10-14T23:30:00+05:30", "Asia/Kolkata"),
    ("TZ-12a", "2011-12-30T12:00:00+14:00", "Pacific/Apia"),
    ("TZ-12b", "2011-12-31T00:00:00+14:00", "Pacific/Apia"),
    ("TZ-13", "1981-12-31T23:45:00+07:30", "Asia/Singapore"),
]
INVALID_DATES = ["1900-02-29T12:00:00+05:21:10", "2100-02-29T12:00:00+05:30"]


def tzdata_version() -> str:
    path = Path("/usr/share/zoneinfo/tzdata.zi")
    try:
        return path.read_text(encoding="utf-8").splitlines()[0]
    except OSError:
        return "unknown (no system tzdata.zi)"


print("tzdata:", tzdata_version())
for cid, text, tz in CASES:
    local = datetime.fromisoformat(text)
    actual = local.astimezone(ZoneInfo(tz))
    valid = (actual.replace(tzinfo=None) == local.replace(tzinfo=None)
             and actual.utcoffset() == local.utcoffset())
    utc = local.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    print(f"{cid:7s} {text:29s} {tz:31s} {'VALID ' if valid else 'REJECT'} utc={utc}")
for text in INVALID_DATES:
    try:
        datetime.fromisoformat(text)
        print(f"{text}: parses (unexpected)")
    except ValueError as exc:
        print(f"{text}: invalid calendar date ({exc})")
