"""Free Kundali preview (KUN-FREEMIUM-PREVIEW-001, issue #91). QA ONLY, NOT DEPLOYED.

A visitor sends a birthplace id, a birth date and an exact birth time. The same validation and the same
engine call as the paid route (`kundali_prototype.server.compute`) produce a chart in memory; this module
returns a SMALL FIXED WHITELIST of fields from it and discards everything else. Nothing is stored, logged,
cached or rendered to PDF. The optional name never reaches the server (the page keeps it in the browser).

Field registry (what may be shown, and why):

* ``lagna_rashi`` ENABLED. Sidereal Lagna Rashi, SCI-01e (owner approved / canonical 2026-10-24, ledger row 4)
  within chart schema baseline SCI-02 (ledger row 9).
* ``moon_rashi`` ENABLED. Moon Rashi, SCI-02 baseline field (ledger row 9).
* ``vara`` WITHHELD. The sunrise Vara convention (PAN-D03/PAN-D05) is recorded for the development stage only,
  "not for customer release" (src/sabpuja_kundali/panchanga/vara.py). It cannot be enabled by configuration.

Birth-time sensitivity (SCI-06 Option 1, owner selected pre-merge, canonical adoption pending): for the two
shown fields only, the same instant is recomputed 120 s earlier and later. If either field would differ, or a
neighbour cannot be computed, ``birth_time_sensitive`` is true and the page shows a short note. This is a
disclosure, not a correction; the shown values are always those of the entered time.

No prediction, interpretation, degree, house, Navamsa, Nakshatra or other chart value is returned.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import threading
import time

PREVIEW_VERSION = "kundali-preview/1"
MAX_PREVIEW_BODY_BYTES = 512
FORM_KEYS = frozenset({"place_id", "birth_date", "birth_time"})
OPTIONAL_KEYS = frozenset({"utc_offset"})
SENSITIVITY_SECONDS = 120

FIELD_REGISTRY = {
    "lagna_rashi": {"status": "enabled", "basis": "SCI-01e and SCI-02 (ledger rows 4 and 9), canonical 2026-10-24"},
    "moon_rashi": {"status": "enabled", "basis": "SCI-02 (ledger row 9), canonical 2026-10-24"},
    "vara": {"status": "withheld",
             "basis": "PAN-D03/PAN-D05 sunrise Vara: development stage only, not for customer release"},
}
ENABLED_FIELDS = tuple(k for k, v in FIELD_REGISTRY.items() if v["status"] == "enabled")

# Mesha..Meena as the engine names them, with the conventional English equivalents the paid report's
# term register uses (report/phase1 terms, "western"); a test keeps both in step.
from sabpuja_kundali.rules import SIGNS as RASHIS  # noqa: E402 - the engine's own spelling (e.g. "Vrischika")
WESTERN = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
           "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")

# Births after "today" are refused. India Standard Time decides the date, because every supported place uses it.
IST = timezone(timedelta(hours=5, minutes=30))


class PreviewRefused(Exception):
    """A fixed refusal; no input value is ever part of it."""

    def __init__(self, status: int, code: str, message: str, category: str = "input", extra: dict | None = None):
        super().__init__(code)
        self.status, self.code, self.message, self.category, self.extra = status, code, message, category, extra or {}


class PreviewUnavailable(Exception):
    """Server-side fault (pinned data, Swiss runtime, defect). Nothing is shown."""

    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status, self.code = status, code


class WindowLimiter:
    """Fixed-window counter per key, in memory only (no address is ever written anywhere)."""

    def __init__(self, limit: int, window_seconds: int, clock=time.time, max_keys: int = 50_000):
        self._limit, self._window, self._clock = limit, window_seconds, clock
        self._lock, self._hits, self._max = threading.Lock(), {}, max_keys

    def allow(self, key: str) -> bool:
        window = int(self._clock() // self._window)
        with self._lock:
            if len(self._hits) > self._max:
                self._hits = {k: v for k, v in self._hits.items() if v[0] == window}
            win, count = self._hits.get(key, (window, 0))
            if win != window:
                win, count = window, 0
            self._hits[key] = (win, count + 1)
            return count + 1 <= self._limit


def _no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key")
    return dict(pairs)


def parse(body: bytes) -> dict:
    """Shape checks before any computation: one small JSON object of strings with the allowed keys only."""
    if len(body) > MAX_PREVIEW_BODY_BYTES:
        raise PreviewRefused(413, "BODY_TOO_LARGE", "request too large", "request")
    try:
        data = json.loads(body.decode("utf-8"), object_pairs_hook=_no_duplicates)
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise PreviewRefused(400, "REQUEST_INVALID", "the request must be one UTF-8 JSON object", "request") from None
    if not isinstance(data, dict):
        raise PreviewRefused(400, "REQUEST_INVALID", "the request must be one JSON object", "request")
    keys = set(data)
    if keys - FORM_KEYS - OPTIONAL_KEYS:
        # Names, e-mails, locales, editions, "full": the preview takes birth fields only.
        raise PreviewRefused(400, "REQUEST_INVALID", "only birthplace, birth date and birth time are accepted",
                             "request")
    if not FORM_KEYS <= keys:
        raise PreviewRefused(400, "REQUEST_INVALID", "birthplace, birth date and birth time are required", "request")
    if not all(isinstance(v, str) and len(v) <= 64 for v in data.values()):
        raise PreviewRefused(400, "REQUEST_INVALID", "every field must be a short string", "request")
    return data


def _rashi(name: str) -> dict:
    index = RASHIS.index(name)  # ValueError -> defect: the engine returned an unknown sign
    return {"rashi": name, "number": index + 1, "western": WESTERN[index]}


def _shift(req: dict, seconds: int) -> dict:
    instant = datetime.fromisoformat(req["birth_datetime"]) + timedelta(seconds=seconds)
    return dict(req, birth_datetime=instant.isoformat())


class PreviewService:
    """Computes one preview. `places` are the India reference places the paid route serves."""

    def __init__(self, places: dict, ephe_path: str, fields: tuple[str, ...] = ENABLED_FIELDS, today=None):
        unknown = [f for f in fields if FIELD_REGISTRY.get(f, {}).get("status") != "enabled"]
        if unknown or not fields:
            raise ValueError("preview fields must be a non-empty subset of the enabled registry fields")
        self.places, self.ephe, self.fields = places, ephe_path, tuple(fields)
        self._today = today or (lambda: datetime.now(IST).date())

    def __call__(self, form: dict) -> dict:
        from kundali_prototype import server
        from sabpuja_kundali.engine import calculate

        # The date must exist and not lie in the future; everything else is the paid route's own validation.
        try:
            birth_day = date.fromisoformat(form["birth_date"]) if len(form["birth_date"]) == 10 else None
        except ValueError:
            birth_day = None
        if birth_day is not None and birth_day > self._today():
            raise PreviewRefused(422, "BIRTH_DATE_FUTURE", "the birth date cannot be in the future")
        try:
            result = server.compute(form, self.places, self.ephe)
        except Exception as exc:  # map exactly as the paid route and the prototype do
            status, code, message, category = server.classify(exc)
            if status >= 500:
                raise PreviewUnavailable(status, code) from None
            extra = getattr(exc, "extra", None) if isinstance(exc, server.FormError) else None
            raise PreviewRefused(status, code, message, category, extra) from None
        chart = result["chart"]
        values = {"lagna_rashi": chart["lagna"]["rashi"], "moon_rashi": chart["planets"]["moon"]["rashi"]}
        sensitive = False
        req = {"birth_datetime": f"{result['input']['local_date']}T{result['input']['local_time']}"
                                 f"{result['input']['utc_offset']}",
               "timezone": self.places[form["place_id"]]["timezone"],
               "latitude": self.places[form["place_id"]]["latitude"],
               "longitude": self.places[form["place_id"]]["longitude"]}
        for seconds in (-SENSITIVITY_SECONDS, SENSITIVITY_SECONDS):
            try:
                other = calculate(_shift(req, seconds), ephe_path=self.ephe)
            except Exception:  # e.g. 1969-12-31 23:58 is refused: we cannot confirm, so we disclose
                sensitive = True
                continue
            near = {"lagna_rashi": other["lagna"]["rashi"], "moon_rashi": other["planets"]["moon"]["rashi"]}
            if any(near[f] != values[f] for f in self.fields):
                sensitive = True
        return {"preview_version": PREVIEW_VERSION,
                "fields": {f: _rashi(values[f]) for f in self.fields},
                "birth_time_sensitive": sensitive,
                "method": "sidereal_lahiri_swiss_ephemeris"}
