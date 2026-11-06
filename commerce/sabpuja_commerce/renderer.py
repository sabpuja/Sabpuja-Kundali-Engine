"""The paid PDF: English Essentials edition only, in memory.

Paid output always goes through the frozen Essentials entry point
(`report.phase1.essentials.render_for_form`, KUN-RC-ESS-001). If that module is not present the
service refuses to generate (503) instead of falling back to a development edition. The request
the customer sends is reduced to the four birth fields plus an optional display name; a language
or Panchanga-names choice is refused outright, so Hindi and unapproved traditional names can not
be requested on the paid route.
"""
from __future__ import annotations

import importlib
import json

ALLOWED_KEYS = {"place_id", "birth_date", "birth_time", "utc_offset", "display_name"}
FORBIDDEN_KEYS = {"report_locale", "locale", "names", "panchanga_names", "edition", "palette", "synthetic"}
MAX_PDF_BYTES = 2 * 1024 * 1024


class InputRefused(Exception):
    """A birth-input refusal. code and message are fixed strings; no input value is ever included."""

    def __init__(self, status: int, code: str, message: str, extra: dict | None = None):
        super().__init__(code)
        self.status, self.code, self.message, self.extra = status, code, message, extra or {}


class RendererUnavailable(Exception):
    """The sellable edition cannot be produced on this server; nothing is charged against the quota."""


def screen(body: object) -> dict:
    """Server-side English-only enforcement and field allow-list for the paid form."""
    if not isinstance(body, dict):
        raise InputRefused(400, "REQUEST_INVALID", "the request must be one JSON object")
    present = FORBIDDEN_KEYS & set(body)
    if present - {"report_locale"} or body.get("report_locale", "en") != "en":
        raise InputRefused(422, "PAID_EDITION_ENGLISH_ONLY", "the paid Janam Kundali is available in English only")
    body = {k: v for k, v in body.items() if k != "report_locale"}
    if set(body) - ALLOWED_KEYS:
        raise InputRefused(400, "REQUEST_INVALID", "unexpected field")
    return body


class EssentialsRenderer:
    """Calls the frozen Essentials pipeline. `module` is overridable for tests only."""

    def __init__(self, places: dict, ephe_path: str, module: str = "report.phase1.essentials"):
        self._places, self._ephe, self._module = places, ephe_path, module

    def _entry(self):
        try:
            mod = importlib.import_module(self._module)
        except ImportError:
            raise RendererUnavailable("essentials edition not installed") from None
        fn = getattr(mod, "render_for_form", None)
        if fn is None or getattr(mod, "EDITION", None) != "janam-kundali-essentials-en/1":
            raise RendererUnavailable("essentials edition mismatch")
        return mod, fn

    def __call__(self, body: dict) -> bytes:
        mod, fn = self._entry()
        body = screen(body)
        name = body.pop("display_name", None)
        form = body
        if name is not None:
            from report.phase1.display_name import DisplayNameError, normalize
            try:
                name = normalize(name)
            except DisplayNameError as exc:
                raise InputRefused(exc.status, exc.code, exc.message) from None
        refusal = getattr(mod, "InputRefusal", None)
        try:
            pdf = fn(form, self._places, self._ephe, display_name=name)
        except Exception as exc:  # map the edition's typed refusals; anything else is a server fault
            if refusal is not None and isinstance(exc, refusal):
                raise InputRefused(exc.status, exc.code, exc.message, getattr(exc, "extra", None)) from None
            raise
        return check_pdf(pdf)


def check_pdf(pdf: bytes) -> bytes:
    if not isinstance(pdf, (bytes, bytearray)) or not pdf.startswith(b"%PDF-") or len(pdf) > MAX_PDF_BYTES:
        raise RuntimeError("controlled PDF check failed")
    return bytes(pdf)


def chart_refusal(status: int, payload: dict) -> InputRefused:
    """Turn the prototype's controlled error JSON into InputRefused (fixed codes and messages only)."""
    err = payload.get("error", {})
    extra = {"choices": err["choices"]} if "choices" in err else None
    return InputRefused(status, str(err.get("code", "REQUEST_INVALID")), str(err.get("message", "")), extra)


def dumps(body: dict) -> bytes:
    return json.dumps(body, ensure_ascii=False).encode("utf-8")
