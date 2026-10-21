"""Shared builders for harness tests.

"Approved world" helpers create a TEMPORARY golden directory where every gate
is satisfied with test-only records, so the PASS/FAIL plumbing can be tested
with a mock engine. Nothing they write is committed, and none of it is an
approval, a frozen tolerance or a reference.
"""
from __future__ import annotations

from pathlib import Path
import copy
import hashlib
import json
import shutil

from ..harness import oracle
from ..harness.run import GOLDEN_DIR, REPO_ROOT

DUMMY_DIR = GOLDEN_DIR / "tests" / "fixtures_dummy"
TEST_ONLY = "TEST-ONLY record inside a temporary directory; not an approval"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> str:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean_env(**overrides) -> dict:
    env = {
        "python": "3.13.0", "implementation": "CPython", "platform": "Linux-x86_64",
        "swiss": {"pyswisseph": "2.10.3.2", "swiss_library": "2.10.03"},
        "tzdata": {"source": "system", "version": "2026e"},
        "git": {"commit": "0" * 40, "dirty": False},
        "ephemeris": {"manifest_version": "1.0.0", "source_commit": "c" * 40, "verified": True,
                      "error_code": None, "files": {"sepl_18.se1": "a" * 64}},
    }
    for key, value in overrides.items():
        env[key] = value
    return env


def dummy_fixture(name: str = "DUMMY-01.json") -> dict:
    return load_json(DUMMY_DIR / name)


def world_fixture(fixture_id: str = "GC-99", **expected) -> dict:
    """A non-dummy synthetic fixture with invented values, for temporary worlds only."""
    fixture = copy.deepcopy(dummy_fixture())
    fixture.update(fixture_id=fixture_id, dummy=False, reference_verified=True, accuracy_claim=True,
                   purpose="TEST-ONLY invented values in a temporary directory")
    fixture["references"] = [{"source_id": "TEST-REF", "source_class": "I-code",
                              "raw_output_path": "raw/test-ref.txt", "raw_output_sha256": "",
                              "coverage_utc": ["1900-01-01T00:00:00Z", "2100-12-31T23:59:59Z"]}]
    fixture["expected"]["sidereal_longitude_deg"] = expected or {
        "sun": 100.5, "moon": 200.5, "rahu_mean": 50.5, "lagna": 5.5}
    return fixture


def build_world(tmp: Path, fixtures: list[dict], *, time_observed_through: str = "2030-01-01T00:00:00Z",
                frozen_arcsec: float = 0.5) -> tuple[Path, Path]:
    """Temporary golden dir and fixture dir where every gate passes. Returns (golden_dir, fixtures_dir)."""
    golden = tmp / "golden"
    shutil.copytree(GOLDEN_DIR / "generator", golden / "generator",
                    ignore=shutil.ignore_patterns("__pycache__"))
    manifest = load_json(GOLDEN_DIR / "method-manifest.json")
    manifest.update(status="REVIEWED", qa_review=TEST_ONLY)
    write_json(golden / "method-manifest.json", manifest)
    cfg = golden / "config"
    decisions = load_json(GOLDEN_DIR / "config" / "decision-status.json")
    for entry in decisions["decisions"].values():
        entry.update(status="APPROVED", approver=TEST_ONLY, approved_on="2000-01-01", decisions_md_commit="0" * 40)
    write_json(cfg / "decision-status.json", decisions)
    tolerances = load_json(GOLDEN_DIR / "config" / "tolerances.json")
    for row in tolerances["tolerances"].values():
        row.update(status="FROZEN", frozen_arcsec=frozen_arcsec, qa_ref=TEST_ONLY)
    write_json(cfg / "tolerances.json", tolerances)
    registry = load_json(GOLDEN_DIR / "config" / "reference-registry.json")
    registry["references"]["TEST-REF"] = {"class": "I-code", "name": TEST_ONLY, "obtained": True}
    write_json(cfg / "reference-registry.json", registry)
    write_json(cfg / "time-track.json", {"status": "VERIFIED", "qa_ref": TEST_ONLY,
                                         "observed_delta_t_through_utc": time_observed_through})
    fixtures_dir = tmp / "fixtures"
    raw = fixtures_dir / "raw" / "test-ref.txt"
    raw.parent.mkdir(parents=True)
    raw.write_text("TEST-ONLY raw bytes\n", encoding="utf-8")
    raw_sha = hashlib.sha256(raw.read_bytes()).hexdigest()
    index = {"fixtures": {}}
    for fixture in fixtures:
        for ref in fixture["references"]:
            if ref["source_id"] == "TEST-REF" and not ref["raw_output_sha256"]:
                ref["raw_output_sha256"] = raw_sha
        name = f"{fixture['fixture_id']}.json"
        index["fixtures"][name] = {"revision": fixture["fixture_revision"],
                                   "sha256": write_json(fixtures_dir / name, fixture)}
    write_json(fixtures_dir / "INDEX.json", index)
    return golden, fixtures_dir


def mock_output(expected: dict, utc: str, offsets_arcsec: dict | None = None, method: dict | None = None) -> dict:
    """Engine-shaped output built from reference values plus offsets. Categories via the oracle."""
    offsets = offsets_arcsec or {}
    lon = {b: (v + offsets.get(b, 0.0) / 3600) % 360 for b, v in expected.items() if v is not None}
    if "rahu_mean" in lon and "ketu_mean" not in lon:
        lon["ketu_mean"] = (lon["rahu_mean"] + 180) % 360
    lagna = lon.get("lagna", 0.0)

    def place(value):
        return {"longitude_deg": value, "rashi": oracle.rashi(value), "navamsa_rashi": oracle.navamsa(value)}

    planets = {b: {**place(v), "whole_sign_house": oracle.whole_sign_house(v, lagna)}
               for b, v in lon.items() if b != "lagna"}
    moon = lon.get("moon", 0.0)
    name, pada = oracle.nakshatra(moon)
    return {"method": method or {"ayanamsa": "Lahiri", "nodes": "mean", "houses": "whole_sign",
                                 "ephemeris": "Swiss Ephemeris, local .se1", "binding_version": "2.10.03"},
            "birth": {"utc": utc}, "lagna": place(lagna), "planets": planets,
            "moon_nakshatra": {"index": None, "name": name, "pada": pada}}


def fixed_clock():
    from datetime import datetime, timezone
    return datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


__all__ = ["REPO_ROOT", "GOLDEN_DIR", "DUMMY_DIR"]
