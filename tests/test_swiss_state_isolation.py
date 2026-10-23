"""P9: Swiss Ephemeris global-state isolation regression tests (KUN-03).

pyswisseph keeps process-wide state (ephemeris path, sidereal mode and its
flag bits, Delta T settings, open file handles). These tests prove that one
chart request cannot be influenced by state left behind by any earlier caller,
thread or failed request, and that the tests themselves fail when the engine's
state reset or lock is deliberately broken.

Synthetic birth details only. Requires the pinned data in SABPUJA_TEST_EPHE_PATH
(same rule as test_swiss_integration: unset skips, set-but-wrong errors). The
static lock-contract test runs without data.
"""
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager, nullcontext
from pathlib import Path
from unittest import mock

from sabpuja_kundali import engine
from sabpuja_kundali.engine import ChartComputationError, calculate
from sabpuja_kundali.ephemeris import EphemerisDataError, verify_ephemeris_dir

DATA_ENV = "SABPUJA_TEST_EPHE_PATH"
DATA = os.environ.get(DATA_ENV)
TESTS_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = Path(engine.__file__).resolve().parent

# Synthetic inputs inside every currently proposed policy (post-1970, |lat| < 66).
REQUESTS = [
    {"birth_datetime": "2000-01-01T17:30:00+05:30", "timezone": "Asia/Kolkata",
     "latitude": 28.6139, "longitude": 77.2090},
    {"birth_datetime": "1975-08-15T06:45:00+05:30", "timezone": "Asia/Kolkata",
     "latitude": 19.0760, "longitude": 72.8777},
    {"birth_datetime": "2024-02-29T10:15:00+11:00", "timezone": "Australia/Sydney",
     "latitude": -33.8688, "longitude": 151.2093},
    {"birth_datetime": "1988-07-04T21:10:00-04:00", "timezone": "America/New_York",
     "latitude": 40.7128, "longitude": -74.0060},
    {"birth_datetime": "2010-12-21T08:00:00+00:00", "timezone": "Atlantic/Reykjavik",
     "latitude": 64.1466, "longitude": -21.9426},
]
PRIMARY = REQUESTS[0]
# KUN-03 reconciliation: P2 (SCI-01g) refuses |latitude| > 66 with
# LATITUDE_OUTSIDE_SUPPORTED_BAND before the ephemeris check, the lock and Swiss,
# and P3's b"W" Lagna computes at any latitude, so a polar request no longer
# reaches the lock. The in-lock refusal path is exercised by injection instead.


_local = threading.local()


@contextmanager
def _recording():
    """Wrap Swiss once so each thread records only its own request's raw values."""
    import swisseph as swe
    real_calc, real_houses = swe.calc_ut, swe.houses_ex

    def calc(jd, body, flags):
        pos, ret = real_calc(jd, body, flags)
        raw = getattr(_local, "raw", None)
        if raw is not None:
            raw.append(["calc_ut", body, flags, ret, [float(x).hex() for x in pos]])
        return pos, ret

    def houses(jd, lat, lon, hsys, flags):
        cusps, ascmc = real_houses(jd, lat, lon, hsys, flags)
        raw = getattr(_local, "raw", None)
        if raw is not None:
            raw.append(["houses_ex", hsys.decode(), flags, [float(x).hex() for x in ascmc]])
        return cusps, ascmc

    with mock.patch.object(swe, "calc_ut", calc), mock.patch.object(swe, "houses_ex", houses):
        yield


def _capture(request, ephe_path, patch=True):
    """Run calculate and record every unrounded Swiss result it consumed.

    Returns (output, raw) where raw lists float.hex of each calc_ut position
    and its returned flag, and of the houses_ex ascmc values, in call order.
    patch=False reuses an enclosing _recording() (required across threads,
    because mock.patch is not thread-safe).
    """
    _local.raw = []
    try:
        with (_recording() if patch else nullcontext()):
            output = calculate(request, ephe_path=ephe_path)
        return output, _local.raw
    finally:
        _local.raw = None


def _emit(ephe_path):
    """Fresh-interpreter baseline: print every request's output and raw values."""
    print(json.dumps([_capture(r, ephe_path) for r in REQUESTS], sort_keys=True))


def _fresh_process_baseline(ephe_path):
    env = {k: v for k, v in os.environ.items() if k != "SE_EPHE_PATH"}
    env["PYTHONPATH"] = os.pathsep.join(
        [str(TESTS_DIR), str(PACKAGE_DIR.parent)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    proc = subprocess.run(
        [sys.executable, "-c", f"import test_swiss_state_isolation as t; t._emit({ephe_path!r})"],
        capture_output=True, text=True, env=env, check=True)
    return [tuple(item) for item in json.loads(proc.stdout)]


def _sidereal_contaminations():
    import swisseph as swe
    lahiri = swe.SIDM_LAHIRI
    cases = {
        "fagan_bradley": (swe.SIDM_FAGAN_BRADLEY, 0, 0),
        "krishnamurti": (swe.SIDM_KRISHNAMURTI, 0, 0),
        "raman": (swe.SIDM_RAMAN, 0, 0),
        "lahiri_1940": (43, 0, 0),
        "lahiri_vp285": (44, 0, 0),
        "lahiri_icrc": (46, 0, 0),
        "true_citra": (swe.SIDM_TRUE_CITRA, 0, 0),
        "user_t0_ayan": (swe.SIDM_USER, 2451545.0, 10.0),
        "user_ut": (swe.SIDM_USER | swe.SIDBIT_USER_UT, 2451545.0, 10.0),
    }
    for bit in ("SIDBIT_PREC_ORIG", "SIDBIT_ECL_T0", "SIDBIT_SSY_PLANE",
                "SIDBIT_ECL_DATE", "SIDBIT_NO_PREC_OFFSET"):
        cases[f"lahiri|{bit}"] = (lahiri | getattr(swe, bit), 0, 0)
        cases[f"fagan|{bit}"] = (swe.SIDM_FAGAN_BRADLEY | getattr(swe, bit), 0, 0)
    return cases


def _contaminate_sidereal(mode, t0, ayan_t0):
    import swisseph as swe
    swe.set_sid_mode(mode, t0, ayan_t0)
    # Exercise the mode so any lazily cached precession/ayanamsa state is built.
    swe.calc_ut(2451545.0, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    swe.houses_ex(2451545.0, 10.0, 10.0, b"P", swe.FLG_SIDEREAL)


def _swiss_state_is_thread_local():
    """pyswisseph builds Swiss with __thread storage on Linux (sweodef.h TLS)
    but process-global state on macOS and Windows. Probe which one we run."""
    import swisseph as swe
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    before = swe.get_ayanamsa_ut(2451545.0)
    t = threading.Thread(target=lambda: swe.set_sid_mode(swe.SIDM_RAMAN, 0, 0))
    t.start()
    t.join()
    after = swe.get_ayanamsa_ut(2451545.0)
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    return after == before


@contextmanager
def _mutant(name):
    """Deliberately broken engine variants; isolation tests must fail under each."""
    import swisseph as swe
    if name == "no_set_sid_mode":
        with mock.patch.object(swe, "set_sid_mode", lambda *a, **k: None):
            yield
    elif name == "no_set_ephe_path":
        with mock.patch.object(swe, "set_ephe_path", lambda *a, **k: None):
            yield
    elif name == "no_reset_at_all":
        with mock.patch.object(swe, "set_sid_mode", lambda *a, **k: None), \
                mock.patch.object(swe, "set_ephe_path", lambda *a, **k: None):
            yield
    elif name == "no_lock":
        with mock.patch.object(engine, "_SWISS_LOCK", nullcontext()):
            yield
    else:
        raise KeyError(name)


class SwissLockContractTests(unittest.TestCase):
    """Static contract: Swiss is only touched under the engine lock (no data needed)."""

    # Pure arithmetic, no global state read or written.
    STATELESS = {"julday"}

    def test_only_engine_imports_swisseph(self):
        importers = []
        for path in sorted(PACKAGE_DIR.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                if any(n.split(".")[0] == "swisseph" for n in names):
                    importers.append(path.name)
        self.assertEqual(sorted(set(importers)), ["engine.py"])

    def test_every_stateful_swiss_call_is_inside_the_lock(self):
        tree = ast.parse((PACKAGE_DIR / "engine.py").read_text(encoding="utf-8"))
        outside, inside = [], []

        def visit(node, locked):
            if isinstance(node, ast.With) and any(
                    isinstance(i.context_expr, ast.Name) and i.context_expr.id == "_SWISS_LOCK"
                    for i in node.items):
                locked = True
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == "swe"):
                (inside if locked else outside).append(node.func.attr)
            for child in ast.iter_child_nodes(node):
                visit(child, locked)

        visit(tree, False)
        self.assertEqual(sorted(set(outside) - self.STATELESS), [],
                         "Swiss calls outside _SWISS_LOCK can read or race global state")
        # The reset calls exist and precede computation inside the lock.
        self.assertEqual(inside[:2], ["set_ephe_path", "set_sid_mode"])
        self.assertTrue({"calc_ut", "houses_ex"} <= set(inside))


@unittest.skipIf(DATA is None, f"{DATA_ENV} unset: real-data isolation tests not requested")
class SwissStateIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            with mock.patch.dict(os.environ):
                os.environ.pop("SE_EPHE_PATH", None)
                verify_ephemeris_dir(DATA)
        except EphemerisDataError as exc:
            raise AssertionError(f"{DATA_ENV} is set but does not hold the pinned required files: {exc}") from None
        # Reference values from an interpreter that never touched Swiss before.
        cls.baseline = _fresh_process_baseline(DATA)

    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("SE_EPHE_PATH", None)
        import swisseph
        self.swe = swisseph

    def assertMatchesBaseline(self, index=0, msg=None):
        output, raw = _capture(REQUESTS[index], DATA)
        base_output, base_raw = self.baseline[index]
        self.assertEqual(raw, base_raw, msg)
        self.assertEqual(json.loads(json.dumps(output, sort_keys=True)), base_output, msg)

    def assertAllMatchBaseline(self, msg=None):
        for index in range(len(REQUESTS)):
            with self.subTest(request=index):
                self.assertMatchesBaseline(index, msg)

    # 1. Explicit initialization on every call --------------------------------

    def test_every_call_sets_verified_path_and_lahiri_before_computing(self):
        swe = self.swe
        events = []
        real = {n: getattr(swe, n) for n in ("set_ephe_path", "set_sid_mode", "calc_ut", "houses_ex")}

        def spy(name):
            def call(*args):
                events.append((name, args))
                return real[name](*args)
            return call

        patches = [mock.patch.object(swe, n, spy(n)) for n in real]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        verified = str(Path(DATA).resolve())
        for round_ in range(2):
            for index, request in enumerate(REQUESTS):
                with self.subTest(round=round_, request=index):
                    events.clear()
                    calculate(request, ephe_path=DATA)
                    names = [e[0] for e in events]
                    self.assertEqual(names[:2], ["set_ephe_path", "set_sid_mode"])
                    self.assertEqual(names.count("set_ephe_path"), 1)
                    self.assertEqual(names.count("set_sid_mode"), 1)
                    self.assertEqual(events[0][1], (verified,))
                    self.assertEqual(events[1][1], (swe.SIDM_LAHIRI, 0, 0))
                    for name, args in events[2:]:
                        if name == "calc_ut":
                            self.assertEqual(args[2], swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
                        elif name == "houses_ex":
                            self.assertEqual(args[4], swe.FLG_SIDEREAL)

    def test_isolated_value_differs_from_unreset_swiss_default(self):
        # Guard against a vacuous baseline: Swiss's own default (Fagan/Bradley)
        # gives a different sidereal Lagna, so a missing reset is observable.
        swe = self.swe
        jd = 2451545.0
        swe.set_ephe_path(DATA)
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        lahiri = swe.houses_ex(jd, 28.6139, 77.2090, b"P", swe.FLG_SIDEREAL)[1][0]
        swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY, 0, 0)
        fagan = swe.houses_ex(jd, 28.6139, 77.2090, b"P", swe.FLG_SIDEREAL)[1][0]
        self.assertGreater(abs(lahiri - fagan) * 3600, 3000)

    # 2-3. Earlier sidereal modes and flag bits cannot leak -------------------

    def test_previous_sidereal_modes_and_flag_bits_do_not_leak(self):
        for name, args in _sidereal_contaminations().items():
            with self.subTest(contamination=name):
                _contaminate_sidereal(*args)
                self.assertAllMatchBaseline(f"state left by {name} leaked into the chart")

    def test_prec_orig_cleared_even_after_plain_lahiri_reset_by_caller(self):
        # KUN-02 finding: set_sid_mode(LAHIRI) alone does not undo SIDBIT_PREC_ORIG.
        swe = self.swe
        _contaminate_sidereal(swe.SIDM_LAHIRI | swe.SIDBIT_PREC_ORIG, 0, 0)
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        leaked = swe.houses_ex(2451545.0, 28.6139, 77.2090, b"P", swe.FLG_SIDEREAL)[1][0]
        swe.set_ephe_path(DATA)
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        clean = swe.houses_ex(2451545.0, 28.6139, 77.2090, b"P", swe.FLG_SIDEREAL)[1][0]
        self.assertNotEqual(leaked, clean, "precondition: the Swiss leak is still reproducible")
        _contaminate_sidereal(swe.SIDM_LAHIRI | swe.SIDBIT_PREC_ORIG, 0, 0)
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        self.assertAllMatchBaseline()

    def test_other_process_wide_settings_do_not_leak(self):
        swe = self.swe
        cases = {
            "tidal_acceleration": lambda: swe.set_tid_acc(swe.TIDAL_DE200),
            "topocentric_observer": lambda: swe.set_topo(77.2, 28.6, 5000.0),
            "lapse_rate": lambda: swe.set_lapse_rate(0.01),
            "swe_close": swe.close,
            "foreign_ephe_path": lambda: swe.set_ephe_path(tempfile.gettempdir()),
            "moshier_call": lambda: swe.calc_ut(2451545.0, swe.MOON, swe.FLG_MOSEPH | swe.FLG_SIDEREAL),
        }
        for name, contaminate in cases.items():
            with self.subTest(contamination=name):
                contaminate()
                self.assertAllMatchBaseline(f"state left by {name} leaked into the chart")

    def test_known_defect_engine_inherits_user_delta_t(self):
        # KNOWN DEFECT, pinned so it cannot change unnoticed (fix awaiting owner
        # authorization; see the P9 PR). swe.set_delta_t_userdef survives
        # set_ephe_path and swe.close, and the engine never restores
        # DELTAT_AUTOMATIC, so an earlier caller on the same thread shifts every
        # later chart (Moon by about 400 arcsec for 0.01 day). The fix PR must
        # turn this into an equality assertion against the baseline. Not marked
        # expectedFailure because the documented release gate requires a bare OK.
        # KUN-03 reconciliation: still reproduced on the P1+P2-P8 integration
        # baseline (2d1300f). This test passing means the defect is PRESENT; it is an
        # open release gate, and no production Delta T change is authorized.
        swe = self.swe
        swe.set_delta_t_userdef(0.01)
        try:
            output, raw = _capture(PRIMARY, DATA)
        finally:
            swe.set_delta_t_userdef(swe.DELTAT_AUTOMATIC)
        self.assertNotEqual(raw, self.baseline[0][1])
        # Restoring automatic Delta T (the proposed fix) gives the baseline back.
        self.assertMatchesBaseline()

    # 4. Lock prevents request-level interference -----------------------------

    def _interfere_mid_request(self):
        """Inside the first calc_ut of a request, let another thread try to switch
        Swiss to Fagan/Bradley through the engine lock. Returns (output, raw,
        whether the interferer ran while the request was still in progress)."""
        swe = self.swe
        real_calc = swe.calc_ut
        state = {"armed": True, "ran_inside": None}
        done = threading.Event()

        def interferer():
            with engine._SWISS_LOCK:
                swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY, 0, 0)
            done.set()

        def calc(*args):
            if state["armed"]:
                state["armed"] = False
                threading.Thread(target=interferer, daemon=True).start()
                # With a real lock the interferer blocks until the request ends.
                state["ran_inside"] = done.wait(1.0)
            return real_calc(*args)

        with mock.patch.object(swe, "calc_ut", calc):
            output, raw = _capture(PRIMARY, DATA)
        self.assertTrue(done.wait(10), "interferer never acquired the lock")
        return output, raw, state["ran_inside"]

    def test_lock_blocks_interference_inside_a_request(self):
        output, raw, ran_inside = self._interfere_mid_request()
        self.assertFalse(ran_inside, "another thread changed Swiss state mid-request")
        self.assertEqual(raw, self.baseline[0][1])
        self.assertEqual(json.loads(json.dumps(output, sort_keys=True)), self.baseline[0][0])

    def test_first_request_on_a_new_thread_matches_baseline(self):
        # On TLS builds a new thread starts from Swiss defaults (Fagan/Bradley,
        # no ephemeris path, so Moshier); the engine must initialize per call.
        results = []

        def run():
            results.append(_capture(PRIMARY, DATA, patch=False))

        with _recording():
            t = threading.Thread(target=run)
            t.start()
            t.join(60)
        self.assertEqual(len(results), 1)
        output, raw = results[0]
        self.assertEqual(raw, self.baseline[0][1])
        self.assertEqual(json.loads(json.dumps(output, sort_keys=True)), self.baseline[0][0])

    def test_concurrent_requests_are_bit_identical_to_fresh_process(self):
        swe = self.swe
        results, errors = {}, []
        stop = threading.Event()

        def worker(wid):
            try:
                for rep in range(6):
                    index = (wid + rep) % len(REQUESTS)
                    output, raw = _capture(REQUESTS[index], DATA, patch=False)
                    results[(wid, rep)] = (index, json.loads(json.dumps(output, sort_keys=True)), raw)
            except Exception as exc:  # surfaced below
                errors.append(repr(exc))

        def hostile():
            # A cooperating foreign caller: always uses the engine lock.
            modes = [swe.SIDM_FAGAN_BRADLEY, swe.SIDM_LAHIRI | swe.SIDBIT_PREC_ORIG, swe.SIDM_RAMAN]
            i = 0
            while not stop.is_set():
                with engine._SWISS_LOCK:
                    _contaminate_sidereal(modes[i % len(modes)], 0, 0)
                i += 1

        noise = [threading.Thread(target=hostile, daemon=True) for _ in range(2)]
        workers = [threading.Thread(target=worker, args=(w,)) for w in range(8)]
        with _recording():
            for t in noise + workers:
                t.start()
            for t in workers:
                t.join(120)
            stop.set()
            for t in noise:
                t.join(10)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 8 * 6)
        for key, (index, output, raw) in sorted(results.items()):
            with self.subTest(worker=key[0], rep=key[1], request=index):
                self.assertEqual(raw, self.baseline[index][1])
                self.assertEqual(output, self.baseline[index][0])

    # 5. Repeated identical inputs are bit-identical --------------------------

    def test_repeated_interleaved_inputs_bit_identical(self):
        for round_ in range(3):
            for index in (0, 3, 1, 0, 4, 2, 0):
                with self.subTest(round=round_, request=index):
                    self.assertMatchesBaseline(index)

    def test_in_process_matches_fresh_process_for_every_request(self):
        self.assertAllMatchBaseline()
        # And a second fresh interpreter reproduces the first exactly.
        self.assertEqual(_fresh_process_baseline(DATA), self.baseline)

    # 6. No silent Moshier fallback -------------------------------------------

    def test_swiss_reports_swieph_for_every_body(self):
        swe = self.swe
        _, raw = _capture(PRIMARY, DATA)
        calcs = [entry for entry in raw if entry[0] == "calc_ut"]
        self.assertEqual(len(calcs), 8)
        for entry in calcs:
            self.assertTrue(entry[3] & swe.FLG_SWIEPH)
            self.assertFalse(entry[3] & swe.FLG_MOSEPH)

    def test_unreadable_data_after_verification_refuses_moshier(self):
        # Even if the manifest gate were bypassed, Swiss falling back to Moshier
        # must refuse the chart, and must not poison the next valid request.
        with tempfile.TemporaryDirectory() as empty:
            with mock.patch.object(engine, "verify_ephemeris_dir", return_value=Path(empty)):
                with self.assertRaisesRegex(RuntimeError, "refused Moshier fallback"):
                    calculate(PRIMARY, ephe_path=empty)
        self.assertAllMatchBaseline()

    # 7. Missing or incorrect files fail closed, even after a warm start -------

    def test_bad_directory_fails_closed_after_successful_request(self):
        self.assertMatchesBaseline()  # Swiss now has the pinned files open
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shutil.copy(Path(DATA, "sepl_18.se1"), folder / "sepl_18.se1")
            cases = {"EPHEMERIS_FILE_MISSING": folder}
            corrupt = Path(tmp, "corrupt")
            corrupt.mkdir()
            shutil.copy(Path(DATA, "sepl_18.se1"), corrupt / "sepl_18.se1")
            data = bytearray(Path(DATA, "semo_18.se1").read_bytes())
            data[len(data) // 2] ^= 0xFF
            (corrupt / "semo_18.se1").write_bytes(bytes(data))
            cases["EPHEMERIS_FILE_MISMATCH"] = corrupt
            cases["EPHEMERIS_PATH_MISSING"] = Path(tmp, "absent")
            for code, path in cases.items():
                with self.subTest(code=code):
                    with mock.patch.object(self.swe, "calc_ut") as calc:
                        with self.assertRaises(EphemerisDataError) as ctx:
                            calculate(PRIMARY, ephe_path=str(path))
                    self.assertEqual(ctx.exception.code, code)
                    calc.assert_not_called()
        os.environ["SE_EPHE_PATH"] = DATA
        with self.assertRaises(EphemerisDataError) as ctx:
            calculate(PRIMARY, ephe_path=DATA)
        self.assertEqual(ctx.exception.code, "EPHEMERIS_PATH_OVERRIDE")
        del os.environ["SE_EPHE_PATH"]
        self.assertAllMatchBaseline()

    # 8. Exception paths leave no persistent state ----------------------------

    def _lock_is_free(self):
        # Probe from another thread: an RLock is re-entrant for its owner.
        acquired = []

        def probe():
            ok = engine._SWISS_LOCK.acquire(timeout=2)
            acquired.append(ok)
            if ok:
                engine._SWISS_LOCK.release()

        t = threading.Thread(target=probe)
        t.start()
        t.join(5)
        return acquired == [True]

    def test_band_refusal_never_reaches_the_lock_or_swiss(self):
        # P2: refused before the ephemeris check, the lock and any Swiss call.
        swe = self.swe
        entered = []

        class RecordingLock:
            def __enter__(self):
                entered.append(True)
                return self

            def __exit__(self, *exc):
                return False

        def forbidden(*args, **kwargs):
            raise AssertionError("Swiss was called for a band refusal")

        with mock.patch.object(engine, "_SWISS_LOCK", RecordingLock()), \
                mock.patch.object(engine, "verify_ephemeris_dir", side_effect=forbidden), \
                mock.patch.object(swe, "calc_ut", forbidden), mock.patch.object(swe, "houses_ex", forbidden), \
                mock.patch.object(swe, "set_ephe_path", forbidden), mock.patch.object(swe, "set_sid_mode", forbidden):
            for latitude in (70.0, -70.0, 66.000001, 89.9):
                with self.subTest(latitude=latitude):
                    with self.assertRaises(engine.UnsupportedInputError) as ctx:
                        calculate({**PRIMARY, "latitude": latitude}, ephe_path=DATA)
                    self.assertEqual(ctx.exception.code, "LATITUDE_OUTSIDE_SUPPORTED_BAND")
        self.assertEqual(entered, [])
        self.assertTrue(self._lock_is_free())
        self.assertAllMatchBaseline()

    def test_refusals_inside_lock_leave_no_state(self):
        # A real in-lock refusal: Swiss fails inside houses_ex after a foreign state
        # change, and the engine raises ASCENDANT_UNCOMPUTABLE from inside the lock.
        swe = self.swe
        real_calc, real_houses = swe.calc_ut, swe.houses_ex
        inside, planet_calls, result = [], [], None

        def counting_calc(*args):
            planet_calls.append(engine._SWISS_LOCK._is_owned())
            return real_calc(*args)

        def failing_houses(*args):
            inside.append((engine._SWISS_LOCK._is_owned(), args[3]))
            swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY | swe.SIDBIT_PREC_ORIG, 0, 0)
            swe.set_ephe_path(None)
            raise swe.Error("synthetic houses failure")

        with mock.patch.object(swe, "calc_ut", counting_calc), mock.patch.object(swe, "houses_ex", failing_houses):
            with self.assertRaises(ChartComputationError) as ctx:
                result = calculate(PRIMARY, ephe_path=DATA)
        self.assertIs(swe.houses_ex, real_houses)
        self.assertIsNone(result)  # no partial chart
        self.assertEqual(ctx.exception.code, "ASCENDANT_UNCOMPUTABLE")
        # The whole locked path ran: 8 planet calls, then the b"W" ascendant call, all under the lock.
        self.assertEqual(planet_calls, [True] * 8)
        self.assertEqual(inside, [(True, b"W")])
        self.assertTrue(self._lock_is_free())
        self.assertAllMatchBaseline()

    def test_exception_mid_calculation_after_foreign_state_leaves_no_state(self):
        swe = self.swe
        real_calc = swe.calc_ut
        calls = {"n": 0}

        def failing(*args):
            calls["n"] += 1
            if calls["n"] == 3:
                # Foreign state change, then a crash, both inside the request.
                swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY | swe.SIDBIT_PREC_ORIG, 0, 0)
                raise swe.Error("synthetic failure")
            return real_calc(*args)

        with mock.patch.object(swe, "calc_ut", failing):
            with self.assertRaises(swe.Error):
                calculate(PRIMARY, ephe_path=DATA)
        self.assertTrue(self._lock_is_free())
        self.assertAllMatchBaseline()

    def test_invalid_requests_leave_no_state(self):
        bad = [
            {**PRIMARY, "latitude": 95.0},
            {**PRIMARY, "birth_datetime": "2000-01-01T17:30:00"},
            {**PRIMARY, "timezone": "Not/AZone"},
            {**PRIMARY, "birth_datetime": "1850-01-01T12:00:00+05:53"},
        ]
        for request in bad:
            with self.assertRaises(ValueError):
                calculate(request, ephe_path=DATA)
        self.assertTrue(self._lock_is_free())
        self.assertAllMatchBaseline()

    # 9. The tests detect deliberately broken resets --------------------------

    def _isolation_holds(self, mutant, contamination):
        try:
            if contamination:
                _contaminate_sidereal(*contamination)
            with _mutant(mutant):
                for index in range(len(REQUESTS)):
                    output, raw = _capture(REQUESTS[index], DATA)
                    if raw != self.baseline[index][1]:
                        return False
            return True
        finally:
            # Leave the process clean for later tests.
            self.swe.set_ephe_path(DATA)
            self.swe.set_sid_mode(self.swe.SIDM_LAHIRI, 0, 0)

    def test_detects_missing_sidereal_mode_reset(self):
        swe = self.swe
        swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY, 0, 0)
        with _mutant("no_set_sid_mode"):
            output, raw = _capture(PRIMARY, DATA)
        self.assertNotEqual(raw, self.baseline[0][1])
        self.assertFalse(self._isolation_holds("no_set_sid_mode", (swe.SIDM_RAMAN, 0, 0)))

    def test_detects_missing_ephe_path_reset(self):
        # set_sid_mode alone cannot clear SIDBIT_PREC_ORIG; only set_ephe_path does.
        swe = self.swe
        self.assertFalse(self._isolation_holds(
            "no_set_ephe_path", (swe.SIDM_LAHIRI | swe.SIDBIT_PREC_ORIG, 0, 0)))

    def test_detects_missing_reset_entirely(self):
        swe = self.swe
        self.assertFalse(self._isolation_holds("no_reset_at_all", (swe.SIDM_FAGAN_BRADLEY, 0, 0)))

    def test_detects_missing_lock(self):
        with _mutant("no_lock"):
            output, raw, ran_inside = self._interfere_mid_request()
        self.swe.set_ephe_path(DATA)
        self.swe.set_sid_mode(self.swe.SIDM_LAHIRI, 0, 0)
        # Deterministic on every platform: without the lock another lock user
        # ran in the middle of the request.
        self.assertTrue(ran_inside)
        if not _swiss_state_is_thread_local():
            # Process-global Swiss (macOS/Windows builds): its Fagan switch also
            # reaches this request's numbers.
            self.assertNotEqual(raw, self.baseline[0][1])

    def test_mutants_pass_without_contamination(self):
        # The mutants are realistic: in a clean process they produce correct
        # charts, so only the isolation tests (not ordinary tests) catch them.
        self.swe.set_ephe_path(DATA)
        self.swe.set_sid_mode(self.swe.SIDM_LAHIRI, 0, 0)
        for mutant in ("no_set_sid_mode", "no_set_ephe_path", "no_reset_at_all", "no_lock"):
            with self.subTest(mutant=mutant):
                self.assertTrue(self._isolation_holds(mutant, None))


if __name__ == "__main__":
    unittest.main()
