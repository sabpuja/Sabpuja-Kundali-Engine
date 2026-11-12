"""The frozen 14-page English Janam Kundali Essentials edition (KUN-RC-ESS-001, KUN-RC-COM-001 phase 1).

Essentials is the opt-in 14-page sunrise and Vara edition (KUN-PAN-RPT-002) with three fixed choices and a few
English sentences replaced, nothing else:

* English only. Any other locale is refused; the edition has no Hindi text.
* Traditional Tithi, Karana and Yoga names stay off (names=None). The QA preview and customer names are refused.
* The owner's report palette ("baseline", OD-10) and customer mode (synthetic=False), as on the preview route.
* `essentials_en.json` replaces the development-preview and pending-QA notices of pages 12 and 13 and the
  ten-page "Hindi ... separate edition" exclusion, which would be untrue of an English-only paid edition.
* It also replaces nine sunrise and Vara page strings with customer English (KUN-PAN-VARA-COPY-001, from the
  scientific review KUN-PAN-VARA-RELEASE-001: method wording R1-R6, the first-supported-date note and the
  Birth and sunrise card). Text only: no value, rule or layout changes, and the development catalogs are unchanged.

The renderers are called through their existing entry point with a validated overlay; without the overlay they are
unchanged, so the 10-, 13- and 14-page pins stay byte-identical. `essentials-edition-manifest.json` pins every
source file the edition is drawn from (renderers, catalogs, fonts, logo, chart engine, Panchanga package, places,
form handler); a test regenerates it, so any change to the edition is explicit.

Everything is in memory: nothing is written to disk, nothing is logged, and a refusal carries a fixed code and
message, never the birth details or the name.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

try:
    from . import premium_report as pr
    from . import report_locale as loc
except ImportError:  # loaded by path or run as a script
    import premium_report as pr
    import report_locale as loc

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
EDITION = 'janam-kundali-essentials-en/1'
LOCALE = 'en'
PALETTE = 'baseline'
CATALOG_PATH = ROOT / 'essentials_en.json'
CATALOG_SHA256 = '4d9a22e7d69ae1492cb9e2a5729fa16194b7db0976af2e8cbe3d8cf4cf24e9b3'
MANIFEST_PATH = ROOT / 'essentials-edition-manifest.json'
PAGES = 14
OVERLAY_KEYS = ('method.exc5', 'pm.status', 'pm.status_title', 'v.after', 'v.before', 'v.intro', 'v.m.checks_value',
                'v.m.convention_value', 'v.m.data_value', 'v.m.times_value', 'v.near', 'v.status', 'v.sub.outside')
# Released only when the owner approves the wording in chat after independent English QA (KUN-RC-COM-001).
WORDING_STATUS_RELEASED = 'APPROVED_FOR_CUSTOMER_RELEASE'

# Files the edition is drawn from, pinned by the manifest. Paths are repository-relative.
SOURCE_FILES = (
    'prototype/kundali_prototype/places.json',
    'prototype/kundali_prototype/places.py',
    'prototype/kundali_prototype/server.py',
    'prototype/kundali_prototype/static/brand/sabpuja-logo-horizontal-color.svg',
    'report/phase1/display_name.py',
    'report/phase1/essentials.py',
    'report/phase1/essentials_en.json',
    'report/phase1/panchanga_names.json',
    'report/phase1/panchanga_names.py',
    'report/phase1/panchanga_report.py',
    'report/phase1/premium_layout.py',
    'report/phase1/premium_report.py',
    'report/phase1/premium_theme.json',
    'report/phase1/report_i18n.json',
    'report/phase1/report_locale.py',
    'report/phase1/report_panchanga_i18n.json',
    'report/phase1/report_vara_i18n.json',
    'report/phase1/vara_report.py',
)
SOURCE_DIRS = ('prototype/kundali_prototype/static/fonts/', 'src/sabpuja_kundali/')


class EssentialsError(ValueError):
    """A refusal with a fixed status, code, message and category, and the form handler's `extra` fields (for
    example the two offsets of a repeated local hour, `choices`). It never carries the name or other input text."""

    def __init__(self, status: int, code: str, message: str, category: str = 'request', extra: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.category = status, code, message, category
        self.extra = dict(extra or {})


InputRefusal = EssentialsError   # the name the commerce package uses


def _load_catalog() -> dict:
    data = CATALOG_PATH.read_bytes()
    if hashlib.sha256(data).hexdigest() != CATALOG_SHA256:
        raise RuntimeError('Essentials catalog does not match its pinned SHA-256')
    doc = json.loads(data)
    if doc.get('edition') != EDITION or tuple(sorted(doc.get('strings', {}))) != OVERLAY_KEYS:
        raise RuntimeError('Essentials catalog structure changed')
    for key, entry in doc['strings'].items():
        if set(entry) != {LOCALE} or not isinstance(entry[LOCALE], str) or not entry[LOCALE].strip():
            raise RuntimeError(f'Essentials catalog entry must be one English string: {key}')
    return doc


CATALOG = _load_catalog()
OVERLAY = {key: dict(entry) for key, entry in CATALOG['strings'].items()}


def release_problems() -> list[str]:
    """Why the edition may not yet be sold. Empty only once the owner has approved the wording."""
    problems = []
    if CATALOG['wording_status'] != WORDING_STATUS_RELEASED:
        problems.append(f"Essentials wording is {CATALOG['wording_status']}")
    return problems


def generate(response: dict, panchanga_doc: dict, vara_doc: dict, display_name: str | None = None,
             *, locale: str = LOCALE, names: str | None = None) -> bytes:
    """The 14-page Essentials PDF for one engine response and its M1 and Vara documents.

    `locale` and `names` exist only to be refused: Essentials is English with names off."""
    return render(response, panchanga_doc, vara_doc, display_name, locale=locale, names=names)[0]


def render(response, panchanga_doc, vara_doc, display_name=None, *, locale=LOCALE, names=None):
    """generate() plus the renderer's audit, for the tests."""
    if locale != LOCALE:
        raise EssentialsError(422, 'REPORT_LOCALE_UNSUPPORTED', 'the Essentials edition is English only')
    if names is not None:
        raise EssentialsError(422, 'NAMES_UNSUPPORTED', 'traditional names are not shown in this edition')
    if not isinstance(panchanga_doc, dict) or not isinstance(vara_doc, dict):
        raise EssentialsError(422, 'EDITION_INPUT_MISSING', 'the Panchanga and Vara documents are required')
    data, audit = pr.render(response, synthetic=False, palette=PALETTE, display_name=display_name, locale=LOCALE,
                            panchanga=panchanga_doc, vara=vara_doc, catalog_overlay=copy.deepcopy(OVERLAY))
    if audit.get('page_keys') is None or len(audit['page_keys']) != PAGES:
        raise RuntimeError('Essentials page plan changed')
    if len(data) > pr.MAX_PDF_BYTES or not data.startswith(b'%PDF-'):
        raise RuntimeError('controlled PDF size exceeded')
    audit = dict(audit, essentials=EDITION)
    return data, audit


def engine_request(response: dict) -> dict:
    """The request the form handler sent to the engine for this response (server.compute)."""
    info = response['input']
    place = info['place']
    return {'birth_datetime': f"{info['local_date']}T{info['local_time']}{info['utc_offset']}",
            'timezone': place['timezone'], 'latitude': place['latitude'], 'longitude': place['longitude']}


def render_for_form(body: dict, places: dict, ephe_path: str, display_name: str | None = None) -> bytes:
    """The whole in-memory pipeline for one private-form submission.

    `body` is the birth form exactly as /api/chart takes it (place_id, birth_date, birth_time and optional
    utc_offset); the same handler validates it, so the same refusals apply. A `report_locale` other than "en"
    is refused, and any other key (edition, names, vara, display_name ...) is refused by the chart handler.
    The name, if any, is passed separately and validated by display_name.normalize. Returns the PDF bytes or
    raises EssentialsError with a fixed code; nothing is written or logged here."""
    if not isinstance(body, dict):
        raise EssentialsError(400, 'REQUEST_INVALID', 'the request must be one JSON object')
    body = dict(body)
    if 'report_locale' in body:
        if body.pop('report_locale') != LOCALE:
            raise EssentialsError(422, 'REPORT_LOCALE_UNSUPPORTED', 'the Essentials edition is English only')
    if display_name is not None:
        try:
            from . import display_name as dn
        except ImportError:
            import display_name as dn
        try:
            display_name = dn.normalize(display_name)
        except dn.DisplayNameError as exc:
            raise EssentialsError(exc.status, exc.code, exc.message, 'display_name') from None
    from kundali_prototype import server
    from sabpuja_kundali import panchanga
    from sabpuja_kundali.panchanga import vara
    status, response = server.handle_chart(json.dumps(body, ensure_ascii=False).encode('utf-8'), places, ephe_path)
    if status != 200:
        err = response.get('error', {}) if isinstance(response, dict) else {}
        extra = {k: v for k, v in err.items() if k not in ('code', 'message', 'category')}
        raise EssentialsError(status, str(err.get('code', 'REQUEST_INVALID')),
                              str(err.get('message', 'the request was refused')), str(err.get('category', 'request')),
                              extra)
    try:
        req = engine_request(response)
        pdf = generate(response, panchanga.calculate(req, ephe_path), vara.calculate(req, ephe_path), display_name)
    except EssentialsError:
        raise
    except Exception:
        # Never the exception message, which could quote the input.
        raise EssentialsError(500, 'REPORT_UNAVAILABLE', 'the report could not be produced', 'server') from None
    return pdf


# ---------------------------------------------------------------------------
# The edition manifest.

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_paths(root: Path = REPO) -> list[str]:
    root = Path(root)
    paths = set(SOURCE_FILES)
    for d in SOURCE_DIRS:
        for f in (root / d).rglob('*'):
            if f.is_file() and '__pycache__' not in f.parts:
                paths.add(f.relative_to(root).as_posix())
    return sorted(paths)


def build_manifest(root: Path = REPO) -> bytes:
    root = Path(root)
    doc = {'edition': EDITION, 'catalog_sha256': CATALOG_SHA256, 'pages': PAGES, 'locale': LOCALE,
           'palette': PALETTE, 'overlay_keys': list(OVERLAY_KEYS),
           'note': 'Every source file of the Essentials edition with its SHA-256. Regenerate with '
                   'python -m report.phase1.essentials --write-manifest; a change here is a change to the edition.',
           'files': {p: _sha256((root / p).read_bytes()) for p in manifest_paths(root)}}
    return (json.dumps(doc, indent=1, ensure_ascii=False) + '\n').encode('utf-8')


def manifest_problems(root: Path = REPO) -> list[str]:
    root = Path(root)
    path = root / MANIFEST_PATH.relative_to(REPO)
    if not path.is_file():
        return ['Essentials edition manifest missing']
    committed, built = json.loads(path.read_bytes()), json.loads(build_manifest(root))
    problems = [f'{k} differs' for k in sorted(set(committed) | set(built)) if k != 'files'
                and committed.get(k) != built.get(k)]
    have, want = built['files'], committed.get('files', {})
    problems += [f'changed: {p}' for p in sorted(set(have) & set(want)) if have[p] != want[p]]
    problems += [f'added: {p}' for p in sorted(set(have) - set(want))]
    problems += [f'removed: {p}' for p in sorted(set(want) - set(have))]
    return problems


if __name__ == '__main__':
    import argparse
    import sys
    ap = argparse.ArgumentParser(description='Essentials edition manifest (KUN-RC-ESS-001)')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--check', action='store_true')
    g.add_argument('--write-manifest', action='store_true')
    args = ap.parse_args()
    if args.write_manifest:
        MANIFEST_PATH.write_bytes(build_manifest())
        print(f'wrote {MANIFEST_PATH.relative_to(REPO)} sha256 {_sha256(MANIFEST_PATH.read_bytes())}')
        sys.exit(0)
    found = manifest_problems()
    print('PASS Essentials edition manifest' if not found else 'FAIL\n  ' + '\n  '.join(found))
    sys.exit(1 if found else 0)
