"""KUN-PAN-RPT-002: the opt-in sunrise and Vara edition of the premium report (14 pages).

Synthetic data only. fixtures/vara holds the `sabpuja-panchanga-vara/1` document of each of the 13
existing report scenarios; fixtures/vara-cases holds 12 further synthetic boundary cases (typical,
pre-sunrise, first and last whole second around sunrise, just inside and outside the 5-minute band,
London clocks forward and repeated hour, UTC+14, polar day, a Vara day without an end, a sunset after
local midnight), each with its chart response and Panchanga M1 document. All were captured by
tools/make_vara_fixtures.py from the unchanged engine, M1 module and sun module.

Covers: the ten-page and 13-page editions are unchanged byte for byte (pinned hashes, also after a
Vara render); the Vara edition renders 14 A4 pages in English and Hindi with the extra page after the
transition times, dynamic contents, page numbers, cross-references and overrides of the three M1
sentences that would otherwise be untrue; every displayed value is the document's; the near-sunrise
caution appears exactly when the document flags it; unavailable cases show the typed reason and no Vara;
layout (no overlap, clipping, sub-8 pt text); fonts, palette and metadata; no file writes, no input
mutation; and every mismatched, stale, unsupported or malformed document is refused before drawing.
With SABPUJA_TEST_EPHE_PATH set, every fixture is recomputed and compared.
"""
import copy
import hashlib
import json
import os
import re
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from report.phase1 import premium_report as premium  # noqa: E402
from report.phase1 import panchanga_report as pan  # noqa: E402
from report.phase1 import vara_report as vr  # noqa: E402
from report.phase1 import report_locale as loc  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(ROOT / 'report/phase1/tools')]
import test_premium_name as name_tests  # noqa: E402
import test_premium_report as base_tests  # noqa: E402
import make_vara_fixtures as maker  # noqa: E402

SCENARIOS = name_tests.SCENARIOS
DOCS = {case: json.loads((HERE / 'fixtures/panchanga' / f'{case}.json').read_text()) for case in SCENARIOS}
VARA = {case: json.loads((HERE / 'fixtures/vara' / f'{case}.json').read_text()) for case in SCENARIOS}
CASES = {p.stem: json.loads(p.read_text()) for p in sorted((HERE / 'fixtures/vara-cases').glob('v*.json'))}
PINS_13 = json.loads((HERE / 'fixtures/extended-13-page-sha256-f26dd10.json').read_text())['sha256']
PINS_14_PATH = HERE / 'fixtures/extended-14-page-vara-sha256.json'
PRIMARY = 's07-noon'
KEYS = [k for k, _, _ in premium.PAGES[:-1]] + ['panchanga', 'transitions', 'sunrise', 'pmethod', 'method']
SYNTHETIC = set(maker.SYNTHETIC_PLACES)
_CACHE = {}


def all_cases():
    """(id, response, panchanga, vara) for the 13 scenarios and the 12 boundary cases."""
    out = [(c, SCENARIOS[c], DOCS[c], VARA[c]) for c in SCENARIOS]
    out += [(c, r['response'], r['panchanga'], r['vara']) for c, r in CASES.items()]
    return out


def render(case, locale='en', name=None, synthetic=True):
    key = (case, locale, name, synthetic)
    if key not in _CACHE:
        _, response, doc, v = next(x for x in all_cases() if x[0] == case)
        with maker.synthetic_hindi_places():
            data, audit = premium.render(response, synthetic, 'baseline', name, locale, panchanga=doc, vara=v)
        _CACHE[key] = data, audit, fitz.open(stream=data, filetype='pdf')
    return _CACHE[key]


def squash(text):
    return ' '.join(text.split())


def sunrise_text(pdf, audit):
    return squash(pdf[audit['page_keys'].index('sunrise')].get_text())


def S(key, locale, **values):
    return squash(vr.STRINGS[key][locale].format(**values))


def refused(test, response, doc, v, locale='en', error=vr.VaraReportError):
    with test.assertRaises(error):
        premium.generate_extended(response, doc, synthetic=True, palette='baseline', locale=locale, vara=v)


class DefaultsUnchanged(unittest.TestCase):
    def test_ten_page_pins(self):
        for case, (customer, sample) in name_tests.BEFORE.items():
            self.assertEqual(hashlib.sha256(premium.generate(SCENARIOS[case], palette='baseline')).hexdigest(), customer)
            self.assertEqual(hashlib.sha256(premium.generate(SCENARIOS[case], synthetic=True,
                                                             palette='baseline')).hexdigest(), sample)

    def test_thirteen_page_pins_all_52(self):
        self.assertEqual(len(PINS_13), 52)
        for key, want in PINS_13.items():
            case, locale, mode = key.split('|')
            data = premium.generate_extended(SCENARIOS[case], DOCS[case], synthetic=mode == 'sample',
                                             palette='baseline', locale=locale)
            self.assertEqual(hashlib.sha256(data).hexdigest(), want, key)

    def test_no_state_leaks_into_later_renders(self):
        render(PRIMARY, 'hi')
        before = PINS_13[f'{PRIMARY}|hi|sample']
        data = premium.generate_extended(SCENARIOS[PRIMARY], DOCS[PRIMARY], synthetic=True, palette='baseline',
                                         locale='hi', vara=None)
        self.assertEqual(hashlib.sha256(data).hexdigest(), before)
        customer, _ = name_tests.BEFORE[PRIMARY]
        self.assertEqual(hashlib.sha256(premium.generate(SCENARIOS[PRIMARY], palette='baseline')).hexdigest(), customer)

    def test_vara_needs_the_extended_edition(self):
        with self.assertRaises(ValueError):
            premium.render(SCENARIOS[PRIMARY], True, 'baseline', vara=VARA[PRIMARY])

    def test_other_catalogs_and_the_preview_are_untouched(self):
        text = (ROOT / 'prototype/kundali_prototype/server.py').read_text(encoding='utf-8')
        self.assertNotIn('vara', text.lower())
        self.assertNotIn('sunrise', json.dumps(pan.CATALOG['strings']['meta.subject']).lower())


class PinnedInputs(unittest.TestCase):
    def test_method_claim_and_schema_are_the_engine_module_s(self):
        from sabpuja_kundali.panchanga import vara
        self.assertEqual(vr.canonical_sha256(vara.METHOD), vr.METHOD_SHA256)
        self.assertEqual(vara.CLAIM_BOUNDARY, vr.CLAIM_BOUNDARY)
        self.assertEqual((vara.SCHEMA, vara.STATUS, vara.NEAR_SUNRISE_SECONDS), (vr.SCHEMA, vr.STATUS, vr.NEAR_SECONDS))

    def test_catalog_consistent_nfc_and_scoped(self):
        import unicodedata
        self.assertEqual(vr.check_catalog(), [])
        self.assertTrue(vr.CATALOG['status'].startswith('DEVELOPER DRAFT'))
        for key, entry in vr.STRINGS.items():
            for text in entry.values():
                self.assertEqual(unicodedata.normalize('NFC', text), text, key)
        overrides = sorted(k[len('override.'):] for k in vr.STRINGS if k.startswith('override.'))
        self.assertEqual(overrides, ['method.inc6', 'pan.instant', 'pm.exc1'])
        for key in overrides:
            target = pan.STRINGS[key]
            self.assertEqual(loc.placeholders(target['en']) | ({'sunrise'} if key == 'pan.instant' else set()),
                             loc.placeholders(vr.STRINGS['override.' + key]['en']))
        words = set(re.findall(r'[A-Za-zऀ-ॿ]+', json.dumps(vr.STRINGS, ensure_ascii=False)))
        import test_panchanga_report as m1_tests
        self.assertFalse(words & set(m1_tests.FORBIDDEN_NAMES) - {'Shiva'})
        self.assertFalse(words & set(m1_tests.FORBIDDEN_HINDI))

    def test_fixtures_are_synthetic_and_bound_to_their_scenarios(self):
        for case, response, doc, v in all_cases():
            self.assertEqual(v['birth']['utc'], response['chart']['birth']['utc'], case)
            self.assertEqual(doc['birth']['utc'], response['chart']['birth']['utc'], case)
            if response['input']['place']['id'] in SYNTHETIC:
                self.assertEqual(response['input']['place']['source'], maker.SYNTHETIC_SOURCE)

    @unittest.skipUnless(os.environ.get('SABPUJA_TEST_EPHE_PATH'), 'set SABPUJA_TEST_EPHE_PATH to recompute fixtures')
    def test_every_fixture_is_reproduced(self):
        from sabpuja_kundali.panchanga import vara
        import make_panchanga_fixtures as m1maker
        ephe = os.environ['SABPUJA_TEST_EPHE_PATH']
        for case in SCENARIOS:
            self.assertEqual(vara.calculate(m1maker.engine_request(SCENARIOS[case]), ephe), VARA[case], case)
        places = maker._places(maker.load_places())
        for case_id, _, place, day, at, offset in maker.cases(ephe):
            got = maker.compute(places, ephe, place, day, at, offset)
            for key in ('response', 'panchanga', 'vara'):
                self.assertEqual(got[key], CASES[case_id][key], (case_id, key))
        self.assertEqual(sorted(c[0] for c in maker.cases(ephe)), sorted(CASES))


class Edition(unittest.TestCase):
    def test_every_case_both_languages(self):
        for case, *_ in all_cases():
            for locale in ('en', 'hi'):
                with self.subTest(case=case, locale=locale):
                    data, audit, pdf = render(case, locale)
                    self.assertEqual(len(pdf), 14)
                    self.assertLess(len(data), premium.MAX_PDF_BYTES)
                    self.assertEqual(audit['page_keys'], KEYS)
                    self.assertEqual(audit['edition'], 'extended-panchanga-m2-vara/1')
                    self.assertEqual(audit['layout'], 'phase2a-premium+extended-panchanga-m2-vara/1')
            _CACHE.clear()

    def test_pinned_fourteen_page_hashes(self):
        pins = json.loads(PINS_14_PATH.read_text())['sha256']
        self.assertEqual(len(pins), 4 * (len(SCENARIOS) + len(CASES)))
        for key, want in pins.items():
            case, locale, mode = key.split('|')
            data, _, _ = render(case, locale, synthetic=mode == 'sample')
            self.assertEqual(hashlib.sha256(data).hexdigest(), want, key)
            _CACHE.clear()

    def test_deterministic_and_names_mode_combines(self):
        a = render(PRIMARY, 'hi')[0]
        _CACHE.clear()
        self.assertEqual(a, render(PRIMARY, 'hi')[0])
        data, audit = premium.render(SCENARIOS[PRIMARY], True, 'baseline', None, 'en', panchanga=DOCS[PRIMARY],
                                     panchanga_names='qa_preview', vara=VARA[PRIMARY])
        self.assertEqual(audit['page_keys'], KEYS)
        self.assertEqual(audit['panchanga']['names']['mode'], 'qa_preview')

    def test_page_numbers_contents_cross_references_and_overrides(self):
        for locale in ('en', 'hi'):
            _, audit, pdf = render(PRIMARY, locale)
            tr = loc.Translator(locale)
            titles = {k: t for k, t, _ in premium.pages(locale)}
            titles.update({k: pan.STRINGS[f'page.{k}.title'][locale] for k in ('panchanga', 'transitions', 'pmethod')})
            titles['sunrise'] = vr.STRINGS['page.sunrise.title'][locale]
            for number, key in enumerate(KEYS[1:], 2):
                text = squash(pdf[number - 1].get_text()).upper()
                with self.subTest(locale=locale, page=number):
                    self.assertIn(squash(tr.t('footer.page', number=number, total=14)).upper(), text)
                    self.assertIn(squash(tr.t('header.kicker', title=titles[key])).upper(), text)
            contents = squash(pdf[1].get_text())
            for number, key in enumerate(KEYS[1:], 2):
                self.assertIn(f'{number - 1:02d}', contents)
                self.assertIn(squash(titles[key]), contents)
            self.assertIn(squash(tr.t('birth.method_ref', page=14)), squash(pdf[3].get_text()))
            method = squash(pdf[13].get_text())
            self.assertIn(S('override.method.inc6', locale, first=10, last=13), method)
            self.assertNotIn(squash(pan.STRINGS['method.inc6'][locale].format(first=10, last=13)), method)
            first = squash(pdf[9].get_text())
            self.assertIn(S('override.pan.instant', locale, sunrise=12), first)
            self.assertNotIn(squash(pan.STRINGS['pan.instant'][locale]), first)
            pm = squash(pdf[12].get_text())
            self.assertIn(S('override.pm.exc1', locale), pm)
            self.assertNotIn(squash(pan.STRINGS['pm.exc1'][locale]), pm)
            self.assertIn(S('v.intro', locale, birth=4), sunrise_text(pdf, audit))

    def test_values_are_the_document_s(self):
        for case, response, doc, v in all_cases():
            zone = maker.get_zone(v['birth']['timezone'])
            for locale in ('en', 'hi'):
                with self.subTest(case=case, locale=locale):
                    _, audit, pdf = render(case, locale)
                    text = sunrise_text(pdf, audit)
                    self.assertIn(S(f"civil.{v['civil']['weekday']}", locale), text)
                    self.assertIsNone(re.search(r'\d\d:\d\d:\d\d', text), 'no seconds are printed')
                    if v['vara']['status'] == 'available':
                        self.assertIn(S(f"vara.{v['vara']['vara_id']}", locale), text)
                        for key in ('governing_sunrise', 'sunset', 'next_sunrise'):
                            if v[key]['status'] != 'available':
                                continue
                            utc, local = vr.display_instant(v[key]['utc_us'], zone)
                            self.assertIn(S('v.time', locale, time=local.strftime('%H:%M')), text, key)
                            self.assertIn(f"UTC {utc.strftime('%H:%M')}", text, key)
                        self.assertEqual(audit['vara']['near_sunrise'], v['boundary']['near_sunrise'])
                        near = S('v.near_title', locale)
                        self.assertEqual(near.upper() in text.upper(), v['boundary']['near_sunrise'], case)
                        self.assertNotIn(S('v.na_title', locale).upper(), text.upper())
                    else:
                        self.assertIn(S('v.na_title', locale).upper(), text.upper())
                        missing = sum(v[k]['status'] == 'unavailable' for k in ('governing_sunrise', 'sunset', 'next_sunrise'))
                        self.assertEqual(text.count(S('v.unavailable', locale)), 2 + missing)
                        for vid in vr.VARA_IDS:
                            if locale == 'en':
                                self.assertNotIn(S(f'vara.{vid}', locale), text)
                    for key in ('page.sunrise.title', 'v.m.convention_value', 'v.m.place_value', 'v.m.checks_value',
                                'v.status', 'v.m.times_value'):
                        self.assertIn(S(key, locale), text, key)
            _CACHE.clear()

    def test_boundary_cases_flag_as_specified(self):
        flags = {c: CASES[c]['vara']['boundary'].get('near_sunrise') for c in CASES}
        self.assertEqual({c for c, f in flags.items() if f}, {'v03-first-second-after-sunrise',
                                                              'v04-last-second-before-sunrise', 'v05-inside-band-after'})
        self.assertFalse(flags['v06-outside-band-after'])
        v04, v03 = CASES['v04-last-second-before-sunrise']['vara'], CASES['v03-first-second-after-sunrise']['vara']
        self.assertEqual((v04['vara']['vara_id'], v04['civil']['weekday']), ('shanivara', 'sunday'))
        self.assertEqual((v03['vara']['vara_id'], v03['civil']['weekday']), ('ravivara', 'sunday'))
        self.assertEqual(v04['next_sunrise']['utc_us'], v03['governing_sunrise']['utc_us'])
        self.assertLess(v04['boundary']['before_next_sunrise_us'], 10**6)
        self.assertLess(v03['boundary']['after_governing_sunrise_us'], 10**6)
        b5, b6 = CASES['v05-inside-band-after']['vara']['boundary'], CASES['v06-outside-band-after']['vara']['boundary']
        self.assertLessEqual(b5['after_governing_sunrise_us'], 300 * 10**6)
        self.assertGreater(b6['after_governing_sunrise_us'], 300 * 10**6)
        self.assertLess(b6['after_governing_sunrise_us'], 302 * 10**6)

    def test_near_sunrise_rule_is_inclusive_on_microseconds(self):
        g, n, w = 10**12, 10**12 + 86_400 * 10**6, 300 * 10**6
        self.assertTrue(vr.near_sunrise(g + w, g, n)['near_sunrise'])
        self.assertFalse(vr.near_sunrise(g + w + 1, g, n)['near_sunrise'])
        self.assertTrue(vr.near_sunrise(n - w, g, n)['near_sunrise'])
        self.assertFalse(vr.near_sunrise(n - w - 1, g, n)['near_sunrise'])
        self.assertEqual(vr.near_sunrise(g, g, n)['nearest'], 'governing')
        self.assertEqual(vr.near_sunrise(n - 1, g, n)['nearest'], 'next')
        self.assertEqual(vr.near_sunrise(g + w + 1, g, None)['status'], 'partial')

    def test_display_rounding(self):
        zone = maker.get_zone('Asia/Kolkata')
        base = int(datetime(2039, 7, 31, 0, 20, tzinfo=timezone.utc).timestamp()) * 10**6
        for offset_us, minute in ((29_499_999, 20), (29_500_000, 21), (30 * 10**6, 21), (89_499_999, 21)):
            utc, local = vr.display_instant(base + offset_us, zone)
            self.assertEqual((utc.minute, local.strftime('%H:%M')), (minute, f'05:{50 + minute - 20:02d}'))
        self.assertEqual(vr.hours_minutes(29 * 10**6 + 999_999), (0, 0))
        self.assertEqual(vr.hours_minutes(30 * 10**6), (0, 1))
        self.assertEqual(vr.hours_minutes((2 * 3600 + 59 * 60 + 30) * 10**6), (3, 0))

    def test_layout_overlap_margins_and_minimum_size(self):
        checks = base_tests.PremiumPDFTests()
        for case, *_ in all_cases():
            for locale in ('en', 'hi'):
                with self.subTest(case=case, locale=locale):
                    _, audit, pdf = render(case, locale)
                    checks._assert_no_text_overlap(pdf, case)
                    checks._assert_inside_margins(pdf, case)
                    page = pdf[audit['page_keys'].index('sunrise')]
                    for span in base_tests.spans(page):
                        self.assertGreaterEqual(round(span['size'], 2), premium.MIN_TEXT, (case, span['text']))
                    for clip in (fitz.Rect(0, 80, premium.M - 4, premium.H - 40),
                                 fitz.Rect(premium.W - premium.M + 4, 80, premium.W, premium.H - 40),
                                 fitz.Rect(premium.M, premium.H - premium.FOOTER_Y - 14 - 12, premium.W - premium.M,
                                           premium.H - premium.FOOTER_Y - 14 - 1)):
                        pix = page.get_pixmap(dpi=72, clip=clip, colorspace=fitz.csGRAY)
                        self.assertEqual(sum(1 for x in pix.samples if x < 120), 0, (case, locale, clip))
            _CACHE.clear()

    def test_full_names_fonts_palette_metadata(self):
        for locale in ('en', 'hi'):
            for name in ('Zoë-Anne O’Brien', 'क्षत्रिय प्रियंका सिद्धार्थ'):
                data, audit, pdf = render(PRIMARY, locale, name)
                self.assertEqual(len(pdf), 14)
                for page in pdf:
                    for _, fext, _, fname, *_ in page.get_fonts(full=True):
                        self.assertEqual(fext, 'ttf', fname)
                        self.assertTrue(fname.split('+')[-1].startswith(('Poppins', 'Inter')), fname)
                meta = pdf.metadata
                self.assertEqual(meta['subject'], vr.STRINGS['meta.subject'][locale])
                blob = json.dumps(meta, ensure_ascii=False)
                for secret in (name, SCENARIOS[PRIMARY]['input']['local_date'], SCENARIOS[PRIMARY]['input']['place']['name']):
                    self.assertNotIn(secret, blob)
                self.assertEqual(b'/Lang (hi)' in data, locale == 'hi')
        allowed = {premium.Palette('baseline').hex[r].lower() for r in premium.Palette('baseline').hex}
        for case in (PRIMARY, 'v04-last-second-before-sunrise'):
            _, audit, pdf = render(case, 'en')
            for drawing in pdf[audit['page_keys'].index('sunrise')].get_drawings():
                if drawing['rect'].y1 < 90:
                    continue
                for key in ('fill', 'color'):
                    colour = drawing.get(key)
                    if colour:
                        self.assertIn('#%02x%02x%02x' % tuple(round(c * 255) for c in colour), allowed)

    def test_searchable_hindi_text(self):
        _, audit, pdf = render(PRIMARY, 'hi')
        text = sunrise_text(pdf, audit)
        for key in ('v.title', 'v.card.vara', 'v.card.civil', 'v.m_title'):
            self.assertIn(S(key, 'hi'), text)

    def test_no_files_written_and_inputs_not_mutated(self):
        import builtins
        real_open = builtins.open
        written = []

        def guard(file, mode='r', *a, **k):
            if any(m in mode for m in 'wax+'):
                written.append(str(file))
            return real_open(file, mode, *a, **k)
        response, doc, v = (copy.deepcopy(x) for x in (SCENARIOS[PRIMARY], DOCS[PRIMARY], VARA[PRIMARY]))
        builtins.open = guard
        try:
            premium.generate_extended(response, doc, synthetic=False, palette='baseline', locale='hi', vara=v)
        finally:
            builtins.open = real_open
        self.assertEqual(written, [])
        self.assertEqual((response, doc, v), (SCENARIOS[PRIMARY], DOCS[PRIMARY], VARA[PRIMARY]))


class Refusals(unittest.TestCase):
    """Every mismatched, stale, unsupported or malformed Vara document fails closed before drawing."""

    def mutate(self, fn, case=PRIMARY):
        if case in CASES:
            response, doc, v = (copy.deepcopy(CASES[case][k]) for k in ('response', 'panchanga', 'vara'))
        else:
            response, doc, v = copy.deepcopy(SCENARIOS[case]), copy.deepcopy(DOCS[case]), copy.deepcopy(VARA[case])
        fn(v)
        for locale in ('en', 'hi'):
            refused(self, response, doc, v, locale)

    def test_wrong_chart(self):
        for other in ('s08-dawn', 's12-morning'):
            refused(self, SCENARIOS[PRIMARY], DOCS[PRIMARY], VARA[other])
        refused(self, SCENARIOS[PRIMARY], DOCS[PRIMARY], CASES['v01-typical-afternoon']['vara'])   # same place, other time

    def test_shape_schema_status_claim_method(self):
        for bad in ([], 'x', {}):
            refused(self, SCENARIOS[PRIMARY], DOCS[PRIMARY], bad)
        self.mutate(lambda v: v.update(extra=1))
        self.mutate(lambda v: v.pop('boundary'))
        self.mutate(lambda v: v.update(schema='sabpuja-panchanga-vara/2'))
        self.mutate(lambda v: v.update(status='CUSTOMER_RELEASED'))
        self.mutate(lambda v: v.update(claim_boundary=v['claim_boundary'] + ' '))
        self.mutate(lambda v: v['method'].update(convention='SUN-A-USNO-50'))
        self.mutate(lambda v: v['method'].update(depression_arcmin=50))

    def test_birth_place_and_provenance(self):
        self.mutate(lambda v: v['birth'].update(utc='2039-07-31T06:30:01Z'))
        self.mutate(lambda v: v['birth'].update(timezone='Asia/Calcutta'))
        self.mutate(lambda v: v['birth'].update(latitude=v['birth']['latitude'] + 1e-9))
        self.mutate(lambda v: v['birth'].update(longitude=-v['birth']['longitude']))
        self.mutate(lambda v: v['birth'].update(latitude=True))
        self.mutate(lambda v: v['birth'].update(latitude=str(v['birth']['latitude'])))
        self.mutate(lambda v: v['provenance'].update(ephemeris_manifest_sha256='0' * 64))
        self.mutate(lambda v: v['provenance']['timezone_data'].update(iana_version='2020a'))
        self.mutate(lambda v: v['provenance'].update(swiss_calls=0))
        self.mutate(lambda v: v['provenance'].update(swiss_calls=True))

    def test_values(self):
        self.mutate(lambda v: v['civil'].update(weekday='monday'))
        self.mutate(lambda v: v['civil'].update(date='2039-07-30'))
        self.mutate(lambda v: v['vara'].update(vara_id='somavara'))
        self.mutate(lambda v: v['vara'].update(sunrise_local_date='2039-07-30'))
        self.mutate(lambda v: v.update(vara_differs_from_civil_weekday=True))
        self.mutate(lambda v: v.update(vara_differs_from_civil_weekday=None))
        self.mutate(lambda v: v['governing_sunrise'].update(utc_us=v['governing_sunrise']['utc_us'] + 10**6))
        self.mutate(lambda v: v['governing_sunrise'].update(local=v['governing_sunrise']['local'][:-6] + '+05:00'))
        self.mutate(lambda v: v['governing_sunrise'].update(utc_us=float(v['governing_sunrise']['utc_us'])))
        self.mutate(lambda v: v['sunset'].update(utc_us=v['governing_sunrise']['utc_us'] - 1, utc=v['governing_sunrise']['utc']))
        self.mutate(lambda v: v['next_sunrise'].update(v['governing_sunrise']))
        self.mutate(lambda v: v['next_sunrise'].update(status='unavailable'))
        self.mutate(lambda v: v.update(next_sunrise={'status': 'unavailable', 'reason': 'PANCHANGA_SUNRISE_OUTSIDE_ENVELOPE',
                                                     'condition': 'NEXT_SUNRISE_OUTSIDE_ENVELOPE'}))

    def test_near_sunrise_flag_must_be_the_instants(self):
        self.mutate(lambda v: v['boundary'].update(near_sunrise=True, nearest='governing'))
        self.mutate(lambda v: v['boundary'].update(near_sunrise=False, nearest=None), 'v04-last-second-before-sunrise')
        self.mutate(lambda v: v['boundary'].update(window_seconds=60), 'v05-inside-band-after')
        self.mutate(lambda v: v['boundary'].update(after_governing_sunrise_us=v['boundary']['after_governing_sunrise_us'] + 1))
        self.mutate(lambda v: v.update(boundary={'status': 'not_assessed', 'reason': 'VARA_UNAVAILABLE'}))

    def test_unavailable_cannot_carry_or_invent_a_vara(self):
        polar = 'v10-polar-day-unavailable'
        self.mutate(lambda v: v['vara'].update(condition='SOMETHING_ELSE'), polar)
        self.mutate(lambda v: v['vara'].update(reason='PANCHANGA_SUNRISE_OUTSIDE_ENVELOPE'), polar)
        self.mutate(lambda v: v.update(vara_differs_from_civil_weekday=False), polar)
        self.mutate(lambda v: v.update(vara={'status': 'available', 'vara_id': 'mangalavara',
                                             'sunrise_local_date': '2044-06-21'}), polar)
        self.mutate(lambda v: v.update(sunset=CASES['v12-sunset-after-midnight']['vara']['sunset']), polar)
        self.mutate(lambda v: v['vara'].update(status='available'), 's01-first-supported-date')
        end = 'v11-vara-day-end-undefined'
        self.mutate(lambda v: v.update(next_sunrise=v['governing_sunrise']), end)
        self.mutate(lambda v: v.update(vara={'status': 'available', 'vara_id': 'shukravara',
                                             'sunrise_local_date': '2044-06-13'}), end)

    def test_unregistered_birthplace_is_refused_in_hindi_outside_tests(self):
        r = CASES['v10-polar-day-unavailable']
        with self.assertRaises(loc.ReportLocaleError):
            premium.generate_extended(r['response'], r['panchanga'], synthetic=True, palette='baseline', locale='hi',
                                      vara=r['vara'])
        premium.generate_extended(r['response'], r['panchanga'], synthetic=True, palette='baseline', locale='en',
                                  vara=r['vara'])

    def test_errors_carry_no_birth_data(self):
        v = copy.deepcopy(VARA[PRIMARY])
        v['civil']['weekday'] = 'monday'
        with self.assertRaises(vr.VaraReportError) as cm:
            premium.generate_extended(SCENARIOS[PRIMARY], DOCS[PRIMARY], synthetic=True, palette='baseline', vara=v)
        message = str(cm.exception)
        for secret in ('2039', 'Jaipur', '26.9', '75.7', 'ravivara'):
            self.assertNotIn(secret, message)


if __name__ == '__main__':
    unittest.main()
