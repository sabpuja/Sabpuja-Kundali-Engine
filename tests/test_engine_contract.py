import unittest
from sabpuja_kundali.engine import _parse_birth, calculate

SYNTHETIC = {
    "birth_datetime": "2000-01-01T17:30:00+05:30",
    "timezone": "Asia/Kolkata",
    "latitude": 28.6139,
    "longitude": 77.2090
}

class ContractTests(unittest.TestCase):
    def test_valid_timezone_offset(self):
        self.assertEqual(_parse_birth(SYNTHETIC["birth_datetime"], "Asia/Kolkata").hour, 12)

    def test_reject_missing_offset(self):
        with self.assertRaises(ValueError):
            _parse_birth("2000-01-01T17:30:00", "Asia/Kolkata")

    def test_reject_wrong_timezone_offset(self):
        with self.assertRaises(ValueError):
            _parse_birth("2000-01-01T17:30:00+04:00", "Asia/Kolkata")

    def test_reject_bad_shape(self):
        with self.assertRaises(ValueError):
            calculate({**SYNTHETIC, "name": "do not store"})

    def test_fail_closed_without_ephemeris(self):
        with self.assertRaises(RuntimeError):
            calculate(SYNTHETIC, ephe_path="/does-not-exist/sabpuja")

if __name__ == "__main__":
    unittest.main()
