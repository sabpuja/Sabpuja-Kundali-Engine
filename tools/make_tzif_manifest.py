"""Generate the pinned TZif SHA-256 manifest (src/sabpuja_kundali/tzif-manifest.json).

Usage: python -I tools/make_tzif_manifest.py <tzdata-2026.5-py2.py3-none-any.whl> <out.json>
Reads zone bytes straight from the published wheel (a zip), never from an
installed copy, and parses rather than executes its version constants. Covers
every TZif file the package ships, including backward-compatible links such as
Asia/Calcutta. Which keys are accepted for a birthplace is an SCI-03 decision;
the loader refuses anything not listed here.
"""
import hashlib
import json
import re
import sys
import zipfile

wheel, out = sys.argv[1], sys.argv[2]
wheel_sha = hashlib.sha256(open(wheel, "rb").read()).hexdigest()
zones = {}
with zipfile.ZipFile(wheel) as zf:
    init = zf.read("tzdata/__init__.py").decode()
    # Parse, never execute, the two version constants.
    ns = dict(re.findall(r'^(IANA_VERSION|__version__)\s*=\s*"([^"]+)"', init, re.M))
    prefix = "tzdata/zoneinfo/"
    for name in sorted(zf.namelist()):
        if not name.startswith(prefix) or name.endswith((".py", "/")):
            continue
        key = name[len(prefix):]
        data = zf.read(name)
        if not data.startswith(b"TZif"):
            continue  # tzdata.zi, zone.tab and friends
        zones[key] = {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
manifest = {
    "source": "https://pypi.org/project/tzdata/",
    "package_version": ns["__version__"],
    "iana_version": ns["IANA_VERSION"],
    "wheel": wheel.rsplit("/", 1)[-1],
    "wheel_sha256": wheel_sha,
    "zones": zones,
}
body = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
manifest["manifest_sha256"] = hashlib.sha256(body).hexdigest()
with open(out, "w", encoding="utf-8") as handle:
    json.dump(manifest, handle, indent=1, sort_keys=True)
    handle.write("\n")
print(f"{len(zones)} zones, IANA {manifest['iana_version']}, manifest {manifest['manifest_sha256']}")
