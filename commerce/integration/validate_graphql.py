"""KUN-RC-COM-001B: validate the commerce GraphQL operations and webhook topics against Shopify's published
Admin API introspection schema (offline; no store, no token).

Schema source: the `dist/data/admin_<version>.json.gz` files shipped by Shopify in the npm package
@shopify/dev-mcp (1.18.0 used for the handoff). Needs graphql-core (3.2.6 used), installed in a separate venv;
it is a QA tool, not a runtime dependency.

    python validate_graphql.py admin_2026-10.json.gz
Exit 0 when every operation validates and every topic exists.
"""
import gzip
import json
from pathlib import Path
import sys

from graphql import build_client_schema, parse, validate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sabpuja_commerce import admin_auth, shopify  # noqa: E402

TOPICS = ("ORDERS_PAID", "ORDERS_CANCELLED", "REFUNDS_CREATE")
FIELDS = {"Order": ("id", "number", "email", "createdAt", "cancelledAt", "displayFinancialStatus", "test",
                    "currencyCode", "lineItems", "refunds"),
          "LineItem": ("id", "sku", "currentQuantity", "variant", "originalUnitPriceSet"),
          "Refund": ("refundLineItems",)}


def main(path: str) -> int:
    schema = build_client_schema(json.load(gzip.open(path))["data"])
    ok = True
    for name, query in (("ORDER_QUERY", shopify.ORDER_QUERY), ("RECOVERY_QUERY", shopify.RECOVERY_QUERY),
                        ("SHOP_QUERY", admin_auth.SHOP_QUERY)):
        errors = validate(schema, parse(query))
        ok &= not errors
        print(f"{name}: {'VALID' if not errors else 'INVALID'}")
        for e in errors:
            print("   ", e.message)
    for type_name, fields in FIELDS.items():
        t = schema.get_type(type_name)
        for f in fields:
            dep = t.fields[f].deprecation_reason
            ok &= dep is None
            print(f"{type_name}.{f}: {t.fields[f].type}" + (f"  DEPRECATED: {dep}" if dep else ""))
    statuses = set(schema.get_type("OrderDisplayFinancialStatus").values)
    ok &= shopify.PAID_STATUSES <= statuses
    print("PAID_STATUSES in OrderDisplayFinancialStatus:", shopify.PAID_STATUSES <= statuses)
    topics = schema.get_type("WebhookSubscriptionTopic").values
    for t in TOPICS:
        present = t in topics and not topics[t].deprecation_reason
        ok &= present
        print(f"WebhookSubscriptionTopic.{t}:", "present" if present else "MISSING OR DEPRECATED")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
