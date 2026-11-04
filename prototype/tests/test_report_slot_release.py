"""KUN-I18N-INT-001A: the PDF render slot is free before any /api/report response is written.

Independent QA (PR #71 review 5765253656) saw HTTP 429 REPORT_BUSY instead of the fixed
422/400 refusals for strictly sequential requests. The cause: the handler wrote its response
while still holding `_PDF_RENDER_SLOT` and released it afterwards, so a client that had
already read a complete response could send its next request before the server thread had
released the slot. Under CPU contention that window is wide enough to hit.

These tests make the window deterministic instead of relying on timing: they hold the
handler thread *after* its response has been written, with an event (no sleeps), and
require that the next sequential request is answered on its own merits. Positive controls
keep a genuinely concurrent render refused with 429. Synthetic data only; the chart engine
and the renderer are mocked, so nothing here depends on Swiss data, fonts or timing.
"""
import contextlib
import copy
import http.client
import io
import json
import threading
import unittest
from unittest import mock

from kundali_prototype import server

from test_premium_pdf_http import PRIMARY, SCENARIOS, Server, premium

CANARY = "Zzyzx Qwertyuiop"   # synthetic, never a real person
BODY = {"place_id": "in-new-delhi", "birth_date": "1990-05-15", "birth_time": "10:30"}
FAKE_PDF = b"%PDF-1.7 synthetic"


def with_(body, **extra):
    out = dict(body)
    out.update(extra)
    return out


def slot_is_free() -> bool:
    if server._PDF_RENDER_SLOT.acquire(blocking=False):
        server._PDF_RENDER_SLOT.release()
        return True
    return False


class SlotReleasedBeforeResponse(Server):
    """Every /api/report outcome is written only after the render slot is free again."""

    def setUp(self):
        self.assertTrue(slot_is_free(), "slot leaked from an earlier test")
        self.seen = []
        real_send, real_pdf = server.Handler._send, server.Handler._pdf
        test = self

        def send(handler, status, body, ctype):
            if handler.path == "/api/report":
                test.seen.append((status, slot_is_free()))
            return real_send(handler, status, body, ctype)

        def pdf(handler, body):
            test.seen.append((200, slot_is_free()))
            return real_pdf(handler, body)
        patches = [mock.patch.object(server.Handler, "_send", send), mock.patch.object(server.Handler, "_pdf", pdf),
                   mock.patch.object(server, "compute", return_value=copy.deepcopy(SCENARIOS[PRIMARY]))]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def outcome(self, body, generate=None, want=None, code=None):
        self.seen.clear()
        err = io.StringIO()
        gen = mock.patch.object(premium, "generate", **(generate or {"return_value": FAKE_PDF}))
        with gen, contextlib.redirect_stderr(err):
            status, headers, data = self.post("/api/report", body)
        self.assertEqual(status, want, data[:200])
        if code is not None:
            self.assertEqual(json.loads(data)["error"]["code"], code)
        self.assertEqual(self.seen, [(want, True)], "response written while the render slot was still held")
        self.assertTrue(slot_is_free())
        for leak in (CANARY, "1990-05-15", "10:30", "in-new-delhi"):
            self.assertNotIn(leak.encode(), data)
            self.assertNotIn(leak, err.getvalue())
        return data

    def test_pdf(self):
        self.assertEqual(self.outcome(BODY, want=200), FAKE_PDF)

    def test_invalid_name(self):
        self.outcome(with_(BODY, display_name="Asha & Ravi"), want=422, code="DISPLAY_NAME_INVALID")

    def test_unsupported_and_non_string_locale(self):
        self.outcome(with_(BODY, report_locale=CANARY), want=422, code="REPORT_LOCALE_UNSUPPORTED")
        self.outcome(with_(BODY, report_locale=7), want=400, code="REQUEST_INVALID")

    def test_malformed_json(self):
        # Not one UTF-8 JSON value (a non-object such as [] is refused inside compute(), which is
        # mocked here; test_premium_pdf_http.test_malformed_json covers it unmocked).
        for raw in (b"{", b"not json", b'{"place_id": "a", "place_id": "b"}', b"\xff\xfe"):
            with self.subTest(raw=raw):
                data = self.outcome(raw, want=400)
                self.assertFalse(data.startswith(b"%PDF"))

    def test_renderer_failure_then_recovery(self):
        self.outcome(with_(BODY, display_name=CANARY), generate={"side_effect": ValueError(CANARY)}, want=503,
                     code="REPORT_UNAVAILABLE")
        self.assertEqual(self.outcome(BODY, want=200), FAKE_PDF)


class SequentialRequestsWhileHandlerFinishes(Server):
    """Hold the previous handler thread after its response is on the wire; the next request must
    still get its own answer. Before the fix every follow-up here was 429 REPORT_BUSY."""

    def setUp(self):
        self.assertTrue(slot_is_free())
        self.hold = threading.Event()
        self.written = threading.Event()
        real_send, real_pdf = server.Handler._send, server.Handler._pdf
        test = self

        def after(handler):
            if getattr(handler, "_hold_after_write", False):
                test.written.set()
                test.hold.wait(20)

        def send(handler, status, body, ctype):
            real_send(handler, status, body, ctype)
            handler.wfile.flush()
            after(handler)

        def pdf(handler, body):
            real_pdf(handler, body)
            handler.wfile.flush()
            after(handler)
        real_post = server.Handler.do_POST

        def do_post(handler):
            handler._hold_after_write = test.first_pending
            test.first_pending = False
            return real_post(handler)
        self.first_pending = False
        patches = [mock.patch.object(server.Handler, "_send", send), mock.patch.object(server.Handler, "_pdf", pdf),
                   mock.patch.object(server.Handler, "do_POST", do_post),
                   mock.patch.object(server, "compute", return_value=copy.deepcopy(SCENARIOS[PRIMARY])),
                   mock.patch.object(premium, "generate", return_value=FAKE_PDF)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.hold.set)

    def first_then(self, first, follow_ups):
        """Send `first`, keep its handler thread parked after the write, then send `follow_ups`."""
        self.first_pending = True
        result = {}
        t = threading.Thread(target=lambda: result.update(first=self.post("/api/report", first)))
        t.start()
        self.assertTrue(self.written.wait(20), "first response was not written")
        t.join(20)
        self.assertFalse(t.is_alive(), "client did not receive the complete first response")
        out = [self.post("/api/report", body) for body in follow_ups]
        self.hold.set()
        self.written.clear()
        self.hold = threading.Event()
        return result["first"], out

    def test_refusals_after_a_pdf(self):
        first, out = self.first_then(BODY, [with_(BODY, display_name="Asha & Ravi"),
                                            with_(BODY, report_locale=CANARY), with_(BODY, report_locale=7), b"{"])
        self.assertEqual(first[0], 200)
        self.assertEqual([s for s, _, _ in out], [422, 422, 400, 400])
        for _, _, data in out:
            self.assertNotIn(CANARY.encode(), data)

    def test_pdf_after_a_refusal(self):
        first, out = self.first_then(with_(BODY, display_name="Asha & Ravi"), [BODY])
        self.assertEqual(first[0], 422)
        self.assertEqual(out[0][0], 200)
        self.assertEqual(out[0][2], FAKE_PDF)


class ConcurrentRenderStillRefused(Server):
    """Positive control: a request that arrives while another PDF is being rendered gets 429,
    whatever its body, without echo or renderer call; the slot is free afterwards."""

    def test_concurrent_requests_get_report_busy(self):
        started, release = threading.Event(), threading.Event()
        calls = []

        def slow(*a, **k):
            calls.append(k)
            started.set()
            release.wait(20)
            return FAKE_PDF
        result = {}
        with mock.patch.object(server, "compute", return_value=copy.deepcopy(SCENARIOS[PRIMARY])), \
                mock.patch.object(premium, "generate", side_effect=slow):
            t = threading.Thread(target=lambda: result.update(first=self.post("/api/report", BODY)))
            t.start()
            self.assertTrue(started.wait(20))
            busy = [self.post("/api/report", b) for b in (BODY, with_(BODY, display_name=CANARY),
                                                          with_(BODY, display_name="Asha & Ravi"),
                                                          with_(BODY, report_locale=CANARY), b"{")]
            chart = self.post("/api/chart", BODY)
            release.set()
            t.join(30)
        for status, headers, data in busy:
            self.assertRefusedWithoutPDF(status, headers, data, 429, "REPORT_BUSY")
            self.assertNotIn(CANARY.encode(), data)
        self.assertEqual(chart[0], 200)
        self.assertEqual(result["first"][0], 200)
        self.assertEqual(result["first"][2], FAKE_PDF)
        self.assertEqual(len(calls), 1, "a refused request reached the renderer")
        self.assertTrue(slot_is_free())


if __name__ == "__main__":
    unittest.main()
