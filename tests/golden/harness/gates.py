"""Fixture-level gates. Any reason here makes the fixture BLOCKED before the engine runs.

Gates collect every reason instead of stopping at the first, so a report
shows the full list of what is missing.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from ..generator.isolation import check_reference_classes
from .schema import sha256_file

DECISION_FIELDS = ("approver", "approved_on", "decisions_md_commit")


def parse_utc(text: str) -> datetime:
    """Strict UTC ISO timestamp ('Z' or +00:00 only)."""
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must be UTC")
    return value.astimezone(timezone.utc)


def decision_reasons(required: list[str], decisions: dict) -> list[str]:
    reasons = []
    for decision_id in required:
        entry = decisions.get(decision_id)
        if entry is None:
            reasons.append(f"DECISION_UNKNOWN: {decision_id}")
        elif entry.get("status") != "APPROVED":
            reasons.append(f"SCI_DECISION_PENDING: {decision_id}")
        elif not all(entry.get(f) for f in DECISION_FIELDS):
            reasons.append(f"DECISION_RECORD_INCOMPLETE: {decision_id}")
    return reasons


def tolerance_reasons(tolerance_ids: dict, tolerances: dict) -> list[str]:
    reasons = []
    for tolerance_id in sorted(set(tolerance_ids.values())):
        row = tolerances.get(tolerance_id)
        if row is None:
            reasons.append(f"TOLERANCE_UNKNOWN: {tolerance_id}")
        elif row.get("status") != "FROZEN":
            reasons.append(f"TOLERANCE_NOT_FROZEN: {tolerance_id}")
        elif type(row.get("frozen_arcsec")) not in (int, float) or row["frozen_arcsec"] < 0 or not row.get("qa_ref"):
            reasons.append(f"TOLERANCE_RECORD_INCOMPLETE: {tolerance_id}")
    return reasons


def source_reasons(references: list[dict], fixture_dir: Path) -> list[str]:
    """Raw reference bytes must exist inside the fixture directory and match their SHA-256."""
    reasons = []
    root = fixture_dir.resolve()
    for ref in references:
        rel = PurePosixPath(ref["raw_output_path"])
        path = (fixture_dir / rel).resolve()
        if rel.is_absolute() or ".." in rel.parts or root not in path.parents:
            reasons.append(f"SOURCE_PATH_INVALID: {ref['source_id']}")
        elif not path.is_file():
            reasons.append(f"SOURCE_BYTES_MISSING: {ref['source_id']}")
        elif sha256_file(path) != ref["raw_output_sha256"]:
            reasons.append(f"SOURCE_HASH_MISMATCH: {ref['source_id']}")
    return reasons


def coverage_reasons(fixture: dict) -> list[str]:
    try:
        instant = parse_utc(fixture["derived_time"]["utc"])
    except ValueError:
        return ["DERIVED_UTC_INVALID"]
    reasons = []
    for ref in fixture["references"]:
        try:
            start, end = (parse_utc(t) for t in ref["coverage_utc"])
        except ValueError:
            reasons.append(f"COVERAGE_INVALID: {ref['source_id']}")
            continue
        if not start <= instant <= end:
            reasons.append(f"OUTSIDE_REFERENCE_COVERAGE: {ref['source_id']}")
    return reasons


def fixture_reasons(fixture: dict, fixture_dir: Path, configs: dict, tzdata_version: str | None) -> list[str]:
    """All blocking reasons for one schema-valid fixture."""
    reasons = []
    if fixture["dummy"]:
        reasons.append("DUMMY_FIXTURE: synthetic demonstration data, never a reference")
    if not fixture["reference_verified"]:
        reasons.append("REFERENCE_UNVERIFIED")
    reasons += check_reference_classes(fixture["references"], configs["references"])
    reasons += source_reasons(fixture["references"], fixture_dir)
    reasons += coverage_reasons(fixture)
    reasons += decision_reasons(fixture["approved_decisions_required"], configs["decisions"])
    reasons += tolerance_reasons(fixture["tolerance_ids"], configs["tolerances"])
    if fixture["derived_time"]["tzdata_version"] != tzdata_version:
        reasons.append("TZDATA_MISMATCH")
    return reasons


def time_track_reasons(time_track: dict) -> list[str]:
    if time_track.get("status") != "VERIFIED" or not time_track.get("qa_ref"):
        return ["TIME_TRACK_NOT_VERIFIED"]
    try:
        parse_utc(time_track.get("observed_delta_t_through_utc") or "")
    except ValueError:
        return ["TIME_TRACK_INCOMPLETE: observed_delta_t_through_utc"]
    return []


def time_qualification(utc: str, observed_through: str) -> str | None:
    """QUALIFIED reason when the epoch is after the last observed Delta T, else None."""
    if parse_utc(utc) > parse_utc(observed_through):
        return "FUTURE_DELTA_T: epoch after last observed Delta T (T-TIME-4 band)"
    return None
