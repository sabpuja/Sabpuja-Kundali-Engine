"""KUN-SCI-GOLD-001 independent TZif reader (test-only, isolated).

A small RFC 8536 reader written for this task. It does not use zoneinfo,
datetime.tzinfo or the engine's `timezones.py`; it reads the version 2+ body
(64-bit transition times) of a TZif file given as bytes, and answers "which UTC
offsets does this local wall time have" by brute force over the transitions.

It covers the instants used by the KUN-SCI-GOLD-001 fixtures (1969-2100). For
an instant after the last transition it applies the POSIX TZ footer only for
the rule shapes those fixtures need (`Mm.w.d[/time]`); any other footer raises,
so an unsupported case is never answered silently.

The same IANA data (tzdata 2026e) feeds the engine, so agreement here proves
that the engine applies the IANA rules correctly; it is not historical
civil-clock evidence (DATA-01 remains open).
"""
from __future__ import annotations

import re
import struct
from calendar import monthrange, timegm


class TzifError(ValueError):
    pass


def _parse_body(data: bytes, offset: int, time_size: int):
    if data[offset:offset + 4] != b"TZif":
        raise TzifError("bad magic")
    counts = struct.unpack(">6l", data[offset + 20:offset + 44])
    isutcnt, isstdcnt, leapcnt, timecnt, typecnt, charcnt = counts
    pos = offset + 44
    fmt = ">%d%s" % (timecnt, "q" if time_size == 8 else "l")
    times = list(struct.unpack(fmt, data[pos:pos + timecnt * time_size]))
    pos += timecnt * time_size
    idx = list(data[pos:pos + timecnt])
    pos += timecnt
    types = []
    for _ in range(typecnt):
        utoff, isdst, desig = struct.unpack(">lBB", data[pos:pos + 6])
        types.append((utoff, isdst, desig))
        pos += 6
    chars = data[pos:pos + charcnt]
    pos += charcnt
    pos += leapcnt * (time_size + 4) + isstdcnt + isutcnt
    names = [chars[d:chars.index(b"\0", d)].decode("ascii") for _, _, d in types]
    return times, idx, [(t[0], t[1], n) for t, n in zip(types, names)], pos


def parse(data: bytes) -> dict:
    if data[:4] != b"TZif" or data[4:5] not in (b"2", b"3", b"4"):
        raise TzifError("need TZif version 2 or later")
    # Skip the version 1 body, then read the 64-bit body and the footer.
    _, _, _, end_v1 = _parse_body(data, 0, 4)
    times, idx, types, end = _parse_body(data, end_v1, 8)
    footer = data[end:].split(b"\n")[1].decode("ascii")
    return {"times": times, "idx": idx, "types": types, "footer": footer}


_FOOTER = re.compile(
    r"^(?P<std>[A-Za-z]+|<[^>]+>)(?P<stdoff>[-+]?\d+(?::\d+){0,2})"
    r"(?:(?P<dst>[A-Za-z]+|<[^>]+>)(?P<dstoff>[-+]?\d+(?::\d+){0,2})?"
    r",M(?P<m1>\d+)\.(?P<w1>\d)\.(?P<d1>\d)(?:/(?P<t1>[-+]?\d+(?::\d+){0,2}))?"
    r",M(?P<m2>\d+)\.(?P<w2>\d)\.(?P<d2>\d)(?:/(?P<t2>[-+]?\d+(?::\d+){0,2}))?)?$")


def _hms(text: str | None, default: int) -> int:
    if text is None:
        return default
    sign = -1 if text.startswith("-") else 1
    parts = [int(p) for p in text.lstrip("+-").split(":")]
    parts += [0] * (3 - len(parts))
    return sign * (parts[0] * 3600 + parts[1] * 60 + parts[2])


def _mwd(year: int, month: int, week: int, dow: int) -> int:
    """Day of month of the w-th (5 = last) weekday dow (0 = Sunday) of month."""
    first_dow = (timegm((year, month, 1, 0, 0, 0)) // 86400 + 4) % 7  # 1970-01-01 was a Thursday
    day = 1 + (dow - first_dow) % 7 + (week - 1) * 7
    while day > monthrange(year, month)[1]:
        day -= 7
    return day


def _footer_transitions(footer: str, year: int) -> list[tuple[int, int, int]]:
    """[(utc_seconds, new_utoff, isdst)] for one year from a POSIX TZ footer."""
    m = _FOOTER.match(footer)
    if not m:
        raise TzifError("unsupported POSIX TZ footer")
    std = -_hms(m["stdoff"], 0)              # POSIX sign is inverted
    if not m["dst"]:
        return []
    dst = -_hms(m["dstoff"], -std - 3600) if m["dstoff"] else std + 3600
    on_local = timegm((year, int(m["m1"]), _mwd(year, int(m["m1"]), int(m["w1"]), int(m["d1"])), 0, 0, 0)) + _hms(m["t1"], 7200)
    off_local = timegm((year, int(m["m2"]), _mwd(year, int(m["m2"]), int(m["w2"]), int(m["d2"])), 0, 0, 0)) + _hms(m["t2"], 7200)
    # The start time is in local standard time, the end time in local daylight time.
    return sorted([(on_local - std, dst, 1), (off_local - dst, std, 0)])


def offset_at(tz: dict, utc: int) -> int:
    """UTC offset in seconds at a UTC instant (seconds since 1970-01-01T00:00:00Z)."""
    times, idx, types = tz["times"], tz["idx"], tz["types"]
    if not times or utc < times[0]:
        first_std = next((t for t in types if not t[1]), types[0])
        return first_std[0]
    if utc < times[-1] or not tz["footer"]:
        k = max(i for i, t in enumerate(times) if t <= utc)
        return types[idx[k]][0]
    # After the table: last transition, then the footer rules.
    current = types[idx[-1]][0]
    year = 1970 + utc // 31556952
    for y in range(year - 1, year + 2):
        for when, off, _ in _footer_transitions(tz["footer"], y):
            if when <= utc and when >= times[-1]:
                current = off
    return current


def local_offsets(tz: dict, wall: int) -> list[int]:
    """All offsets o with offset_at(wall - o) == o: [] in a gap, two in a fold.

    wall is the local wall time expressed as seconds since 1970-01-01T00:00:00 (naive).
    """
    candidates = {t[0] for t in tz["types"]}
    if tz["footer"]:
        m = _FOOTER.match(tz["footer"])
        if not m:
            raise TzifError("unsupported POSIX TZ footer")
        candidates.add(-_hms(m["stdoff"], 0))
        if m["dst"]:
            std = -_hms(m["stdoff"], 0)
            candidates.add(-_hms(m["dstoff"], -std - 3600) if m["dstoff"] else std + 3600)
    return sorted(o for o in candidates if offset_at(tz, wall - o) == o)
