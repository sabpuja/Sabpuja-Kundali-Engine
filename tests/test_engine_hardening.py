"""Gate 3C (PKG-2): typed Swiss runtime failures, pinned-version enforcement and the
engine-to-CLI error boundary. Synthetic inputs only.

The mocked classes use the swisseph test double from test_engine_boundaries, so they
run without the binding or data. The real-data class needs SABPUJA_TEST_EPHE_PATH
(unset skips, as in test_swiss_integration).
"""
import contextlib
import json
import os
import re
import runpy
import subprocess
import sys
import tempfile
import threading
import tomllib
import unittest
from importlib import metadata
from pathlib import Path
from unittest import mock

from sabpuja_kundali import engine, provenance, readiness
from sabpuja_kundali.engine import ChartComputationError, InputRefusalError, calculate
from sabpuja_kundali.ephemeris import EphemerisDataError
from sabpuja_kundali.timezones import TimezoneDataError

from test_engine_boundaries import FIXTURE, LAGNA, SYNTHETIC, fake_swisseph

DATA_ENV = "SABPUJA_TEST_EPHE_PATH"
DATA = os.environ.get(DATA_ENV)
TESTS_DIR = Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent
SRC = ROOT / "src"
REQUEST_PIECES = ("2000-01-01", "17:30", "Asia/Kolkata", "28.6139", "77.209")
SWISS_CALLS = ("julday", "set_ephe_path", "set_sid_mode", "set_delta_t_userdef", "calc_ut", "houses_ex")

FIXED = {
    "SWISS_BINDING_MISSING":
        "the pinned Swiss Ephemeris Python binding is not installed; no chart produced",
    "SWISS_LIBRARY_VERSION_MISMATCH":
        "the Swiss Ephemeris library is not the pinned version; no chart produced",
    "SWISS_BINDING_METADATA_MISSING":
        "the Swiss Ephemeris binding version cannot be verified; no chart produced",
    "SWISS_BINDING_VERSION_MISMATCH":
        "the Swiss Ephemeris binding is not the pinned version; no chart produced",
    "SWISS_EPHEMERIS_FALLBACK_REFUSED":
        "Swiss Ephemeris did not use the verified local files; refused Moshier fallback; no chart produced",
}
# Codes that existed before Gate 3C (docs/api-contract.md); the new ones must not collide.
EXISTING_CODES = {
    "REQUEST_INVALID", "TIME_FORMAT_INVALID", "TIME_OFFSET_REQUIRED", "TIME_LEAP_SECOND_UNSUPPORTED",
    "DATE_INVALID", "TIMEZONE_INVALID", "TIMEZONE_NOT_LOCATION_BASED", "DATE_OUTSIDE_SUPPORTED_RANGE",
    "TIME_NONEXISTENT_LOCAL", "TIME_OFFSET_MISMATCH", "HISTORICAL_CLOCK_UNVERIFIED", "COORDINATE_INVALID",
    "LATITUDE_OUTSIDE_SUPPORTED_BAND", "SWISS_TIME_CALCULATION_FAILED", "SWISS_STATE_INITIALIZATION_FAILED",
    "SWISS_PLANET_CALCULATION_FAILED", "ASCENDANT_UNCOMPUTABLE", "EPHEMERIS_PATH_OVERRIDE",
    "EPHEMERIS_PATH_MISSING", "EPHEMERIS_MANIFEST_INVALID", "EPHEMERIS_FILE_MISSING",
    "EPHEMERIS_FILE_UNREADABLE", "EPHEMERIS_FILE_MISMATCH", "TZDATA_MANIFEST_MISSING",
    "TZDATA_MANIFEST_INVALID", "TZDATA_PACKAGE_MISSING", "TZDATA_VERSION_MISMATCH", "TZDATA_FILE_MISSING",
    "TZDATA_FILE_MISMATCH",
}


_ABSENT = object()


def recording_swisseph(calls, fallback_body=None, **attrs):
    """The boundary test double, recording every Swiss call; fallback_body clears
    FLG_SWIEPH in the flags returned for that body (a Moshier fallback)."""
    swe = fake_swisseph(FIXTURE, LAGNA)
    for name in SWISS_CALLS:
        def wrap(*args, _name=name, _real=getattr(swe, name)):
            calls.append(_name)
            result = _real(*args)
            if _name == "calc_ut" and args[1] == fallback_body:
                return result[0], result[1] & ~swe.FLG_SWIEPH
            return result
        setattr(swe, name, wrap)
    for key, value in attrs.items():
        if value is _ABSENT:
            delattr(swe, key)
        else:
            setattr(swe, key, value)
    return swe


@contextlib.contextmanager
def fake_runtime(swe, binding=engine.REQUIRED_BINDING_VERSION, verify=True):
    """Install swe as swisseph (None: not importable), fake the ephemeris gate and set
    the installed binding distribution version (None: metadata unavailable)."""
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.dict(sys.modules, {"swisseph": swe}))
        if verify:
            stack.enter_context(mock.patch.object(engine, "verify_ephemeris_dir", return_value=Path("/unused")))
        stack.enter_context(mock.patch.object(provenance, "binding_distribution_version", return_value=binding))
        yield


def lock_is_free():
    acquired = []

    def probe():
        ok = engine._SWISS_LOCK.acquire(timeout=2)
        acquired.append(ok)
        if ok:
            engine._SWISS_LOCK.release()

    t = threading.Thread(target=probe, daemon=True)
    t.start()
    t.join(5)
    return acquired == [True]


class TypedSwissFailureTests(unittest.TestCase):
    """Group A: binding missing, fallback detected, fixed error mapping."""

    def assertFixed(self, exc, code):
        self.assertIsInstance(exc, ChartComputationError)
        self.assertNotIsInstance(exc, ValueError)  # a server fault, never an input refusal
        self.assertEqual(exc.code, code)
        self.assertEqual(str(exc), f"{code}: {FIXED[code]}")
        self.assertIsNone(exc.__cause__)
        self.assertTrue(exc.__suppress_context__ or exc.__context__ is None)
        for piece in REQUEST_PIECES + ("/", "\\"):
            self.assertNotIn(piece, str(exc))

    def test_new_codes_are_distinct_and_not_existing_contracts(self):
        self.assertEqual(len(set(FIXED)), len(FIXED))
        self.assertFalse(set(FIXED) & EXISTING_CODES)
        for code in FIXED:
            self.assertRegex(code, r"^SWISS_[A-Z_]+$")

    def test_missing_binding_is_typed(self):
        result = None
        with fake_runtime(None), self.assertRaises(ChartComputationError) as ctx:
            result = calculate(dict(SYNTHETIC))
        self.assertIsNone(result)
        self.assertFixed(ctx.exception, "SWISS_BINDING_MISSING")

    def test_fallback_flag_on_any_body_is_refused_with_no_partial_chart(self):
        for body in range(8):  # the double numbers the eight bodies 0..7 in calculation order
            with self.subTest(body=body):
                calls, result = [], None
                with fake_runtime(recording_swisseph(calls, fallback_body=body)), \
                        self.assertRaises(ChartComputationError) as ctx:
                    result = calculate(dict(SYNTHETIC))
                self.assertIsNone(result)
                self.assertFixed(ctx.exception, "SWISS_EPHEMERIS_FALLBACK_REFUSED")
                # Nothing is computed after the refused body; no ascendant, no substitute value.
                self.assertEqual(calls.count("calc_ut"), body + 1)
                self.assertNotIn("houses_ex", calls)
                self.assertEqual(calls[-1], "calc_ut")
                self.assertTrue(lock_is_free())

    def test_fallback_refusal_still_matches_the_historical_text(self):
        # Older callers matched the RuntimeError text; it is still a RuntimeError with that phrase.
        with fake_runtime(recording_swisseph([], fallback_body=1)), \
                self.assertRaisesRegex(RuntimeError, "refused Moshier fallback"):
            calculate(dict(SYNTHETIC))

    def test_existing_swiss_error_mapping_is_unchanged(self):
        # Every swe.Error still maps to its earlier fixed code (test_swiss_error_contract owns the
        # full matrix); here: the version gate does not intercept or rename them.
        calls = []
        swe = recording_swisseph(calls)
        swe.houses_ex = mock.Mock(side_effect=swe.Error("/srv/secret path 28.6139"))
        with fake_runtime(swe), self.assertRaises(ChartComputationError) as ctx:
            calculate(dict(SYNTHETIC))
        self.assertEqual(ctx.exception.code, "ASCENDANT_UNCOMPUTABLE")
        self.assertNotIn("/srv", str(ctx.exception))

    def test_programming_defects_are_not_classified(self):
        swe = recording_swisseph([])
        swe.calc_ut = mock.Mock(side_effect=ZeroDivisionError("defect"))
        with fake_runtime(swe), self.assertRaises(ZeroDivisionError):
            calculate(dict(SYNTHETIC))
        self.assertTrue(lock_is_free())
        for exc in (ZeroDivisionError, TypeError, KeyError):
            self.assertFalse(issubclass(exc, engine.EXPECTED_ERRORS))

    def test_input_refusals_and_data_faults_still_come_first(self):
        refusals = {
            "REQUEST_INVALID": {**SYNTHETIC, "extra": 1},
            "TIME_OFFSET_REQUIRED": {**SYNTHETIC, "birth_datetime": "2000-01-01T17:30:00"},
            "TIMEZONE_NOT_LOCATION_BASED": {**SYNTHETIC, "timezone": "UTC"},
            "HISTORICAL_CLOCK_UNVERIFIED": {**SYNTHETIC, "birth_datetime": "1965-01-01T12:00:00+05:30"},
            "COORDINATE_INVALID": {**SYNTHETIC, "latitude": "north"},
            "LATITUDE_OUTSIDE_SUPPORTED_BAND": {**SYNTHETIC, "latitude": 70.0},
        }
        for runtime in (None, recording_swisseph([], version="2.10.02")):
            for code, request in refusals.items():
                with self.subTest(runtime=runtime is None, code=code):
                    with fake_runtime(runtime, binding="9.9"), self.assertRaises(InputRefusalError) as ctx:
                        calculate(request)
                    self.assertEqual(ctx.exception.code, code)
            # The ephemeris gate (real, not faked) still precedes the binding and version checks.
            with self.subTest(runtime=runtime is None, code="EPHEMERIS_PATH_MISSING"):
                with fake_runtime(runtime, binding="9.9", verify=False), \
                        self.assertRaises(EphemerisDataError) as ctx:
                    calculate(dict(SYNTHETIC), ephe_path="/nonexistent/sabpuja-ephemeris")
                self.assertEqual(ctx.exception.code, "EPHEMERIS_PATH_MISSING")
        broken = TimezoneDataError("TZDATA_FILE_MISMATCH", "a zone file does not match the pinned SHA-256")
        with fake_runtime(None), mock.patch.object(engine, "get_zone", side_effect=broken), \
                self.assertRaises(TimezoneDataError):
            calculate(dict(SYNTHETIC))


class VersionEnforcementTests(unittest.TestCase):
    """Group B: exact pins accepted; mismatched, missing and malformed versions refused
    before any Swiss computation."""

    def assertRefusedBeforeSwiss(self, code, binding=engine.REQUIRED_BINDING_VERSION, **attrs):
        calls = []
        with fake_runtime(recording_swisseph(calls, **attrs), binding=binding), \
                self.assertRaises(ChartComputationError) as ctx:
            calculate(dict(SYNTHETIC))
        self.assertEqual(ctx.exception.code, code)
        self.assertEqual(str(ctx.exception), f"{code}: {FIXED[code]}")
        self.assertEqual(calls, [], "no Swiss call after a version failure")
        self.assertFalse(engine._SWISS_LOCK._is_owned())

    def test_exact_pins_are_accepted(self):
        calls = []
        with fake_runtime(recording_swisseph(calls)):
            chart = calculate(dict(SYNTHETIC))
        self.assertEqual(chart["calculation_metadata"]["swiss_ephemeris"],
                         {"library_version": "2.10.03", "python_binding": "pyswisseph",
                          "python_binding_version": "2.10.3.2"})
        self.assertEqual(calls[0], "julday")

    def test_library_version_mismatch_or_malformed(self):
        for value in ("2.10.02", "2.10.04", "2.10.3", "2.10.03 ", " 2.10.03", "2.10.03b", "", None,
                      b"2.10.03", 2.1003, _ABSENT):
            with self.subTest(value=value):
                self.assertRefusedBeforeSwiss("SWISS_LIBRARY_VERSION_MISMATCH", version=value)

    def test_binding_version_mismatch_or_malformed(self):
        for value in ("2.10.3.1", "2.10.3.3", "2.10.3.2.post1", "2.10.3.2 ", "2.10.03", "2.10.3"):
            with self.subTest(value=value):
                self.assertRefusedBeforeSwiss("SWISS_BINDING_VERSION_MISMATCH", binding=value)

    def test_missing_binding_metadata_is_not_compatibility(self):
        self.assertRefusedBeforeSwiss("SWISS_BINDING_METADATA_MISSING", binding=None)

    def test_metadata_reader_treats_absent_or_unusable_metadata_as_missing(self):
        original = provenance.binding_distribution_version
        self.addCleanup(original.cache_clear)
        for effect in (metadata.PackageNotFoundError("pyswisseph"), KeyError("Version"), None, "", 2):
            with self.subTest(effect=effect):
                original.cache_clear()
                kwargs = ({"side_effect": effect} if isinstance(effect, BaseException)
                          else {"return_value": effect})
                with mock.patch.object(provenance.metadata, "version", **kwargs):
                    self.assertIsNone(original())
        original.cache_clear()
        with mock.patch.object(provenance.metadata, "version", return_value="2.10.3.2"):
            self.assertEqual(original(), "2.10.3.2")
        original.cache_clear()

    def test_library_checked_before_binding(self):
        self.assertRefusedBeforeSwiss("SWISS_LIBRARY_VERSION_MISMATCH", binding=None, version="2.10.02")

    def test_pins_match_the_packaging_and_conformance_pins(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertIn(f"pyswisseph=={engine.REQUIRED_BINDING_VERSION}", project["dependencies"])
        self.assertIn(f"tzdata=={readiness.REQUIRED_TZDATA_VERSION}", project["dependencies"])
        spec = json.loads((TESTS_DIR / "swiss_conformance" / "spec.json").read_text(encoding="utf-8"))
        text = json.dumps(spec)
        self.assertIn(f'"pyswisseph": "{engine.REQUIRED_BINDING_VERSION}"', text)
        self.assertIn(engine.REQUIRED_SWISS_LIBRARY_VERSION, text)

    def test_no_bypass_switch(self):
        source = (SRC / "sabpuja_kundali" / "engine.py").read_text(encoding="utf-8")
        body = source[source.index("def swiss_runtime"):source.index("def _parse_birth")]
        for token in ("environ", "getenv", "argv", "skip", "bypass", "allow", ">", "<", "startswith"):
            self.assertNotIn(token, body)


class EphemerisManifestTests(unittest.TestCase):
    """Group A: an unreadable or malformed packaged ephemeris manifest is a typed fault
    (before Gate 3C: a JSON position text at exit 2, or a traceback)."""

    def test_unreadable_or_malformed_manifest_is_typed(self):
        from sabpuja_kundali import ephemeris
        cases = (("side_effect", FileNotFoundError("/srv/pkg/ephemeris-manifest.json")),
                 ("side_effect", UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad")),
                 ("return_value", "{not json"), ("return_value", "[]"), ("return_value", '{"files": {}}'))
        for kind, value in cases:
            with self.subTest(value=value):
                resource = mock.Mock()
                setattr(resource.read_text, kind, value)
                with mock.patch.object(ephemeris.resources, "files") as files:
                    files.return_value.joinpath.return_value = resource
                    with self.assertRaises(EphemerisDataError) as ctx:
                        ephemeris.load_manifest()
                self.assertEqual(ctx.exception.code, "EPHEMERIS_MANIFEST_INVALID")
                self.assertNotIn("/", str(ctx.exception))
        self.assertEqual(len(ephemeris.load_manifest()["files"]), 2)



PACKAGED_MANIFEST = Path(engine.__file__).with_name("ephemeris-manifest.json")


def _mutated(change):
    manifest = json.loads(PACKAGED_MANIFEST.read_text(encoding="utf-8"))
    change(manifest)
    return manifest


def _set(entry_field, value):
    def change(m):
        if value is _ABSENT:
            del m["files"][0][entry_field]
        else:
            m["files"][0][entry_field] = value
    return change


def _top(path, value):
    def change(m):
        *parents, last = path
        for key in parents:
            m = m[key]
        if value is _ABSENT:
            del m[last]
        else:
            m[last] = value
    return change


# G3C-MAN-01: syntactically valid JSON whose shape the gate cannot use. Each must be
# EPHEMERIS_MANIFEST_INVALID, never an AttributeError, KeyError or TypeError.
MALFORMED_MANIFESTS = {
    "files [null]": {"files": [None]},
    "files [{required: true}]": {"files": [{"required": True}]},
    "entry is a list": _mutated(lambda m: m["files"].__setitem__(0, ["sepl_18.se1"])),
    "entry is a string": _mutated(lambda m: m["files"].__setitem__(0, "sepl_18.se1")),
    "required missing": _mutated(_set("required", _ABSENT)),
    "required is a string": _mutated(_set("required", "true")),
    "required is 1": _mutated(_set("required", 1)),
    "required is null": _mutated(_set("required", None)),
    "name missing": _mutated(_set("name", _ABSENT)),
    "name not a string": _mutated(_set("name", 7)),
    "name empty": _mutated(_set("name", "")),
    "name is ..": _mutated(_set("name", "..")),
    "name has a directory": _mutated(_set("name", "../sepl_18.se1")),
    "name has a backslash": _mutated(_set("name", "ephe\\sepl_18.se1")),
    "name has a NUL": _mutated(_set("name", "sepl_18.se1\0")),
    "size_bytes missing": _mutated(_set("size_bytes", _ABSENT)),
    "size_bytes a string": _mutated(_set("size_bytes", "484061")),
    "size_bytes a boolean": _mutated(_set("size_bytes", True)),
    "size_bytes a float": _mutated(_set("size_bytes", 484061.0)),
    "size_bytes negative": _mutated(_set("size_bytes", -1)),
    "sha256 missing": _mutated(_set("sha256", _ABSENT)),
    "sha256 not a string": _mutated(_set("sha256", 0)),
    "sha256 uppercase": _mutated(lambda m: m["files"][0].update(sha256=m["files"][0]["sha256"].upper())),
    "sha256 too short": _mutated(lambda m: m["files"][0].update(sha256=m["files"][0]["sha256"][:-1])),
    "manifest_version missing": _mutated(_top(("manifest_version",), _ABSENT)),
    "source missing": _mutated(_top(("source",), _ABSENT)),
    "source.commit not a string": _mutated(_top(("source", "commit"), 1)),
    "coverage missing": _mutated(_top(("coverage",), _ABSENT)),
    "coverage.start_year a string": _mutated(_top(("coverage", "start_year"), "1800")),
}
MANIFEST_INVALID = "EPHEMERIS_MANIFEST_INVALID: ephemeris manifest has an unexpected structure"


@contextlib.contextmanager
def packaged_manifest_text(text):
    """Serve `text` as the packaged ephemeris manifest (the resource, not json.loads)."""
    from sabpuja_kundali import ephemeris
    real_files = ephemeris.resources.files
    resource = mock.Mock()
    resource.read_text.return_value = text

    def files(package):
        root = real_files(package)
        if package != ephemeris.__package__:
            return root  # the timezone manifest and anything else stay real
        wrapped = mock.Mock()
        wrapped.joinpath.side_effect = lambda name: resource if name == ephemeris._MANIFEST_NAME else root.joinpath(name)
        return wrapped

    with mock.patch.object(ephemeris.resources, "files", side_effect=files):
        yield


class MalformedManifestEntryTests(unittest.TestCase):
    """G3C-MAN-01 (QA review on 097f3fa): entry and field shapes are checked before use."""

    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("SE_EPHE_PATH", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_load_manifest_refuses_each_malformed_shape(self):
        from sabpuja_kundali import ephemeris
        for label, manifest in MALFORMED_MANIFESTS.items():
            with self.subTest(label):
                with packaged_manifest_text(json.dumps(manifest)), self.assertRaises(EphemerisDataError) as ctx:
                    ephemeris.load_manifest()
                self.assertEqual(str(ctx.exception), MANIFEST_INVALID)
                self.assertIsNone(ctx.exception.__cause__)

    def test_verify_refuses_each_malformed_entry_supplied_by_a_caller(self):
        from sabpuja_kundali import ephemeris
        for label, manifest in MALFORMED_MANIFESTS.items():
            if not label.startswith(("files", "entry", "required", "name", "size", "sha")):
                continue  # top-level metadata fields are read by load_manifest, not the file gate
            with self.subTest(label):
                with self.assertRaises(EphemerisDataError) as ctx:
                    ephemeris.verify_ephemeris_dir(self._tmp.name, manifest)
                self.assertEqual(str(ctx.exception), MANIFEST_INVALID)

    def test_refusal_order_is_unchanged(self):
        from sabpuja_kundali import ephemeris
        bad = MALFORMED_MANIFESTS["files [null]"]
        with self.assertRaises(EphemerisDataError) as ctx:
            ephemeris.verify_ephemeris_dir("/nonexistent/sabpuja-ephe", bad)
        self.assertEqual(ctx.exception.code, "EPHEMERIS_PATH_MISSING")
        os.environ["SE_EPHE_PATH"] = self._tmp.name
        with self.assertRaises(EphemerisDataError) as ctx:
            ephemeris.verify_ephemeris_dir(self._tmp.name, bad)
        self.assertEqual(ctx.exception.code, "EPHEMERIS_PATH_OVERRIDE")
        del os.environ["SE_EPHE_PATH"]
        # A well-formed manifest still reaches the file checks, and "no required files" keeps its text.
        with self.assertRaises(EphemerisDataError) as ctx:
            ephemeris.verify_ephemeris_dir(self._tmp.name, json.loads(PACKAGED_MANIFEST.read_text()))
        self.assertEqual(str(ctx.exception), "EPHEMERIS_FILE_MISSING: required file sepl_18.se1 not found")
        with self.assertRaises(EphemerisDataError) as ctx:
            ephemeris.verify_ephemeris_dir(self._tmp.name, {"files": [{"name": "x", "required": False}]})
        self.assertEqual(str(ctx.exception), "EPHEMERIS_MANIFEST_INVALID: manifest lists no required files")

    def test_packaged_manifest_is_accepted_unchanged(self):
        from sabpuja_kundali import ephemeris
        raw = PACKAGED_MANIFEST.read_bytes()
        self.assertEqual(ephemeris.load_manifest(), json.loads(raw))
        self.assertEqual(provenance.canonical_sha256(ephemeris.load_manifest()),
                         provenance.canonical_sha256(json.loads(raw)))

    def test_calculate_refuses_before_any_swiss_call(self):
        calls = []
        with fake_runtime(recording_swisseph(calls)), packaged_manifest_text('{"files": [null]}'), \
                self.assertRaises(EphemerisDataError) as ctx:
            calculate(SYNTHETIC, ephe_path=self._tmp.name)
        self.assertEqual(str(ctx.exception), MANIFEST_INVALID)
        self.assertEqual(calls, [])


def _cli_body(kind):
    """Subprocess body: the real CLI module run as __main__ under an injected fault."""
    if kind == "binding_missing":
        runtime, binding = None, None
    elif kind == "fallback":
        runtime, binding = recording_swisseph([], fallback_body=1), engine.REQUIRED_BINDING_VERSION
    elif kind == "library_mismatch":
        runtime, binding = recording_swisseph([], version="2.10.04"), engine.REQUIRED_BINDING_VERSION
    elif kind == "binding_mismatch":
        runtime, binding = recording_swisseph([]), "2.10.3.1"
    elif kind == "metadata_missing":
        runtime, binding = recording_swisseph([]), None
    else:
        runtime, binding = recording_swisseph([]), engine.REQUIRED_BINDING_VERSION
    with contextlib.ExitStack() as stack:
        stack.enter_context(fake_runtime(runtime, binding=binding))
        if kind in ("defect_value", "defect_runtime", "defect_other"):
            exc = {"defect_value": ValueError, "defect_runtime": RuntimeError,
                   "defect_other": KeyError}[kind]("defect /srv/internal 28.6139")
            stack.enter_context(mock.patch.object(engine, "calculate", side_effect=exc))
        if kind.startswith("manifest:"):
            text = json.dumps(MALFORMED_MANIFESTS[kind.split(":", 1)[1]])
            stack.enter_context(packaged_manifest_text(text))
        if kind == "json_recursion":
            stack.enter_context(mock.patch("json.loads", side_effect=RecursionError("deep")))
        runpy.run_module("sabpuja_kundali.cli", run_name="__main__")


def run_cli(kind, request=SYNTHETIC):
    env = {k: v for k, v in os.environ.items() if k not in ("SE_EPHE_PATH", "SABPUJA_EPHE_PATH")}
    env["PYTHONPATH"] = os.pathsep.join([str(TESTS_DIR), str(SRC)])
    code = f"import test_engine_hardening as t; t._cli_body({kind!r})"
    return subprocess.run([sys.executable, "-c", code], input=json.dumps(request),
                          capture_output=True, text=True, env=env, timeout=60)


class CliBoundaryTests(unittest.TestCase):
    """Groups A and D: the real CLI entrypoint in a fresh interpreter."""

    def test_typed_runtime_faults_are_one_private_json_error_with_exit_2(self):
        for kind, code in (("binding_missing", "SWISS_BINDING_MISSING"),
                           ("fallback", "SWISS_EPHEMERIS_FALLBACK_REFUSED"),
                           ("library_mismatch", "SWISS_LIBRARY_VERSION_MISMATCH"),
                           ("binding_mismatch", "SWISS_BINDING_VERSION_MISMATCH"),
                           ("metadata_missing", "SWISS_BINDING_METADATA_MISSING")):
            with self.subTest(kind=kind):
                proc = run_cli(kind)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(proc.stdout, "")
                self.assertEqual(proc.stderr.count("\n"), 1)
                self.assertEqual(json.loads(proc.stderr), {"error": f"{code}: {FIXED[code]}"})
                self.assertNotIn("Traceback", proc.stderr)
                for piece in REQUEST_PIECES + ("/", "\\", str(SRC)):
                    self.assertNotIn(piece, proc.stderr)

    def test_malformed_manifest_is_one_private_json_error_with_exit_2(self):
        for label in ("files [null]", "files [{required: true}]", "name missing", "size_bytes a string",
                      "sha256 missing", "required is a string", "source missing"):
            with self.subTest(label):
                proc = run_cli(f"manifest:{label}")
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(proc.stdout, "")
                self.assertEqual(proc.stderr, json.dumps({"error": MANIFEST_INVALID}) + "\n")
                self.assertNotIn("Traceback", proc.stderr)

    def test_success_still_prints_only_the_chart(self):
        proc = run_cli("success")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, "")
        self.assertEqual(json.loads(proc.stdout)["schema_version"], "0.2.0")

    def test_untyped_exceptions_are_defects_not_refusals(self):
        # Before Gate 3C a bare ValueError or RuntimeError from inside calculate() was printed
        # as an exit-2 {"error"} like a refusal; now only typed engine errors are.
        for kind, name in (("defect_value", "ValueError"), ("defect_runtime", "RuntimeError"),
                           ("defect_other", "KeyError")):
            with self.subTest(kind=kind):
                proc = run_cli(kind)
                self.assertEqual(proc.returncode, 1)
                self.assertEqual(proc.stdout, "")
                self.assertIn(name, proc.stderr)
                self.assertNotIn('{"error"', proc.stderr)

    def test_over_deep_json_is_request_invalid(self):
        proc = run_cli("json_recursion")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stderr), {"error": "REQUEST_INVALID: input must be one JSON object"})

    def test_refusal_output_is_unchanged(self):
        proc = run_cli("success", request={**SYNTHETIC, "latitude": 70.0})
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stderr), {
            "error": "LATITUDE_OUTSIDE_SUPPORTED_BAND: latitude must be between -66 and 66 (inclusive)"})


@unittest.skipIf(DATA is None, f"{DATA_ENV} unset: real-data hardening tests not requested")
class RealRuntimeTests(unittest.TestCase):
    """Groups A, B and D with the pinned binding and data: real fallback, real versions,
    and a failed request never contaminates the next one."""

    @classmethod
    def setUpClass(cls):
        env = {k: v for k, v in os.environ.items() if k not in ("SE_EPHE_PATH", "SABPUJA_EPHE_PATH")}
        env["PYTHONPATH"] = str(SRC)
        code = ("import json; from sabpuja_kundali.engine import calculate; "
                f"print(json.dumps(calculate({SYNTHETIC!r}, ephe_path={DATA!r}), sort_keys=True))")
        cls.reference = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                                       env=env, check=True, timeout=60).stdout

    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("SE_EPHE_PATH", None)

    def assertClean(self):
        chart = calculate(dict(SYNTHETIC), ephe_path=DATA)
        self.assertEqual(json.dumps(chart, sort_keys=True) + "\n", self.reference)

    def test_installed_runtime_is_the_pinned_one(self):
        swe = engine.swiss_runtime()
        self.assertEqual(swe.version, "2.10.03")
        self.assertEqual(metadata.version("pyswisseph"), "2.10.3.2")
        self.assertEqual(provenance.binding_distribution_version(), "2.10.3.2")

    def test_real_moshier_fallback_is_typed_and_the_next_chart_is_clean(self):
        # The gate is bypassed onto an empty folder, so real Swiss falls back to Moshier.
        self.assertClean()
        with tempfile.TemporaryDirectory() as empty:
            with mock.patch.object(engine, "verify_ephemeris_dir", return_value=Path(empty)), \
                    self.assertRaises(ChartComputationError) as ctx:
                calculate(dict(SYNTHETIC), ephe_path=empty)
            self.assertNotIn(empty, str(ctx.exception))
        self.assertEqual(ctx.exception.code, "SWISS_EPHEMERIS_FALLBACK_REFUSED")
        self.assertTrue(lock_is_free())
        self.assertClean()

    def test_version_failures_do_not_touch_swiss_or_the_next_chart(self):
        import swisseph as swe
        for patch, code in ((mock.patch.object(swe, "version", "2.10.04"), "SWISS_LIBRARY_VERSION_MISMATCH"),
                            (mock.patch.object(provenance, "binding_distribution_version", return_value="2.10.3.1"),
                             "SWISS_BINDING_VERSION_MISMATCH"),
                            (mock.patch.object(provenance, "binding_distribution_version", return_value=None),
                             "SWISS_BINDING_METADATA_MISSING")):
            with self.subTest(code=code):
                with patch, mock.patch.object(swe, "julday") as julday, \
                        mock.patch.object(swe, "set_ephe_path") as path, \
                        mock.patch.object(swe, "calc_ut") as calc, \
                        self.assertRaises(ChartComputationError) as ctx:
                    calculate(dict(SYNTHETIC), ephe_path=DATA)
                self.assertEqual(ctx.exception.code, code)
                for call in (julday, path, calc):
                    call.assert_not_called()
                self.assertClean()

    def test_missing_binding_then_clean_chart(self):
        with mock.patch.dict(sys.modules, {"swisseph": None}), self.assertRaises(ChartComputationError) as ctx:
            calculate(dict(SYNTHETIC), ephe_path=DATA)
        self.assertEqual(ctx.exception.code, "SWISS_BINDING_MISSING")
        self.assertClean()

    def test_real_cli_success_bytes_are_unchanged_by_the_boundary(self):
        env = {k: v for k, v in os.environ.items() if k != "SE_EPHE_PATH"}
        env.update(PYTHONPATH=str(SRC), SABPUJA_EPHE_PATH=DATA)
        proc = subprocess.run([sys.executable, "-m", "sabpuja_kundali.cli"], input=json.dumps(SYNTHETIC),
                              capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, "")
        chart = json.loads(proc.stdout)
        self.assertEqual(proc.stdout, json.dumps(chart, ensure_ascii=False, indent=2) + "\n")
        self.assertEqual(json.dumps(chart, sort_keys=True) + "\n", self.reference)
        self.assertIsNone(re.search(r"Traceback|SWISS_", proc.stdout))


if __name__ == "__main__":
    unittest.main()
