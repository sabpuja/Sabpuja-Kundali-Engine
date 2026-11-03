"""Positive and negative tests for compare_phase_sources.py.

Run from the repository root:
    python3 -I -m unittest discover -s docs/science/kun-pan-m1-dec-001/evidence -p 'test_*.py' -v

Every test works on copies in a fresh temporary directory. The committed
fixture and snapshots are only read, never modified.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SCRIPT = os.path.join(HERE, "compare_phase_sources.py")
FIXTURE = os.path.join(ROOT, "research", "panchanga", "reference-fixtures",
                       "geocentric-lunar-phase-events-2026.json")
USNO = os.path.join(HERE, "usno-moon-phases-2026-retrieved-20261103.txt")
NASA = os.path.join(HERE, "nasa-espenak-phases-2026-retrieved-20261103.txt")


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.fx = shutil.copy(FIXTURE, os.path.join(self.tmp, "fixture.json"))
        self.usno = shutil.copy(USNO, os.path.join(self.tmp, "usno.txt"))
        self.nasa = shutil.copy(NASA, os.path.join(self.tmp, "nasa.txt"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_script(self, fx=None, usno=None, nasa=None):
        p = subprocess.run([sys.executable, "-I", SCRIPT, fx or self.fx,
                            usno or self.usno, nasa or self.nasa],
                           capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def edit_text(self, path, old, new, count=1):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn(old, text)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace(old, new, count))

    def edit_fixture(self, fn):
        with open(self.fx, encoding="utf-8") as fh:
            data = json.load(fh)
        fn(data)
        with open(self.fx, "w", encoding="utf-8") as fh:
            json.dump(data, fh)

    # positive
    def test_committed_inputs_pass(self):
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertIn("values 100 mismatches 0", out)
        self.assertIn("live inter-source differences 8", out)
        self.assertIn("RESULT PASS", out)
        self.assertNotIn("ERROR", out)

    # negative: fixture side
    def test_altered_fixture_minute_fails(self):
        def f(d):
            d["cases"][0]["published_values"][0]["value_utc_minute"] = "2026-01-03T10:04Z"
            d["cases"][0]["inter_source_difference_minutes"] = 1
        self.edit_fixture(f)
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("fixture 10:04 vs publisher 10:03", out)

    def test_duplicate_fixture_key_fails(self):
        self.edit_fixture(lambda d: d["cases"].append(d["cases"][0]))
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("duplicate fixture key", out)
        self.assertIn("fixture has 51 cases", out)

    def test_missing_fixture_case_fails(self):
        self.edit_fixture(lambda d: d["cases"].pop())
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("publisher event absent from fixture", out)

    def test_wrong_recorded_difference_fails(self):
        self.edit_fixture(lambda d: d["cases"][0].update(inter_source_difference_minutes=1))
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("recorded inter-source difference", out)

    def test_fixture_marker_removed_fails(self):
        def f(d):
            d["cases"][6]["published_values"][1]["source_markers"] = None
        self.edit_fixture(f)
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("marker fixture None vs publisher 'A'", out)

    # negative: publisher side
    def test_altered_publisher_minute_fails(self):
        self.edit_text(self.usno, "01-03 Full Moon 10:03", "01-03 Full Moon 10:05")
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("MISMATCH", out)

    def test_absent_publisher_event_fails(self):
        self.edit_text(self.nasa, "01-03 Full Moon 10:03\n", "")
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("not found in publisher file", out)
        self.assertIn("SRC-NASA-PHASES file has 49 events", out)

    def test_duplicate_publisher_event_fails(self):
        with open(self.usno, "a", encoding="utf-8") as fh:
            fh.write("01-03 Full Moon 10:03\n")
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("duplicate publisher event", out)

    def test_extra_publisher_event_fails(self):
        with open(self.usno, "a", encoding="utf-8") as fh:
            fh.write("12-31 New Moon 23:59\n")
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("publisher event absent from fixture", out)

    def test_publisher_marker_changed_fails(self):
        self.edit_text(self.nasa, "02-17 New Moon 12:01 A", "02-17 New Moon 12:01 T")
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("MARKER_MISMATCH", out)

    def test_marker_in_usno_file_fails(self):
        self.edit_text(self.usno, "02-17 New Moon 12:01", "02-17 New Moon 12:01 A")
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("unexpected marker", out)

    # malformed input
    def test_malformed_line_exits_2(self):
        self.edit_text(self.usno, "01-03 Full Moon 10:03", "01-03 Fullmoon 10:03")
        code, out = self.run_script()
        self.assertEqual(code, 2, out)
        self.assertIn("INPUT ERROR", out)

    def test_out_of_range_time_exits_2(self):
        self.edit_text(self.usno, "01-03 Full Moon 10:03", "01-03 Full Moon 25:99")
        code, out = self.run_script()
        self.assertEqual(code, 2, out)
        self.assertIn("INPUT ERROR", out)
        self.assertNotIn("RESULT FAIL", out)

    def test_non_numeric_date_exits_2(self):
        self.edit_text(self.nasa, "01-03 Full Moon 10:03", "AA-BB Full Moon 10:03")
        code, out = self.run_script()
        self.assertEqual(code, 2, out)
        self.assertIn("INPUT ERROR", out)

    def test_impossible_calendar_date_exits_2(self):
        self.edit_text(self.usno, "02-24 First Quarter 12:27", "02-30 First Quarter 12:27")
        code, out = self.run_script()
        self.assertEqual(code, 2, out)
        self.assertIn("INPUT ERROR", out)

    def test_malformed_fixture_datetime_exits_2(self):
        def f(d):
            d["cases"][0]["published_values"][0]["value_utc_minute"] = "2026-13-03T10:03Z"
        self.edit_fixture(f)
        code, out = self.run_script()
        self.assertEqual(code, 2, out)
        self.assertIn("INPUT ERROR", out)

    def test_valid_but_wrong_minute_still_exits_1(self):
        self.edit_text(self.usno, "01-03 Full Moon 10:03", "01-03 Full Moon 23:59")
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("RESULT FAIL", out)

    def test_missing_file_exits_2(self):
        code, out = self.run_script(usno=os.path.join(self.tmp, "absent.txt"))
        self.assertEqual(code, 2, out)

    def test_committed_files_untouched(self):
        for src, copy in ((FIXTURE, self.fx), (USNO, self.usno), (NASA, self.nasa)):
            with open(src, "rb") as a, open(copy, "rb") as b:
                self.assertEqual(a.read(), b.read())


if __name__ == "__main__":
    unittest.main()
