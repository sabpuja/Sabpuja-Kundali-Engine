"""Tithi, Karana and Panchanga Yoga names for the extended report (KUN-PAN-M2-NAMES-001, issue #80).

Display only. The `sabpuja-panchanga/1` document keeps its numbers and `name_omitted` fields; this
module maps an already validated number to a stable machine id and to its display forms:

    Tithi 1-30   -> paksha + tithi_name.*   (15 Purnima, 30 Amavasya)
    Karana 1-60  -> karana.*                (1 Kimstughna; 2-57 Bava..Vishti eight times; 58-60 fixed)
    Yoga 1-27    -> panchanga_yoga.*        (Vishkambha .. Vaidhriti; not a planetary Yoga)

The catalog `panchanga_names.json` keeps three separate things per term: the machine id, the
publisher spelling exactly as printed by IMD, and the proposed English and Hindi display forms with
their human review status. The mappings are checked against the IMD facts in
`research/panchanga/names/imd-names-evidence.json` by the tests.

Activation (fail closed):
    names=None          the default: nothing here is used, the report is byte-identical to M1.
    names='qa_preview'  internal QA only: names drawn with a "QA PREVIEW, NOT FOR CUSTOMERS" notice.
    names='customer'    refused until release_problems() is empty, that is every display form has
                        ACCEPTED human Hindi language and Jyotish terminology review and the owner's
                        release is recorded in a GitHub issue or PR of this repository.
Any other mode, an index out of range, a bool or non-int index, a missing term or an unsupported
locale raises NamesError. Nothing is guessed.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / 'panchanga_names.json'
CATALOG = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))

LOCALES = ('en', 'hi')
MODES = ('qa_preview', 'customer')
COUNTS = {'tithi': 30, 'karana': 60, 'yoga': 27}
TERM_TYPES = {'tithi': 'tithi_name', 'karana': 'karana', 'yoga': 'panchanga_yoga'}
REVIEW_LAYERS = ('en_display', 'hi_display', 'jyotish_terminology')
REVIEW_STATUSES = ('PENDING_HUMAN_REVIEW', 'ACCEPTED', 'REVISED', 'REJECTED')
RECORD_URL = re.compile(r'^https://github\.com/sabpuja/Sabpuja-Kundali-Engine/(issues|pull)/[1-9][0-9]*'
                        r'(#(issuecomment|pullrequestreview|discussion_r)-[0-9]+)?$')
DEVANAGARI = re.compile(r'^[ऀ-ॿ ]+$')
LATIN = re.compile(r'^[A-Za-z][A-Za-z ]*$')


class NamesError(ValueError):
    """A Panchanga name cannot be shown. Fixed text; never birth data."""


def _refuse(reason):
    raise NamesError('Panchanga name refused: ' + reason)


def _index(element, value):
    if element not in COUNTS:
        _refuse('unknown element')
    if type(value) is not int or not 1 <= value <= COUNTS[element]:
        _refuse('index out of range')
    return value


def _locale(locale):
    if locale not in LOCALES:
        _refuse('unsupported locale')
    return locale


def _display(entry, locale):
    text = entry.get('display', {}).get(_locale(locale)) if isinstance(entry, dict) else None
    if not isinstance(text, str) or not text or unicodedata.normalize('NFC', text) != text:
        _refuse('display form missing')
    return text


def term_id(element, index, catalog=CATALOG):
    """Stable machine id of the name at a validated index."""
    index = _index(element, index)
    if element == 'tithi':
        entry = catalog['tithi'].get(str(index))
        tid = entry.get('name') if isinstance(entry, dict) else None
    else:
        tid = catalog[element].get(str(index))
    term = catalog['terms'].get(tid) if isinstance(tid, str) else None
    if term is None or term.get('id') != tid or term.get('type') != TERM_TYPES[element]:
        _refuse('mapping missing or of the wrong type')
    return tid


def name(element, index, locale, catalog=CATALOG):
    """Display form of the bare name (Tithi without its Paksha)."""
    return _display(catalog['terms'][term_id(element, index, catalog)], locale)


def tithi_label(number, locale, catalog=CATALOG):
    """'Shukla Ekadashi', 'Krishna Pratipada'; Purnima and Amavasya stand alone."""
    number = _index('tithi', number)
    entry = catalog['tithi'][str(number)]
    bare = name('tithi', number, locale, catalog)
    if number in (15, 30):
        return bare
    prefix = _display(catalog['paksha_prefix'].get(entry.get('paksha')), locale)
    return f'{prefix} {bare}'


def karana_kind(index, locale, catalog=CATALOG):
    kind = catalog['terms'][term_id('karana', index, catalog)].get('karana_kind')
    return _display(catalog['karana_kind_label'].get(kind), locale)


def source_spelling(element, index, catalog=CATALOG):
    return catalog['terms'][term_id(element, index, catalog)]['source_spelling']['text']


def text(key, locale, catalog=CATALOG, **values):
    entry = catalog['strings'].get(key)
    if entry is None:
        _refuse('missing string')
    return entry[_locale(locale)].format(**values)


# ---------------------------------------------------------------------------
# Catalog shape and release gate.

def _reviewed_entries(catalog):
    for tid, term in catalog['terms'].items():
        yield tid, term
    for group in ('paksha_prefix', 'karana_kind_label'):
        for key, entry in catalog[group].items():
            yield f'{group}.{key}', entry


def catalog_problems(catalog=CATALOG):
    """Structural problems; an empty list means every index resolves and every form is well formed."""
    problems = []
    for tid, term in catalog['terms'].items():
        kind = tid.split('.', 1)[0]
        if term.get('id') != tid or term.get('type') != kind or kind not in TERM_TYPES.values():
            problems.append(f'{tid}: id or type')
        spelling = term.get('source_spelling', {})
        if spelling.get('publisher') != 'IMD-NAMES' or not LATIN.match(spelling.get('text') or ''):
            problems.append(f'{tid}: source spelling')
    for key, entry in _reviewed_entries(catalog):
        display = entry.get('display', {}) if isinstance(entry, dict) else {}
        if set(display) != set(LOCALES):
            problems.append(f'{key}: locales')
            continue
        for locale, form in display.items():
            if not isinstance(form, str) or unicodedata.normalize('NFC', form) != form:
                problems.append(f'{key}: {locale} not NFC')
            elif not (DEVANAGARI if locale == 'hi' else LATIN).match(form):
                problems.append(f'{key}: {locale} script')
        review = entry.get('review', {})
        if set(review) != set(REVIEW_LAYERS) or any(v not in REVIEW_STATUSES for v in review.values()):
            problems.append(f'{key}: review layers')
    for element, count in COUNTS.items():
        if set(catalog[element]) != {str(i) for i in range(1, count + 1)}:
            problems.append(f'{element}: index set')
            continue
        for i in range(1, count + 1):
            try:
                term_id(element, i, catalog)
            except NamesError:
                problems.append(f'{element} {i}: unresolved')
    for key, entry in catalog['strings'].items():
        if set(entry) != set(LOCALES):
            problems.append(f'string {key}: locales')
        elif (set(re.findall(r'\{(\w+)\}', entry['en'])) != set(re.findall(r'\{(\w+)\}', entry['hi']))):
            problems.append(f'string {key}: placeholders differ')
    return problems


def release_problems(catalog=CATALOG):
    """Why the names may not be shown to customers. Empty only when every layer is ACCEPTED and the
    owner's release is recorded in GitHub. This decides nothing; it only refuses."""
    problems = catalog_problems(catalog)
    for key, entry in _reviewed_entries(catalog):
        for layer in REVIEW_LAYERS:
            if entry.get('review', {}).get(layer) != 'ACCEPTED':
                problems.append(f'{key}: {layer} not accepted')
    release = catalog.get('customer_release', {})
    if release.get('status') != 'APPROVED':
        problems.append('customer release not approved by the owner')
    if not isinstance(release.get('record'), str) or not RECORD_URL.match(release['record']):
        problems.append('customer release has no GitHub record')
    return problems


def check_mode(mode, catalog=CATALOG):
    """None, or a mode that may be drawn now. Raises NamesError otherwise."""
    if mode is None:
        return None
    if mode not in MODES:
        _refuse('unknown names mode')
    if catalog_problems(catalog):
        _refuse('catalog inconsistent')
    if mode == 'customer' and release_problems(catalog):
        _refuse('names are not approved for customer display')
    return mode


if catalog_problems():
    raise RuntimeError('Panchanga names catalog inconsistent')
