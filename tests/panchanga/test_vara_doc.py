"""KUN-PAN-RPT-002: the `sabpuja-panchanga-vara/1` document (src/sabpuja_kundali/panchanga/vara.py).

Every place and instant is synthetic. Without SABPUJA_TEST_EPHE_PATH only the input-refusal and static
checks run; with it, the live cases run (and fail, not skip, on wrong data). The swetest altitude check
also needs SABPUJA_TEST_SWETEST (QA's accepted independent build, or a local one with its receipt).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from sabpuja_kundali import engine
from sabpuja_kundali.engine import InputRefusalError
from sabpuja_kundali.panchanga import sun, vara
from . import sun_compare as C
from .common import EPHE, SWETEST, real_data

IST = timezone(timedelta(hours=5, minutes=30))
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
JAIPUR = (26.91962, 75.78781)
SUN_PY_ACCEPTED_SHA256 = "901e31d58cd87d860f155880b6a8c8ab306dc3ed992273ac9039d8c9463c6f53"   # as accepted at c759c41
SUN_PY_ACCEPTED_COMMIT = "c759c412b22753f7f5b6134e2aaaad0f04412007"
# KUN-PAN-VARA-G2-001 changes only sun.py's docstring and status metadata (owner adoption of PAN-D03, PR #93).
SUN_PY_SHA256 = "34a29d8c868e5e27331105c8cc72b9c56a4aa2832fa4cda815157ec11f569b1b"
SUN_PATH = "src/sabpuja_kundali/panchanga/sun.py"


def _code_fingerprint(src: str) -> str:
    """The module's code with its docstring, status constants and status/claim fields neutralised."""
    import ast
    tree = ast.parse(src)
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
        tree.body = tree.body[1:]
    body = []
    for node in tree.body:
        names = [getattr(t, "id", None) for t in node.targets] if isinstance(node, ast.Assign) else []
        if names == ["CONVENTION_STATUS"]:
            continue
        if names == ["VALIDATION_STATUS"]:
            node.value = ast.Constant("X")
        body.append(node)
    tree.body = body
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for i, key in enumerate(node.keys):
                if isinstance(key, ast.Constant) and key.value in ("convention_status", "claim_boundary"):
                    node.values[i] = ast.Constant("X")
    return ast.dump(tree)


def req(local: str, tz: str = "Asia/Kolkata", lat: float = JAIPUR[0], lon: float = JAIPUR[1]) -> dict:
    return {"birth_datetime": local, "timezone": tz, "latitude": lat, "longitude": lon}


def utc_of(us: int) -> datetime:
    return EPOCH + timedelta(microseconds=us)


def local_iso(us: int, offset=IST) -> str:
    return utc_of(us).astimezone(offset).isoformat()


class Static(unittest.TestCase):
    def test_sun_module_is_pinned(self):
        self.assertEqual(hashlib.sha256(Path(sun.__file__).read_bytes()).hexdigest(), SUN_PY_SHA256)

    def test_sun_module_code_is_the_accepted_one(self):
        """Apart from its docstring and status metadata, sun.py is the code accepted at c759c41: no formula,
        threshold, convention constant, rounding, refusal or timezone line changed (KUN-PAN-VARA-G2-001)."""
        root = Path(sun.__file__).resolve().parents[3]
        try:
            accepted = subprocess.run(["git", "-C", str(root), "show", f"{SUN_PY_ACCEPTED_COMMIT}:{SUN_PATH}"],
                                      capture_output=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("needs a git clone with c759c41 to read the accepted sun.py")
        self.assertEqual(hashlib.sha256(accepted).hexdigest(), SUN_PY_ACCEPTED_SHA256)
        current = Path(sun.__file__).read_text(encoding="utf-8")
        self.assertNotEqual(current.encode("utf-8"), accepted)
        self.assertEqual(_code_fingerprint(current), _code_fingerprint(accepted.decode("utf-8")))
        self.assertEqual(sun.CONVENTIONS["SUN-D-IMD-47"]["depression_arcmin"], 47)
        self.assertEqual(set(sun.CONVENTION_STATUS), set(sun.CONVENTIONS))
        self.assertTrue(sun.CONVENTION_STATUS["SUN-D-IMD-47"].startswith("ADOPTED"))
        self.assertTrue(sun.CONVENTION_STATUS["SUN-A-USNO-50"].startswith("COMPARISON ONLY"))

    def test_one_fixed_convention_and_no_usno(self):
        self.assertEqual(vara.CONVENTION, "SUN-D-IMD-47")
        self.assertEqual(vara.METHOD["depression_arcmin"], 47)
        text = Path(vara.__file__).read_text(encoding="utf-8")
        self.assertNotIn("USNO-50\"", text)
        self.assertEqual(text.count("convention=CONVENTION"), 3)   # vara() and both sun_day() calls
        self.assertNotIn("convention=", re.sub(r"convention=CONVENTION", "", text))

    def test_m1_contract_unchanged_and_not_importing_the_new_module(self):
        root = Path(vara.__file__).resolve().parent
        for name in ("__init__.py", "contract.py", "rules.py", "search.py", "astro.py", "__main__.py", "sun.py"):
            self.assertIsNone(re.search(r"import\s+vara\b|from\s+\.vara\b|panchanga\.vara\b",
                                        (root / name).read_text(encoding="utf-8")), name)

    def test_near_window_is_five_minutes(self):
        self.assertEqual(vara.NEAR_SUNRISE_SECONDS, 300)


class Refusals(unittest.TestCase):
    """Chart refusals first, unchanged; no Swiss call is needed to refuse these."""

    def same_as_chart(self, request):
        with self.assertRaises(InputRefusalError) as chart:
            engine.calculate(request, "/nonexistent")
        with self.assertRaises(InputRefusalError) as doc:
            vara.calculate(request, "/nonexistent")
        self.assertEqual((type(doc.exception), doc.exception.code, str(doc.exception)),
                         (type(chart.exception), chart.exception.code, str(chart.exception)))
        self.assertIsNone(doc.exception.__cause__)
        return doc.exception.code

    def test_codes_text_and_order_are_the_chart_s(self):
        codes = {self.same_as_chart(r) for r in (
            "not an object", [], {}, {**req("2039-07-31T12:00:00+05:30"), "extra": 1},
            req("2039-07-31T12:00:00"), req("2039-02-30T12:00:00+05:30"), req("2101-01-01T00:00:00+05:30"),
            req("2039-07-31T12:00:00+05:30", tz="Nowhere/Zone"), req("2039-07-31T12:00:00+05:30", tz="UTC"),
            req("2039-07-31T12:00:00+05:30", lat=66.5), req("2039-07-31T12:00:00+05:30", lat=True),
            req("2039-07-31T12:00:00+05:30", lon=181.0), req("2039-07-31T12:00:00+05:00"))}
        self.assertGreaterEqual(len(codes), 6)

    def test_no_birth_data_in_errors_or_cli(self):
        secret = "2039-07-31T12:34:56+05:30"
        bad = req(secret, lat=66.5)
        with self.assertRaises(InputRefusalError) as cm:
            vara.calculate(bad, "/nonexistent")
        self.assertNotIn("12:34:56", str(cm.exception))
        self.assertNotIn("66.5", str(cm.exception))
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(bad).encode()))), \
                redirect_stdout(out), redirect_stderr(err):
            code = vara.main()
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn("12:34:56", err.getvalue())
        self.assertEqual(set(json.loads(err.getvalue())), {"error"})

    def test_ephemeris_path_refused_without_fallback(self):
        with self.assertRaises(vara.EXPECTED_ERRORS):
            vara.calculate(req("2039-07-31T12:00:00+05:30"), "/nonexistent")


@real_data
class Live(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.day = sun.sun_day("2039-07-31", *JAIPUR, "Asia/Kolkata", convention="SUN-D-IMD-47", ephe_path=EPHE)
        cls.g = cls.day["sunrise"]["utc_us"]
        prev = sun.sun_day("2039-07-30", *JAIPUR, "Asia/Kolkata", convention="SUN-D-IMD-47", ephe_path=EPHE)
        cls.prev = prev["sunrise"]["utc_us"]

    def doc(self, request):
        return vara.calculate(request, EPHE)

    def at(self, us):
        """A request whose birth instant is exactly `us` (microseconds), written in IST."""
        return req(local_iso(us))

    def test_exactly_at_sunrise_and_one_microsecond_before(self):
        on = self.doc(self.at(self.g))
        self.assertEqual(on["vara"], {"status": "available", "vara_id": "ravivara", "sunrise_local_date": "2039-07-31"})
        self.assertEqual(on["governing_sunrise"]["utc_us"], self.g)
        self.assertEqual(on["boundary"]["after_governing_sunrise_us"], 0)
        self.assertTrue(on["boundary"]["near_sunrise"])
        self.assertEqual(on["boundary"]["nearest"], "governing")
        before = self.doc(self.at(self.g - 1))
        self.assertEqual(before["vara"], {"status": "available", "vara_id": "shanivara",
                                          "sunrise_local_date": "2039-07-30"})
        self.assertEqual(before["governing_sunrise"]["utc_us"], self.prev)
        self.assertEqual(before["next_sunrise"]["utc_us"], self.g)
        self.assertEqual(before["boundary"]["before_next_sunrise_us"], 1)
        self.assertEqual(before["boundary"]["nearest"], "next")
        self.assertTrue(before["vara_differs_from_civil_weekday"])
        self.assertEqual(before["civil"], {"date": "2039-07-31", "weekday": "sunday"})

    def test_five_minute_band_inclusive_on_both_sides(self):
        w = 300 * 10**6
        cases = ((self.g + w, True), (self.g + w + 1, False), (self.g - w, True), (self.g - w - 1, False))
        for us, near in cases:
            with self.subTest(offset_us=us - self.g):
                d = self.doc(self.at(us))
                self.assertIs(d["boundary"]["near_sunrise"], near)
                self.assertEqual(d["boundary"]["status"], "assessed")

    def test_document_shape_and_internal_consistency(self):
        d = self.doc(req("2039-07-31T15:20:00+05:30"))
        self.assertEqual(set(d), {"schema", "status", "claim_boundary", "method", "birth", "civil", "vara",
                                  "vara_differs_from_civil_weekday", "governing_sunrise", "sunset", "next_sunrise",
                                  "boundary", "provenance"})
        self.assertEqual(d["schema"], "sabpuja-panchanga-vara/1")
        self.assertEqual(d["status"], "OWNER_ADOPTED_FOR_ESSENTIALS_EN_CUSTOMER_RELEASE")
        self.assertEqual(d["governing_sunrise"]["utc_us"], self.g)
        self.assertLess(d["governing_sunrise"]["utc_us"], d["sunset"]["utc_us"])
        self.assertLess(d["sunset"]["utc_us"], d["next_sunrise"]["utc_us"])
        self.assertEqual(d["sunset"]["utc_us"], self.day["sunset"]["utc_us"])
        chart = engine.calculate(req("2039-07-31T15:20:00+05:30"), EPHE)
        self.assertEqual(d["birth"]["utc"], chart["birth"]["utc"])
        self.assertEqual(d["provenance"]["ephemeris_manifest_sha256"],
                         chart["calculation_metadata"]["ephemeris_data"]["manifest_sha256"])

    def test_deterministic(self):
        r = req("2039-07-31T15:20:00+05:30")
        self.assertEqual(json.dumps(self.doc(r), sort_keys=True), json.dumps(self.doc(r), sort_keys=True))

    def test_civil_weekday_never_substitutes_and_midnight_to_sunrise(self):
        d = self.doc(req("2039-07-31T00:00:00+05:30"))
        self.assertEqual(d["civil"]["weekday"], "sunday")
        self.assertEqual(d["vara"]["vara_id"], "shanivara")
        d = self.doc(req("2039-07-30T23:59:59+05:30"))
        self.assertEqual((d["civil"]["weekday"], d["vara"]["vara_id"]), ("saturday", "shanivara"))
        self.assertFalse(d["vara_differs_from_civil_weekday"])

    def test_dst_and_date_line(self):
        d = self.doc(req("2031-03-30T00:30:00+00:00", "Europe/London", 51.50853, -0.12574))
        self.assertEqual(d["vara"]["vara_id"], "shanivara")             # before the 30 March sunrise
        self.assertTrue(d["next_sunrise"]["local"].endswith("+01:00"))   # clocks went forward overnight
        self.assertTrue(d["governing_sunrise"]["local"].endswith("+00:00"))
        d = self.doc(req("2030-01-01T00:20:00+14:00", "Pacific/Kiritimati", 1.87, -157.4))
        self.assertEqual((d["civil"]["weekday"], d["vara"]["vara_id"]), ("tuesday", "somavara"))
        self.assertEqual(d["governing_sunrise"]["local_date"], "2029-12-31")

    def test_polar_and_envelope_unavailable(self):
        d = self.doc(req("2044-06-21T12:00:00+03:00", "Europe/Helsinki", 65.95, 25.0))
        self.assertEqual(d["vara"], {"status": "unavailable", "reason": "PANCHANGA_SUNRISE_UNDEFINED",
                                     "condition": "SUN_ABOVE_DEPRESSION_ALL_DAY"})
        self.assertIsNone(d["vara_differs_from_civil_weekday"])
        self.assertEqual(d["boundary"], {"status": "not_assessed", "reason": "VARA_UNAVAILABLE"})
        d = self.doc(req("2044-06-13T12:00:00+03:00", "Europe/Helsinki", 65.95, 25.0))
        self.assertEqual(d["vara"]["condition"], "VARA_DAY_END_UNDEFINED")
        self.assertEqual(d["governing_sunrise"]["status"], "available")
        self.assertEqual(d["sunset"]["condition"], "NO_SUNSET_WITHIN_24_HOURS_OF_SUNRISE")
        self.assertEqual(d["next_sunrise"]["condition"], "SUN_ABOVE_DEPRESSION_ALL_DAY")
        d = self.doc(req("1970-01-01T00:00:00+05:30"))
        self.assertEqual(d["vara"]["condition"], "GOVERNING_SUNRISE_BEFORE_1970_01_01")
        with self.assertRaises(InputRefusalError) as cm:   # the chart refuses before 1970 here (SCI-03)
            self.doc(req("1969-12-31T12:00:00+05:30"))
        self.assertEqual(cm.exception.code, "HISTORICAL_CLOCK_UNVERIFIED")
        d = self.doc(req("2100-12-31T23:59:59+05:30"))
        self.assertEqual(d["vara"]["vara_id"], "shukravara")
        self.assertEqual(d["next_sunrise"]["condition"], "NEXT_SUNRISE_OUTSIDE_ENVELOPE")
        self.assertEqual(d["boundary"]["status"], "partial")

    def test_cli(self):
        r = req("2039-07-31T15:20:00+05:30")
        env = {**os.environ, "SABPUJA_EPHE_PATH": EPHE, "PYTHONPATH": os.pathsep.join(sys.path)}
        env.pop("SE_EPHE_PATH", None)
        proc = subprocess.run([sys.executable, "-m", "sabpuja_kundali.panchanga.vara"], input=json.dumps(r),
                              capture_output=True, text=True, env=env, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), self.doc(r))
        self.assertEqual(proc.stderr, "")

    def test_events_against_the_independent_oracle(self):
        """The governing sunrise, sunset and next sunrise of three synthetic births against the non-Swiss oracle."""
        from . import sun_oracle
        for r in (req("2039-07-31T15:20:00+05:30"), req("1978-12-12T03:15:00+05:30", lat=26.83928, lon=80.92313),
                  req("2031-03-30T00:30:00+00:00", "Europe/London", 51.50853, -0.12574)):
            d = self.doc(r)
            for key, kind in (("governing_sunrise", "rise"), ("sunset", "set"), ("next_sunrise", "rise")):
                t = utc_of(d[key]["utc_us"])
                o = sun_oracle.event_utc(t + timedelta(minutes=20), r["latitude"], r["longitude"], 47, kind)
                self.assertLess(abs((t - o).total_seconds()), 10.0, key)

    def test_events_against_swetest_altitude(self):
        if not SWETEST:
            self.skipTest("SABPUJA_TEST_SWETEST unset: swetest altitude layer not run")
        for r in (req("2039-07-31T15:20:00+05:30"), req("2031-03-30T00:30:00+00:00", "Europe/London", 51.50853, -0.12574)):
            d = self.doc(r)
            for key in ("governing_sunrise", "sunset", "next_sunrise"):
                jd = d[key]["utc_us"] / 1e6 / 86400 + 2440587.5
                check = C.swetest_altitude_check(SWETEST, EPHE, jd, r["latitude"], r["longitude"], 47)
                self.assertLess(abs(check), 0.2, key)


if __name__ == "__main__":
    unittest.main()
