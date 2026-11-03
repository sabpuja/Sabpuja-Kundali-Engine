"""Shared helpers for the KUN-PAN-M1 tests: pinned inputs, environment and requests.

Real-data tests follow the existing suite convention: they skip when
SABPUJA_TEST_EPHE_PATH is unset, and once it is set wrong or incomplete data is
a failure, never a skip. Release evidence must show 0 skipped tests.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import os
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
TOLERANCES_PATH = HERE / "tolerances.json"
FIXTURE_PATH = REPO / "research/panchanga/reference-fixtures/geocentric-lunar-phase-events-2026.json"
GOLD_MATRIX_PATH = REPO / "tests/sci_gold/matrix.json"

# Frozen before any numerical run (commits b3883ba and d8d487a). Never edited here.
TOLERANCES_SHA256 = "6f188600ba2fbf2e81f2a16e78c6e6eee692101468b71404fe674961d444f39d"
FIXTURE_SHA256 = "dfd964cf450cee57d76aff780fc2541814ca3ab79ac7e55028f4a88aa6459850"

EPHE_ENV = "SABPUJA_TEST_EPHE_PATH"
EPHE = os.environ.get(EPHE_ENV)
SWETEST = os.environ.get("SABPUJA_TEST_SWETEST")
RECEIPT = os.environ.get("SABPUJA_TEST_SWETEST_RECEIPT")


class PinnedInputError(AssertionError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_pinned(path: Path, expected_sha: str) -> dict:
    data = path.read_bytes()
    if sha256_bytes(data) != expected_sha:
        raise PinnedInputError(f"{path.name} does not match its frozen SHA-256")
    return json.loads(data)


def tolerances() -> dict:
    return load_pinned(TOLERANCES_PATH, TOLERANCES_SHA256)


def fixture() -> dict:
    return load_pinned(FIXTURE_PATH, FIXTURE_SHA256)


def real_data(cls):
    """Class decorator: skip without SABPUJA_TEST_EPHE_PATH; fail if it is set but unverified."""
    cls = unittest.skipIf(EPHE is None, f"{EPHE_ENV} unset: real-data Panchanga tests not requested")(cls)
    original = cls.__dict__.get("setUpClass")

    @classmethod
    def setUpClass(klass):
        from sabpuja_kundali.ephemeris import EphemerisDataError, verify_ephemeris_dir
        try:
            with mock.patch.dict(os.environ):
                os.environ.pop("SE_EPHE_PATH", None)
                verify_ephemeris_dir(EPHE)
        except EphemerisDataError as exc:
            raise AssertionError(f"{EPHE_ENV} is set but does not hold the pinned required files: {exc.code}") from None
        if original is not None:
            original.__func__(klass)
    cls.setUpClass = setUpClass
    return cls


def request_at_utc(utc: datetime, zone: str = "Asia/Kolkata", offset: timedelta = timedelta(hours=5, minutes=30),
                   latitude: float = 28.6139, longitude: float = 77.209) -> dict:
    """A synthetic chart request whose instant is `utc`, written as local time with a fixed offset."""
    local = (utc + offset).replace(tzinfo=None)
    sign = "+" if offset >= timedelta(0) else "-"
    total = abs(int(offset.total_seconds()))
    stamp = local.isoformat(timespec="microseconds" if local.microsecond else "seconds")
    return {"birth_datetime": f"{stamp}{sign}{total // 3600:02d}:{total % 3600 // 60:02d}",
            "timezone": zone, "latitude": latitude, "longitude": longitude}


def parse_utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def gold_chart_requests() -> list[tuple[str, dict, str]]:
    """(fixture id, request, expected UTC) for every chart fixture of the KUN-SCI-GOLD-001 matrix."""
    matrix = json.loads(GOLD_MATRIX_PATH.read_text(encoding="utf-8"))
    out = []
    for f in matrix["fixtures"]:
        if f["expect"]["kind"] == "chart":
            out.append((f["id"], dict(f["input"]), f["time_reference"]["expected_utc"]))
    return out
