"""PAN-QA-04: all 50 independently rechecked phase events inside the frozen D15-a window.

Gate: every case PASS, exactly 50 cases, no fixture or tolerance drift. Residuals
and NEAR_WINDOW_EDGE cases are reported by `python -m tests.panchanga.run`.
Claim limited to agreement with publisher-printed minutes (D20-M1-SCOPED (4)).
"""
from __future__ import annotations

import unittest

from .common import EPHE, real_data
from . import phase_events


@real_data
class PhaseEventGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = phase_events.evaluate(EPHE)

    def test_all_fifty_cases_pass_inside_the_frozen_window(self):
        failing = [(r["case_id"], r["engine_utc"], r["window_utc"], r["problems"])
                   for r in self.report["rows"] if r["status"] != "PASS"]
        self.assertEqual(failing, [])
        self.assertEqual(self.report["case_count"], 50)
        self.assertEqual(self.report["verdict"], "PASS")

    def test_every_angle_class_is_covered(self):
        by_angle = {}
        for r in self.report["rows"]:
            by_angle[r["angle_deg"]] = by_angle.get(r["angle_deg"], 0) + 1
        self.assertEqual(by_angle, {0: 12, 90: 12, 180: 13, 270: 13})

    def test_tithi_transitions_coincide_with_karana_at_0_and_180(self):
        for r in self.report["rows"]:
            if r["angle_deg"] in (0, 180):
                self.assertEqual(r["tithi"]["end"], r["engine_utc"])
                self.assertEqual(r["tithi"]["start"], r["engine_utc"])
            else:
                self.assertIsNone(r["tithi"])


if __name__ == "__main__":
    unittest.main()
