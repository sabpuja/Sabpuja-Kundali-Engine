"""KUN-03 D3: which pinned IANA identifiers may name a birthplace timezone.

A birthplace timezone must be location-based. The identifiers below name
universal time, a fixed UTC offset, an unknown zone or a set of US rules, never
a place, so a request using one is refused with TIMEZONE_NOT_LOCATION_BASED.
The table is judged by name only: an identifier is never refused because its
offsets equal UTC's (Africa/Abidjan, Atlantic/Reykjavik and Europe/London stay
accepted) or because it shares TZif data with another zone. Classification
follows the IANA tz 2026e source files `etcetera`, `backward` and `factory`
(see docs/api-contract.md, D3 identifier audit). Names are compared exactly,
with no case folding, so a spelling outside the pinned manifest stays
TIMEZONE_INVALID.

Change only with an owner decision: ZONE_POLICY names the version. Version 1
refused 45 names; version 2 adds CST6CDT, EST5EDT, MST7MDT and PST8PDT (owner
Option B, PR #20 comment 6377855934) for 49.
"""
from __future__ import annotations

ZONE_POLICY = "KUN-03 D3 location-based birthplace timezone, version 2"

# Every Etc/* identifier: tz `etcetera` ("ships at sea and other miscellany")
# and its `backward` links. 35 keys in the pinned tzdata 2026.5 manifest.
NON_LOCATION_PREFIXES = ("Etc/",)

# Root-level names outside Etc/ that tz defines as UTC/GMT itself or as links
# to Etc/UTC or Etc/GMT, plus Factory (tz `factory`: "the actual time zone is
# unknown", abbreviation -00) and, since version 2, the four US-rules zones.
NON_LOCATION_IDENTIFIERS = (
    "UTC",        # backward: Link Etc/UTC UTC
    "UCT",        # backward: Link Etc/UTC UCT
    "Universal",  # backward: Link Etc/UTC Universal
    "Zulu",       # backward: Link Etc/UTC Zulu
    "GMT",        # etcetera: Link Etc/GMT GMT
    "GMT+0",      # backward: Link Etc/GMT GMT+0
    "GMT-0",      # backward: Link Etc/GMT GMT-0
    "GMT0",       # backward: Link Etc/GMT GMT0
    "Greenwich",  # backward: Link Etc/GMT Greenwich
    "Factory",    # factory: Zone Factory 0 - -00
    "CST6CDT",    # backward: Zone CST6CDT -6:00 USback C%sT (version 2)
    "EST5EDT",    # backward: Zone EST5EDT -5:00 USback E%sT (version 2)
    "MST7MDT",    # backward: Zone MST7MDT -7:00 USback M%sT (version 2)
    "PST8PDT",    # backward: Zone PST8PDT -8:00 USback P%sT (version 2)
)

# Abbreviation-style names reviewed by the owner and kept accepted (version 2):
# tz `backward` links to geographic zones (CET, MET -> Europe/Brussels, EET ->
# Europe/Athens, WET -> Europe/Lisbon, EST -> America/Panama, MST ->
# America/Phoenix, HST -> Pacific/Honolulu).
REVIEWED_ACCEPTED = ("CET", "MET", "EET", "WET", "EST", "MST", "HST")


def is_location_based(name: str) -> bool:
    """False for an identifier that names no place; exact, case-sensitive match."""
    return name not in NON_LOCATION_IDENTIFIERS and not name.startswith(NON_LOCATION_PREFIXES)
