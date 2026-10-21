"""Outcome classes, precedence and exit codes (docs/accuracy/qa-architecture.md section 3)."""
from __future__ import annotations

from enum import Enum


class Outcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    METHOD_MISMATCH = "METHOD-MISMATCH"
    BOUNDARY_INDETERMINATE = "BOUNDARY-INDETERMINATE"
    BLOCKED = "BLOCKED"
    QUALIFIED = "QUALIFIED"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    QUALIFIED = "QUALIFIED"


EXIT_CODES = {Verdict.PASS: 0, Verdict.FAIL: 1, Verdict.BLOCKED: 2, Verdict.QUALIFIED: 2}

_NOT_JUDGEABLE = {Outcome.BLOCKED, Outcome.METHOD_MISMATCH, Outcome.BOUNDARY_INDETERMINATE}


def overall_verdict(outcomes: list[Outcome]) -> Verdict:
    """FAIL beats everything; then anything not judgeable blocks; then QUALIFIED.

    An empty set is BLOCKED: no evidence is never a pass. Self-consistency
    results are reported separately and must not be passed in here.
    """
    if not outcomes:
        return Verdict.BLOCKED
    seen = set(outcomes)
    if Outcome.FAIL in seen:
        return Verdict.FAIL
    if seen & _NOT_JUDGEABLE:
        return Verdict.BLOCKED
    if Outcome.QUALIFIED in seen:
        return Verdict.QUALIFIED
    return Verdict.PASS


def exit_code(verdict: Verdict) -> int:
    """0 only for an unqualified PASS; 1 FAIL; 2 BLOCKED or QUALIFIED."""
    return EXIT_CODES[verdict]


_FIXTURE_ORDER = (Outcome.FAIL, Outcome.BLOCKED, Outcome.METHOD_MISMATCH,
                  Outcome.BOUNDARY_INDETERMINATE, Outcome.QUALIFIED)


def fixture_outcome(outcomes: list[Outcome]) -> Outcome:
    """One outcome per fixture: the most severe of its checks; no checks is BLOCKED."""
    if not outcomes:
        return Outcome.BLOCKED
    for outcome in _FIXTURE_ORDER:
        if outcome in outcomes:
            return outcome
    return Outcome.PASS
