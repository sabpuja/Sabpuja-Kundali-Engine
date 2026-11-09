"""Sabpuja Janam Kundali paid fulfilment (KUN-RC-COM-001). OFFLINE / NOT DEPLOYED.

Shopify takes the payment; this service holds only order entitlements. Birth details and
generated PDFs are never persisted: they live in memory for one request and are discarded.
Standard library only. AGPL-3.0-only, like the rest of this repository.
"""
EDITION_REQUIRED = "janam-kundali-essentials-en/1"
PAID_LOCALE = "en"
