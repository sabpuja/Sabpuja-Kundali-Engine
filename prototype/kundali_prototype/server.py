"""Localhost-only HTTP wrapper around the hardened engine (internal prototype).

Binds 127.0.0.1 only; the host is not configurable. No logging of requests,
no storage, no analytics and no outbound network. Every chart comes from
`sabpuja_kundali.engine.calculate`; this module only turns a form (place id,
local date, local time) into the engine's request and never changes its result.
Start-up readiness is the engine's own `readiness.require_ready()`.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
import json
import re
import sys
import threading

from sabpuja_kundali import readiness
from sabpuja_kundali.engine import (ChartComputationError, InputRefusalError, UnsupportedInputError,
                                    calculate, ephemeris_path)
from sabpuja_kundali.ephemeris import EphemerisDataError
from sabpuja_kundali.timezones import TimezoneDataError, get_zone

from .places import PlaceFixtureError, load_places, public_place

HOST = "127.0.0.1"
MAX_BODY_BYTES = 4096
MAX_PDF_BYTES = 1024 * 1024
_PDF_RENDER_SLOT = threading.BoundedSemaphore(1)
# OD-10: the owner approved the saffron Foundation design (report/phase1/premium_theme.json
# 'baseline', which maps theme.json). The only palette the /api/report route renders.
REPORT_PALETTE = "baseline"
# ChartComputationError codes meaning the pinned Swiss runtime itself is unusable on
# this server (engine.swiss_runtime and the Moshier refusal), reported as "resources".
# Every other ChartComputationError is a server-side calculation failure.
SWISS_RUNTIME_CODES = frozenset({"SWISS_BINDING_MISSING", "SWISS_LIBRARY_VERSION_MISMATCH",
                                 "SWISS_BINDING_METADATA_MISSING", "SWISS_BINDING_VERSION_MISMATCH",
                                 "SWISS_EPHEMERIS_FALLBACK_REFUSED"})

_DATE = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})$")
_TIME = re.compile(r"^([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?$")
_OFFSET = re.compile(r"^[+-][0-9]{2}:[0-9]{2}(?::[0-9]{2})?$")
_FORM_KEYS = {"place_id", "birth_date", "birth_time"}
_OPTIONAL_KEYS = {"utc_offset"}
_STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
           "/static/app.css": ("app.css", "text/css; charset=utf-8"),
           "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
           "/static/chart.js": ("chart.js", "text/javascript; charset=utf-8"),
           "/static/fonts.css": ("fonts.css", "text/css; charset=utf-8")}
# Approved Sabpuja logo masters and self-hosted OFL fonts; see prototype/README.md for provenance.
_STATIC.update({f"/static/brand/{name}": (f"brand/{name}", "image/svg+xml")
                for name in ("sabpuja-logo-horizontal-color.svg", "sabpuja-emblem-color.svg")})
_STATIC.update({f"/static/fonts/{family}-{subset}-{weight}-normal.woff2":
                (f"fonts/{family}-{subset}-{weight}-normal.woff2", "font/woff2")
                for family, weights in (("inter", (400, 500, 600)), ("poppins", (500, 600, 700)))
                for weight in weights for subset in ("latin", "latin-ext")})
# Poppins Devanagari (same @fontsource/poppins 5.3.0 package) for Hindi report names.
_STATIC.update({f"/static/fonts/poppins-devanagari-{weight}-normal.woff2":
                (f"fonts/poppins-devanagari-{weight}-normal.woff2", "font/woff2") for weight in (500, 600, 700)})
_SECURITY_HEADERS = {
    "Content-Security-Policy": ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
                                "font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; "
                                "frame-ancestors 'none'"),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Cache-Control": "no-store",
}


class StartupError(RuntimeError):
    """A pinned resource is missing or invalid; the server does not start."""

    def __init__(self, code: str, detail: str, check: str | None = None, cause: str | None = None):
        super().__init__(f"{code}: {detail}")
        self.code, self.check, self.cause = code, check, cause


class InvariantError(Exception):
    """A wrapper invariant failed; reported as INTERNAL_ERROR and never shown as a chart."""


class FormError(ValueError):
    """A prototype form refusal raised before the engine is called."""

    def __init__(self, status: int, code: str, message: str, category: str = "input", **extra):
        super().__init__(f"{code}: {message}")
        self.status, self.code, self.message, self.category, self.extra = status, code, message, category, extra


def startup_verify(ephe_path: str) -> dict[str, dict]:
    """Fail closed before listening: the engine's readiness preflight, then the place fixture.

    readiness.require_ready() checks the ephemeris data, the pinned Swiss library and
    binding, every pinned zone file, one synthetic chart and the output contract. Its
    typed NOT_READY becomes a StartupError; any other exception is a defect and propagates.
    """
    try:
        readiness.require_ready(ephe_path)
    except readiness.EngineNotReadyError as exc:
        failed = next(c for c in exc.result.checks if c.status == readiness.FAIL)
        raise StartupError(exc.result.code, "the calculation engine is not ready", failed.name,
                           failed.cause) from None
    try:
        return load_places()
    except TimezoneDataError as exc:
        raise StartupError(exc.code, "pinned timezone data failed verification", "place_fixture") from None
    except PlaceFixtureError:
        raise StartupError("PLACE_FIXTURE_INVALID", "birthplace fixture failed verification", "place_fixture") from None


def _offset_text(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    sign = "-" if seconds < 0 else "+"
    hours, rest = divmod(abs(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{sign}{hours:02d}:{minutes:02d}" + (f":{secs:02d}" if secs else "")


def _parse_form(body: object, places: dict[str, dict]) -> tuple[dict, str, str, str | None]:
    if not isinstance(body, dict):
        raise FormError(400, "REQUEST_INVALID", "the request must be one JSON object")
    keys = set(body)
    if not _FORM_KEYS <= keys or keys - _FORM_KEYS - _OPTIONAL_KEYS:
        raise FormError(400, "REQUEST_INVALID", "expected place_id, birth_date, birth_time and optional utc_offset")
    if not all(isinstance(body[k], str) for k in keys):
        raise FormError(400, "REQUEST_INVALID", "every field must be a string")
    place = places.get(body["place_id"])
    if place is None:
        raise FormError(422, "PLACE_UNKNOWN", "choose a birthplace from the supported list", "place")
    match = _DATE.match(body["birth_date"])
    if match is None:
        raise FormError(422, "BIRTH_DATE_INVALID", "enter the birth date as YYYY-MM-DD")
    try:
        date(*(int(g) for g in match.groups()))
    except ValueError:
        raise FormError(422, "BIRTH_DATE_INVALID", "this date does not exist in the calendar") from None
    if body["birth_time"] == "":
        raise FormError(422, "BIRTH_TIME_REQUIRED",
                        "an exact birth time is required; no time is assumed", "unknown_time")
    match = _TIME.match(body["birth_time"])
    if match is None:
        raise FormError(422, "BIRTH_TIME_INVALID", "enter the birth time as HH:MM or HH:MM:SS (24-hour)")
    hour, minute, second = int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)
    if hour > 23 or minute > 59 or second > 59:
        raise FormError(422, "BIRTH_TIME_INVALID",
                        "hours 00-23, minutes and seconds 00-59; leap seconds are not supported")
    offset = body.get("utc_offset")
    if offset is not None and not _OFFSET.match(offset):
        raise FormError(400, "UTC_OFFSET_INVALID", "utc_offset must be +HH:MM or -HH:MM")
    time_text = f"{hour:02d}:{minute:02d}:{second:02d}"
    return place, body["birth_date"], time_text, offset


def _candidate_offsets(local_date: str, local_time: str, zone) -> tuple[list[str], str]:
    """Offsets the pinned zone gives this wall time (mirrors the engine; the engine re-checks).

    Returns (valid offsets in fold order, carrier offset). In a gap there is no
    valid offset; the carrier is the zone's fold-0 offset, which the engine always
    refuses with TIME_NONEXISTENT_LOCAL (or an earlier code), so no chart results.
    """
    wall = datetime.fromisoformat(f"{local_date}T{local_time}")
    valid = []
    try:
        for fold in (0, 1):
            aware = wall.replace(tzinfo=zone, fold=fold)
            if aware.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == wall:
                text = _offset_text(aware.utcoffset())
                if text not in valid:
                    valid.append(text)
        return valid, _offset_text(wall.replace(tzinfo=zone, fold=0).utcoffset())
    except OverflowError:
        # Year 1 or 9999 near the edge of datetime: far outside the engine's
        # 1900-2100 window, which the engine refuses before it reads the offset.
        return [], "+00:00"


def compute(body: object, places: dict[str, dict], ephe_path: str) -> dict:
    """Validate the form, resolve the offset without guessing, and call the engine."""
    place, local_date, local_time, chosen = _parse_form(body, places)
    zone = get_zone(place["timezone"])
    valid, carrier = _candidate_offsets(local_date, local_time, zone)

    def engine(offset: str) -> dict:
        return calculate({"birth_datetime": f"{local_date}T{local_time}{offset}",
                          "timezone": place["timezone"], "latitude": place["latitude"],
                          "longitude": place["longitude"]}, ephe_path=ephe_path)

    if chosen is not None:
        if len(valid) < 2 or chosen not in valid:
            raise FormError(422, "UTC_OFFSET_NOT_APPLICABLE",
                            "utc_offset is accepted only to choose between the two occurrences of a repeated local time")
        offset, resolution = chosen, "user_selected_repeated_hour"
    elif len(valid) == 2:
        # Let the engine refuse first, so its fixed refusal order still applies;
        # a chart for one occurrence is discarded, never shown.
        engine(valid[0])
        raise FormError(409, "TIME_AMBIGUOUS_LOCAL",
                        "this local time occurs twice at this place (clocks were set back); choose which occurrence",
                        "ambiguous", choices=[{"utc_offset": valid[0], "label": f"First occurrence (UTC{valid[0]})"},
                                              {"utc_offset": valid[1], "label": f"Second occurrence (UTC{valid[1]})"}])
    elif len(valid) == 1:
        offset, resolution = valid[0], "unique"
    else:
        engine(carrier)
        raise InvariantError("engine accepted a local time that has no valid offset")
    chart = engine(offset)
    return {"input": {"place": public_place(place), "local_date": local_date, "local_time": local_time,
                      "utc_offset": offset, "offset_resolution": resolution},
            "chart": chart}


def _error(status: int, code: str, message: str, category: str, **extra) -> tuple[int, dict]:
    return status, {"error": {"code": code, "message": message, "category": category, **extra}}


def classify(exc: Exception) -> tuple[int, str, str, str]:
    """The one rule from an exception to (HTTP status, code, message, category).

    Client refusals keep their codes; server-side faults are 503; anything untyped is a
    defect and gets a fixed 500. Server-fault messages are fixed and never carry the
    request, a path or exception text.
    """
    if isinstance(exc, FormError):
        return exc.status, exc.code, exc.message, exc.category
    if isinstance(exc, InputRefusalError):
        category = "unsupported" if isinstance(exc, UnsupportedInputError) else "input"
        # Engine refusal texts are fixed strings without birth data (docs/api-contract.md).
        return 422, exc.code, str(exc).split(": ", 1)[-1], category
    if isinstance(exc, (EphemerisDataError, TimezoneDataError)):
        return 503, exc.code, "pinned calculation data failed verification; no chart produced", "resources"
    if isinstance(exc, ChartComputationError):
        if exc.code in SWISS_RUNTIME_CODES:
            return 503, exc.code, "the pinned Swiss Ephemeris runtime is unavailable on this server; no chart produced", "resources"
        return 503, exc.code, "the server could not compute this chart; no chart produced", "computation"
    return 500, "INTERNAL_ERROR", "unexpected error; no chart produced", "internal"


def handle_chart(raw: bytes, places: dict[str, dict], ephe_path: str) -> tuple[int, dict]:
    """Map every outcome to a controlled JSON response; nothing from the input is echoed in errors."""
    try:
        try:
            body = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
        except (UnicodeDecodeError, ValueError, RecursionError):
            # RecursionError: input nested too deeply for the decoder, a request-format fault
            # (as in the CLI). Caught here only; one from compute() stays a 500 defect.
            raise FormError(400, "REQUEST_INVALID", "the request must be one UTF-8 JSON object") from None
        return 200, compute(body, places, ephe_path)
    except Exception as exc:
        status, code, message, category = classify(exc)
        if status == 500:
            # A defect is never disguised as a refusal: name its type (no message, no data) locally.
            print(json.dumps({"event": "INTERNAL_ERROR", "type": type(exc).__name__}), file=sys.stderr, flush=True)
        return _error(status, code, message, category, **(exc.extra if isinstance(exc, FormError) else {}))


def _split_display_name(raw: bytes) -> tuple[bytes, str | None]:
    """Separate the optional report name from the birth details (KUN-UX-NAME-001).

    Returns the request bytes for handle_chart and the validated name (or None). A request
    without display_name is passed on byte for byte, so existing clients are unaffected. With
    one, the name is validated on its own and the remaining fields are re-serialised for the
    unchanged chart handler, which never sees the name. A body that is not one UTF-8 JSON
    object is passed on as it is, and handle_chart refuses it exactly as before.
    """
    try:
        body = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return raw, None
    if not isinstance(body, dict) or "display_name" not in body:
        return raw, None
    from report.phase1.display_name import DisplayNameError, normalize
    try:
        name = normalize(body.pop("display_name"))
    except DisplayNameError as exc:
        # Fixed messages only: the submitted name is never echoed or logged.
        raise FormError(exc.status, exc.code, exc.message) from None
    return json.dumps(body, ensure_ascii=False).encode("utf-8"), name


def handle_report(raw: bytes, places: dict[str, dict], ephe_path: str) -> tuple[int, dict | bytes]:
    """An in-memory PDF derived only from the authenticated engine request and response.

    Renders the ten-page Phase 2A premium layout in the owner-approved saffron Foundation
    palette (OD-10). The palette is fixed here, never taken from the request. The Phase 1
    renderer (report.phase1.generate_report) stays in the source as the regression and
    rollback baseline; it is no longer called by this route.

    The optional display_name is accepted by this route only (never by /api/chart). It is
    validated separately, removed before the chart handler runs, and passed to the renderer
    as a display-only argument. It is not stored, logged or echoed.
    """
    try:
        raw, display_name = _split_display_name(raw)
    except FormError as exc:
        return _error(exc.status, exc.code, exc.message, exc.category)
    status, response = handle_chart(raw, places, ephe_path)
    if status != 200:
        return status, response
    from report.phase1.premium_report import generate
    # Without a name the renderer is called exactly as before this feature.
    named = {} if display_name is None else {"display_name": display_name}
    pdf = generate(response, synthetic=False, palette=REPORT_PALETTE, **named)
    if len(pdf) > MAX_PDF_BYTES or not pdf.startswith(b"%PDF-"):
        raise RuntimeError("controlled PDF size exceeded")
    return 200, pdf


def _no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key")
    return dict(pairs)


class PrototypeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int, ephe_path: str, places: dict[str, dict]):
        self.ephe_path = ephe_path
        self.places = places
        self.static = {path: (resources.files(__package__).joinpath("static", *name.split("/")).read_bytes(), ctype)
                       for path, (name, ctype) in _STATIC.items()}
        self.places_payload = json.dumps({"places": [public_place(p) for p in places.values()]},
                                         ensure_ascii=False).encode("utf-8")
        super().__init__((HOST, port), Handler)
        if self.socket.getsockname()[0] != HOST:
            self.server_close()
            raise StartupError("BIND_NOT_LOOPBACK", "the server socket is not bound to 127.0.0.1", "local_server")

    @property
    def allowed_hosts(self) -> set[str]:
        port = self.server_address[1]
        return {f"127.0.0.1:{port}", f"localhost:{port}"}


class Handler(BaseHTTPRequestHandler):
    server_version = "SabpujaPrototype"
    sys_version = ""
    timeout = 15

    def log_message(self, format, *args):  # noqa: A002 - no request or birth data is ever logged
        pass

    def send_error(self, code, message=None, explain=None):
        # The default error page echoes parts of the request line; send a fixed body instead.
        self._json(code, {"error": {"code": "HTTP_ERROR", "message": "request not accepted", "category": "http"}})

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for name, value in _SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self.close_connection = status >= 400
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _pdf(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", 'attachment; filename="Sabpuja-Janma-Kundali.pdf"')
        self.send_header("Content-Length", str(len(body)))
        for name, value in _SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self) -> bool:
        # DNS-rebinding guard: only the loopback names this server was opened on.
        if self.headers.get("Host") in self.server.allowed_hosts:
            return True
        self._json(421, {"error": {"code": "HOST_NOT_ALLOWED", "message": "open the prototype at 127.0.0.1",
                                   "category": "http"}})
        return False

    def do_GET(self):
        if not self._host_ok():
            return
        if self.path in self.server.static:
            body, ctype = self.server.static[self.path]
            self._send(200, body, ctype)
        elif self.path == "/api/places":
            self._send(200, self.server.places_payload, "application/json; charset=utf-8")
        else:
            self._json(404, {"error": {"code": "NOT_FOUND", "message": "not found", "category": "http"}})

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        if not self._host_ok():
            return
        if self.path not in ("/api/chart", "/api/report"):
            self._json(404, {"error": {"code": "NOT_FOUND", "message": "not found", "category": "http"}})
            return
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {f"http://{h}" for h in self.server.allowed_hosts}:
            self._json(403, {"error": {"code": "ORIGIN_NOT_ALLOWED", "message": "cross-origin request refused",
                                       "category": "http"}})
            return
        if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
            self._json(415, {"error": {"code": "CONTENT_TYPE_INVALID", "message": "send application/json",
                                       "category": "http"}})
            return
        length = self.headers.get("Content-Length")
        if self.headers.get("Transfer-Encoding") or length is None or not length.isdigit():
            self._json(411, {"error": {"code": "LENGTH_REQUIRED", "message": "Content-Length is required",
                                       "category": "http"}})
            return
        if int(length) > MAX_BODY_BYTES:
            self._json(413, {"error": {"code": "REQUEST_TOO_LARGE", "message": "request exceeds 4 KB",
                                       "category": "http"}})
            return
        raw = self.rfile.read(int(length))
        if self.path == "/api/report":
            if not _PDF_RENDER_SLOT.acquire(blocking=False):
                self._json(429, {"error": {"code": "REPORT_BUSY", "message": "try again shortly",
                                          "category": "resources"}})
                return
            try:
                try:
                    status, payload = handle_report(raw, self.server.places, self.server.ephe_path)
                    if status == 200:
                        self._pdf(payload)
                    else:
                        self._json(status, payload)
                except Exception as exc:
                    # Never log input data, exception text, filenames or personal records.
                    print(json.dumps({"event": "REPORT_FAILURE", "type": type(exc).__name__}),
                          file=sys.stderr, flush=True)
                    self._json(503, {"error": {"code": "REPORT_UNAVAILABLE",
                                               "message": "the PDF could not be generated",
                                               "category": "resources"}})
            finally:
                _PDF_RENDER_SLOT.release()
            return
        status, payload = handle_chart(raw, self.server.places, self.server.ephe_path)
        self._json(status, payload)

    def _method_not_allowed(self):
        self._json(405, {"error": {"code": "METHOD_NOT_ALLOWED", "message": "method not allowed", "category": "http"}})

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _method_not_allowed


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Sabpuja Kundali internal prototype (127.0.0.1 only)")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    # The same path every request's engine.calculate uses (SABPUJA_EPHE_PATH).
    ephe_path = ephemeris_path()
    try:
        places = startup_verify(ephe_path)
        server = PrototypeServer(args.port, ephe_path, places)
    except StartupError as exc:
        report = {"error": exc.code, "check": exc.check, "message": "prototype not started; nothing is listening"}
        if exc.cause:
            report["cause"] = exc.cause
        print(json.dumps(report), file=sys.stderr)
        return 2
    except OSError:
        print(json.dumps({"error": "PORT_UNAVAILABLE", "message": "prototype not started"}), file=sys.stderr)
        return 2
    print(f"Sabpuja Kundali internal prototype: http://127.0.0.1:{server.server_address[1]}/ "
          "(localhost only; Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
