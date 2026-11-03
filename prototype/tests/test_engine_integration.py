"""The wrapper returns the real engine's chart unchanged, and fails closed on bad data."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from sabpuja_kundali import provenance
from sabpuja_kundali.engine import calculate
from sabpuja_kundali.rules import SIGNS
from kundali_prototype import server
from kundali_prototype.places import load_places

from support import EPHE, SYNTHETIC, requires_data

PLACES = load_places()


def post(body, ephe=None):
    return server.handle_chart(json.dumps(body).encode(), PLACES, EPHE if ephe is None else ephe)


@requires_data
class SameAsEngine(unittest.TestCase):
    def test_chart_is_byte_identical_to_a_direct_engine_call(self):
        for pid, d, t in SYNTHETIC:
            with self.subTest(pid=pid, date=d):
                status, body = post({"place_id": pid, "birth_date": d, "birth_time": t})
                self.assertEqual(status, 200, body.get("error"))
                place = PLACES[pid]
                time = t if len(t) == 8 else t + ":00"
                direct = calculate({"birth_datetime": f"{d}T{time}{body['input']['utc_offset']}",
                                    "timezone": place["timezone"], "latitude": place["latitude"],
                                    "longitude": place["longitude"]}, ephe_path=EPHE)
                self.assertEqual(json.dumps(body["chart"], sort_keys=True), json.dumps(direct, sort_keys=True))

    def test_conventions_preserved(self):
        status, body = post({"place_id": "in-new-delhi", "birth_date": "1990-05-15", "birth_time": "10:30"})
        chart = body["chart"]
        self.assertEqual(chart["schema_version"], "0.3.0")  # Gate 3E proposed candidate (owner approval pending)
        self.assertEqual(chart["calculation_metadata"]["metadata_schema"], "sabpuja-calculation-metadata/3")
        self.assertEqual(chart["method"], {"ayanamsa": "Lahiri", "nodes": "mean", "houses": "whole_sign",
                                           "ephemeris": "Swiss Ephemeris, local .se1", "binding_version": "2.10.03"})
        conv = chart["calculation_metadata"]["conventions"]
        self.assertEqual(conv["ayanamsa"]["swiss_mode"], "SIDM_LAHIRI")
        self.assertEqual(conv["planetary_positions"]["swiss_flags"], ["FLG_SWIEPH", "FLG_SIDEREAL"])
        self.assertEqual(chart["validation_status"], "UNVERIFIED_GOLDEN_CHARTS")
        rahu, ketu = chart["planets"]["rahu_mean"], chart["planets"]["ketu_mean"]
        self.assertEqual(SIGNS.index(ketu["rashi"]), (SIGNS.index(rahu["rashi"]) + 6) % 12)
        self.assertAlmostEqual((ketu["longitude_deg"] - rahu["longitude_deg"]) % 360, 180.0, places=7)

    def test_known_reference_values_unchanged(self):
        # The same synthetic request through the engine CLI gave these values (evidence log).
        status, body = post({"place_id": "in-new-delhi", "birth_date": "1990-05-15", "birth_time": "10:30"})
        chart = body["chart"]
        self.assertEqual(chart["lagna"], {"longitude_deg": 99.90641925, "rashi": "Karka", "navamsa_rashi": "Kanya"})
        self.assertEqual(chart["moon_nakshatra"], {"index": 20, "name": "Uttara Ashadha", "pada": 1})
        self.assertEqual(chart["planets"]["sun"]["longitude_deg"], 30.38907071)


@requires_data
class FailsClosed(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.body = {"place_id": "in-mumbai", "birth_date": "1990-05-15", "birth_time": "10:30"}

    def code(self, ephe):
        status, body = post(self.body, ephe)
        self.assertEqual(status, 503, body.get("error"))
        self.assertNotIn("chart", body)
        self.assertNotIn(str(self.tmp), json.dumps(body))
        return body["error"]["code"]

    def test_missing_moon_file_refused_no_moshier(self):
        shutil.copy(Path(EPHE) / "sepl_18.se1", self.tmp)
        self.assertEqual(self.code(str(self.tmp)), "EPHEMERIS_FILE_MISSING")

    def test_tampered_file_refused(self):
        for name in ("sepl_18.se1", "semo_18.se1"):
            shutil.copy(Path(EPHE) / name, self.tmp)
        with open(self.tmp / "semo_18.se1", "r+b") as fh:
            fh.seek(1000)
            byte = fh.read(1)
            fh.seek(1000)
            fh.write(bytes([byte[0] ^ 0xFF]))
        self.assertEqual(self.code(str(self.tmp)), "EPHEMERIS_FILE_MISMATCH")

    def test_empty_and_wrong_path(self):
        self.assertEqual(self.code(str(self.tmp)), "EPHEMERIS_FILE_MISSING")
        self.assertEqual(self.code(str(self.tmp / "absent")), "EPHEMERIS_PATH_MISSING")

    def test_se_ephe_path_override_refused(self):
        os.environ["SE_EPHE_PATH"] = str(self.tmp)
        try:
            self.assertEqual(self.code(EPHE), "EPHEMERIS_PATH_OVERRIDE")
        finally:
            del os.environ["SE_EPHE_PATH"]


class NoDataNoChart(unittest.TestCase):
    def test_unset_path_refused_without_data(self):
        status, body = server.handle_chart(
            json.dumps({"place_id": "in-mumbai", "birth_date": "1990-05-15", "birth_time": "10:30"}).encode(), PLACES, "")
        self.assertEqual((status, body["error"]["code"]), (503, "EPHEMERIS_PATH_MISSING"))


if __name__ == "__main__":
    unittest.main()
