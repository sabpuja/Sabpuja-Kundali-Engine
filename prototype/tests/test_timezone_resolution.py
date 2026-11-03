"""Local time to UTC offset through the pinned zone: unique, gap, repeated hour."""
import json
import unittest

from sabpuja_kundali.engine import calculate
from sabpuja_kundali.timezones import get_zone
from kundali_prototype import server
from kundali_prototype.places import load_places

from support import EPHE, requires_data

PLACES = load_places()


def post(body, ephe=None):
    return server.handle_chart(json.dumps(body).encode(), PLACES, ephe if ephe is not None else EPHE)


class CandidateOffsets(unittest.TestCase):
    def test_kolkata_single_offset(self):
        zone = get_zone("Asia/Kolkata")
        for d, t in (("1990-05-15", "10:30:00"), ("2100-12-31", "23:59:59"), ("1970-01-01", "00:00:00")):
            self.assertEqual(server._candidate_offsets(d, t, zone)[0], ["+05:30"])

    def test_london_gap_has_no_offset(self):
        valid, carrier = server._candidate_offsets("2020-03-29", "01:30:00", get_zone("Europe/London"))
        self.assertEqual(valid, [])
        self.assertEqual(carrier, "+00:00")

    def test_london_fold_has_two_offsets_in_order(self):
        valid, _ = server._candidate_offsets("2020-10-25", "01:30:00", get_zone("Europe/London"))
        self.assertEqual(valid, ["+01:00", "+00:00"])

    def test_edges_of_python_datetime(self):
        self.assertEqual(server._candidate_offsets("0001-01-01", "00:00:00", get_zone("Asia/Kolkata")), ([], "+00:00"))

    def test_offset_text(self):
        from datetime import timedelta
        self.assertEqual(server._offset_text(timedelta(hours=5, minutes=30)), "+05:30")
        self.assertEqual(server._offset_text(timedelta(hours=-3, minutes=-30)), "-03:30")
        self.assertEqual(server._offset_text(timedelta(hours=5, minutes=53, seconds=28)), "+05:53:28")


@requires_data
class ThroughEngine(unittest.TestCase):
    def test_unique_offset_matches_engine_directly(self):
        status, body = post({"place_id": "in-mumbai", "birth_date": "1990-05-15", "birth_time": "10:30"})
        self.assertEqual(status, 200)
        self.assertEqual(body["input"]["utc_offset"], "+05:30")
        self.assertEqual(body["input"]["offset_resolution"], "unique")
        self.assertEqual(body["chart"]["birth"]["utc"], "1990-05-15T05:00:00Z")

    def test_gap_refused_by_engine(self):
        status, body = post({"place_id": "gb-london", "birth_date": "2020-03-29", "birth_time": "01:30"})
        self.assertEqual((status, body["error"]["code"]), (422, "TIME_NONEXISTENT_LOCAL"))

    def test_gap_refused_whatever_offset_the_engine_is_given(self):
        for offset in ("+00:00", "+01:00", "-01:00", "+05:30"):
            with self.subTest(offset):
                with self.assertRaises(Exception) as ctx:
                    calculate({"birth_datetime": "2020-03-29T01:30:00" + offset, "timezone": "Europe/London",
                               "latitude": 51.50853, "longitude": -0.12574}, ephe_path=EPHE)
                self.assertEqual(ctx.exception.code, "TIME_NONEXISTENT_LOCAL")

    def test_fold_asks_instead_of_guessing(self):
        status, body = post({"place_id": "gb-london", "birth_date": "2020-10-25", "birth_time": "01:30"})
        self.assertEqual(status, 409)
        err = body["error"]
        self.assertEqual(err["code"], "TIME_AMBIGUOUS_LOCAL")
        self.assertEqual([c["utc_offset"] for c in err["choices"]], ["+01:00", "+00:00"])
        self.assertNotIn("chart", body)

    def test_fold_choice_gives_each_instant(self):
        utcs = []
        for offset in ("+01:00", "+00:00"):
            status, body = post({"place_id": "gb-london", "birth_date": "2020-10-25", "birth_time": "01:30",
                                 "utc_offset": offset})
            self.assertEqual(status, 200)
            self.assertEqual(body["input"]["offset_resolution"], "user_selected_repeated_hour")
            utcs.append(body["chart"]["birth"]["utc"])
        self.assertEqual(utcs, ["2020-10-25T00:30:00Z", "2020-10-25T01:30:00Z"])

    def test_offset_only_for_a_repeated_hour(self):
        for body in ({"place_id": "in-mumbai", "birth_date": "1990-05-15", "birth_time": "10:30", "utc_offset": "+05:30"},
                     {"place_id": "gb-london", "birth_date": "2020-10-25", "birth_time": "01:30", "utc_offset": "+02:00"},
                     {"place_id": "gb-london", "birth_date": "2020-03-29", "birth_time": "01:30", "utc_offset": "+00:00"}):
            with self.subTest(body):
                status, out = post(body)
                self.assertEqual((status, out["error"]["code"]), (422, "UTC_OFFSET_NOT_APPLICABLE"))

    def test_engine_refusal_order_kept_for_a_pre_1970_fold(self):
        # 1960-10-02 02:30 occurred twice in London (summer time ended at 03:00).
        # The engine's historical-clock refusal is returned; the user is not asked.
        valid, _ = server._candidate_offsets("1960-10-02", "02:30:00", get_zone("Europe/London"))
        self.assertEqual(len(valid), 2)
        status, body = post({"place_id": "gb-london", "birth_date": "1960-10-02", "birth_time": "02:30"})
        self.assertEqual((status, body["error"]["code"]), (422, "HISTORICAL_CLOCK_UNVERIFIED"))

    def test_unsupported_dates_and_latitudes(self):
        cases = [({"place_id": "in-mumbai", "birth_date": "1969-12-31", "birth_time": "23:59:59"}, "HISTORICAL_CLOCK_UNVERIFIED"),
                 ({"place_id": "in-mumbai", "birth_date": "1899-12-31", "birth_time": "12:00"}, "DATE_OUTSIDE_SUPPORTED_RANGE"),
                 ({"place_id": "in-mumbai", "birth_date": "2101-01-01", "birth_time": "00:00"}, "DATE_OUTSIDE_SUPPORTED_RANGE"),
                 ({"place_id": "in-mumbai", "birth_date": "0001-01-01", "birth_time": "00:00"}, "DATE_OUTSIDE_SUPPORTED_RANGE"),
                 ({"place_id": "in-mumbai", "birth_date": "9999-12-31", "birth_time": "23:59"}, "DATE_OUTSIDE_SUPPORTED_RANGE"),
                 ({"place_id": "no-tromso", "birth_date": "1990-05-15", "birth_time": "10:30"}, "LATITUDE_OUTSIDE_SUPPORTED_BAND")]
        for body, code in cases:
            with self.subTest(code=code, body=body):
                status, out = post(body)
                self.assertEqual((status, out["error"]["code"]), (422, code))
                self.assertEqual(out["error"]["category"], "unsupported")

    def test_first_supported_instant(self):
        status, body = post({"place_id": "in-kolkata", "birth_date": "1970-01-01", "birth_time": "00:00"})
        self.assertEqual(status, 200)
        self.assertEqual(body["chart"]["birth"]["utc"], "1969-12-31T18:30:00Z")


if __name__ == "__main__":
    unittest.main()
