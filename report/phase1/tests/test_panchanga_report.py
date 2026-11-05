"""KUN-PAN-RPT-001: extended edition of the premium report with the birth-instant Panchanga M1 pages.

Synthetic data only. The 13 existing report scenarios are used with their `sabpuja-panchanga/1`
documents (tests/fixtures/panchanga, captured by tools/make_panchanga_fixtures.py from the
unchanged Panchanga M1 module). No new birth record is added to the repository.

Covers: the standard ten-page edition is unchanged; the extended edition renders 13 A4 pages in
English and Hindi with and without names, with dynamic contents, page numbers, cross-references
and methodology lists; every displayed Panchanga value and instant is the document's; local times
are in the right zone (and withheld outside the envelope); no Tithi, Karana or Yoga name is shown;
layout (no overlap, clipping, sub-8 pt text, struck text); fonts, palette and metadata; and every
mismatched, stale, unsupported or malformed document is refused before drawing.

With SABPUJA_TEST_EPHE_PATH set, it also recomputes every fixture with the M1 module and runs live
boundary cases (summer-time zones, high latitude, a birth exactly on a transition, failure
injection) that are not stored as fixtures.
"""
import copy
import dataclasses
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
from report.phase1 import report_locale as loc  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_premium_name as name_tests  # noqa: E402  (pinned ten-page hashes)
import test_premium_report as base_tests  # noqa: E402  (overlap, margin and line-strike checks)

SCENARIOS = name_tests.SCENARIOS
DOCS = {case: json.loads((HERE / 'fixtures/panchanga' / f'{case}.json').read_text()) for case in SCENARIOS}
PRIMARY = 's07-noon'
WITHHELD = 's01-first-supported-date'   # its start transitions fall on 31 December 1969, local
HINDI_NAME = 'क्षत्रिय प्रियंका सिद्धार्थ'
LATIN_NAME = 'Zoë-Anne O’Brien'
EXTRA_KEYS = ['panchanga', 'transitions', 'pmethod']
EXTENDED_KEYS = [k for k, _, _ in premium.PAGES[:-1]] + EXTRA_KEYS + ['method']
# Traditional names that must not appear while D07-A / D16-M1-INDEX hold: Tithi names, the
# eleven Karanas and the 27 Yogas (secondary-source spellings, SOURCE-REGISTER.md section 2).
FORBIDDEN_NAMES = (
    'Pratipada Dwitiya Dvitiya Tritiya Chaturthi Panchami Shashthi Saptami Ashtami Navami Dashami Ekadashi '
    'Dwadashi Trayodashi Chaturdashi Purnima Amavasya Amavasya '
    'Bava Balava Kaulava Taitila Garaja Gara Vanija Vanij Vishti Bhadra Shakuni Chatushpada Naga Kimstughna '
    'Kinstughna Vishkambha Viskumbha Priti Ayushman Saubhagya Shobhana Atiganda Sukarma Dhriti Shula Ganda '
    'Vriddhi Dhruva Vyaghata Harshana Vajra Siddhi Vyatipata Variyana Variyan Parigha Shiva Siddha Sadhya '
    'Shubha Brahma Indra Vaidhriti').split()   # Shukla (also a Yoga name) is the adopted Paksha id
FORBIDDEN_HINDI = ('प्रतिपदा द्वितीया तृतीया चतुर्थी पंचमी षष्ठी सप्तमी अष्टमी नवमी दशमी एकादशी द्वादशी त्रयोदशी '
                   'चतुर्दशी पूर्णिमा अमावस्या बव बालव कौलव तैतिल गर वणिज विष्टि भद्रा शकुनि चतुष्पद नाग किंस्तुघ्न '
                   'विष्कंभ प्रीति आयुष्मान सौभाग्य शोभन अतिगंड सुकर्मा धृति शूल गंड ध्रुव व्याघात हर्षण वज्र '
                   # Vriddhi and Shubha are left out: वृद्धि (growth) and शुभ (auspicious) are ordinary words.
                   'सिद्धि व्यतीपात वरीयान परिघ सिद्ध साध्य ब्रह्म ऐंद्र वैधृति').split()
_CACHE = {}


def ext(case=PRIMARY, locale='en', name=None, synthetic=True):
    key = (case, locale, name, synthetic)
    if key not in _CACHE:
        data, audit = premium.render(SCENARIOS[case], synthetic, 'baseline', name, locale, panchanga=DOCS[case])
        _CACHE[key] = data, audit, fitz.open(stream=data, filetype='pdf')
    return _CACHE[key]


def squash(text):
    return ' '.join(text.split())


def page_text(pdf, key, audit):
    return squash(pdf[audit['page_keys'].index(key)].get_text())


SPAN_KEYS = {'tithi': ('tithi', 'start', 'end'), 'karana': ('karana', 'start', 'end'), 'yoga': ('yoga', 'start', 'end'),
             'nakshatra': ('nakshatra', 'start', 'end'), 'pada': ('nakshatra', 'pada_start', 'pada_end')}


def utc(instant):
    return datetime.fromisoformat(instant['utc'].replace('Z', '+00:00'))


def shown(instant, zone_name):
    """Expected display: the UTC instant rounded half up to the minute, and that same instant in the zone."""
    from sabpuja_kundali.timezones import get_zone
    t = utc(instant)
    r = t.replace(second=0) + (timedelta(minutes=1) if t.second >= 30 else timedelta(0))
    return r, r.astimezone(get_zone(zone_name))


def durations(doc, locale):
    """Each span's length as the timeline prints it: whole hours and minutes from the UTC instants."""
    out = {}
    for element, (block, a, b) in SPAN_KEYS.items():
        seconds = int((utc(doc[block][b]) - utc(doc[block][a])).total_seconds())
        out[element] = squash(pan.STRINGS['tr.duration'][locale].format(
            hours=seconds // 3600, minutes=f'{seconds % 3600 // 60:02d}'))
    return out


def refused(test, response, doc, locale='en'):
    with test.assertRaises(pan.PanchangaReportError):
        premium.generate_extended(response, doc, synthetic=True, palette='baseline', locale=locale)


class StandardEditionUnchanged(unittest.TestCase):
    """Rollback baseline: the ten-page report is byte-identical to main 07da75e."""

    def test_pinned_ten_page_hashes_for_every_scenario(self):
        for case, (customer, sample) in name_tests.BEFORE.items():
            with self.subTest(case):
                self.assertEqual(hashlib.sha256(premium.generate(SCENARIOS[case], palette='baseline')).hexdigest(), customer)
                self.assertEqual(hashlib.sha256(premium.generate(SCENARIOS[case], synthetic=True,
                                                                 palette='baseline')).hexdigest(), sample)

    def test_render_without_panchanga_is_the_standard_edition(self):
        data, audit = premium.render(SCENARIOS[PRIMARY], True, 'baseline', panchanga=None)
        self.assertEqual(data, premium.generate(SCENARIOS[PRIMARY], synthetic=True, palette='baseline'))
        self.assertNotIn('edition', audit)
        self.assertEqual(len(fitz.open(stream=data, filetype='pdf')), 10)

    def test_extended_render_does_not_leak_into_a_later_standard_render(self):
        before = premium.generate(SCENARIOS[PRIMARY], synthetic=True, palette='baseline', locale='hi')
        ext(PRIMARY, 'hi')
        _CACHE.clear()
        premium.generate_extended(SCENARIOS[PRIMARY], DOCS[PRIMARY], synthetic=True, palette='baseline')
        self.assertEqual(premium.generate(SCENARIOS[PRIMARY], synthetic=True, palette='baseline', locale='hi'), before)
        self.assertEqual(premium.PAGES, premium.pages('en'))
        self.assertEqual(premium.PAGE_OF['method'], 10)

    def test_preview_server_is_untouched(self):
        source = (ROOT / 'prototype/kundali_prototype/server.py').read_text()
        self.assertNotIn('generate_extended', source)
        self.assertNotIn('panchanga', source.lower())

    def test_ten_page_catalog_unchanged(self):
        # The approved ten-page catalog is pinned by the editorial register; the Panchanga text
        # lives in its own catalog.
        self.assertTrue(set(pan.STRINGS).isdisjoint(set(loc.STRINGS) - {'meta.subject', 'method.exc1', 'method.exc2'}))
        for key in ('meta.subject', 'method.exc1', 'method.exc2'):
            self.assertNotEqual(pan.STRINGS[key], loc.STRINGS[key])


class PinnedInputs(unittest.TestCase):
    def test_method_and_claim_are_the_m1_module_values(self):
        from sabpuja_kundali.panchanga import contract
        from sabpuja_kundali.panchanga.search import DEFAULT_LIMITS
        self.assertEqual(pan.canonical_sha256(contract._method(DEFAULT_LIMITS)), pan.METHOD_SHA256)
        self.assertEqual(pan.SCHEMA, contract.SCHEMA)
        self.assertEqual(pan.VALIDATION_STATUS, contract.VALIDATION_STATUS)
        self.assertEqual((pan.LOCAL_FIRST, pan.LOCAL_LAST),
                         (contract.LOCAL_RENDERING_FIRST_DATE, contract.LOCAL_RENDERING_LAST_DATE))
        self.assertIn(pan.CLAIM_BOUNDARY.split('. ')[0], (ROOT / 'src/sabpuja_kundali/panchanga/contract.py').read_text())
        for case, doc in DOCS.items():
            self.assertEqual(doc['claim_boundary'], pan.CLAIM_BOUNDARY, case)

    def test_fixture_birth_matches_its_scenario(self):
        for case, doc in DOCS.items():
            chart = SCENARIOS[case]['chart']
            self.assertEqual(doc['birth'], {'utc': chart['birth']['utc'], 'timezone': chart['birth']['timezone']})

    def test_catalog_consistent_nfc_and_free_of_unadopted_names(self):
        import unicodedata
        self.assertEqual(pan.check_catalog(), [])
        for key, entry in pan.STRINGS.items():
            for locale, text in entry.items():
                self.assertEqual(unicodedata.normalize('NFC', text), text, key)
                words = set(re.findall(r'[A-Za-z]+', text))
                self.assertFalse(words & set(FORBIDDEN_NAMES), (key, words & set(FORBIDDEN_NAMES)))
                self.assertFalse(set(text.replace('(', ' ').replace(')', ' ').replace(',', ' ').split())
                                 & set(FORBIDDEN_HINDI), key)

    @unittest.skipUnless(os.environ.get('SABPUJA_TEST_EPHE_PATH'), 'set SABPUJA_TEST_EPHE_PATH to recompute fixtures')
    def test_every_fixture_is_reproduced_by_the_m1_module(self):
        sys.path.insert(0, str(ROOT / 'report/phase1/tools'))
        import make_panchanga_fixtures as maker
        from sabpuja_kundali import panchanga
        for case in SCENARIOS:
            doc = panchanga.calculate(maker.engine_request(SCENARIOS[case]), os.environ['SABPUJA_TEST_EPHE_PATH'])
            self.assertEqual(doc, DOCS[case], case)


class ExtendedEdition(unittest.TestCase):
    def test_every_scenario_both_languages_with_and_without_names(self):
        for case in SCENARIOS:
            for locale in ('en', 'hi'):
                for name in (None, LATIN_NAME, HINDI_NAME):
                    with self.subTest(case=case, locale=locale, name=name):
                        data, audit, pdf = ext(case, locale, name)
                        self.assertEqual(len(pdf), 13)
                        self.assertTrue(data.startswith(b'%PDF-'))
                        self.assertLess(len(data), premium.MAX_PDF_BYTES)
                        self.assertEqual(audit['page_keys'], EXTENDED_KEYS)
                        self.assertEqual(audit['layout'], 'phase2a-premium+extended-panchanga-m1/1')
                        for page in pdf:
                            self.assertAlmostEqual(page.rect.width, premium.W, 3)
                            self.assertAlmostEqual(page.rect.height, premium.H, 3)
            _CACHE.clear()

    def test_deterministic(self):
        for locale in ('en', 'hi'):
            a = premium.generate_extended(SCENARIOS[PRIMARY], DOCS[PRIMARY], synthetic=True, palette='baseline', locale=locale)
            b = premium.generate_extended(SCENARIOS[PRIMARY], DOCS[PRIMARY], synthetic=True, palette='baseline', locale=locale)
            self.assertEqual(a, b)

    def test_first_ten_pages_keep_their_content(self):
        """Pages 1 to 9 of the extended edition draw the same text as the ten-page report except
        for the total page count, the contents rows and the page references to the methodology."""
        std = fitz.open(stream=premium.generate(SCENARIOS[PRIMARY], synthetic=True, palette='baseline'), filetype='pdf')
        _, _, pdf = ext()
        for i in (0, 2, 3, 4, 5, 6, 7, 8):
            a = squash(std[i].get_text()).replace('of 10', 'of 13').replace('page 10', 'page 13')
            self.assertEqual(a, squash(pdf[i].get_text()), i + 1)

    def test_page_numbers_titles_and_contents(self):
        for locale in ('en', 'hi'):
            _, audit, pdf = ext(PRIMARY, locale)
            tr = loc.Translator(locale)
            titles = {k: t for k, t, _ in premium.pages(locale)}
            titles.update({k: pan.STRINGS[f'page.{k}.title'][locale] for k in EXTRA_KEYS})
            for number, key in enumerate(EXTENDED_KEYS[1:], 2):     # the cover has no footer
                text = squash(pdf[number - 1].get_text()).upper()
                with self.subTest(locale=locale, page=number):
                    self.assertIn(squash(tr.t('footer.page', number=number, total=13)).upper(), text)
                    self.assertIn(squash(tr.t('header.kicker', title=titles[key])).upper(), text)
                    self.assertIn(squash(tr.t('title.section', number=number - 1)).upper(), text)
            contents = squash(pdf[1].get_text())
            for number, key in enumerate(EXTENDED_KEYS[1:], 2):
                self.assertIn(f'{number - 1:02d}', contents)
                self.assertIn(squash(titles[key]), contents)
            # Cross-references point at the moved methodology page.
            self.assertIn(squash(tr.t('birth.method_ref', page=13)), squash(pdf[3].get_text()))
            method = squash(pdf[12].get_text())
            self.assertIn(squash(pan.STRINGS['method.inc6'][locale].format(first=10, last=12)), method)
            self.assertIn(squash(pan.STRINGS['method.exc6'][locale]), method)
            self.assertNotIn(squash(loc.STRINGS['method.exc1'][locale]), method)
            self.assertIn(squash(pan.STRINGS['pan.intro'][locale].format(positions=7)), squash(pdf[9].get_text()))

    def test_values_and_instants_are_the_documents(self):
        for case in SCENARIOS:
            doc = DOCS[case]
            for locale in ('en', 'hi'):
                with self.subTest(case=case, locale=locale):
                    _, audit, pdf = ext(case, locale)
                    first = page_text(pdf, 'panchanga', audit)
                    table = page_text(pdf, 'transitions', audit)
                    tr = loc.Translator(locale)
                    self.assertIn(squash(pan.STRINGS['pan.tithi_value'][locale].format(number=doc['tithi']['number'])), first)
                    self.assertIn(squash(pan.STRINGS['pan.paksha.' + doc['tithi']['paksha']][locale]), first)
                    self.assertIn(squash(pan.STRINGS['pan.tithi_sub'][locale].format(day=doc['tithi']['paksha_day'])), first)
                    self.assertIn(squash(pan.STRINGS['pan.karana_value'][locale].format(index=doc['karana']['index'])), first)
                    self.assertIn(squash(pan.STRINGS['pan.yoga_value'][locale].format(index=doc['yoga']['index'])), first)
                    self.assertIn(tr.nakshatra(doc['nakshatra']['name']), first)
                    self.assertIn(f"{doc['angles']['elongation_deg']:.8f}°", first)
                    self.assertIn(f"{doc['angles']['yoga_sum_deg']:.8f}°", first)
                    instants = [doc[el][edge] for el in ('tithi', 'karana', 'yoga') for edge in ('start', 'end')]
                    instants += [doc['nakshatra'][k] for k in ('start', 'end', 'pada_start', 'pada_end')]
                    self.assertIsNone(re.search(r'\d\d:\d\d:\d\d', table), 'no seconds are printed')
                    for instant in instants:
                        r_utc, r_local = shown(instant, doc['birth']['timezone'])
                        word = 'about' if locale == 'en' else 'लगभग'
                        if instant['local_rendering'] == 'rendered':   # cell marked once, on the local line
                            self.assertIn(f"UTC {r_utc.strftime('%Y-%m-%d %H:%M')}", table)
                            self.assertIn(f"{word} {r_local.strftime('%H:%M')}", table)
                            self.assertIn(r_local.isoformat()[-6:], table)
                        else:                                          # UTC only, marked on its own line
                            self.assertIn(f"UTC {word} {r_utc.strftime('%Y-%m-%d %H:%M')}", table)
                    for element, text in durations(doc, locale).items():
                        self.assertIn(text, table, element)
                    self.assertIn(pan.VALIDATION_STATUS, page_text(pdf, 'pmethod', audit))
            _CACHE.clear()

    def test_withheld_local_times_are_not_shown(self):
        doc = DOCS[WITHHELD]
        withheld = [i['utc'] for i in (doc['tithi']['start'], doc['karana']['start'], doc['yoga']['start'],
                                       doc['nakshatra']['start'], doc['nakshatra']['pada_start'])
                    if i['local_rendering'] == 'withheld_outside_envelope']
        self.assertEqual(len(withheld), 5)
        for locale in ('en', 'hi'):
            _, audit, pdf = ext(WITHHELD, locale)
            table = page_text(pdf, 'transitions', audit)
            self.assertEqual(sorted(audit['panchanga']['withheld']), sorted(withheld))
            self.assertEqual(table.count(squash(pan.STRINGS['tr.withheld'][locale])), 5)
            self.assertIn(squash(pan.STRINGS['tr.withheld_note'][locale].strip().split(' ')[0]), table)
            self.assertNotIn('1969', re.sub(r'UTC ((about|लगभग) )?1969-\d\d-\d\d', '', table))   # no local 1969 date shown

    def test_no_unadopted_names_anywhere(self):
        for case in SCENARIOS:
            for locale in ('en', 'hi'):
                _, _, pdf = ext(case, locale)
                words = set(re.findall(r'[A-Za-zऀ-ॿ]+', ' '.join(p.get_text() for p in pdf[9:12])))
                self.assertFalse(words & set(FORBIDDEN_NAMES), (case, locale))
                self.assertFalse(words & set(FORBIDDEN_HINDI), (case, locale))
            _CACHE.clear()

    def test_limitations_and_birth_instant_statement(self):
        for locale in ('en', 'hi'):
            _, audit, pdf = ext(PRIMARY, locale)
            self.assertIn(squash(pan.STRINGS['pan.instant'][locale]), page_text(pdf, 'panchanga', audit))
            method = page_text(pdf, 'pmethod', audit)
            self.assertIn(squash(pan.STRINGS['pm.status'][locale]), method)
            for i in range(1, 6):
                self.assertIn(squash(pan.STRINGS[f'pm.exc{i}'][locale]), method)

    def test_layout_overlap_margins_minimum_size_and_struck_text(self):
        checks = base_tests.PremiumPDFTests()
        for case in SCENARIOS:
            for locale in ('en', 'hi'):
                with self.subTest(case=case, locale=locale):
                    _, audit, pdf = ext(case, locale, HINDI_NAME if case == PRIMARY else None)
                    checks._assert_no_text_overlap(pdf, case)
                    checks._assert_inside_margins(pdf, case)
                    for number, page in enumerate(pdf, 1):
                        for span in base_tests.spans(page):
                            self.assertGreaterEqual(round(span['size'], 2), premium.MIN_TEXT, (case, number, span['text']))
                        if number < 10:
                            continue
                        lines = []
                        for drawing in page.get_drawings():
                            if 's' not in drawing['type']:
                                continue
                            for item in drawing['items']:
                                if item[0] == 'l':
                                    lines.append((item[1].x, item[1].y, item[2].x, item[2].y))
                        for span in base_tests.spans(page):
                            x0, y0, x1, y1 = span['bbox']
                            h = y1 - y0
                            body = (x0 + 0.5, y0 + h * 0.28, x1 - 0.5, y1 - h * 0.12)
                            for seg in lines:
                                self.assertFalse(base_tests.segment_hits_rect(seg, body), (case, number, span['text']))
            _CACHE.clear()

    def test_ink_stays_inside_margins_and_above_footer(self):
        for locale in ('en', 'hi'):
            _, _, pdf = ext(PRIMARY, locale)
            for number in (10, 11, 12, 13):
                page = pdf[number - 1]
                for clip in (fitz.Rect(0, 80, premium.M - 4, premium.H - 40),
                             fitz.Rect(premium.W - premium.M + 4, 80, premium.W, premium.H - 40),
                             fitz.Rect(premium.M, premium.H - premium.FOOTER_Y - 14 - 12, premium.W - premium.M,
                                       premium.H - premium.FOOTER_Y - 14 - 1)):   # just above the footer rule
                    pix = page.get_pixmap(dpi=72, clip=clip, colorspace=fitz.csGRAY)
                    self.assertEqual(sum(1 for v in pix.samples if v < 120), 0, (locale, number, clip))

    def test_fonts_palette_metadata_and_language(self):
        for locale in ('en', 'hi'):
            data, _, pdf = ext(PRIMARY, locale, HINDI_NAME)
            for page in pdf:
                for _, fext, _, name, *_ in page.get_fonts(full=True):
                    self.assertEqual(fext, 'ttf', name)
                    self.assertTrue(name.split('+')[-1].startswith(('Poppins', 'Inter')), name)
            meta = pdf.metadata
            self.assertEqual(meta['subject'], pan.STRINGS['meta.subject'][locale])
            self.assertEqual(meta['title'], loc.STRINGS['meta.title'][locale])
            blob = json.dumps(meta, ensure_ascii=False)
            for secret in (HINDI_NAME, SCENARIOS[PRIMARY]['input']['local_date'], SCENARIOS[PRIMARY]['input']['place']['name']):
                self.assertNotIn(secret, blob)
            self.assertEqual(b'/Lang (hi)' in data, locale == 'hi')
        allowed = {premium.Palette('baseline').hex[r].lower() for r in premium.Palette('baseline').hex}
        _, _, pdf = ext(PRIMARY, 'en')
        for page in pdf[9:12]:
            for drawing in page.get_drawings():
                if drawing['rect'].y1 < 90:
                    continue   # the approved logo in the header keeps its own colours
                for key in ('fill', 'color'):
                    colour = drawing.get(key)
                    if colour:
                        self.assertIn('#%02x%02x%02x' % tuple(round(c * 255) for c in colour), allowed)

    def test_no_files_written(self):
        import builtins
        real_open = builtins.open
        written = []

        def guard(file, mode='r', *a, **k):
            if any(m in mode for m in 'wax+'):
                written.append(str(file))
            return real_open(file, mode, *a, **k)
        builtins.open = guard
        try:
            premium.generate_extended(SCENARIOS[PRIMARY], DOCS[PRIMARY], synthetic=False, palette='baseline')
        finally:
            builtins.open = real_open
        self.assertEqual(written, [])

    def test_inputs_not_mutated(self):
        response, doc = copy.deepcopy(SCENARIOS[PRIMARY]), copy.deepcopy(DOCS[PRIMARY])
        premium.generate_extended(response, doc, synthetic=True, palette='baseline', locale='hi')
        self.assertEqual(response, SCENARIOS[PRIMARY])
        self.assertEqual(doc, DOCS[PRIMARY])


class Refusals(unittest.TestCase):
    """Every mismatched, stale, unsupported or malformed document fails closed before drawing."""

    def mutate(self, fn, case=PRIMARY, response_fn=None):
        doc, response = copy.deepcopy(DOCS[case]), copy.deepcopy(SCENARIOS[case])
        fn(doc)
        if response_fn:
            response_fn(response)
        for locale in ('en', 'hi'):
            refused(self, response, doc, locale)

    def test_wrong_chart(self):
        for other in ('s08-dawn', 's12-morning'):
            refused(self, SCENARIOS[PRIMARY], DOCS[other])

    def test_document_shape(self):
        for bad in (None, [], 'x', {}):
            if bad is None:
                continue
            refused(self, SCENARIOS[PRIMARY], bad)
        self.mutate(lambda d: d.pop('angles'))
        self.mutate(lambda d: d.update(extra=1))
        self.mutate(lambda d: d['tithi'].update(name='x'))
        self.mutate(lambda d: d['karana'].pop('name_omitted'))
        self.mutate(lambda d: d['yoga'].update(name_omitted='ADOPTED'))
        self.mutate(lambda d: d['nakshatra'].pop('pada_end'))
        self.mutate(lambda d: d['provenance'].update(note='x'))

    def test_schema_status_claim_and_method(self):
        self.mutate(lambda d: d.update(schema='sabpuja-panchanga/2'))
        self.mutate(lambda d: d.update(validation_status='VERIFIED'))
        self.mutate(lambda d: d.update(claim_boundary='Certified.'))
        self.mutate(lambda d: d['method'].update(method_revision='other'))
        self.mutate(lambda d: d['method']['transition_search'].update(bisection_max_iterations=10))
        self.mutate(lambda d: d['method']['transition_search'].update(bracket_extent_max_days_each_direction=1.0))
        self.mutate(lambda d: d['method']['decisions'].append('D07-B'))

    def test_birth_zone_and_provenance(self):
        self.mutate(lambda d: d['birth'].update(utc='2039-07-31T06:30:01Z'))
        self.mutate(lambda d: d['birth'].update(timezone='Asia/Calcutta'))
        self.mutate(lambda d: d['local_rendering'].update(zone='Europe/London'))
        self.mutate(lambda d: d['local_rendering']['envelope_local_dates'].update(first='1900-01-01'))
        self.mutate(lambda d: d['provenance'].update(ephemeris_manifest_sha256='0' * 64))
        self.mutate(lambda d: d['provenance']['swiss_ephemeris'].update(library_version='2.10.04'))
        self.mutate(lambda d: d['provenance']['timezone_data'].update(iana_version='2026f'))
        self.mutate(lambda d: d['provenance'].update(chart_schema_version_unchanged='0.4.0'))
        self.mutate(lambda d: d['provenance'].update(swiss_calls=0))
        self.mutate(lambda d: None,
                    response_fn=lambda r: r['chart']['calculation_metadata']['ephemeris_data'].update(
                        verified_before_calculation=False))

    def test_values(self):
        self.mutate(lambda d: d['nakshatra'].update(pada=2))
        self.mutate(lambda d: d['nakshatra'].update(name='Mula', index=19))
        self.mutate(lambda d: d['tithi'].update(number=12))
        self.mutate(lambda d: d['tithi'].update(paksha='krishna'))
        self.mutate(lambda d: d['tithi'].update(paksha_day=10))
        self.mutate(lambda d: d['karana'].update(index=23))
        self.mutate(lambda d: d['karana'].update(index=22))       # a half of tithi 11 but not the printed E
        self.mutate(lambda d: d['yoga'].update(index=24))
        self.mutate(lambda d: d['yoga'].update(index=True))
        self.mutate(lambda d: d['angles'].update(elongation_deg=d['angles']['elongation_deg'] + 1e-6))
        self.mutate(lambda d: d['angles'].update(yoga_sum_deg=float('nan')))
        self.mutate(lambda d: d['angles'].update(yoga_sum_deg=360.0))

    def test_transitions(self):
        def shift(instant, seconds):
            t = datetime.strptime(instant['utc'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc) + timedelta(seconds=seconds)
            instant['utc'] = t.strftime('%Y-%m-%dT%H:%M:%SZ')
            if 'local' in instant:
                instant['local'] = datetime.fromisoformat(instant['local']).__add__(timedelta(seconds=seconds)).isoformat()
        self.mutate(lambda d: shift(d['tithi']['start'], 3600 * 9))            # after birth
        self.mutate(lambda d: shift(d['tithi']['end'], -3600 * 16))           # before birth
        self.mutate(lambda d: shift(d['yoga']['start'], -86400 * 3))          # beyond the frozen extent
        self.mutate(lambda d: shift(d['karana']['start'], 60))                # karana no longer half of the tithi
        self.mutate(lambda d: shift(d['nakshatra']['pada_end'], 86400))       # pada leaves the nakshatra
        self.mutate(lambda d: d['tithi']['start'].update(utc='2039-07-31T00:13:13.5Z'))
        self.mutate(lambda d: d['tithi']['start'].update(utc='2039-07-31 00:13:13'))
        self.mutate(lambda d: d['tithi']['start'].update(local='2039-07-31T05:43:13+05:00'))  # wrong offset
        self.mutate(lambda d: d['tithi']['start'].update(local='2039-07-31T00:13:13+00:00'))  # not the zone
        self.mutate(lambda d: d['tithi']['start'].update(local_rendering='withheld_outside_envelope'))
        self.mutate(lambda d: d['tithi']['start'].update(local_rendering='guessed'))
        self.mutate(lambda d: d['tithi']['start']['search'].update(final_bracket_us=600_000))
        self.mutate(lambda d: d['tithi']['start']['search'].update(iterations=65))
        self.mutate(lambda d: d['tithi']['start']['search'].update(bracket_steps=11))

    def test_withheld_must_really_be_outside_the_envelope(self):
        def render_local(d):
            start = d['tithi']['start']
            start['local_rendering'] = 'rendered'
            start['local'] = '1969-12-31T15:45:44+05:30'
        self.mutate(render_local, case=WITHHELD)

    def test_unsupported_locale_and_unnormalised_name(self):
        with self.assertRaises(loc.ReportLocaleError):
            premium.generate_extended(SCENARIOS[PRIMARY], DOCS[PRIMARY], locale='fr')
        with self.assertRaises(ValueError):
            premium.generate_extended(SCENARIOS[PRIMARY], DOCS[PRIMARY], display_name='  Asha  ')


class DisplayRounding(unittest.TestCase):
    """KUN-PAN-RPT-001 QA: transition times are printed to the nearest minute. The UTC instant is rounded
    once and the same rounded instant is converted to the zone; M1 seconds are not changed."""

    @staticmethod
    def at(text):
        return datetime.strptime(text, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

    def setUp(self):
        from sabpuja_kundali.timezones import get_zone
        self.kolkata, self.london = get_zone('Asia/Kolkata'), get_zone('Europe/London')

    def check(self, utc_text, zone, want_utc, want_local, local=True):
        moment = self.at(utc_text)
        r_utc, r_local = pan.display_instant(moment, moment.astimezone(zone) if local else None, zone)
        self.assertEqual(r_utc.strftime('%Y-%m-%d %H:%M:%S'), want_utc)
        self.assertEqual(None if r_local is None else r_local.isoformat(), want_local)

    def test_half_minute_rounds_up_and_29_seconds_down(self):
        self.check('2039-07-31 00:13:29', self.kolkata, '2039-07-31 00:13:00', '2039-07-31T05:43:00+05:30')
        self.check('2039-07-31 00:13:30', self.kolkata, '2039-07-31 00:14:00', '2039-07-31T05:44:00+05:30')
        self.check('2039-07-31 00:13:00', self.kolkata, '2039-07-31 00:13:00', '2039-07-31T05:43:00+05:30')
        self.check('2039-07-31 00:13:59', self.kolkata, '2039-07-31 00:14:00', '2039-07-31T05:44:00+05:30')

    def test_midnight_and_year_roll_over_in_utc_and_local(self):
        self.check('2039-07-31 18:29:30', self.kolkata, '2039-07-31 18:30:00', '2039-08-01T00:00:00+05:30')
        self.check('2039-12-31 23:59:45', self.london, '2040-01-01 00:00:00', '2040-01-01T00:00:00+00:00')

    def test_summer_time_gap_and_repeated_hour(self):
        # Clocks go forward at 01:00 UTC on 30 March 2031: 00:59:30 UTC (00:59 GMT) is shown as 02:00 BST.
        self.check('2031-03-30 00:59:30', self.london, '2031-03-30 01:00:00', '2031-03-30T02:00:00+01:00')
        self.check('2031-03-30 00:59:29', self.london, '2031-03-30 00:59:00', '2031-03-30T00:59:00+00:00')
        # Clocks go back at 01:00 UTC on 26 October 2031: 01:00 local occurs twice; the offset tells which.
        self.check('2031-10-26 00:59:45', self.london, '2031-10-26 01:00:00', '2031-10-26T01:00:00+00:00')
        self.check('2031-10-26 00:00:10', self.london, '2031-10-26 00:00:00', '2031-10-26T01:00:00+01:00')

    def test_withheld_stays_withheld_and_rounding_never_leaves_the_envelope(self):
        self.check('1969-12-31 18:29:40', self.kolkata, '1969-12-31 18:30:00', None, local=False)
        self.check('2100-12-31 23:59:31', self.london, '2101-01-01 00:00:00', None)
        self.check('2100-12-31 23:59:29', self.london, '2100-12-31 23:59:00', '2100-12-31T23:59:00+00:00')


@unittest.skipUnless(os.environ.get('SABPUJA_TEST_EPHE_PATH'), 'set SABPUJA_TEST_EPHE_PATH for live boundary cases')
class LiveBoundaries(unittest.TestCase):
    """Synthetic requests computed live with the pinned ephemeris; nothing here is stored."""

    @classmethod
    def setUpClass(cls):
        sys.path[:0] = [str(ROOT / 'prototype')]
        from kundali_prototype import server
        from kundali_prototype.places import load_places
        from sabpuja_kundali import panchanga
        cls.server, cls.places, cls.panchanga = server, load_places(), panchanga
        cls.ephe = os.environ['SABPUJA_TEST_EPHE_PATH']

    def case(self, place_id, day, clock, utc_offset=None):
        body = {'place_id': place_id, 'birth_date': day, 'birth_time': clock}
        if utc_offset:
            body['utc_offset'] = utc_offset
        status, response = self.server.handle_chart(json.dumps(body).encode(), self.places, self.ephe)
        self.assertEqual(status, 200, response)
        sys.path.insert(0, str(ROOT / 'report/phase1/tools'))
        import make_panchanga_fixtures as maker
        return response, self.panchanga.calculate(maker.engine_request(response), self.ephe)

    def render_both(self, response, doc):
        out = {}
        for locale in ('en', 'hi'):
            data, audit = premium.render(response, True, 'baseline', None, locale, panchanga=doc)
            out[locale] = audit, fitz.open(stream=data, filetype='pdf')
            self.assertEqual(len(out[locale][1]), 13)
        return out

    def test_summer_time_change_inside_a_span(self):
        # London, the night clocks go forward (30 March 2031): later transitions are in +01:00.
        response, doc = self.case('gb-london', '2031-03-30', '00:30:00')
        offsets = {datetime.fromisoformat(doc[e][k]['local']).utcoffset()
                   for e in ('tithi', 'karana', 'yoga') for k in ('start', 'end')}
        self.assertEqual(offsets, {timedelta(0), timedelta(hours=1)})
        for locale, (audit, pdf) in self.render_both(response, doc).items():
            table = page_text(pdf, 'transitions', audit)
            self.assertIn('+00:00', table)
            self.assertIn('+01:00', table)
            self.assertIn(squash(pan.STRINGS['tr.offset_note'][locale].format(offset='+00:00')), table)
            self.assertIn('Europe/London', table)
            for element, text in durations(doc, locale).items():   # lengths come from UTC, not wall clock
                self.assertIn(text, table, element)
        crossing = [el for el, (block, a, b) in SPAN_KEYS.items()
                    if datetime.fromisoformat(doc[block][a]['local']).utcoffset()
                    != datetime.fromisoformat(doc[block][b]['local']).utcoffset()]
        self.assertTrue(crossing)
        for el in crossing:
            block, a, b = SPAN_KEYS[el]
            wall = (datetime.fromisoformat(doc[block][b]['local']).replace(tzinfo=None)
                    - datetime.fromisoformat(doc[block][a]['local']).replace(tzinfo=None))
            self.assertEqual(utc(doc[block][b]) - utc(doc[block][a]), wall - timedelta(hours=1), el)

    def test_repeated_hour_second_occurrence(self):
        response, doc = self.case('gb-london', '2031-10-26', '01:30:00', '+00:00')
        self.assertEqual(response['input']['offset_resolution'], 'user_selected_repeated_hour')
        self.render_both(response, doc)

    def test_summer_time_end_and_winter_birth_in_london(self):
        # Clocks go back on 26 October 2031; a birth the day before has spans on both sides.
        response, doc = self.case('gb-london', '2031-10-25', '22:00:00')
        self.render_both(response, doc)

    def test_birth_exactly_on_a_transition_and_one_second_before(self):
        end_local = datetime.fromisoformat(DOCS[PRIMARY]['tithi']['end']['local'])   # Tithi 12 begins
        day, clock = end_local.date().isoformat(), end_local.strftime('%H:%M:%S')
        response, doc = self.case('in-jaipur', day, clock)
        self.assertEqual(doc['tithi']['number'], 12)
        self.assertEqual(doc['tithi']['start']['utc'], response['chart']['birth']['utc'])
        for locale, (audit, pdf) in self.render_both(response, doc).items():
            r_utc, _ = shown(doc['tithi']['start'], doc['birth']['timezone'])
            self.assertIn(f"UTC {r_utc.strftime('%Y-%m-%d %H:%M')}", page_text(pdf, 'transitions', audit))
        before = (end_local - timedelta(seconds=1)).strftime('%H:%M:%S')
        response, doc = self.case('in-jaipur', day, before)
        self.assertEqual(doc['tithi']['number'], 11)
        self.assertEqual(doc['tithi']['end']['utc'], DOCS[PRIMARY]['tithi']['end']['utc'])
        for locale, (audit, pdf) in self.render_both(response, doc).items():
            r_utc, _ = shown(doc['tithi']['end'], doc['birth']['timezone'])
            self.assertIn(f"UTC {r_utc.strftime('%Y-%m-%d %H:%M')}", page_text(pdf, 'transitions', audit))

    def test_last_supported_instant(self):
        response, doc = self.case('in-new-delhi', '2100-12-31', '23:59:59')
        audits = self.render_both(response, doc)
        ends = [doc[e]['end']['local_rendering'] for e in ('tithi', 'karana', 'yoga', 'nakshatra')]
        self.assertIn('withheld_outside_envelope', ends)
        self.assertTrue(audits['en'][0]['panchanga']['withheld'])

    def test_failed_search_produces_no_document_and_stricter_limits_are_refused(self):
        from sabpuja_kundali.panchanga import PanchangaComputationError
        from sabpuja_kundali.panchanga.search import DEFAULT_LIMITS
        response = SCENARIOS[PRIMARY]
        sys.path.insert(0, str(ROOT / 'report/phase1/tools'))
        import make_panchanga_fixtures as maker
        request = maker.engine_request(response)
        with self.assertRaises(PanchangaComputationError):
            self.panchanga.calculate(request, self.ephe, limits=dataclasses.replace(DEFAULT_LIMITS, max_extent_us=3600 * 10**6))
        strict = self.panchanga.calculate(request, self.ephe, limits=dataclasses.replace(DEFAULT_LIMITS, max_iterations=40))
        refused(self, response, strict)

    def test_unsupported_input_never_reaches_the_report(self):
        for body in ({'place_id': 'in-new-delhi', 'birth_date': '1969-12-31', 'birth_time': '12:00:00'},
                     {'place_id': 'in-new-delhi', 'birth_date': '2101-01-01', 'birth_time': '00:00:00'},
                     {'place_id': 'gb-london', 'birth_date': '2031-03-30', 'birth_time': '01:30:00'},   # skipped hour
                     {'place_id': 'gb-london', 'birth_date': '2031-10-26', 'birth_time': '01:30:00'},   # repeated, unchosen
                     {'place_id': 'no-tromso', 'birth_date': '2044-06-21', 'birth_time': '12:00:00'}):  # latitude band
            status, _ = self.server.handle_chart(json.dumps(body).encode(), self.places, self.ephe)
            self.assertNotEqual(status, 200, body)


if __name__ == '__main__':
    unittest.main()
