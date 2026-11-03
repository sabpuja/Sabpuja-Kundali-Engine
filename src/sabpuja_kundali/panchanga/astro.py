"""Sun and Moon longitudes for Panchanga M1 through the canonical chart call path (D01-A).

Exactly the chart's SCI-01d call: `swe.calc_ut(jd_ut, body, FLG_SWIEPH | FLG_SIDEREAL)`
with Lahiri (`set_sid_mode(SIDM_LAHIRI, 0, 0)`), the verified ephemeris
directory and the automatic Delta T, all set under the chart's own Swiss lock at
the start of every session (SCI-01a, SCI-01h; PAN-SPEC-15). The Julian day is
formed with the chart's own `swe.julday` expression, so a Panchanga evaluation
at an instant equals the chart's evaluation for a birth at that instant.

`FLG_SWIEPH` is checked on every call, including every bracketing and bisection
step; a missing flag is the chart's SWISS_EPHEMERIS_FALLBACK_REFUSED refusal.
No Moshier or JPL fallback, no crossing functions (`swe_mooncross_ut` etc.), no
`FLG_SPEED`, no topocentric flag. Swiss exception text never reaches the caller.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

from .. import engine
from ..engine import ChartComputationError
from .search import MICROS, NonFiniteValue

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def utc_micros(moment: datetime) -> int:
    """Exact integer microseconds since the Unix epoch of an aware UTC datetime."""
    delta = moment - _EPOCH
    return (delta.days * 86400 + delta.seconds) * MICROS + delta.microseconds


def utc_from_micros(t_us: int) -> datetime:
    return _EPOCH + timedelta(microseconds=t_us)


def julian_day(swe, utc: datetime) -> float:
    """The chart's own expression (engine.calculate), unchanged."""
    try:
        return swe.julday(
            utc.year, utc.month, utc.day,
            utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1_000_000) / 3600
        )
    except swe.Error:
        raise ChartComputationError(
            "SWISS_TIME_CALCULATION_FAILED",
            "Swiss Ephemeris could not convert the birth time; no chart produced"
        ) from None


class SwissSession:
    """Holds the chart's Swiss lock for one Panchanga request and evaluates (Sun, Moon).

    Use as a context manager. Values are cached per microsecond instant, so shared
    bracket instants are computed once; the cache lives only for the session.
    """

    def __init__(self, swe, folder: str):
        self._swe = swe
        self._folder = str(folder)
        self._cache: dict[int, tuple[float, float]] = {}
        self.calls = 0

    def __enter__(self) -> "SwissSession":
        engine._SWISS_LOCK.acquire()
        swe = self._swe
        try:
            swe.set_ephe_path(self._folder)
            swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
            swe.set_delta_t_userdef(swe.DELTAT_AUTOMATIC)
        except swe.Error:
            engine._SWISS_LOCK.release()
            raise ChartComputationError(
                "SWISS_STATE_INITIALIZATION_FAILED",
                "Swiss Ephemeris could not be initialized for this request; no chart produced"
            ) from None
        except BaseException:
            engine._SWISS_LOCK.release()
            raise
        return self

    def __exit__(self, *exc) -> None:
        self._cache.clear()
        engine._SWISS_LOCK.release()

    def _longitude(self, jd: float, body: int) -> float:
        swe = self._swe
        self.calls += 1
        try:
            pos, flags = swe.calc_ut(jd, body, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        except swe.Error:
            raise ChartComputationError(
                "SWISS_PLANET_CALCULATION_FAILED",
                "Swiss Ephemeris could not complete the planetary calculation; no chart produced"
            ) from None
        if not (flags & swe.FLG_SWIEPH):
            raise ChartComputationError(
                "SWISS_EPHEMERIS_FALLBACK_REFUSED",
                "Swiss Ephemeris did not use the verified local files; refused Moshier fallback; "
                "no chart produced")
        value = float(pos[0])
        if not math.isfinite(value):
            raise NonFiniteValue()
        return value

    def sun_moon(self, t_us: int) -> tuple[float, float]:
        cached = self._cache.get(t_us)
        if cached is None:
            jd = julian_day(self._swe, utc_from_micros(t_us))
            if not math.isfinite(jd):
                raise NonFiniteValue()
            cached = (self._longitude(jd, self._swe.SUN), self._longitude(jd, self._swe.MOON))
            self._cache[t_us] = cached
        return cached
