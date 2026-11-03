"""PAN-QA-07: D15-b-R Swiss-on-Swiss conformance against the official swetest (subset in discovery).

Runs when SABPUJA_TEST_EPHE_PATH and SABPUJA_TEST_SWETEST are set (existing
convention); a set but unverified swetest or receipt fails, it never skips. The
full instant set (100 instants plus births on transition seconds) is the gate run
`python -m tests.panchanga.run`. Implementation conformance only, not
independent astronomical accuracy.
"""
from __future__ import annotations

import unittest

from .common import EPHE, RECEIPT, SWETEST, real_data
from . import swiss_conformance


@unittest.skipIf(SWETEST is None, "SABPUJA_TEST_SWETEST unset: swetest conformance not requested")
@real_data
class SwissConformanceSubsetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = swiss_conformance.evaluate(EPHE, SWETEST, RECEIPT, subset=4)

    def test_no_failed_check(self):
        failed = [(r["instant_id"], c) for r in self.report["rows"] for c in r["checks"] if c["status"] == "FAIL"]
        self.assertEqual(failed, [])
        self.assertEqual(self.report["verdict"], "SWISS-CONFORMANCE PASS")

    def test_coverage(self):
        self.assertGreaterEqual(self.report["instants"], 8 + 20)
        for row in self.report["rows"]:
            names = [c["check"] for c in row["checks"]]
            self.assertEqual(len(names), 6 + 5 + 10)
            self.assertEqual(len(set(names)), len(names))


class ReferenceInputTest(unittest.TestCase):
    def test_missing_swetest_or_receipt_blocks(self):
        for args in ((None, RECEIPT), ("/nonexistent/swetest", RECEIPT)):
            with self.assertRaises(swiss_conformance.ReferenceBlocked) as ctx:
                swiss_conformance.Swetest(args[0], args[1], EPHE or "/nonexistent")
            self.assertEqual(ctx.exception.code, "SWETEST_MISSING")

    @unittest.skipIf(SWETEST is None, "SABPUJA_TEST_SWETEST unset")
    def test_receipt_hash_mismatch_blocks(self):
        import json, tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "receipt.json")
            data = json.loads(open(RECEIPT, encoding="utf-8").read())
            data["swetest_sha256"] = "0" * 64
            open(bad, "w", encoding="utf-8").write(json.dumps(data))
            with self.assertRaises(swiss_conformance.ReferenceBlocked) as ctx:
                swiss_conformance.Swetest(SWETEST, bad, EPHE)
            self.assertEqual(ctx.exception.code, "SWETEST_BUILD_RECEIPT_MISMATCH")
            with self.assertRaises(swiss_conformance.ReferenceBlocked) as ctx:
                swiss_conformance.Swetest(SWETEST, os.path.join(tmp, "absent.json"), EPHE)
            self.assertEqual(ctx.exception.code, "SWETEST_RECEIPT_MISSING")


if __name__ == "__main__":
    unittest.main()
