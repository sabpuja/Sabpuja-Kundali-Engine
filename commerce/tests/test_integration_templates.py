"""KUN-RC-COM-001B: the QA-store integration templates are consistent with the frozen commerce code.
Templates only; nothing here talks to Shopify, SMTP or a server."""
import json
from pathlib import Path
import re
import tempfile
import tomllib
import unittest

import helpers as h
from sabpuja_commerce import config, shopify

DIR = Path(__file__).resolve().parents[1] / "integration"


class Templates(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raw = json.loads((DIR / "commerce.qa-store.example.json").read_text())
        self.toml = tomllib.loads((DIR / "shopify.app.toml.example").read_text())

    def load(self, raw):
        d = Path(self.tmp.name)
        for name, value in (("wh", h.SECRET), ("pp", h.PEPPER), ("tk", b"shpat_synthetic")):
            (d / name).write_bytes(value)
        raw = dict(raw, webhook_secret_file=str(d / "wh"), pepper_file=str(d / "pp"),
                   admin_api_token_file=str(d / "tk"), db_path=":memory:")
        (d / "c.json").write_text(json.dumps(raw))
        return config.load(str(d / "c.json"))

    def test_qa_config_loads_when_filled_in(self):
        raw = dict(self.raw, shop_domain=h.SHOP, public_origin=h.ORIGIN,
                   mail_from="Sabpuja Kundali <noreply@example.invalid>")
        raw["products"] = [dict(raw["products"][0], product_id=1, variant_id=2, sku="SBK-ESS-EN-1")]
        s = self.load(raw)
        self.assertTrue(s.require_order_verification)
        self.assertFalse(s.allow_unreleased_edition)                 # wording switch stays OFF
        self.assertEqual(s.admin_api_version, "2026-10")
        self.assertEqual((s.claim_validity_days, s.generation_window_days, s.order_read_horizon_days), (30, 30, 60))
        self.assertEqual(s.generations_per_unit, 4)

    def test_qa_config_placeholders_refused(self):
        with self.assertRaises(config.ConfigError):
            self.load(self.raw)

    def test_app_toml_scopes_version_and_topics(self):
        self.assertEqual(self.toml["access_scopes"]["scopes"], "read_orders")
        self.assertEqual(self.toml["webhooks"]["api_version"], self.raw["admin_api_version"])
        subs = self.toml["webhooks"]["subscriptions"]
        self.assertEqual(sorted(t for s in subs for t in s["topics"]),
                         ["orders/cancelled", "orders/paid", "refunds/create"])
        self.assertEqual({s["uri"] for s in subs}, {"https://<commerce-staging-host>/webhooks/shopify"})

    def test_include_fields_cover_what_the_receiver_reads(self):
        fields = {t: set(s.get("include_fields", ())) for s in self.toml["webhooks"]["subscriptions"]
                  for t in s["topics"]}
        src = Path(shopify.__file__).read_text()
        apply_src = src[src.index("def _paid_lines"):src.index("ORDER_QUERY =")]
        read = set(re.findall(r'(?:payload|order)(?:\.get\()?\[?"([a-z_]+)"', apply_src))
        read -= {"line_item_id", "price", "product_id", "variant_id", "sku", "quantity", "current_quantity"}
        self.assertTrue(read)
        self.assertLessEqual(read - {"order_id", "refund_line_items"}, fields["orders/paid"])
        self.assertLessEqual({"order_id", "refund_line_items"}, fields["refunds/create"])
        self.assertLessEqual({"id"}, fields["orders/cancelled"])
        for topic_fields in fields.values():                           # no customer/address fields requested
            self.assertFalse(topic_fields & {"customer", "billing_address", "shipping_address", "phone", "note"})

    def test_no_secret_values_in_templates(self):
        for path in DIR.iterdir():
            text = path.read_text()
            self.assertNotRegex(text, r"shpat_[0-9a-f]{8,}|shpss_[0-9a-f]{8,}|-----BEGIN", path.name)

    def test_claim_link_carries_no_personal_data(self):
        text = (DIR / "order-confirmation-snippet.liquid").read_text()
        hrefs = re.findall(r'href="([^"]+)"', text)
        self.assertEqual(hrefs, ["https://REPLACE-commerce-staging-host/"])


if __name__ == "__main__":
    unittest.main()
