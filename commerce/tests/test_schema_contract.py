"""Contract test: both GraphQL operations against Shopify's published Admin API schema for the configured
version. Skipped unless SABPUJA_TEST_SHOPIFY_SCHEMA names an introspection file `admin_<version>.json.gz`
(shipped by Shopify in npm @shopify/dev-mcp, dist/data/) and graphql-core is installed (a QA-only tool)."""
import gzip
import json
import os
from pathlib import Path
import re
import unittest

from sabpuja_commerce import admin_auth, config, shopify

PATH = os.environ.get("SABPUJA_TEST_SHOPIFY_SCHEMA")
try:
    from graphql import build_client_schema, parse, validate
except ImportError:  # pragma: no cover - QA environment only
    build_client_schema = None


@unittest.skipUnless(PATH and build_client_schema, "SABPUJA_TEST_SHOPIFY_SCHEMA or graphql-core not available")
class Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = build_client_schema(json.load(gzip.open(PATH))["data"])

    def errors(self, query):
        return [e.message for e in validate(self.schema, parse(query))]

    def test_schema_file_is_the_configured_version(self):
        self.assertEqual(Path(PATH).name, f"admin_{config.Settings.admin_api_version}.json.gz")

    def test_operations_validate(self):
        for name in ("ORDER_QUERY", "RECOVERY_QUERY"):
            self.assertEqual(self.errors(getattr(shopify, name)), [], name)
        self.assertEqual(self.errors(admin_auth.SHOP_QUERY), [], "SHOP_QUERY")   # token shop check (F4)

    def test_validator_rejects_wrong_shapes(self):
        # The contract must catch argument and field mistakes, not just parse.
        q = shopify.ORDER_QUERY
        for bad in (q.replace("refunds(first: 50)", "refunds(after: \"x\")"),
                    q.replace("refunds(first: 50) {", "refunds(first: 50) { nodes { id } "),   # treat list as connection
                    q.replace("currentQuantity", "remainingQuantity"),
                    shopify.RECOVERY_QUERY.replace("number", "orderNumber")):
            self.assertNotEqual(self.errors(bad), [])

    def test_every_connection_reports_has_next_page(self):
        for name in ("ORDER_QUERY", "RECOVERY_QUERY"):
            q = getattr(shopify, name)
            self.assertEqual(len(re.findall(r"pageInfo \{ hasNextPage \}", q)), 2, name)
        refunds = self.schema.get_type("Order").fields["refunds"]
        self.assertEqual(str(refunds.type), "[Refund!]!")             # a list: completeness = len < PAGE
        self.assertIn("first", refunds.args)

    def test_number_is_the_canonical_order_number(self):
        self.assertEqual(str(self.schema.get_type("Order").fields["number"].type), "Int!")


if __name__ == "__main__":
    unittest.main()
