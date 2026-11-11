"""KUN-COM-UX-CLAIM-001: Shopify entry points and the customer-facing claim page (synthetic data only).

The browser journeys themselves are in tests/browser/journey.test.cjs; these tests pin the server-side contract the
page and the Shopify blocks rely on."""
import json
from pathlib import Path
import re
import tomllib
import unittest

import helpers as h
from sabpuja_commerce import app as app_mod

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "integration" / "extensions" / "kundali-claim"
ORDER_ID = 5001


class OrderReference(unittest.TestCase):
    """The Thank you page knows the Shopify order id, not the order number: claims accept either, never both."""

    def setUp(self):
        self.h = h.Harness()
        self.h.paid(order_id=ORDER_ID, number=1001)

    def start(self, payload):
        return self.h.post("/api/claim/start", payload)

    def test_claim_by_order_ref_sends_code_naming_the_order_number(self):
        resp = self.start({"order_ref": str(ORDER_ID), "email": h.EMAIL})
        self.assertEqual(resp.status, 202)
        self.assertEqual(len(self.h.mail.sent), 1)
        self.assertIn("order #1001 is", self.h.mail.sent[0].get_content())
        code = self.h.last_code()
        ok = self.h.post("/api/claim/verify", {"order_ref": str(ORDER_ID), "email": h.EMAIL, "code": code})
        self.assertEqual(ok.status, 200)

    def test_code_from_ref_claim_also_works_with_the_order_number(self):
        self.start({"order_ref": str(ORDER_ID), "email": h.EMAIL})
        self.assertEqual(self.h.verify(self.h.last_code()).status, 200)

    def test_same_reply_and_no_mail_for_wrong_email_or_unknown_ref(self):
        good = self.start({"order_ref": str(ORDER_ID), "email": h.EMAIL})
        self.h.clock.advance(61)
        others = [self.start({"order_ref": str(ORDER_ID), "email": "other@example.invalid"}),
                  self.start({"order_ref": "999999999", "email": h.EMAIL}),
                  self.start({"order_ref": "1001", "email": h.EMAIL}),   # an order number is not an order id
                  self.h.start(number="999999")]
        self.assertEqual({(r.status, r.body) for r in others}, {(202, good.body)})
        self.assertEqual(len(self.h.mail.sent), 1)

    def test_malformed_references_refused(self):
        for payload in ({"order_ref": "gid://shopify/Order/5001", "email": h.EMAIL},
                        {"order_ref": "50 01", "email": h.EMAIL}, {"order_ref": "", "email": h.EMAIL},
                        {"order_ref": "1" * 21, "email": h.EMAIL}, {"order_ref": 5001, "email": h.EMAIL},
                        {"order_ref": str(ORDER_ID), "order_number": "1001", "email": h.EMAIL},
                        {"order_ref": str(ORDER_ID)}):
            self.assertEqual(self.start(payload).status, 400, payload)
        self.assertEqual(len(self.h.mail.sent), 0)

    def test_wrong_code_with_ref_is_rejected_and_counts_toward_the_lock(self):
        self.start({"order_ref": str(ORDER_ID), "email": h.EMAIL})
        code = self.h.last_code()
        wrong = f"{(int(code) + 1) % 10 ** 6:06d}"
        for _ in range(5):
            self.assertEqual(self.h.post("/api/claim/verify", {"order_ref": str(ORDER_ID), "email": h.EMAIL,
                                                               "code": wrong}).status, 401)
        self.assertEqual(self.h.verify(code).status, 401)

    def test_refunded_order_ref_gets_no_code(self):
        self.h.hook("refunds/create", {"id": 9, "order_id": ORDER_ID, "refund_line_items": []})
        self.assertEqual(self.start({"order_ref": str(ORDER_ID), "email": h.EMAIL}).status, 202)
        self.assertEqual(len(self.h.mail.sent), 0)


class ClaimReply(unittest.TestCase):
    def test_reply_explains_expiry_and_resend_with_config_values_only(self):
        hx = h.Harness(otp_ttl_seconds=900, otp_resend_cooldown_seconds=90)
        hx.paid()
        replies = [hx.start(), hx.start(email="x@example.invalid"), hx.start(number="42")]
        self.assertEqual(len({r.body for r in replies}), 1)
        self.assertEqual(replies[0].json(), {"status": "sent_if_matching",
                                             "message": app_mod.GENERIC_CLAIM["message"],
                                             "code_ttl_minutes": 15, "resend_after_seconds": 90})


class SessionStatus(unittest.TestCase):
    def test_session_reports_order_number_and_allowance(self):
        hx = h.Harness()
        hx.paid(number=1001)
        cookie = hx.login()
        s = hx.get("/api/session", cookie).json()
        self.assertEqual((s["order_number"], s["remaining"], s["used"], s["window_ends_at"], s["window_days"]),
                         (1001, 4, 0, None, 30))
        hx.generate(cookie)
        s = hx.get("/api/session", cookie).json()
        self.assertEqual((s["remaining"], s["used"]), (3, 1))
        self.assertEqual(s["window_ends_at"], int(hx.clock()) + 30 * 86400)


class Page(unittest.TestCase):
    def setUp(self):
        self.h = h.Harness()

    def test_fonts_and_logo_are_served_same_origin(self):
        for path in app_mod.SHARED_STATIC:
            resp = self.h.get(path)
            self.assertEqual(resp.status, 200, path)
            self.assertEqual(resp.content_type, app_mod.SHARED_STATIC[path][1])
            self.assertGreater(len(resp.body), 1000)
        self.assertEqual(self.h.get("/static/fonts/../../server.py").status, 404)
        self.assertEqual(self.h.get("/static/fonts/other.woff2").status, 404)

    def test_csp_allows_only_same_origin_fonts(self):
        self.assertIn("font-src 'self'", app_mod.SECURITY_HEADERS["Content-Security-Policy"])
        self.assertIn("default-src 'none'", app_mod.SECURITY_HEADERS["Content-Security-Policy"])

    def test_page_has_no_inline_script_style_or_third_party_reference(self):
        html = self.h.get("/").body.decode()
        self.assertNotRegex(html, r"<script(?![^>]*\bsrc=)|<style|\sstyle=|\son[a-z]+=")
        urls = set(re.findall(r'(?:href|src)="(https?://[^"]+)"', html))
        self.assertEqual(urls, {h.settings().source_url})
        for f in ("app.js", "app.css"):
            text = (ROOT / "sabpuja_commerce" / "static" / f).read_text()
            self.assertNotRegex(text, r"https?://(?!127\.0\.0\.1)", f)
        js = (ROOT / "sabpuja_commerce" / "static" / "app.js").read_text()
        self.assertNotRegex(js, r"localStorage\.|sessionStorage\.|document\.cookie|indexedDB", "no browser storage")

    def test_every_field_has_a_label_and_hindi_notice_is_marked(self):
        html = self.h.get("/").body.decode()
        for field in re.findall(r'<(?:input|select)[^>]*\bid="([a-z_]+)"', html):
            self.assertTrue(re.search(rf'<label[^>]*for="{field}"', html) or
                            re.search(rf'<label[^>]*>\s*<input id="{field}"', html), field)
        self.assertRegex(html, r'<p class="notice notice--hi" lang="hi">')


class CodeStepHints(unittest.TestCase):
    def test_sender_shown_escaped_and_junk_folder_hint(self):
        hx = h.Harness(mail_from='Sabpuja <noreply@sabpuja.com>')
        page = hx.get("/").body.decode()
        self.assertIn("It comes from <strong>Sabpuja &lt;noreply@sabpuja.com&gt;</strong>", page)
        self.assertIn("Check your Junk or Spam folder", page)
        self.assertNotIn("{{", page)


class ShopifyEntryPoints(unittest.TestCase):
    def test_extension_targets_and_no_extra_capabilities(self):
        conf = tomllib.loads((EXT / "shopify.extension.toml").read_text())
        self.assertEqual(conf["api_version"], "2026-10")
        ext = conf["extensions"][0]
        self.assertEqual(ext["type"], "ui_extension")
        self.assertEqual({t["target"] for t in ext["targeting"]},
                         {"purchase.thank-you.block.render", "customer-account.order-status.block.render"})
        for t in ext["targeting"]:
            self.assertTrue((EXT / t["module"]).is_file(), t["module"])
        self.assertEqual(ext["capabilities"], {"api_access": False, "network_access": False, "block_progress": False})
        self.assertEqual({f["key"] for f in ext["settings"]["fields"]}, {"claim_url", "sku", "qa_diagnostics"})

    def test_jsx_compiles_for_preact_in_the_cli_build(self):
        # Shopify CLI's esbuild reads tsconfig.json; without it JSX targets react/jsx-runtime and the bundle fails.
        tsconfig = json.loads((EXT / "tsconfig.json").read_text())
        self.assertEqual(tsconfig["compilerOptions"]["jsxImportSource"], "preact")
        self.assertEqual(tsconfig["compilerOptions"]["jsx"], "react-jsx")

    def test_extension_reads_no_customer_data(self):
        src = "\n".join(p.read_text() for p in (EXT / "src").iterdir())
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", src, flags=re.S)
        # Only these Shopify APIs are read: no buyer identity, address, e-mail, network or GraphQL query.
        self.assertEqual(set(re.findall(r"shopify\.([A-Za-z0-9]+)", code)),
                         {"settings", "lines", "orderConfirmation", "order", "i18n"})
        self.assertNotRegex(code, r"fetch\(|query\(|https?://|email")

    def test_locales_match(self):
        en = json.loads((EXT / "locales" / "en.default.json").read_text())
        hi = json.loads((EXT / "locales" / "hi.json").read_text())
        self.assertEqual(set(en), set(hi))
        self.assertEqual(en["button"], "Prepare your Janam Kundali")
        self.assertIn("English", en["language"])
        self.assertIn("अंग्रेज़ी", hi["language"])

    def test_email_snippet_numbers_match_the_configured_allowance(self):
        s = h.settings()
        text = (ROOT / "integration" / "order-confirmation-snippet.liquid").read_text()
        self.assertIn(f"within {s.claim_validity_days} days of\n        your order", text)
        self.assertIn(f"up to {s.additional_generations} corrected versions within {s.generation_window_days} days",
                      text)
        self.assertIn("Prepare your Janam Kundali</a>", text)


class EligibilityCopy(unittest.TestCase):
    def test_listing_names_exactly_the_cities_the_claim_page_offers(self):
        places = json.loads((ROOT.parent / "prototype" / "kundali_prototype" / "places.json").read_text())["places"]
        served = [p["name"] for p in places if p["id"].startswith("in-")]
        text = (ROOT / "integration" / "product-listing-eligibility.md").read_text()
        listed = re.search(r"born in one of these cities:\s*(.+?)\.\n", text, re.S).group(1)
        self.assertEqual([c.strip() for c in listed.replace("\n", " ").split(",")], served)
        self.assertIn("1 January 1970 to 31 December 2100", text)
        self.assertIn("English only", text)


if __name__ == "__main__":
    unittest.main()
