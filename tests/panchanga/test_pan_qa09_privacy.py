"""PAN-QA-09: privacy-safe errors, refusal codes and order, fault injection, CLI contract.

The Panchanga path must refuse exactly as the chart does (same exception type,
code and fixed text, same order), then add only its own typed refusals. No
error, log line or exception chain may contain birth data or computed instants.
"""
from __future__ import annotations

from pathlib import Path
from unittest import mock
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from .common import EPHE, REPO, real_data

VALID = {"birth_datetime": "1991-08-17T14:37:23+05:30", "timezone": "Asia/Kolkata",
         "latitude": 19.07283, "longitude": 72.88261}
SECRETS = ("1991", "08-17", "14:37", "37:23", "19.07283", "72.88261", "19.0728", "72.8826")

# (request override, expected code). Ordered P5 checks; several requests carry more
# than one fault, so the first code proves the order.
REFUSALS = [
    ({"birth_datetime": "1991-08-17 14:37+05:30"}, "TIME_FORMAT_INVALID"),
    ({"birth_datetime": "1991-08-17T14:37"}, "TIME_OFFSET_REQUIRED"),
    ({"birth_datetime": "1991-08-17T14:37:60+05:30"}, "TIME_LEAP_SECOND_UNSUPPORTED"),
    ({"birth_datetime": "1991-02-30T14:37+05:30", "latitude": 99}, "DATE_INVALID"),
    ({"timezone": "Asia/Atlantis", "latitude": 99}, "TIMEZONE_INVALID"),
    ({"timezone": "Etc/GMT-5", "latitude": 99}, "TIMEZONE_NOT_LOCATION_BASED"),
    ({"birth_datetime": "2101-01-01T00:00+05:30"}, "DATE_OUTSIDE_SUPPORTED_RANGE"),
    ({"birth_datetime": "1991-03-31T02:30+01:00", "timezone": "Europe/Berlin"}, "TIME_NONEXISTENT_LOCAL"),
    ({"birth_datetime": "1991-08-17T14:37+05:00"}, "TIME_OFFSET_MISMATCH"),
    ({"birth_datetime": "1969-12-31T23:00+05:30", "latitude": 99}, "HISTORICAL_CLOCK_UNVERIFIED"),
    ({"latitude": "19"}, "COORDINATE_INVALID"),
    ({"longitude": 181.0, "latitude": 70.0}, "COORDINATE_INVALID"),
    ({"latitude": 66.0000001}, "LATITUDE_OUTSIDE_SUPPORTED_BAND"),
    ({"latitude": -66.0000001}, "LATITUDE_OUTSIDE_SUPPORTED_BAND"),
    ({"extra": 1}, "REQUEST_INVALID"),
]


def refusal_requests():
    for override, code in REFUSALS:
        req = dict(VALID)
        req.update(override)
        yield req, code


def assert_private(test, text: str, req=VALID):
    for s in SECRETS + (str(req.get("latitude")), str(req.get("longitude"))):
        if s and s not in ("None",) and len(s) >= 3:
            test.assertNotIn(s, text)


class RefusalParityTest(unittest.TestCase):
    """Without data: every input refusal precedes the ephemeris gate, so these run anywhere."""

    def test_same_type_code_and_text_as_the_chart_in_the_same_order(self):
        from sabpuja_kundali import engine
        from sabpuja_kundali.panchanga import EXPECTED_ERRORS, calculate
        for req, code in refusal_requests():
            with self.subTest(code=code):
                with self.assertRaises(EXPECTED_ERRORS) as p:
                    calculate(req, "/nonexistent/ephe")
                with self.assertRaises(engine.EXPECTED_ERRORS) as c:
                    engine.calculate(req, "/nonexistent/ephe")
                self.assertEqual(p.exception.code, code)
                self.assertIs(type(p.exception), type(c.exception))
                self.assertEqual(str(p.exception), str(c.exception))
                assert_private(self, str(p.exception), req)

    def test_non_dict_request(self):
        from sabpuja_kundali.panchanga import calculate
        from sabpuja_kundali.engine import InputRefusalError
        for bad in (None, [], "x", 1):
            with self.assertRaises(InputRefusalError) as ctx:
                calculate(bad)
            self.assertEqual(ctx.exception.code, "REQUEST_INVALID")

    def test_ephemeris_refusals_come_after_input_checks(self):
        from sabpuja_kundali.panchanga import calculate
        from sabpuja_kundali.ephemeris import EphemerisDataError
        with self.assertRaises(EphemerisDataError) as ctx:
            calculate(VALID, "/nonexistent/ephe")
        self.assertEqual(ctx.exception.code, "EPHEMERIS_PATH_MISSING")
        with mock.patch.dict(os.environ, {"SE_EPHE_PATH": "/tmp"}):
            with self.assertRaises(EphemerisDataError) as ctx:
                calculate(VALID, "/nonexistent/ephe")
        self.assertEqual(ctx.exception.code, "EPHEMERIS_PATH_OVERRIDE")
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "sepl_18.se1").write_bytes(b"x")
            Path(tmp, "semo_18.se1").write_bytes(b"y")
            with self.assertRaises(EphemerisDataError) as ctx:
                calculate(VALID, tmp)
            self.assertEqual(ctx.exception.code, "EPHEMERIS_FILE_MISMATCH")


class _Proxy:
    """Delegates to swisseph; `fault(n, value)` fires on the n-th calc_ut call of the session."""

    def __init__(self, swe, mode: str, at: int):
        self._swe, self.mode, self.at, self.n = swe, mode, at, 0

    def __getattr__(self, name):
        return getattr(self._swe, name)

    def calc_ut(self, jd, body, flags):
        self.n += 1
        pos, ret = self._swe.calc_ut(jd, body, flags)
        if self.n == self.at:
            if self.mode == "moshier":
                return pos, (ret & ~self._swe.FLG_SWIEPH) | self._swe.FLG_MOSEPH
            if self.mode == "error":
                raise self._swe.Error("/secret/server/path 1991-08-17 failure text")
            if self.mode == "nan":
                return (float("nan"),) + tuple(pos[1:]), ret
        return pos, ret


@real_data
class FaultInjectionTest(unittest.TestCase):
    def run_with(self, mode: str, at: int):
        from sabpuja_kundali.panchanga import contract
        real = contract.SwissSession
        holder = {}

        def factory(swe, folder):
            holder["proxy"] = _Proxy(swe, mode, at)
            return real(holder["proxy"], folder)
        with mock.patch.object(contract, "SwissSession", factory):
            try:
                contract.calculate(VALID, EPHE)
            finally:
                pass
        return holder

    def test_missing_swieph_flag_at_any_call_refuses(self):
        from sabpuja_kundali.engine import ChartComputationError
        from sabpuja_kundali.panchanga import calculate
        last = calculate(VALID, EPHE)["provenance"]["swiss_calls"]
        self.assertGreater(last, 100)
        for at in (1, 2, 3, 17, 60, last // 2, last - 1, last):
            with self.subTest(call=at):
                with self.assertRaises(ChartComputationError) as ctx:
                    self.run_with("moshier", at)
                self.assertEqual(ctx.exception.code, "SWISS_EPHEMERIS_FALLBACK_REFUSED")
                assert_private(self, str(ctx.exception))

    def test_swiss_error_text_never_reaches_the_caller(self):
        from sabpuja_kundali.engine import ChartComputationError
        for at in (1, 40, 101):
            with self.assertRaises(ChartComputationError) as ctx:
                self.run_with("error", at)
            self.assertEqual(ctx.exception.code, "SWISS_PLANET_CALCULATION_FAILED")
            self.assertNotIn("secret", str(ctx.exception))
            self.assertTrue(ctx.exception.__suppress_context__)
            self.assertIsNone(ctx.exception.__cause__)

    def test_non_finite_longitude_is_a_typed_non_convergence(self):
        from sabpuja_kundali.panchanga import PanchangaComputationError
        for at in (5, 101):
            with self.assertRaises(PanchangaComputationError) as ctx:
                self.run_with("nan", at)
            self.assertEqual(ctx.exception.code, "PANCHANGA_TRANSITION_NOT_CONVERGED")
            self.assertIsNone(ctx.exception.__cause__)
            self.assertTrue(ctx.exception.__suppress_context__)

    def test_every_session_call_is_flag_checked(self):
        """The fault at the last call still refuses: no call escapes the FLG_SWIEPH check."""
        from sabpuja_kundali.panchanga import calculate
        doc = calculate(VALID, EPHE)
        last = doc["provenance"]["swiss_calls"]
        from sabpuja_kundali.engine import ChartComputationError
        with self.assertRaises(ChartComputationError):
            self.run_with("moshier", last)
        self.run_with("moshier", last + 1)   # beyond the last call: the document is produced

    def test_chart_identity_failure_is_refused(self):
        from sabpuja_kundali import engine
        from sabpuja_kundali.panchanga import PanchangaComputationError, contract
        real = engine.calculate

        def tampered(req, ephe=None):
            chart = real(req, ephe)
            chart["moon_nakshatra"] = dict(chart["moon_nakshatra"], pada=chart["moon_nakshatra"]["pada"] % 4 + 1)
            return chart
        with mock.patch.object(contract.engine, "calculate", tampered):
            with self.assertRaises(PanchangaComputationError) as ctx:
                contract.calculate(VALID, EPHE)
        self.assertEqual(ctx.exception.code, "PANCHANGA_CHART_IDENTITY_FAILED")

    def test_non_convergence_message_is_fixed_and_private(self):
        from sabpuja_kundali.panchanga import PanchangaComputationError, calculate
        from sabpuja_kundali.panchanga.search import SearchLimits
        with self.assertRaises(PanchangaComputationError) as ctx:
            calculate(VALID, EPHE, limits=SearchLimits(max_iterations=2))
        text = str(ctx.exception)
        assert_private(self, text)
        self.assertNotRegex(text, r"\d{4}-\d{2}-\d{2}")
        self.assertIsNone(ctx.exception.__cause__)

    def test_no_logging_on_success_or_refusal(self):
        from sabpuja_kundali.panchanga import EXPECTED_ERRORS, calculate
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        root = logging.getLogger()
        old = root.level
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        try:
            calculate(VALID, EPHE)
            for req, _ in refusal_requests():
                try:
                    calculate(req, EPHE)
                except EXPECTED_ERRORS:
                    pass
        finally:
            root.removeHandler(handler)
            root.setLevel(old)
        self.assertEqual(stream.getvalue(), "")


class CliTest(unittest.TestCase):
    def run_cli(self, payload: bytes, ephe: str | None):
        env = {k: v for k, v in os.environ.items() if k not in ("SE_EPHE_PATH", "SABPUJA_EPHE_PATH")}
        env["PYTHONPATH"] = str(REPO / "src")
        if ephe:
            env["SABPUJA_EPHE_PATH"] = ephe
        return subprocess.run([sys.executable, "-m", "sabpuja_kundali.panchanga"], input=payload,
                              capture_output=True, env=env, timeout=120, check=False)

    def test_refusals_exit_2_with_fixed_json_and_no_traceback(self):
        cases = [(json.dumps(r).encode(), c) for r, c in refusal_requests()]
        cases += [(b"x" * 4097, "REQUEST_INVALID"), (b"\xff\xfe", "REQUEST_INVALID"), (b"{", "REQUEST_INVALID"),
                  (json.dumps(VALID).encode(), "EPHEMERIS_PATH_MISSING")]
        for payload, code in cases:
            with self.subTest(code=code):
                proc = self.run_cli(payload, None)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(proc.stdout, b"")
                err = json.loads(proc.stderr)
                self.assertEqual(list(err), ["error"])
                self.assertTrue(err["error"].startswith(code + ": "))
                self.assertNotIn(b"Traceback", proc.stderr)
                assert_private(self, proc.stderr.decode())

    @unittest.skipIf(EPHE is None, "SABPUJA_TEST_EPHE_PATH unset")
    def test_success_prints_the_document_only(self):
        proc = self.run_cli(json.dumps(VALID).encode(), EPHE)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, b"")
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["schema"], "sabpuja-panchanga/1")
        self.assertNotIn("latitude", json.dumps(doc["birth"]))


if __name__ == "__main__":
    unittest.main()
