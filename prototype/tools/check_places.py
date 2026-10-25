"""Re-check prototype/kundali_prototype/places.json against its two pinned sources.

Not used at run time. Usage (sources downloaded by hand, then hash-checked here):
  python -I prototype/tools/check_places.py GEONAMESCACHE_WHEEL NE_POPULATED_PLACES_GEOJSON
Exit 0 only if both artifacts match their pinned SHA-256 and every place's
coordinates, IANA zone and Natural Earth cross-check match the fixture.
"""
import hashlib
import json
import math
import sys
import zipfile
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "kundali_prototype" / "places.json"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def distance_km(lat1, lon1, lat2, lon2):
    r = math.radians
    cos = (math.sin(r(lat1)) * math.sin(r(lat2))
           + math.cos(r(lat1)) * math.cos(r(lat2)) * math.cos(r(lon2 - lon1)))
    return 6371.0088 * math.acos(min(1.0, cos))


def main(wheel, geojson):
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    sources = fixture["sources"]
    problems = []
    if sha256(wheel) != sources["geonames"]["artifact_sha256"]:
        problems.append("geonames artifact SHA-256 mismatch")
    if sha256(geojson) != sources["natural_earth"]["artifact_sha256"]:
        problems.append("natural earth artifact SHA-256 mismatch")
    with zipfile.ZipFile(wheel) as zf:
        cities = json.loads(zf.read("geonamescache/data/cities15000.json"))
    features = json.loads(Path(geojson).read_text(encoding="utf-8"))["features"]
    for place in fixture["places"]:
        prov = place["provenance"]
        city = cities.get(str(prov["geonames_id"]))
        if city is None:
            problems.append(f"{place['id']}: geonames id not found")
            continue
        if (city["latitude"], city["longitude"], city["timezone"], city["name"]) != (
                place["latitude"], place["longitude"], place["timezone"], prov["geonames_name"]):
            problems.append(f"{place['id']}: differs from geonames")
        best = min(features, key=lambda f: distance_km(place["latitude"], place["longitude"],
                                                       f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0]))
        lon, lat = best["geometry"]["coordinates"][:2]
        d = distance_km(place["latitude"], place["longitude"], lat, lon)
        check = prov["cross_check"]
        if best["properties"]["name"] != check["name"] or round(d, 2) != check["distance_km"] or d >= 10:
            problems.append(f"{place['id']}: natural earth cross-check differs")
        print(f"{place['id']:14} {place['latitude']:>9} {place['longitude']:>10} {place['timezone']:14} "
              f"NE {check['name']} {d:.2f} km")
    print("PROBLEMS:", problems or "none")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:3]))
