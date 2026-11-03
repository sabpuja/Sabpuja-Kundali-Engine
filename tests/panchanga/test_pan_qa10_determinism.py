"""PAN-QA-10: determinism, cross-process and cross-locale consistency, Swiss state isolation (PAN-SPEC-15)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import sys
import unittest

from .common import EPHE, REPO, real_data

REQUESTS = [
    {"birth_datetime": "2026-01-03T13:00:00+05:30", "timezone": "Asia/Kolkata", "latitude": 28.6139, "longitude": 77.209},
    {"birth_datetime": "1970-01-01T00:30:00+05:30", "timezone": "Asia/Kolkata", "latitude": 12.97, "longitude": 77.59},
    {"birth_datetime": "2088-11-30T23:59:59.999999+05:45", "timezone": "Asia/Kathmandu", "latitude": 27.7, "longitude": 85.3},
    {"birth_datetime": "2001-06-21T05:15:00-04:00", "timezone": "America/New_York", "latitude": 40.71, "longitude": -74.0},
]


def dumps(doc) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=2)


@real_data
class DeterminismTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from sabpuja_kundali import engine
        from sabpuja_kundali.panchanga import calculate
        cls.reference = [dumps(calculate(r, EPHE)) for r in REQUESTS]
        cls.charts = [dumps(engine.calculate(r, EPHE)) for r in REQUESTS]

    def test_repeat_runs_identical(self):
        from sabpuja_kundali.panchanga import calculate
        for _ in range(3):
            self.assertEqual([dumps(calculate(r, EPHE)) for r in REQUESTS], self.reference)

    def test_cross_process_and_locale_identical(self):
        envs = [{"LC_ALL": "C", "TZ": "UTC", "PYTHONHASHSEED": "0"},
                {"LC_ALL": "C.UTF-8", "LANG": "hi_IN.UTF-8", "TZ": "Pacific/Kiritimati", "PYTHONHASHSEED": "12345"},
                {"TZ": "America/St_Johns", "PYTHONHASHSEED": "random"}]
        for extra in envs:
            env = {k: v for k, v in os.environ.items() if k not in ("SE_EPHE_PATH",)}
            env.update(extra, PYTHONPATH=str(REPO / "src"), SABPUJA_EPHE_PATH=EPHE)
            for req, want in zip(REQUESTS, self.reference):
                proc = subprocess.run([sys.executable, "-m", "sabpuja_kundali.panchanga"], input=json.dumps(req).encode(),
                                      capture_output=True, env=env, timeout=120, check=False)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stdout.decode("utf-8").rstrip("\n"), want)

    def test_foreign_swiss_state_does_not_leak_in_or_out(self):
        import swisseph as swe
        from sabpuja_kundali import engine
        from sabpuja_kundali.panchanga import calculate
        swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY, 0, 0)
        swe.set_delta_t_userdef(0.01)
        swe.set_topo(77.2, 28.6, 200)
        swe.set_ephe_path("/nonexistent")
        try:
            self.assertEqual([dumps(calculate(r, EPHE)) for r in REQUESTS], self.reference)
            swe.set_sid_mode(swe.SIDM_RAMAN, 0, 0)
            swe.set_delta_t_userdef(-0.02)
            self.assertEqual([dumps(engine.calculate(r, EPHE)) for r in REQUESTS], self.charts)
            # Interleaved chart and Panchanga calls.
            for r, want_doc, want_chart in zip(REQUESTS, self.reference, self.charts):
                self.assertEqual(dumps(engine.calculate(r, EPHE)), want_chart)
                self.assertEqual(dumps(calculate(r, EPHE)), want_doc)
                self.assertEqual(dumps(engine.calculate(r, EPHE)), want_chart)
        finally:
            swe.set_delta_t_userdef(swe.DELTAT_AUTOMATIC)
            swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

    def test_concurrent_threads_identical_to_sequential(self):
        from sabpuja_kundali import engine
        from sabpuja_kundali.panchanga import calculate
        jobs = [(i % len(REQUESTS), i % 2) for i in range(32)]

        def work(job):
            idx, kind = job
            fn = calculate if kind == 0 else engine.calculate
            return job, dumps(fn(REQUESTS[idx], EPHE))
        with ThreadPoolExecutor(max_workers=8) as pool:
            for (idx, kind), out in pool.map(work, jobs):
                self.assertEqual(out, (self.reference if kind == 0 else self.charts)[idx])

    def test_session_releases_the_swiss_lock_on_every_outcome(self):
        from sabpuja_kundali import engine
        from sabpuja_kundali.panchanga import PanchangaComputationError, calculate
        from sabpuja_kundali.panchanga.search import SearchLimits
        with self.assertRaises(PanchangaComputationError):
            calculate(REQUESTS[0], EPHE, limits=SearchLimits(max_iterations=1))
        self.assertTrue(engine._SWISS_LOCK.acquire(blocking=False))
        engine._SWISS_LOCK.release()

    def test_pre_1970_and_post_2100_instants_are_withheld_locally_only(self):
        from sabpuja_kundali.panchanga import calculate
        doc = json.loads(self.reference[1])          # 1970-01-01 00:30 local (PAN-SPEC-12)
        start = doc["tithi"]["start"]
        self.assertTrue(start["utc"].startswith("1969-"))
        self.assertEqual(start["local_rendering"], "withheld_outside_envelope")
        self.assertNotIn("local", start)
        late = calculate({"birth_datetime": "2100-12-31T23:00:00+05:30", "timezone": "Asia/Kolkata",
                          "latitude": 28.6, "longitude": 77.2}, EPHE)
        ends = [late[k]["end"] for k in ("tithi", "karana", "yoga", "nakshatra")]
        self.assertTrue(any(e["local_rendering"] == "withheld_outside_envelope" for e in ends))
        for e in ends:
            if e["local_rendering"] == "rendered":
                self.assertTrue(e["local"].startswith("2100-12-31"))
            else:
                self.assertNotIn("local", e)
        self.assertEqual(doc["local_rendering"]["envelope_local_dates"], {"first": "1970-01-01", "last": "2100-12-31"})

    def test_envelope_constants_derive_from_the_chart_policy(self):
        from datetime import timedelta
        from sabpuja_kundali import engine
        from sabpuja_kundali.panchanga import contract
        self.assertEqual(contract.LOCAL_RENDERING_FIRST_DATE, engine.HISTORICAL_CLOCK_GATE[0][2] + timedelta(days=1))
        self.assertEqual(contract.LOCAL_RENDERING_LAST_DATE, engine.SUPPORTED_LOCAL_DATES[1])


if __name__ == "__main__":
    unittest.main()
