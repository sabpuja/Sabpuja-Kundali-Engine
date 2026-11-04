"""Curated birthplace fixture for the internal prototype (not the DATA-01 gazetteer).

The browser sends only a place id. Coordinates and the IANA zone always come
from this fixture, so a client can never pair an arbitrary place with a zone.
"""
from __future__ import annotations

from importlib import resources
import json
import math
import re

from sabpuja_kundali import zone_policy
from sabpuja_kundali.engine import SUPPORTED_LATITUDE_DEG
from sabpuja_kundali.timezones import get_zone

_ID = re.compile(r"^[a-z]{2}-[a-z0-9-]{1,40}$")
_PUBLIC_KEYS = ("id", "name", "region", "country", "latitude", "longitude", "timezone", "note")


class PlaceFixtureError(RuntimeError):
    """The fixture is missing, malformed, or names a zone the engine would not verify."""


def load_places() -> dict[str, dict]:
    """Read and check the fixture; any problem stops the server from starting."""
    try:
        text = resources.files(__package__).joinpath("places.json").read_text(encoding="utf-8")
        fixture = json.loads(text)
        rows = fixture["places"]
    except (OSError, ValueError, KeyError, TypeError):
        raise PlaceFixtureError("place fixture missing or not valid JSON") from None
    if not isinstance(rows, list) or not rows:
        raise PlaceFixtureError("place fixture lists no places")
    places: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not _ID.match(row["id"]):
            raise PlaceFixtureError("place fixture row has an invalid id")
        pid = row["id"]
        if pid in places:
            raise PlaceFixtureError(f"duplicate place id {pid}")
        for key in ("name", "region", "country", "timezone"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise PlaceFixtureError(f"{pid}: {key} missing")
        for key, limit in (("latitude", 90.0), ("longitude", 180.0)):
            value = row.get(key)
            if type(value) is not float or not math.isfinite(value) or not -limit <= value <= limit:
                raise PlaceFixtureError(f"{pid}: {key} invalid")
        prov = row.get("provenance")
        if not isinstance(prov, dict) or not isinstance(prov.get("geonames_id"), int) \
                or not isinstance(prov.get("cross_check"), dict):
            raise PlaceFixtureError(f"{pid}: provenance missing")
        # Same pinned loader and D3 policy the engine uses; TZDATA_* errors propagate.
        try:
            get_zone(row["timezone"])
        except ValueError:
            raise PlaceFixtureError(f"{pid}: timezone not in the pinned tzdata") from None
        if not zone_policy.is_location_based(row["timezone"]):
            raise PlaceFixtureError(f"{pid}: timezone is not a geographic IANA identifier")
        places[pid] = row
    return places


def public_place(row: dict) -> dict:
    """Fields the browser may show; provenance is summarised, never needed to calculate."""
    out = {key: row[key] for key in _PUBLIC_KEYS if key in row}
    out["in_supported_latitude_band"] = abs(row["latitude"]) <= SUPPORTED_LATITUDE_DEG
    out["source"] = (f"GeoNames {row['provenance']['geonames_id']}; Natural Earth cross-check "
                     f"{row['provenance']['cross_check']['distance_km']} km")
    return out
