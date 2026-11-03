"""Server request validation for the birth form (no Swiss data needed).

Form refusals are raised before the engine is called, so these run with an
empty ephemeris path and never compute.
"""
import json
import unittest

from kundali_prototype import server
from kundali_prototype.places import load_places

PLACES = load_places()


def post(body):
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    return server.handle_chart(raw, PLACES, "")


def form(**over):
    body = {"place_id": "in-mumbai", "birth_date": "1990-05-15", "birth_time": "10:30"}
    body.update(over)
    return {k: v for k, v in body.items() if v is not None}


class RequestShape(unittest.TestCase):
    def assertCode(self, result, status, code):
        self.assertEqual(result[0], status, result)
        self.assertEqual(result[1]["error"]["code"], code)

    def test_not_json_or_not_utf8(self):
        for raw in (b"", b"{", b"[1,2]", b"\xff\xfe", b"null", b'"x"', b"NaN"):
            with self.subTest(raw):
                self.assertCode(post(raw), 400, "REQUEST_INVALID")

    def test_duplicate_keys_refused(self):
        raw = b'{"place_id":"in-mumbai","place_id":"in-chennai","birth_date":"1990-05-15","birth_time":"10:30"}'
        self.assertCode(post(raw), 400, "REQUEST_INVALID")

    def test_missing_and_extra_keys(self):
        for body in (form(place_id=None), form(birth_date=None), form(birth_time=None),
                     dict(form(), latitude=19.0), dict(form(), timezone="Asia/Kolkata"), dict(form(), longitude=72.8)):
            with self.subTest(body):
                self.assertCode(post(body), 400, "REQUEST_INVALID")

    def test_coordinates_and_zone_cannot_be_sent(self):
        # The browser may only name a place; it can never pair coordinates with a zone.
        body = dict(form(), latitude=0.0, longitude=0.0, timezone="Europe/London")
        self.assertCode(post(body), 400, "REQUEST_INVALID")

    def test_non_string_fields(self):
        for body in (form(birth_date=19900515), form(birth_time=10.5), form(place_id=["in-mumbai"]),
                     form(birth_time=True), dict(form(), utc_offset=5.5)):
            with self.subTest(body):
                self.assertCode(post(body), 400, "REQUEST_INVALID")

    def test_unknown_place(self):
        for pid in ("in-pune", "", "IN-MUMBAI", "../in-mumbai", "Mumbai"):
            with self.subTest(pid):
                self.assertCode(post(form(place_id=pid)), 422, "PLACE_UNKNOWN")


class BirthForm(unittest.TestCase):
    def assertCode(self, result, status, code):
        self.assertEqual(result[0], status, result)
        self.assertEqual(result[1]["error"]["code"], code)

    def test_date_format(self):
        for d in ("15-05-1990", "1990/05/15", "1990-5-15", "19900515", "1990-05-15T10:30", " 1990-05-15", "١٩٩٠-05-15"):
            with self.subTest(d):
                self.assertCode(post(form(birth_date=d)), 422, "BIRTH_DATE_INVALID")

    def test_nonexistent_dates(self):
        for d in ("2023-02-29", "1990-02-30", "1990-04-31", "1990-13-01", "1990-00-10", "0000-01-01"):
            with self.subTest(d):
                self.assertCode(post(form(birth_date=d)), 422, "BIRTH_DATE_INVALID")

    def test_unknown_time_is_never_assumed(self):
        result = post(form(birth_time=""))
        self.assertCode(result, 422, "BIRTH_TIME_REQUIRED")
        self.assertEqual(result[1]["error"]["category"], "unknown_time")

    def test_time_format_and_ranges(self):
        for t in ("24:00", "23:60", "23:59:60", "10:30:00.5", "10:30Z", "10:30+05:30", "1030", "10", "10:3",
                  "noon", " 10:30", "10:30 ", "-1:00"):
            with self.subTest(t):
                self.assertCode(post(form(birth_time=t)), 422, "BIRTH_TIME_INVALID")

    def test_utc_offset_format(self):
        for o in ("+5:30", "05:30", "+05:30Z", "IST", "", "+0530"):
            with self.subTest(o):
                self.assertCode(post(form(utc_offset=o)), 400, "UTC_OFFSET_INVALID")

    def test_errors_never_echo_input(self):
        marker = "1987-07-07"
        for body in (form(birth_date="1987-07-77"), form(birth_time="77:77"), form(place_id="secret-place")):
            text = json.dumps(post(body)[1])
            for value in body.values():
                if value not in ("in-mumbai",):
                    self.assertNotIn(value, text)
        self.assertNotIn(marker, json.dumps(post(form(birth_date="1987-07-77"))[1]))

    def test_parse_normalises_seconds(self):
        place, d, t, offset = server._parse_form(form(birth_time="07:05"), PLACES)
        self.assertEqual((d, t, offset), ("1990-05-15", "07:05:00", None))
        self.assertEqual(server._parse_form(form(birth_time="07:05:09"), PLACES)[2], "07:05:09")


if __name__ == "__main__":
    unittest.main()
