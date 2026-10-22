"""Deterministic IANA timezone loading from the pinned PyPI `tzdata` package.

Standard-library `ZoneInfo(key)` reads the host TZPATH (/usr/share/zoneinfo,
overridable by PYTHONTZPATH) before the tzdata package and caches by key
process-wide, so the same birth could convert differently on two hosts (KUN-02:
Ubuntu's 2026e build vs PyPI's 2026e build disagree for historical offsets).

Here zone bytes come only from the installed `tzdata` distribution and must match
the pinned TZif SHA-256 manifest; the host TZPATH, PYTHONTZPATH, TZ and
time.tzset() are never consulted or changed. Error messages carry a code and
never the requested key or any birth detail.
"""
from __future__ import annotations

from importlib import resources
from io import BytesIO
from threading import Lock
from zoneinfo import ZoneInfo
import hashlib
import importlib
import json
import re

_MANIFEST_NAME = "tzif-manifest.json"
# IANA keys are ASCII path components; refuse anything that could leave the package.
_KEY = re.compile(r"^[A-Za-z0-9_+\-]+(/[A-Za-z0-9_+\-]+)*$")


class TimezoneDataError(RuntimeError):
    """Pinned timezone data is absent, of the wrong version, or does not match the manifest.

    Distinct from an unsupported timezone identifier, which is invalid input (ValueError).
    """

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code


def load_manifest() -> dict:
    text = resources.files(__package__).joinpath(_MANIFEST_NAME).read_text(encoding="utf-8")
    return json.loads(text)


def manifest_digest(manifest: dict) -> str:
    """SHA-256 of the manifest content, excluding its own `manifest_sha256` field."""
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class PinnedZoneLoader:
    def __init__(self, manifest: dict, package: str = "tzdata"):
        if manifest_digest(manifest) != manifest.get("manifest_sha256"):
            raise TimezoneDataError("TZDATA_MANIFEST_INVALID", "timezone manifest digest does not match its content")
        self._manifest = manifest
        self._files = manifest["zones"]
        self._package = package
        # Entries are verified before insertion and never replaced.
        self._cache: dict[str, ZoneInfo] = {}
        self._lock = Lock()
        self._version_checked = False

    def _check_version(self) -> None:
        if self._version_checked:
            return
        try:
            module = importlib.import_module(self._package)
        except ImportError:
            raise TimezoneDataError("TZDATA_PACKAGE_MISSING", "pinned tzdata package is not installed") from None
        if (getattr(module, "IANA_VERSION", None) != self._manifest["iana_version"]
                or getattr(module, "__version__", None) != self._manifest["package_version"]):
            raise TimezoneDataError("TZDATA_VERSION_MISMATCH", "installed tzdata does not match the pinned manifest")
        self._version_checked = True

    def provenance(self) -> dict[str, str]:
        """Timezone-data provenance for calculation metadata (P7)."""
        return {
            "source": "PyPI tzdata",
            "package_version": self._manifest["package_version"],
            "iana_version": self._manifest["iana_version"],
            "manifest_sha256": self._manifest["manifest_sha256"],
        }

    def keys(self) -> frozenset[str]:
        return frozenset(self._files)

    def get(self, key: object) -> ZoneInfo:
        """Return the verified zone, or raise ValueError for an unsupported key."""
        if not isinstance(key, str) or not _KEY.match(key) or key not in self._files:
            raise ValueError("timezone must be a valid IANA timezone identifier")
        with self._lock:
            zone = self._cache.get(key)
            if zone is not None:
                return zone
            self._check_version()
            entry = self._files[key]
            node = resources.files(f"{self._package}.zoneinfo")
            for part in key.split("/"):
                node = node.joinpath(part)
            try:
                data = node.read_bytes()
            except OSError:
                raise TimezoneDataError("TZDATA_FILE_MISSING", "a pinned zone file is missing") from None
            if len(data) != entry["size_bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise TimezoneDataError("TZDATA_FILE_MISMATCH", "a zone file does not match the pinned SHA-256")
            # from_file keeps the instance out of ZoneInfo's global key cache.
            zone = ZoneInfo.from_file(BytesIO(data), key=key)
            self._cache[key] = zone
            return zone

    def verify_all(self) -> int:
        """Load and verify every manifest zone; for a service start-up gate."""
        for key in self._files:
            self.get(key)
        return len(self._files)


_LOADER: PinnedZoneLoader | None = None
_LOADER_LOCK = Lock()


def default_loader() -> PinnedZoneLoader:
    global _LOADER
    with _LOADER_LOCK:
        if _LOADER is None:
            _LOADER = PinnedZoneLoader(load_manifest())
        return _LOADER


def get_zone(key: object) -> ZoneInfo:
    return default_loader().get(key)
