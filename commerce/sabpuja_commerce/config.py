"""Commerce settings. Secrets come from files outside Git; nothing here has a usable default secret."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import re


class ConfigError(ValueError):
    """The configuration is incomplete or unsafe; the service refuses to start."""


_DOMAIN = re.compile(r"^[a-z0-9][a-z0-9-]*\.myshopify\.com$")


@dataclass(frozen=True)
class Product:
    """One sellable Shopify variant mapped to the frozen report edition."""
    product_id: int
    variant_id: int
    sku: str
    currency: str
    edition: str


@dataclass(frozen=True)
class Settings:
    shop_domain: str
    webhook_secret: bytes
    pepper: bytes                      # HMAC key for emails, codes and session tokens at rest
    products: tuple[Product, ...]
    db_path: str
    public_origin: str                 # exact browser Origin, e.g. https://kundali.example
    ephe_path: str = ""
    allow_test_orders: bool = False    # Shopify `test: true` orders; staging only
    allow_unreleased_edition: bool = False  # staging QA only: render before the wording is owner-approved
    # Regeneration policy (owner proposal 2026-11-06, not commercially final): 1 + 3 within 30 days.
    initial_generations: int = 1
    additional_generations: int = 3
    generation_window_days: int = 30   # counted from the first delivered PDF
    claim_validity_days: int = 180     # how long an unused entitlement can be claimed
    otp_ttl_seconds: int = 600
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    otp_max_per_order_per_day: int = 5
    session_ttl_seconds: int = 1800
    webhook_max_age_seconds: int = 0   # 0 disables the X-Shopify-Triggered-At freshness check
    webhook_id_retention_days: int = 90
    claim_rate_per_minute: int = 10    # per client address, in memory
    max_concurrent_renders: int = 1
    verify_orders_with_admin_api: bool = False
    admin_api_token: str = field(default="", repr=False)
    admin_api_version: str = "2025-10"
    trusted_proxies: tuple[str, ...] = ()   # peers whose last X-Forwarded-For entry is the client
    source_url: str = "https://github.com/sabpuja/Sabpuja-Kundali-Engine"  # AGPL-3.0 Corresponding Source
    mail_from: str = "Sabpuja <no-reply@sabpuja.com>"

    @property
    def generations_per_unit(self) -> int:
        return self.initial_generations + self.additional_generations

    def product_for(self, product_id, variant_id, sku) -> Product | None:
        for p in self.products:
            if p.product_id == product_id and p.variant_id == variant_id and p.sku == sku:
                return p
        return None

    def validate(self) -> "Settings":
        if not _DOMAIN.match(self.shop_domain):
            raise ConfigError("shop_domain must be <name>.myshopify.com")
        if len(self.webhook_secret) < 16:
            raise ConfigError("webhook secret too short")
        if len(self.pepper) < 32:
            raise ConfigError("pepper must be at least 32 bytes")
        if not self.products:
            raise ConfigError("at least one product mapping is required")
        from . import EDITION_REQUIRED
        for p in self.products:
            if p.edition != EDITION_REQUIRED:
                raise ConfigError("only the frozen English Essentials edition can be sold")
            if not re.fullmatch(r"[A-Z]{3}", p.currency) or not p.sku:
                raise ConfigError("product currency and sku are required")
        if not re.fullmatch(r"https://[a-z0-9.-]+(:[0-9]+)?", self.public_origin) \
                and not self.public_origin.startswith("http://127.0.0.1"):
            raise ConfigError("public_origin must be an https origin")
        for name in ("initial_generations", "otp_ttl_seconds", "otp_max_attempts", "session_ttl_seconds",
                     "generation_window_days", "claim_validity_days", "max_concurrent_renders"):
            if getattr(self, name) < 1:
                raise ConfigError(f"{name} must be positive")
        if self.additional_generations < 0:
            raise ConfigError("additional_generations must not be negative")
        if self.verify_orders_with_admin_api and not self.admin_api_token:
            raise ConfigError("admin api verification needs a token")
        return self


def _read_secret(path: str) -> bytes:
    with open(path, "rb") as fh:
        value = fh.read().strip()
    if not value:
        raise ConfigError("empty secret file")
    return value


def load(path: str) -> Settings:
    """Load a JSON settings file. Secret values are file paths, never inline values."""
    with open(path, encoding="utf-8") as fh:
        raw = {k: v for k, v in json.load(fh).items() if not k.startswith("_")}
    products = tuple(Product(int(p["product_id"]), int(p["variant_id"]), str(p["sku"]), str(p["currency"]),
                             str(p["edition"])) for p in raw.pop("products"))
    secrets = {key: _read_secret(raw.pop(f"{key}_file")) for key in ("webhook_secret", "pepper")}
    token_file = raw.pop("admin_api_token_file", None)
    token = _read_secret(token_file).decode() if token_file else ""
    raw.setdefault("ephe_path", os.environ.get("SABPUJA_EPHE_PATH", ""))
    raw["trusted_proxies"] = tuple(raw.get("trusted_proxies", ()))
    return Settings(products=products, admin_api_token=token, **secrets, **raw).validate()
