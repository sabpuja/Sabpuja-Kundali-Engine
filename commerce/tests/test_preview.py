"""KUN-FREEMIUM-PREVIEW-001 (issue #91): free preview, paid hand-off, funnel and optional opt-in.

Synthetic birth records only. Engine-backed classes need SABPUJA_TEST_EPHE_PATH (pinned .se1 files).
"""
from __future__ import annotations

import contextlib
from datetime import date, datetime, timedelta, timezone
import io
import json
import re
import sqlite3
import threading
import unittest
from pathlib import Path

import helpers as h
from sabpuja_commerce import app as app_mod, funnel as funnel_mod, leads as leads_mod, mailer, preview as pv
from sabpuja_commerce.config import ConfigError
from sabpuja_commerce.store import Store

needs_data = unittest.skipUnless(h.EPHE, "set SABPUJA_TEST_EPHE_PATH to run engine-backed tests")
ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "commerce" / "sabpuja_commerce" / "static"
TODAY = date(2026, 11, 10)
OK = {"place_id": "in-jaipur", "birth_date": "1990-05-17", "birth_time": "14:30:00"}
CITIES = ("in-new-delhi", "in-mumbai", "in-kolkata", "in-chennai", "in-bengaluru", "in-hyderabad", "in-jaipur",
          "in-lucknow", "in-varanasi", "in-guwahati")
# Words that would mean more than the whitelisted preview left the server.
LEAK_WORDS = ("longitude", "degree", "navamsa", "house", "nakshatra", "pada", "d9", "planets", "sun", "mars",
              "mercury", "jupiter", "venus", "saturn", "rahu", "ketu", "tithi", "vara", "sunrise", "utc", "latitude",
              "chart", "calculation_metadata", "%pdf")


def _places():
    from kundali_prototype.places import load_places
    return {k: v for k, v in load_places().items() if k.startswith("in-")}


class PreviewHarness(h.Harness):
    """The real App with the preview, a real Funnel and a real LeadStore (all in memory)."""

    def __init__(self, service=None, leads=True, **kw):
        base = dict(preview_enabled=True, lead_capture_enabled=leads, leads_db_path=":memory:" if leads else "")
        base.update(kw)
        super().__init__(**base)
        self.funnel = funnel_mod.Funnel(":memory:", clock=self.clock)
        self.leads = leads_mod.LeadStore(":memory:", self.s.pepper, clock=self.clock) if leads else None
        self.app = app_mod.App(self.s, self.store, self.mail, self.render, {"in-jaipur": {}}, async_mail=False,
                               preview=service, funnel=self.funnel, leads=self.leads)

    def preview(self, payload=None, raw=None, peer="203.0.113.5", **kw):
        return self.post("/api/preview", OK if payload is None else payload, raw=raw, peer=peer, **kw)


class FakeService:
    """Stands in for the engine where only the HTTP contract is tested."""

    fields = ("lagna_rashi", "moon_rashi")

    def __init__(self, result=None, exc=None, hold=None):
        self.calls, self.result, self.exc, self.hold = 0, result, exc, hold

    def _today(self):
        return TODAY

    def __call__(self, form):
        self.calls += 1
        if self.hold is not None:
            self.hold.wait(5)
        if self.exc is not None:
            raise self.exc
        return self.result or {"preview_version": pv.PREVIEW_VERSION,
                               "fields": {"lagna_rashi": {"rashi": "Kanya", "number": 6, "western": "Virgo"},
                                          "moon_rashi": {"rashi": "Makara", "number": 10, "western": "Capricorn"}},
                               "birth_time_sensitive": False, "method": "sidereal_lahiri_swiss_ephemeris"}


def independent_signs(place: dict, local_date: str, local_time: str) -> tuple[str, str]:
    """Lagna and Moon Rashi straight from the pinned Swiss binding (SCI-01e definition), not through the engine."""
    import swisseph as swe
    swe.set_ephe_path(h.EPHE)
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    local = datetime.fromisoformat(f"{local_date}T{local_time}+05:30")
    u = local.astimezone(timezone.utc)
    jd = swe.julday(u.year, u.month, u.day, u.hour + u.minute / 60 + u.second / 3600, swe.GREG_CAL)
    moon, flags = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    assert flags & swe.FLG_SWIEPH
    _, ascmc = swe.houses_ex(jd, place["latitude"], place["longitude"], b"W", swe.FLG_SIDEREAL)
    return pv.RASHIS[int(ascmc[0] // 30) % 12], pv.RASHIS[int(moon[0] // 30) % 12]


# ---------------------------------------------------------------------------------------------------------------
@needs_data
class VerifiedFields(unittest.TestCase):
    """The two published fields equal the engine and an independent Swiss computation; nothing else leaves."""

    @classmethod
    def setUpClass(cls):
        cls.places = _places()
        cls.service = pv.PreviewService(cls.places, h.EPHE, today=lambda: TODAY)

    def test_matrix_all_ten_cities_matches_engine_and_independent_swiss(self):
        from kundali_prototype import server
        times = ("00:00:00", "05:47:13", "11:59:59", "18:20:00", "23:59:59")
        dates = ("1970-01-02", "1984-10-31", "1999-12-31", "2012-02-29", "2026-11-09")
        n = 0
        for i, pid in enumerate(CITIES):
            for j in range(3):
                form = {"place_id": pid, "birth_date": dates[(i + j) % 5], "birth_time": times[(i * 2 + j) % 5]}
                with self.subTest(form=form):
                    out = self.service(form)
                    chart = server.compute(form, self.places, h.EPHE)["chart"]
                    self.assertEqual(out["fields"]["lagna_rashi"]["rashi"], chart["lagna"]["rashi"])
                    self.assertEqual(out["fields"]["moon_rashi"]["rashi"], chart["planets"]["moon"]["rashi"])
                    lagna, moon = independent_signs(self.places[pid], form["birth_date"], form["birth_time"])
                    self.assertEqual((out["fields"]["lagna_rashi"]["rashi"], out["fields"]["moon_rashi"]["rashi"]),
                                     (lagna, moon))
                    n += 1
        self.assertEqual(n, 30)

    def test_exact_response_shape(self):
        out = self.service(dict(OK))
        self.assertEqual(set(out), {"preview_version", "fields", "birth_time_sensitive", "method"})
        self.assertEqual(set(out["fields"]), {"lagna_rashi", "moon_rashi"})
        for f in out["fields"].values():
            self.assertEqual(set(f), {"rashi", "number", "western"})
            self.assertEqual(pv.RASHIS[f["number"] - 1], f["rashi"])
        self.assertIsInstance(out["birth_time_sensitive"], bool)

    def test_no_paid_content_or_bulk_payload_leaks(self):
        text = json.dumps(self.service(dict(OK))).lower()
        for word in LEAK_WORDS:
            self.assertNotIn(word, text.replace("lagna_rashi", "").replace("moon_rashi", ""), word)
        self.assertNotRegex(text, r"[0-9]+\.[0-9]+")          # no fractional values of any kind
        self.assertLess(len(text), 400)

    def test_vara_is_withheld_and_cannot_be_configured(self):
        self.assertEqual(pv.FIELD_REGISTRY["vara"]["status"], "withheld")
        self.assertNotIn("vara", pv.ENABLED_FIELDS)
        with self.assertRaises(ValueError):
            pv.PreviewService(self.places, h.EPHE, fields=("vara",))
        with self.assertRaises(ValueError):
            pv.PreviewService(self.places, h.EPHE, fields=("lagna_rashi", "moon_nakshatra"))
        with self.assertRaises(ConfigError):
            h.settings(preview_enabled=True, preview_fields=("lagna_rashi", "vara"))

    def test_field_subset(self):
        out = pv.PreviewService(self.places, h.EPHE, fields=("moon_rashi",), today=lambda: TODAY)(dict(OK))
        self.assertEqual(set(out["fields"]), {"moon_rashi"})

    def _lagna_change(self, pid="in-mumbai", day="1995-03-21"):
        """The first minute of the day at which the Lagna Rashi changes (found with the independent path)."""
        prev = independent_signs(self.places[pid], day, "06:00:00")[0]
        for minute in range(361, 1440):
            t = f"{minute // 60:02d}:{minute % 60:02d}:00"
            cur = independent_signs(self.places[pid], day, t)[0]
            if cur != prev:
                return minute
        self.fail("no Lagna change found")

    def test_sensitivity_note_near_lagna_boundary(self):
        minute = self._lagna_change()
        near = f"{(minute - 1) // 60:02d}:{(minute - 1) % 60:02d}:00"
        out = self.service({"place_id": "in-mumbai", "birth_date": "1995-03-21", "birth_time": near})
        self.assertTrue(out["birth_time_sensitive"])

    def test_no_sensitivity_note_far_from_boundaries(self):
        minute = self._lagna_change()
        far = minute + 40
        out = self.service({"place_id": "in-mumbai", "birth_date": "1995-03-21",
                            "birth_time": f"{far // 60:02d}:{far % 60:02d}:00"})
        self.assertFalse(out["birth_time_sensitive"])

    def test_first_supported_minute_is_flagged_not_refused(self):
        out = self.service({"place_id": "in-new-delhi", "birth_date": "1970-01-01", "birth_time": "00:00:30"})
        self.assertTrue(out["birth_time_sensitive"])         # 1969-12-31 23:58:30 cannot be confirmed
        self.assertEqual(set(out["fields"]), {"lagna_rashi", "moon_rashi"})

    def test_rashi_tables_match_engine_and_report_register(self):
        from sabpuja_kundali.rules import SIGNS
        self.assertEqual(tuple(SIGNS), pv.RASHIS)
        from report.phase1.report_locale import TERMS
        self.assertEqual(tuple(TERMS["rashi"][r]["western"] for r in pv.RASHIS), pv.WESTERN)


# ---------------------------------------------------------------------------------------------------------------
@needs_data
class Refusals(unittest.TestCase):
    """Unsupported places, historical dates and malformed times are refused with the engine's own codes."""

    @classmethod
    def setUpClass(cls):
        cls.places = _places()
        cls.service = pv.PreviewService(cls.places, h.EPHE, today=lambda: TODAY)

    def setUp(self):
        self.h = PreviewHarness(service=self.service, preview_rate_per_minute=1000, preview_rate_per_hour=1000,
                                preview_global_per_minute=1000)

    def refused(self, status, code, **change):
        resp = self.h.preview(dict(OK, **change))
        self.assertEqual(resp.status, status, resp.body)
        self.assertEqual(resp.json()["error"]["code"], code)
        self.assertNotIn("fields", resp.json())
        return resp

    def test_unsupported_and_foreign_places(self):
        for pid in ("gb-london", "no-tromso", "in-pune", "in-jaipur ", "Jaipur", "", "in-JAIPUR", "xx-atlantis"):
            with self.subTest(pid=pid):
                self.refused(422, "PLACE_UNKNOWN", place_id=pid)

    def test_historical_dates_refused(self):
        for day in ("1969-12-31", "1947-08-15", "1900-01-01"):
            with self.subTest(day=day):
                self.refused(422, "HISTORICAL_CLOCK_UNVERIFIED", birth_date=day)

    def test_dates_outside_engine_range(self):
        for day in ("1850-06-01", "1799-12-31"):
            with self.subTest(day=day):
                resp = self.h.preview(dict(OK, birth_date=day))
                self.assertEqual(resp.status, 422)
                self.assertIn(resp.json()["error"]["code"], ("DATE_OUTSIDE_SUPPORTED_RANGE", "HISTORICAL_CLOCK_UNVERIFIED"))

    def test_future_dates_refused(self):
        for day in ("2026-11-11", "2030-01-01", "2100-12-31"):
            with self.subTest(day=day):
                self.refused(422, "BIRTH_DATE_FUTURE", birth_date=day)

    def test_today_is_accepted(self):
        self.assertEqual(self.h.preview(dict(OK, birth_date="2026-11-10", birth_time="00:10:00")).status, 200)

    def test_invalid_dates(self):
        for day in ("2023-02-29", "1990-13-01", "17/05/1990", "1990-5-17", "１９９０-05-17", "1990-05-17T00:00"):
            with self.subTest(day=day):
                self.refused(422, "BIRTH_DATE_INVALID", birth_date=day)

    def test_missing_or_invalid_times(self):
        self.refused(422, "BIRTH_TIME_REQUIRED", birth_time="")
        for t in ("25:00", "14:60", "14:30:60", "2pm", "14.30", "1430", " 14:30"):
            with self.subTest(t=t):
                self.refused(422, "BIRTH_TIME_INVALID", birth_time=t)

    def test_offset_only_for_repeated_hours(self):
        self.refused(422, "UTC_OFFSET_NOT_APPLICABLE", utc_offset="+05:30")
        self.refused(400, "UTC_OFFSET_INVALID", utc_offset="IST")

    def test_refusals_counted_in_aggregate_only(self):
        self.refused(422, "PLACE_UNKNOWN", place_id="gb-london")
        totals = self.h.funnel.totals()
        self.assertEqual((totals["preview_initiated"], totals["preview_refused"], totals["preview_generated"]),
                         (1, 1, 0))


# ---------------------------------------------------------------------------------------------------------------
class AbuseAndShape(unittest.TestCase):
    def setUp(self):
        self.service = FakeService()
        self.h = PreviewHarness(service=self.service)

    def code(self, resp):
        return resp.status, resp.json()["error"]["code"]

    def test_valid_request_contract(self):
        resp = self.h.preview()
        self.assertEqual(resp.status, 200)
        self.assertEqual(self.service.calls, 1)

    def test_malformed_bodies(self):
        for raw in (b"not json", b"[]", b'"x"', b"null", b"\xff\xfe", b'{"place_id": "in-jaipur"',
                    b"[" * 5000 + b"]" * 5000):
            with self.subTest(raw=raw[:20]):
                self.h.clock.advance(61)
                status, code = self.code(self.h.preview(raw=raw))
                self.assertIn(status, (400, 413))
        self.assertEqual(self.service.calls, 0)

    def test_duplicate_keys(self):
        raw = b'{"place_id":"in-jaipur","place_id":"in-mumbai","birth_date":"1990-05-17","birth_time":"14:30"}'
        self.assertEqual(self.code(self.h.preview(raw=raw)), (400, "REQUEST_INVALID"))

    def test_extra_fields_refused_including_name(self):
        for extra in ({"display_name": "Synthetic"}, {"email": "a@example.invalid"}, {"report_locale": "en"},
                      {"edition": "janam-kundali-essentials-en/1"}, {"full": True}, {"panchanga_names": "on"},
                      {"fields": ["vara"]}):
            with self.subTest(extra=extra):
                self.h.clock.advance(61)                      # malformed requests count against the limit too
                self.assertEqual(self.code(self.h.preview(dict(OK, **extra))), (400, "REQUEST_INVALID"))
        self.assertEqual(self.service.calls, 0)

    def test_missing_fields_and_non_strings(self):
        for body in ({"place_id": "in-jaipur", "birth_date": "1990-05-17"}, {},
                     dict(OK, birth_time=1430), dict(OK, birth_date=None), dict(OK, place_id=["in-jaipur"]),
                     dict(OK, place_id={"id": "in-jaipur"}), dict(OK, birth_time="1" * 65)):
            with self.subTest(body=body):
                self.h.clock.advance(61)
                self.assertEqual(self.code(self.h.preview(body)), (400, "REQUEST_INVALID"))

    def test_oversized_body(self):
        raw = json.dumps(dict(OK, birth_time="14:30" + " " * 600)).encode()
        self.assertEqual(self.code(self.h.preview(raw=raw)), (413, "BODY_TOO_LARGE"))

    def test_origin_and_content_type(self):
        self.assertEqual(self.code(self.h.preview(origin="https://evil.invalid")), (403, "ORIGIN_REJECTED"))
        resp = self.h.app.handle("POST", "/api/preview", {"Origin": h.ORIGIN, "Content-Type": "text/plain"},
                                 json.dumps(OK).encode(), "203.0.113.5")
        self.assertEqual(resp.status, 415)
        self.assertEqual(self.h.get("/api/preview").status, 404)

    def test_per_client_minute_limit(self):
        for _ in range(6):
            self.assertEqual(self.h.preview().status, 200)
        self.assertEqual(self.code(self.h.preview()), (429, "PREVIEW_RATE_LIMITED"))
        self.assertEqual(self.h.preview(peer="203.0.113.99").status, 200)   # another client is unaffected
        self.h.clock.advance(61)
        self.assertEqual(self.h.preview().status, 200)

    def test_per_client_hour_limit(self):
        hits = 0
        for _ in range(60):
            if self.h.preview().status == 200:
                hits += 1
            self.h.clock.advance(61)
        self.assertEqual(hits, 40)

    def test_global_limit_across_clients(self):
        hp = PreviewHarness(service=FakeService(), preview_global_per_minute=5)
        statuses = [hp.preview(peer=f"198.51.100.{i}").status for i in range(8)]
        self.assertEqual(statuses.count(200), 5)
        self.assertEqual(statuses.count(429), 3)

    def test_concurrency_slot_busy(self):
        gate = threading.Event()
        hp = PreviewHarness(service=FakeService(hold=gate), max_concurrent_previews=1)
        first = threading.Thread(target=hp.preview, kwargs={"peer": "198.51.100.1"})
        first.start()
        for _ in range(100):
            if hp.app.preview.calls:
                break
            threading.Event().wait(0.01)
        second = hp.preview(peer="198.51.100.2")
        gate.set()
        first.join()
        self.assertEqual((second.status, second.json()["error"]["code"]), (429, "PREVIEW_BUSY"))

    def test_rate_limit_spoofed_forwarded_for_from_untrusted_peer(self):
        for i in range(6):
            self.h.post("/api/preview", OK, peer="203.0.113.5")
        headers = {"Origin": h.ORIGIN, "Content-Type": "application/json", "X-Forwarded-For": "10.9.9.9"}
        resp = self.h.app.handle("POST", "/api/preview", headers, json.dumps(OK).encode(), "203.0.113.5")
        self.assertEqual(resp.status, 429)

    def test_server_fault_is_503_without_input_in_logs(self):
        hp = PreviewHarness(service=FakeService(exc=RuntimeError("1990-05-17 in-jaipur 14:30")))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            resp = hp.preview()
        self.assertEqual((resp.status, resp.json()["error"]["code"]), (503, "PREVIEW_UNAVAILABLE"))
        for value in OK.values():
            self.assertNotIn(value, err.getvalue())
            self.assertNotIn(value.encode(), resp.body)

    def test_preview_unavailable_maps_to_503(self):
        hp = PreviewHarness(service=FakeService(exc=pv.PreviewUnavailable(503, "EPHEMERIS_FILE_MISSING")))
        self.assertEqual(hp.preview().status, 503)


# ---------------------------------------------------------------------------------------------------------------
class Isolation(unittest.TestCase):
    """The preview never touches entitlements, sessions, the renderer or storage."""

    def setUp(self):
        self.h = PreviewHarness(service=FakeService())

    def test_no_cookie_no_session_no_render(self):
        resp = self.h.preview()
        self.assertNotIn("Set-Cookie", dict(resp.headers))
        self.assertEqual(self.h.post("/api/generate", OK).status, 401)
        self.assertEqual(self.h.get("/api/session").status, 401)
        self.assertEqual(self.h.render.calls, 0)

    def test_preview_does_not_touch_a_paid_order(self):
        self.h.paid()
        cookie = self.h.login()
        before = self.h.get("/api/session", cookie=cookie).json()
        self.assertEqual(self.h.preview().status, 200)
        self.assertEqual(self.h.get("/api/session", cookie=cookie).json(), before)
        self.assertEqual(self.h.render.calls, 0)

    def test_paid_route_unchanged_by_preview_fields(self):
        self.h.paid()
        cookie = self.h.login()
        # The preview's whitelist is not a way into the paid route: a "preview" key is refused there.
        resp = self.h.post("/api/generate", dict(h.BIRTH, preview_version=pv.PREVIEW_VERSION), cookie=cookie)
        self.assertEqual(resp.status, 400)

    def test_nothing_persisted(self):
        for _ in range(3):
            self.h.preview()
        dump = "\n".join(self.h.store._db.iterdump())
        for value in ("1990-05-17", "14:30", "in-jaipur", "Kanya", "Makara"):
            self.assertNotIn(value, dump)
        self.assertNotIn("1990", "\n".join(self.h.leads._db.iterdump()))
        self.assertNotIn("1990", "\n".join(self.h.funnel._db.iterdump()))

    def test_disabled_by_default(self):
        hd = h.Harness()
        app = app_mod.App(hd.s, hd.store, hd.mail, hd.render, {}, async_mail=False, preview=FakeService(),
                          funnel=funnel_mod.Funnel(), leads=leads_mod.LeadStore(":memory:", hd.s.pepper))
        hd.app = app
        self.assertFalse(hd.s.preview_enabled)
        for path in ("/kundali", "/static/preview.js", "/api/preview/config", "/marketing"):
            self.assertEqual(hd.get(path).status, 404, path)
        self.assertEqual(hd.post("/api/preview", OK).status, 404)
        self.assertEqual(hd.post("/api/funnel", {"event": "checkout_started"}).status, 404)
        self.assertEqual(hd.post("/api/leads/subscribe", {}).status, 404)

    def test_pages_served_with_strict_headers_and_no_third_parties(self):
        resp = self.h.get("/kundali")
        self.assertEqual(resp.status, 200)
        html = resp.body.decode()
        self.assertNotIn("{{SOURCE_URL}}", html)
        self.assertEqual(re.findall(r'(?:src|href)="(https?:[^"]+)"', html), [self.h.s.source_url])
        for tracker in ("gtag", "googletagmanager", "facebook", "fbq", "pixel", "analytics.js", "hotjar",
                        "localStorage", "sessionStorage", "document.cookie"):
            self.assertNotIn(tracker, html)
            self.assertNotIn(tracker, (STATIC / "preview.js").read_text())
        from sabpuja_commerce.app import SECURITY_HEADERS
        self.assertIn("connect-src 'self'", SECURITY_HEADERS["Content-Security-Policy"])
        self.assertEqual(self.h.get("/static/preview.css").status, 200)

    def test_name_never_sent_from_page(self):
        js = (STATIC / "preview.js").read_text()
        body = re.search(r'return \{ place_id: [^}]+\}', js).group(0)
        self.assertNotIn("display_name", body)


# ---------------------------------------------------------------------------------------------------------------
class ConfigAndHandoff(unittest.TestCase):
    def test_config_endpoint(self):
        hp = PreviewHarness(service=FakeService())
        cfg = hp.get("/api/preview/config").json()
        self.assertEqual(cfg["fields"], ["lagna_rashi", "moon_rashi"])
        self.assertIsNone(cfg["price_display"])                  # owner price not set: placeholder on the page
        self.assertEqual(cfg["buy_url"], f"https://{h.SHOP}/cart/{h.PRODUCT.variant_id}:1")
        self.assertEqual((cfg["date_min"], cfg["date_max"]), ("1970-01-01", "2026-11-10"))
        self.assertTrue(cfg["lead_capture"])
        self.assertEqual(cfg["consent_version"], leads_mod.CONSENT_VERSION)
        self.assertEqual((cfg["report_pages"], cfg["report_language"]), (14, "en"))

    def test_price_set_by_owner_config(self):
        hp = PreviewHarness(service=FakeService(), preview_price_display="₹ 000 (placeholder)")
        self.assertEqual(hp.get("/api/preview/config").json()["price_display"], "₹ 000 (placeholder)")

    def test_buy_url_rules(self):
        h.settings(preview_buy_url=f"https://{h.SHOP}/products/janam-kundali-essentials")
        for bad in ("https://evil.invalid/cart/1:1", f"https://{h.SHOP}/cart/1:1?attributes[dob]=1990",
                    f"http://{h.SHOP}/cart/1:1", f"https://{h.SHOP}/cart/1:1#x", f"https://{h.SHOP}.evil.invalid/cart/1:1"):
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                h.settings(preview_buy_url=bad)

    def test_price_text_rules(self):
        for bad in ("<b>₹99</b>", "x" * 41, "₹99\n", '"99"'):
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                h.settings(preview_price_display=bad)

    def test_lead_capture_needs_preview_and_its_own_database(self):
        with self.assertRaises(ConfigError):
            h.settings(lead_capture_enabled=True, leads_db_path="/tmp/l.sqlite")             # no preview
        with self.assertRaises(ConfigError):
            h.settings(preview_enabled=True, lead_capture_enabled=True, leads_db_path="")
        with self.assertRaises(ConfigError):
            h.settings(preview_enabled=True, lead_capture_enabled=True, db_path="/tmp/e.sqlite",
                       leads_db_path="/tmp/e.sqlite")
        with self.assertRaises(ConfigError):
            h.settings(funnel_db_path="/tmp/e.sqlite", db_path="/tmp/e.sqlite")

    def test_checkout_link_carries_no_birth_detail(self):
        url = h.settings().buy_url
        self.assertRegex(url, r"^https://[a-z0-9.-]+/cart/[0-9]+:1$")
        html = (STATIC / "preview.html").read_text()
        self.assertIn("After payment you will enter your birth details again", html)
        self.assertIn('id="checkout"', html)

    def test_eligibility_copy_matches_places(self):
        from kundali_prototype.places import load_places
        names = [v["name"] for k, v in load_places().items() if k.startswith("in-")]
        html = (STATIC / "preview.html").read_text()
        listed = re.search(r'<span id="elig-cities">(.*?)</span>', html, re.S).group(1)
        listed = re.sub(r"\s+", " ", listed).replace(" or ", ", ").split(", ")
        self.assertEqual(listed, names)
        self.assertIn("1 January 1970", html)
        self.assertIn("never guess a time", html)
        self.assertLess(html.index('id="h-elig"'), html.index('id="preview-form"'))   # limits before input

    def test_gateway_limits_preview_routes(self):
        conf = (ROOT / "commerce/deploy/gateway.nginx.conf").read_text()
        for line in ("location = /api/preview", "zone=preview", "location = /api/funnel", "location ^~ /api/leads/"):
            self.assertIn(line, conf)


# ---------------------------------------------------------------------------------------------------------------
class FunnelCounts(unittest.TestCase):
    def setUp(self):
        self.h = PreviewHarness(service=FakeService())

    def test_server_events(self):
        self.h.preview()
        self.h.preview(raw=b"junk")                                  # shape error: not initiated
        t = self.h.funnel.totals()
        self.assertEqual((t["preview_initiated"], t["preview_generated"]), (1, 1))

    def test_browser_events_only_whitelisted(self):
        for ev in ("full_report_selected", "checkout_started"):
            self.assertEqual(self.h.post("/api/funnel", {"event": ev}).status, 204)
        for body in ({"event": "preview_generated"}, {"event": "paid_order_completed"}, {"event": "x"},
                     {"event": "checkout_started", "email": "a@example.invalid"}, {"event": "checkout_started",
                                                                                   "birth_date": "1990-05-17"}):
            with self.subTest(body=body):
                self.assertEqual(self.h.post("/api/funnel", body).status, 400)
        t = self.h.funnel.totals()
        self.assertEqual((t["full_report_selected"], t["checkout_started"], t["paid_order_completed"]), (1, 1, 0))

    def test_beacon_flood_is_capped(self):
        for _ in range(50):
            self.h.post("/api/funnel", {"event": "checkout_started"})
        self.assertEqual(self.h.funnel.totals()["checkout_started"], 20)

    def test_paid_order_webhook_counted_once(self):
        self.h.hook("orders/paid", h.order(), webhook_id="dup-1")
        self.h.hook("orders/paid", h.order(), webhook_id="dup-1")
        self.h.hook("orders/paid", h.order(order_id=5002, number=1002, status="pending"))
        self.assertEqual(self.h.funnel.totals()["paid_order_completed"], 1)

    def test_daily_aggregate_has_no_identifiers(self):
        self.h.preview()
        cols = [r[1] for r in self.h.funnel._db.execute("PRAGMA table_info(funnel_daily)")]
        self.assertEqual(cols, ["day", "event", "count"])
        self.assertEqual({r["day"] for r in self.h.funnel.report()}, {"2027-01-15"})   # day granularity only
        with self.assertRaises(ValueError):
            self.h.funnel.count("visitor_ip")

    def test_null_funnel_when_not_configured(self):
        hp = PreviewHarness(service=FakeService())
        hp.app.funnel = funnel_mod.NullFunnel()
        self.assertEqual(hp.preview().status, 200)
        self.assertEqual(hp.app.funnel.report(), [])


# ---------------------------------------------------------------------------------------------------------------
class LeadConsent(unittest.TestCase):
    EMAIL = "synthetic.lead@example.invalid"

    def setUp(self):
        self.h = PreviewHarness(service=FakeService())

    def sub(self, **change):
        body = {"email": self.EMAIL, "marketing_consent": True, "adult": True,
                "consent_version": leads_mod.CONSENT_VERSION, "locale": "en"}
        body.update(change)
        for k in [k for k, v in body.items() if v is ...]:
            del body[k]
        return self.h.post("/api/leads/subscribe", body)

    def token(self, kind="confirm"):
        return re.search(rf"#{kind}=([A-Za-z0-9_-]+)", self.h.mail.sent[-1].get_content()).group(1)

    def test_preview_never_requires_consent(self):
        self.assertEqual(self.h.preview().status, 200)
        self.assertEqual(self.h.leads.counts(), {"pending": 0, "subscribed": 0, "withdrawn": 0})
        self.assertEqual(len(self.h.mail.sent), 0)

    def test_consent_must_be_explicit_true(self):
        for value in (False, "true", 1, None, ...):
            with self.subTest(value=value):
                resp = self.sub(marketing_consent=value)
                self.assertEqual(resp.status, 400)
        self.assertEqual(self.h.leads.counts()["pending"], 0)

    def test_adult_confirmation_required(self):
        for value in (False, "yes", ...):
            with self.subTest(value=value):
                self.assertEqual(self.sub(adult=value).status, 400)

    def test_consent_version_must_match_shown_wording(self):
        self.assertEqual(self.sub(consent_version="old").status, 409)

    def test_invalid_email_and_extra_fields(self):
        for email in ("", "no-at", "a@b@c", "x" * 300 + "@example.invalid"):
            with self.subTest(email=email):
                self.assertEqual(self.sub(email=email).status, 400)
        for extra in ({"birth_date": "1990-05-17"}, {"name": "Synthetic"}, {"lagna": "Kanya"}):
            with self.subTest(extra=extra):
                self.assertEqual(self.sub(**extra).status, 400)
        self.assertEqual(self.sub(locale="fr").status, 400)

    def test_double_opt_in_confirm_then_mailable(self):
        self.assertEqual(self.sub().status, 202)
        self.assertEqual(self.h.leads.mailable(), [])                 # nothing until confirmed
        mail = self.h.mail.sent[-1]
        self.assertEqual(mail["Subject"], leads_mod.CONFIRM_SUBJECT)
        text = mail.get_content()
        for value in ("1990", "Kanya", "Jaipur", "14:30"):
            self.assertNotIn(value, text)
        resp = self.h.post("/api/leads/confirm", {"token": self.token()})
        self.assertEqual(resp.json(), {"status": "subscribed"})
        self.assertEqual(self.h.leads.mailable(), [self.EMAIL])

    def test_reply_identical_for_new_existing_and_capped(self):
        bodies = {self.sub().body}
        self.h.post("/api/leads/confirm", {"token": self.token()})
        bodies.add(self.sub().body)
        self.assertEqual(len(bodies), 1)
        self.assertEqual(len(self.h.mail.sent), 1)                     # subscribed: no second mail

    def test_withdraw_stops_marketing_and_keeps_minimal_record(self):
        self.sub()
        tok = self.token()
        self.h.post("/api/leads/confirm", {"token": tok})
        self.assertEqual(self.h.post("/api/leads/withdraw", {"token": tok}).json(), {"status": "withdrawn"})
        self.assertEqual(self.h.leads.mailable(), [])
        self.assertEqual(self.h.leads.counts()["withdrawn"], 1)

    def test_delete_erases_row(self):
        self.sub()
        tok = self.token()
        self.assertEqual(self.h.post("/api/leads/delete", {"token": tok}).json(), {"status": "deleted"})
        self.assertEqual(self.h.leads.counts(), {"pending": 0, "subscribed": 0, "withdrawn": 0})
        self.assertNotIn(self.EMAIL, "\n".join(self.h.leads._db.iterdump()))
        self.assertEqual(self.h.post("/api/leads/delete", {"token": tok}).status, 404)

    def test_bad_and_expired_tokens(self):
        for tok in ("", "short", "x" * 43, "../../etc", 123):
            with self.subTest(tok=tok):
                self.assertIn(self.h.post("/api/leads/confirm", {"token": tok}).status, (400, 404))
        self.sub()
        tok = self.token()
        self.h.clock.advance(31 * 86400)
        self.assertEqual(self.h.post("/api/leads/status", {"token": tok}).status, 404)

    def test_unconfirmed_sign_up_purged_after_seven_days(self):
        self.sub()
        self.h.clock.advance(8 * 86400)
        self.assertEqual(self.h.leads.purge(), 1)
        self.assertNotIn(self.EMAIL, "\n".join(self.h.leads._db.iterdump()))

    def test_resubscribe_after_withdraw_needs_new_confirmation(self):
        self.sub()
        tok = self.token()
        self.h.post("/api/leads/confirm", {"token": tok})
        self.h.post("/api/leads/withdraw", {"token": tok})
        self.h.clock.advance(601)
        self.sub()
        self.assertEqual(self.h.leads.mailable(), [])
        self.h.post("/api/leads/confirm", {"token": self.token()})
        self.assertEqual(self.h.leads.mailable(), [self.EMAIL])

    def test_manage_link_and_mail_caps(self):
        self.sub()
        self.assertEqual(self.h.post("/api/leads/link", {"email": self.EMAIL}).status, 202)
        self.assertEqual(len(self.h.mail.sent), 1)                     # inside the 10-minute cooldown
        for _ in range(5):
            self.h.clock.advance(601)
            self.h.post("/api/leads/link", {"email": self.EMAIL})
        self.assertEqual(len(self.h.mail.sent), 3)                     # at most 3 per address per day
        self.assertEqual(self.h.post("/api/leads/link", {"email": "unknown@example.invalid"}).status, 202)

    def test_link_token_supersedes_old(self):
        self.sub()
        old = self.token()
        self.h.clock.advance(601)
        self.h.post("/api/leads/link", {"email": self.EMAIL})
        new = self.token("manage")
        self.assertEqual(self.h.post("/api/leads/status", {"token": old}).status, 404)
        self.assertEqual(self.h.post("/api/leads/status", {"token": new}).json(), {"status": "pending"})

    def test_schema_holds_no_birth_or_chart_columns(self):
        cols = {r[1] for r in self.h.leads._db.execute("PRAGMA table_info(leads)")}
        for forbidden in ("name", "birth_date", "birth_time", "place", "place_id", "lagna", "moon", "order_id",
                          "ip", "user_agent", "fingerprint"):
            self.assertNotIn(forbidden, cols)
        self.assertLessEqual(cols, {"id", "email", "email_hash", "status", "purpose", "consent_version", "source",
                                    "locale", "adult_confirmed", "created_at", "consented_at", "confirmed_at",
                                    "withdrawn_at", "token_hash", "token_expires_at", "mails_day", "mails_on_day",
                                    "last_mail_at"})

    def test_lead_store_is_not_the_entitlement_database(self):
        ent = {r[0] for r in self.h.store._db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("leads", ent)

    def test_lead_rate_limit(self):
        statuses = [self.sub(email=f"s{i}@example.invalid").status for i in range(12)]
        self.assertEqual(statuses.count(429), 2)

    def test_lead_capture_off_in_config(self):
        hp = PreviewHarness(service=FakeService(), leads=False)
        self.assertFalse(hp.get("/api/preview/config").json()["lead_capture"])
        self.assertEqual(hp.post("/api/leads/subscribe", {}).status, 404)
        self.assertEqual(hp.get("/marketing").status, 404)


if __name__ == "__main__":
    unittest.main()
