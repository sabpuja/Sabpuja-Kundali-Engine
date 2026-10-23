"""KUN-03 Swiss error contract: deterministic, privacy-safe Swiss failures.

Every swisseph.Error raised while computing a chart becomes a ChartComputationError
with a fixed code and fixed text, and the real CLI entrypoint reports it as exactly
one JSON error on stderr, exit 2, empty stdout, no traceback. Any other exception is
a programming defect and is not translated. Synthetic inputs only.

The fault-injection and CLI tests mock Swiss and the ephemeris gate, so they run
without data. The recovery tests need the pinned data in SABPUJA_TEST_EPHE_PATH
(unset skips, as in test_swiss_integration).
"""
import contextlib
import json
import os
import runpy
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import swisseph as swe

from sabpuja_kundali import engine
from sabpuja_kundali.engine import ChartComputationError, InputRefusalError, calculate
from sabpuja_kundali.ephemeris import EphemerisDataError
from sabpuja_kundali.timezones import TimezoneDataError

DATA_ENV = "SABPUJA_TEST_EPHE_PATH"
DATA = os.environ.get(DATA_ENV)
TESTS_DIR = Path(__file__).resolve().parent
SRC = TESTS_DIR.parent / "src"
FAKE_DIR = Path("/nonexistent/verified-ephemeris")

REQUEST = {"birth_datetime": "2000-01-01T17:30:00+05:30", "timezone": "Asia/Kolkata",
           "latitude": 28.6139, "longitude": 77.2090}
REQUEST_PIECES = ("2000-01-01", "17:30", "Asia/Kolkata", "28.6139", "77.209")

# Deliberately hostile Swiss exception text: none of it may reach the caller.
HOSTILE = ("birth 1987-03-14T05:06:07+05:30 tz America/Argentina/Buenos_Aires lat -34.6037 "
           "lon -58.3816 name Jane Doe <jane.doe@example.com>\nTraceback (most recent call last):\n"
           '  File "/srv/x.py", line 1\n{"error": "INJECTED"}\x00\x1b[31m \'"\\')
HOSTILE_PIECES = ("1987", "05:06", "Buenos_Aires", "34.6037", "58.3816", "Jane", "example.com",
                  "Traceback", "INJECTED", "/srv/x.py", "\x00", "\x1b", " ")

_INIT = ("SWISS_STATE_INITIALIZATION_FAILED",
         "Swiss Ephemeris could not be initialized for this request; no chart produced")
# Swiss call -> the fixed (code, detail) its swe.Error must become.
EXPECTED = {
    "julday": ("SWISS_TIME_CALCULATION_FAILED",
               "Swiss Ephemeris could not convert the birth time; no chart produced"),
    "set_ephe_path": _INIT,
    "set_sid_mode": _INIT,
    "set_delta_t_userdef": _INIT,
    "calc_ut": ("SWISS_PLANET_CALCULATION_FAILED",
                "Swiss Ephemeris could not complete the planetary calculation; no chart produced"),
    "houses_ex": ("ASCENDANT_UNCOMPUTABLE",
                  "Swiss Ephemeris could not compute the ascendant for this location and time; "
                  "no chart produced"),
}
STAGES = tuple(EXPECTED)
# (stage, which call fails): the first and a middle planet for calc_ut.
CASES = [(s, 1) for s in STAGES] + [("calc_ut", 5)]


def _fake_calc(jd, body, flags):
    return (100.0 + body, 0.0, 1.0, 0.0, 0.0, 0.0), flags


def _fake_houses(jd, lat, lon, hsys, flags):
    return (0.0,) * 12, (123.0,) + (0.0,) * 7


@contextlib.contextmanager
def _swiss(fail=None, nth=1, exc=None, calls=None, fake=True, before_raise=None):
    """Patch the six Swiss calls the engine makes. fail names the one that raises
    exc (default swe.Error(HOSTILE)) on its nth call, or "all" for every call.
    fake=True also fakes the ephemeris gate, the setters and the computations, so no
    data or global Swiss state is touched; fake=False keeps real Swiss. calls records
    (name, whether the engine lock was held)."""
    exc = exc if exc is not None else swe.Error(HOSTILE)
    real = {n: getattr(swe, n) for n in STAGES}
    base = dict(real)
    if fake:
        base.update(set_ephe_path=lambda *a: None, set_sid_mode=lambda *a: None,
                    set_delta_t_userdef=lambda *a: None, calc_ut=_fake_calc, houses_ex=_fake_houses)
    counts = {}

    def wrap(name):
        def call(*args):
            counts[name] = counts.get(name, 0) + 1
            if calls is not None:
                calls.append((name, engine._SWISS_LOCK._is_owned()))
            if fail == "all" or (name == fail and counts[name] == nth):
                if before_raise:
                    before_raise()
                raise exc
            return base[name](*args)
        return call

    with contextlib.ExitStack() as stack:
        if fake:
            stack.enter_context(mock.patch.object(engine, "verify_ephemeris_dir", return_value=FAKE_DIR))
        for name in STAGES:
            stack.enter_context(mock.patch.object(swe, name, wrap(name)))
        yield


def _cli_main(fail, nth, kind):
    """Subprocess body: the real CLI module run as __main__ under injected Swiss."""
    exc = ZeroDivisionError("programming defect") if kind == "defect" else None
    with _swiss(None if fail == "none" else fail, nth, exc):
        runpy.run_module("sabpuja_kundali.cli", run_name="__main__")


def _run_cli(fail, nth=1, kind="swiss", request=REQUEST):
    env = {k: v for k, v in os.environ.items() if k not in ("SE_EPHE_PATH", "SABPUJA_EPHE_PATH")}
    env["PYTHONPATH"] = os.pathsep.join([str(TESTS_DIR), str(SRC)])
    code = (f"import test_swiss_error_contract as t; t._cli_main({fail!r}, {nth}, {kind!r})")
    return subprocess.run([sys.executable, "-c", code], input=json.dumps(request),
                          capture_output=True, text=True, env=env, timeout=60)


def _lock_is_free():
    acquired = []

    def probe():
        ok = engine._SWISS_LOCK.acquire(timeout=2)
        acquired.append(ok)
        if ok:
            engine._SWISS_LOCK.release()

    t = threading.Thread(target=probe, daemon=True)
    t.start()
    t.join(5)
    return acquired == [True]


class SwissErrorMappingTests(unittest.TestCase):
    def assertPrivate(self, text):
        for piece in HOSTILE_PIECES + REQUEST_PIECES:
            self.assertNotIn(piece, text)

    def test_each_swiss_failure_has_its_fixed_code_and_text(self):
        for stage, nth in CASES:
            with self.subTest(stage=stage, call=nth):
                result = None
                with _swiss(stage, nth), self.assertRaises(ChartComputationError) as ctx:
                    result = calculate(REQUEST)
                code, detail = EXPECTED[stage]
                self.assertIsNone(result)
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual(str(ctx.exception), f"{code}: {detail}")
                # Raised "from None": the Swiss exception is neither cause nor shown context.
                self.assertIsNone(ctx.exception.__cause__)
                self.assertTrue(ctx.exception.__suppress_context__)
                self.assertPrivate(str(ctx.exception))
                self.assertTrue(_lock_is_free())

    def test_a_failure_stops_all_later_swiss_calls(self):
        for stage, nth in CASES:
            with self.subTest(stage=stage, call=nth):
                calls = []
                with _swiss(stage, nth, calls=calls), self.assertRaises(ChartComputationError):
                    calculate(REQUEST)
                names = [c[0] for c in calls]
                # The failing call is the last Swiss call: nothing computes after it.
                self.assertEqual(names[-1], stage)
                self.assertEqual(names.count(stage), nth)
                if stage in ("julday", "set_ephe_path", "set_sid_mode", "set_delta_t_userdef"):
                    self.assertNotIn("calc_ut", names)
                self.assertNotIn("houses_ex", names[:-1])
                # julday is pure arithmetic before the lock; every stateful call is inside it.
                for name, owned in calls:
                    self.assertEqual(owned, name != "julday", name)

    def test_programming_defects_are_not_translated(self):
        for stage in STAGES:
            with self.subTest(stage=stage):
                with _swiss(stage, exc=ZeroDivisionError("defect")), self.assertRaises(ZeroDivisionError):
                    calculate(REQUEST)
                self.assertTrue(_lock_is_free())

    def test_success_path_is_unchanged(self):
        calls = []
        with _swiss(calls=calls):
            chart = calculate(REQUEST)
        self.assertEqual(len(chart["planets"]), 9)
        self.assertEqual([c[0] for c in calls][:4],
                         ["julday", "set_ephe_path", "set_sid_mode", "set_delta_t_userdef"])

    def test_refusal_order_is_unchanged_when_swiss_would_fail(self):
        # With every Swiss call failing, each earlier refusal still wins, so the new
        # codes are reachable only from their computation stage.
        cases = {
            "REQUEST_INVALID": {**REQUEST, "extra": 1},
            "TIME_OFFSET_REQUIRED": {**REQUEST, "birth_datetime": "2000-01-01T17:30:00"},
            "TIMEZONE_INVALID": {**REQUEST, "timezone": "Not/AZone"},
            # P5 order: a wrong offset is refused before the P8 historical-clock gate.
            "TIME_OFFSET_MISMATCH": {**REQUEST, "birth_datetime": "1965-01-01T12:00:00+05:00"},
            "HISTORICAL_CLOCK_UNVERIFIED": {**REQUEST, "birth_datetime": "1965-01-01T12:00:00+05:30"},
            "COORDINATE_INVALID": {**REQUEST, "latitude": "north"},
            "LATITUDE_OUTSIDE_SUPPORTED_BAND": {**REQUEST, "latitude": 70.0},
        }
        for code, request in cases.items():
            with self.subTest(code=code):
                calls = []
                with _swiss("all", calls=calls), self.assertRaises(InputRefusalError) as ctx:
                    calculate(request)
                self.assertEqual(ctx.exception.code, code)
                self.assertEqual(calls, [])

    def test_timezone_and_ephemeris_data_failures_keep_their_codes(self):
        broken = TimezoneDataError("TZDATA_FILE_MISMATCH", "a zone file does not match the pinned SHA-256")
        with _swiss("all"), mock.patch.object(engine, "get_zone", side_effect=broken), \
                self.assertRaises(TimezoneDataError) as ctx:
            calculate(REQUEST)
        self.assertEqual(ctx.exception.code, "TZDATA_FILE_MISMATCH")
        with tempfile.TemporaryDirectory() as empty:
            for path, code in (("/nonexistent/sabpuja-ephemeris", "EPHEMERIS_PATH_MISSING"),
                               (empty, "EPHEMERIS_FILE_MISSING")):
                with self.subTest(code=code):
                    calls = []
                    with _swiss("all", calls=calls, fake=False), self.assertRaises(EphemerisDataError) as ctx:
                        calculate(REQUEST, ephe_path=path)
                    self.assertEqual(ctx.exception.code, code)
                    self.assertEqual(calls, [])


class SwissCliContractTests(unittest.TestCase):
    """The real CLI module, run as __main__ in a fresh interpreter."""

    def test_every_swiss_failure_is_one_private_json_error_with_exit_2(self):
        for stage, nth in CASES:
            with self.subTest(stage=stage, call=nth):
                proc = _run_cli(stage, nth)
                code, detail = EXPECTED[stage]
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(proc.stdout, "")  # no chart, partial or whole
                self.assertTrue(proc.stderr.endswith("\n"))
                self.assertEqual(proc.stderr.count("\n"), 1, "exactly one stderr line")
                self.assertEqual(json.loads(proc.stderr), {"error": f"{code}: {detail}"})
                self.assertNotIn("Traceback", proc.stderr)
                for piece in HOSTILE_PIECES + REQUEST_PIECES:
                    self.assertNotIn(piece, proc.stderr)

    def test_success_still_prints_the_chart_and_nothing_else(self):
        proc = _run_cli("none")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, "")
        self.assertEqual(len(json.loads(proc.stdout)["planets"]), 9)

    def test_a_programming_defect_is_not_reported_as_a_chart_or_a_refusal(self):
        # Not swallowed or relabelled: the interpreter's own failure (exit 1), no output.
        proc = _run_cli("calc_ut", kind="defect")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout, "")
        self.assertIn("ZeroDivisionError", proc.stderr)
        self.assertNotIn('"error"', proc.stderr)


@unittest.skipIf(DATA is None, f"{DATA_ENV} unset: real-data recovery tests not requested")
class SwissFailureRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = {k: v for k, v in os.environ.items() if k not in ("SE_EPHE_PATH", "SABPUJA_EPHE_PATH")}
        env["PYTHONPATH"] = str(SRC)
        code = ("import json, sys; from sabpuja_kundali.engine import calculate; "
                f"print(json.dumps(calculate({REQUEST!r}, ephe_path={DATA!r}), sort_keys=True))")
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                             env=env, check=True, timeout=60).stdout
        cls.reference = json.loads(out)  # from an interpreter that never touched Swiss

    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("SE_EPHE_PATH", None)

    def poison(self):
        # Foreign state changes made by the failing call itself, before it raises.
        swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY | swe.SIDBIT_PREC_ORIG, 0, 0)
        swe.set_delta_t_userdef(0.01)

    def test_lock_released_and_next_chart_clean_after_each_in_lock_failure(self):
        self.addCleanup(swe.set_delta_t_userdef, swe.DELTAT_AUTOMATIC)
        for stage, nth in CASES:
            if stage == "julday":
                continue  # before the lock; nothing to recover
            with self.subTest(stage=stage, call=nth):
                with _swiss(stage, nth, fake=False, before_raise=self.poison), \
                        self.assertRaises(ChartComputationError) as ctx:
                    calculate(REQUEST, ephe_path=DATA)
                self.assertEqual(ctx.exception.code, EXPECTED[stage][0])
                self.assertTrue(_lock_is_free())
                chart = calculate(REQUEST, ephe_path=DATA)
                self.assertEqual(json.loads(json.dumps(chart, sort_keys=True)), self.reference)

    def test_real_out_of_range_swiss_error_is_translated(self):
        # A genuine (unmocked) Swiss error: calc_ut beyond the pinned files' range.
        # Unreachable through the date window; forced here by moving the instant.
        real_julday = swe.julday
        with mock.patch.object(swe, "julday", lambda *a: real_julday(*a) + 400 * 365.25 * 1000), \
                self.assertRaises(ChartComputationError) as ctx:
            calculate(REQUEST, ephe_path=DATA)
        self.assertEqual(str(ctx.exception), "SWISS_PLANET_CALCULATION_FAILED: " + EXPECTED["calc_ut"][1])
        self.assertNotIn(DATA, str(ctx.exception))
        self.assertTrue(_lock_is_free())
        chart = calculate(REQUEST, ephe_path=DATA)
        self.assertEqual(json.loads(json.dumps(chart, sort_keys=True)), self.reference)


if __name__ == "__main__":
    unittest.main()
