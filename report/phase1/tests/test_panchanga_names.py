"""KUN-PAN-M2-NAMES-001 (issue #80): Tithi, Karana and Panchanga Yoga names.

Reference facts: research/panchanga/names/imd-names-evidence.json (IMD Positional Astronomy Centre,
Rashtriya Panchang names page, explanation page and the complete Kartika 1948 daily month). The
catalog under test: report/phase1/panchanga_names.json.

1. Mappings. Every Tithi 1-30, Karana 1-60 and Yoga 1-27 resolves to one machine id whose IMD
   spelling is the one the sources give: from the names list and the explanation's Karana rule,
   and again, independently, from the order in which the IMD daily pages print them over a full
   lunar month, where every one of the 60 Karana slots is observed and aligned with the Tithi
   ending times. Cycle boundaries are checked explicitly.
2. Fail closed. Out-of-range, bool, float, string or None indices, unknown elements, unsupported
   locales, broken catalogs, unknown modes and customer display without the recorded human review
   and owner release are all refused.
3. Report. names=None (the default) is byte-identical to f26dd10 for every synthetic scenario,
   both languages, sample and customer marking. names='qa_preview' draws exactly the expected
   names with a not-for-customers notice on every Panchanga page, keeps 13 pages, keeps pages 1-9
   and 13 identical, passes the layout, font, metadata and privacy checks, and leaks no birth data.
4. Live (SABPUJA_TEST_EPHE_PATH): at the middle of every IMD-printed span, the engine's own index
   maps to the name IMD printed. A cross-check only; IMD is the reference.
"""
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from report.phase1 import premium_report as premium  # noqa: E402
from report.phase1 import panchanga_report as pan  # noqa: E402
from report.phase1 import panchanga_names as pn  # noqa: E402
from sabpuja_kundali.panchanga import rules  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_premium_name as name_tests  # noqa: E402
import test_premium_report as base_tests  # noqa: E402

EVIDENCE = json.loads((ROOT / 'research/panchanga/names/imd-names-evidence.json').read_text(encoding='utf-8'))
PINNED = json.loads((HERE / 'fixtures/extended-13-page-sha256-f26dd10.json').read_text())['sha256']
SCENARIOS = name_tests.SCENARIOS
DOCS = {case: json.loads((HERE / 'fixtures/panchanga' / f'{case}.json').read_text()) for case in SCENARIOS}
NAMES = EVIDENCE['names_page']
ROWS = EVIDENCE['daily_kartika_1948']['rows']
IST = timezone(timedelta(hours=5, minutes=30))
QA = 'qa_preview'


def spelling_matches(element, index, printed):
    """A printed IMD name matches the catalog's publisher spelling or a recorded alternate."""
    term = pn.CATALOG['terms'][pn.term_id(element, index)]
    return printed in [term['source_spelling']['text']] + term['source_spelling']['alternates']


def tithi_number(paksha_printed, printed):
    """Tithi 1-30 from an IMD daily entry such as ('Asvina Krishna', 'Tritiya')."""
    day = {v: int(k) for k, v in NAMES['tithi'].items()}[printed]
    if day in (15, 30):
        return day
    return day + (15 if paksha_printed.split()[-1] == 'Krishna' else 0)


def ending(date_text, clock):
    """An IMD ending moment (IST, 'h. HH-MM', 24 h or more = next date) as a UTC datetime."""
    hours, minutes = (int(x) for x in clock.split('-'))
    base = datetime.fromisoformat(date_text).replace(tzinfo=IST)
    return (base + timedelta(hours=hours, minutes=minutes)).astimezone(timezone.utc)


def daily(element):
    """[(printed name or tithi number, ending UTC or None for ahoratra)] in printed order."""
    out = []
    for row in ROWS:
        for entry in row[element]:
            if element == 'tithi':
                paksha, printed, clock = entry
                value = tithi_number(paksha, printed)
            else:
                (value, clock) = entry
            out.append((value, None if clock == 'ahoratra' else ending(row['date'], clock)))
    return out


def collapse(seq):
    """IMD repeats an entry that lasts through a whole day ('ahoratra'); keep each span once."""
    out = []
    for value, end in seq:
        if out and out[-1][0] == value and out[-1][1] is None:
            out[-1] = (value, end)
        else:
            out.append((value, end))
    return out


class SourceFacts(unittest.TestCase):
    """The evidence file holds what the issue requires and nothing computed."""

    def test_sources_dated_and_official(self):
        for key, source in EVIDENCE['sources'].items():
            self.assertTrue(source['url'].startswith('https://packolkata.imd.gov.in/panchang/'), key)
            self.assertEqual(source['accessed'], '2026-11-06')
            self.assertIn('India Meteorological Department', source['publisher'])
        self.assertIn('All Rights Reserved', EVIDENCE['rights'])

    def test_names_page_counts(self):
        self.assertEqual(sorted(int(k) for k in NAMES['tithi']), list(range(1, 16)) + [30])
        self.assertEqual(len(NAMES['yoga_in_order']), 27)
        self.assertEqual(len(set(NAMES['yoga_in_order'])), 27)
        self.assertEqual(len(NAMES['karana_in_printed_order']), 11)

    def test_daily_month_is_complete_and_chronological(self):
        dates = [datetime.fromisoformat(r['date']).date() for r in ROWS]
        self.assertEqual(len(dates), 30)
        self.assertEqual([(b - a).days for a, b in zip(dates, dates[1:])], [1] * 29)
        for element in ('tithi', 'karana', 'yoga'):
            ends = [e for _, e in daily(element) if e is not None]
            self.assertEqual(ends, sorted(ends), element)


class Catalog(unittest.TestCase):

    def test_shape_ids_types_and_scripts(self):
        self.assertEqual(pn.catalog_problems(), [])
        terms = pn.CATALOG['terms']
        self.assertEqual(len(terms), 16 + 11 + 27)
        self.assertEqual(len({t['id'] for t in terms.values()}), len(terms))
        self.assertEqual({t['type'] for t in terms.values()}, {'tithi_name', 'karana', 'panchanga_yoga'})
        for tid, term in terms.items():
            for locale in pn.LOCALES:
                form = term['display'][locale]
                self.assertEqual(unicodedata.normalize('NFC', form), form)
            self.assertRegex(term['display']['hi'], r'^[ऀ-ॿ ]+$', tid)
            self.assertRegex(term['display']['en'], r'^[A-Za-z ]+$', tid)
        # The Yoga 'Shukla' and the Paksha 'shukla' are different things with different ids.
        self.assertEqual(terms['panchanga_yoga.shukla']['type'], 'panchanga_yoga')
        self.assertNotIn('shukla', [t.split('.', 1)[1] for t in terms if not t.startswith('panchanga_yoga.')])

    def test_source_spelling_is_kept_apart_from_display(self):
        terms = pn.CATALOG['terms']
        self.assertEqual(terms['karana.vanija']['source_spelling']['text'], 'Vanij')
        self.assertEqual(terms['karana.vanija']['display']['en'], 'Vanija')
        self.assertEqual(terms['panchanga_yoga.vishkambha']['source_spelling']['text'], 'Viskumbha')
        self.assertEqual(terms['panchanga_yoga.vishkambha']['display']['en'], 'Vishkambha')
        self.assertEqual(terms['karana.kimstughna']['source_spelling']['alternates'], ['Kinstughna'])
        printed = set(NAMES['yoga_in_order']) | set(NAMES['karana_in_printed_order']) | set(NAMES['tithi'].values())
        self.assertEqual({t['source_spelling']['text'] for t in terms.values()}, printed)

    def test_every_display_form_is_pending_human_review(self):
        """Nothing here is approved: the developer may not mark its own translation accepted."""
        for key, entry in pn._reviewed_entries(pn.CATALOG):
            self.assertEqual(set(entry['review'].values()), {'PENDING_HUMAN_REVIEW'}, key)
        self.assertEqual(pn.CATALOG['customer_release'], {'status': 'PENDING', 'record': None})
        self.assertTrue(pn.release_problems())

    def test_committed_crosswalk_is_current(self):
        run = subprocess.run([sys.executable, str(ROOT / 'report/phase1/tools/panchanga_names_crosswalk.py')],
                             capture_output=True, text=True, check=True)
        doc = (ROOT / 'docs/i18n/PANCHANGA-NAMES-CROSSWALK.md').read_text(encoding='utf-8')
        self.assertEqual(run.stdout, doc)
        for line in ('Tithi slots printed in the month read: 30 of 30', 'Karana slots printed in the month read: 60 of 60',
                     'Yoga slots printed in the month read: 27 of 27'):
            self.assertIn(line, doc)

    def test_m1_catalog_and_contract_untouched(self):
        """The names live in their own catalog; the M1 page catalog has none of them."""
        m1 = pan.CATALOG_PATH.read_text(encoding='utf-8')
        for term in pn.CATALOG['terms'].values():
            for form in [term['display']['en'], term['source_spelling']['text']]:
                if form in ('Shukla', 'Sukla'):
                    continue   # the adopted Paksha word
                self.assertIsNone(re.search(rf'\b{form}\b', m1), form)
        self.assertEqual(pan.SCHEMA, 'sabpuja-panchanga/1')
        self.assertEqual(pan.NAME_OMITTED, 'PANCHANGA_METHOD_NOT_ADOPTED')


class TithiMapping(unittest.TestCase):

    def test_all_thirty(self):
        for n in range(1, 31):
            with self.subTest(n=n):
                entry = pn.CATALOG['tithi'][str(n)]
                self.assertEqual(entry['paksha'], rules.paksha(n))
                self.assertEqual(entry['paksha_day'], rules.paksha_day(n))
                day = rules.paksha_day(n)
                expected = NAMES['tithi']['30' if n == 30 else str(day)]
                self.assertEqual(pn.source_spelling('tithi', n), expected)

    def test_paksha_boundaries_and_labels(self):
        cases = {1: ('Shukla Pratipada', 'शुक्ल प्रतिपदा'), 14: ('Shukla Chaturdashi', 'शुक्ल चतुर्दशी'),
                 15: ('Purnima', 'पूर्णिमा'), 16: ('Krishna Pratipada', 'कृष्ण प्रतिपदा'),
                 29: ('Krishna Chaturdashi', 'कृष्ण चतुर्दशी'), 30: ('Amavasya', 'अमावस्या'),
                 11: ('Shukla Ekadashi', 'शुक्ल एकादशी'), 26: ('Krishna Ekadashi', 'कृष्ण एकादशी')}
        for n, (en, hi) in cases.items():
            self.assertEqual(pn.tithi_label(n, 'en'), en)
            self.assertEqual(pn.tithi_label(n, 'hi'), hi)
        self.assertEqual(pn.CATALOG['tithi']['15']['paksha'], 'shukla')
        self.assertEqual(pn.CATALOG['tithi']['30']['paksha'], 'krishna')
        # Krishna days 1-14 reuse the Shukla names; only 15 differs (Purnima / Amavasya).
        for day in range(1, 15):
            self.assertEqual(pn.term_id('tithi', day), pn.term_id('tithi', day + 15))
        self.assertNotEqual(pn.term_id('tithi', 15), pn.term_id('tithi', 30))

    def test_imd_daily_month(self):
        """Consecutive Tithis across Purnima and Amavasya, each with the IMD name and Paksha."""
        seq = collapse(daily('tithi'))
        numbers = [n for n, _ in seq]
        self.assertEqual(numbers[0], 12)
        for a, b in zip(numbers, numbers[1:]):
            self.assertEqual(b, a % 30 + 1)
        self.assertIn(15, numbers)
        self.assertIn(30, numbers)
        for row in ROWS:
            for paksha, printed, _ in row['tithi']:
                n = tithi_number(paksha, printed)
                self.assertTrue(spelling_matches('tithi', n, printed))
                self.assertEqual(pn.CATALOG['tithi'][str(n)]['paksha'],
                                 'shukla' if paksha.endswith('Sukla') else 'krishna')


class KaranaMapping(unittest.TestCase):

    def test_rule_from_names_list_and_explanation(self):
        """IMD: 7 repeating Karanas from the 2nd half of Shukla Pratipada (2) to the 1st half of
        Krishna Chaturdashi (57); 4 fixed from the 2nd half of Krishna Chaturdashi (58) to the
        1st half of Shukla Pratipada (1), in the printed order."""
        quotes = EVIDENCE['explanation_quotes']
        self.assertIn('7 karanas which repeat in a cyclic order starting from 2nd half of sukla pratipada',
                      quotes['karana_repeating'])
        self.assertIn('4 sthira', quotes['karana_fixed'])
        printed = NAMES['karana_in_printed_order']
        repeating, fixed = printed[:7], printed[7:]
        slots = {i: repeating[(i - 2) % 7] for i in range(2, 58)}
        slots.update(zip((58, 59, 60, 1), fixed))
        self.assertEqual(sorted(slots), list(range(1, 61)))
        self.assertEqual(56, 8 * 7)
        for i in range(1, 61):
            with self.subTest(index=i):
                self.assertEqual(pn.source_spelling('karana', i), slots[i])
                kind = pn.CATALOG['terms'][pn.term_id('karana', i)]['karana_kind']
                self.assertEqual(kind, 'repeating' if 2 <= i <= 57 else 'fixed')

    def test_every_slot_observed_in_the_imd_daily_month(self):
        """Independent of the rule above: walk the 61 Karanas IMD prints for Kartika 1948. Each
        Tithi ending time printed equals the ending time of its 2nd-half Karana; that fixes the
        index of every Karana, and every one of the 60 slots must carry the printed name."""
        karanas = daily('karana')
        tithi_ends = {end: n for n, end in collapse(daily('tithi')) if end is not None}
        self.assertEqual(len(karanas), 61)
        anchor = next(i for i, (_, end) in enumerate(karanas) if end in tithi_ends)
        first_index = 2 * tithi_ends[karanas[anchor][1]] - anchor
        seen = {}
        for offset, (printed, end) in enumerate(karanas):
            index = (first_index + offset - 1) % 60 + 1
            if end in tithi_ends:
                self.assertEqual(index, 2 * tithi_ends[end], (printed, end))     # a 2nd half
            elif index % 2 == 0:
                self.fail(f'2nd-half Karana {printed} does not end with its Tithi')
            self.assertTrue(spelling_matches('karana', index, printed), (index, printed))
            seen.setdefault(index, printed)
        self.assertEqual(sorted(seen), list(range(1, 61)))
        # 31 Tithi endings (Dvadasi to Dvadasi): each closes exactly one 2nd-half Karana.
        self.assertEqual(len(tithi_ends), 31)
        self.assertEqual(sum(1 for _, end in karanas if end in tithi_ends), 31)
        # The fixed span seen directly: Krishna Chaturdashi and Amavasya, then Shukla Pratipada.
        self.assertEqual([seen[i] for i in (57, 58, 59, 60, 1, 2)],
                         ['Vishti', 'Sakuni', 'Chatuspada', 'Naga', 'Kinstughna', 'Bava'])

    def test_cycle_boundaries(self):
        ids = lambda *ix: [pn.term_id('karana', i).split('.')[1] for i in ix]
        self.assertEqual(ids(1, 2, 8, 9, 57, 58, 59, 60),
                         ['kimstughna', 'bava', 'vishti', 'bava', 'vishti', 'shakuni', 'chatushpada', 'naga'])
        counts = {}
        for i in range(1, 61):
            counts[pn.term_id('karana', i)] = counts.get(pn.term_id('karana', i), 0) + 1
        self.assertEqual(sorted(counts.values()), [1, 1, 1, 1] + [8] * 7)
        # A Tithi n holds Karanas 2n-1 and 2n (the report's own nesting rule).
        for n in range(1, 31):
            self.assertEqual({2 * n - 1, 2 * n} & {i for i in range(1, 61)}, {2 * n - 1, 2 * n})


class YogaMapping(unittest.TestCase):

    def test_order_from_names_page(self):
        for i, printed in enumerate(NAMES['yoga_in_order'], 1):
            self.assertEqual(pn.source_spelling('yoga', i), printed)
        self.assertIn('13° 20', EVIDENCE['explanation_quotes']['yoga_first'])
        self.assertEqual((pn.term_id('yoga', 1), pn.term_id('yoga', 27)),
                         ('panchanga_yoga.vishkambha', 'panchanga_yoga.vaidhriti'))

    def test_imd_daily_month_is_one_consecutive_cycle(self):
        seq = collapse(daily('yoga'))
        index = {**{n: i for i, n in enumerate(NAMES['yoga_in_order'], 1)}, 'Siddhi (Asrik)': 16, 'Sukla (Sukra)': 24}
        numbers = [index[name] for name, _ in seq]
        for a, b in zip(numbers, numbers[1:]):
            self.assertEqual(b, a % 27 + 1)
        self.assertEqual(set(numbers), set(range(1, 28)))
        for name, _ in seq:
            self.assertTrue(spelling_matches('yoga', index[name], name))


class FailClosed(unittest.TestCase):

    def test_bad_indices(self):
        for element, count in pn.COUNTS.items():
            for bad in (0, -1, count + 1, 61, 100, True, False, 1.0, '1', None, [1]):
                with self.subTest(element=element, bad=bad):
                    with self.assertRaises(pn.NamesError):
                        pn.term_id(element, bad)
        with self.assertRaises(pn.NamesError):
            pn.term_id('yoga', 28)
        with self.assertRaises(pn.NamesError):
            pn.tithi_label(31, 'en')
        for element in ('nakshatra', 'vara', 'Tithi', '', None):
            with self.assertRaises(pn.NamesError):
                pn.term_id(element, 1)

    def test_bad_locales(self):
        for locale in ('fr', 'EN', 'hi-IN', '', None):
            with self.assertRaises(pn.NamesError):
                pn.name('karana', 2, locale)
            with self.assertRaises(pn.NamesError):
                pn.tithi_label(3, locale)

    def test_broken_catalogs(self):
        def broken(fn):
            catalog = copy.deepcopy(pn.CATALOG)
            fn(catalog)
            return catalog
        cases = [
            lambda c: c['karana'].pop('58'),
            lambda c: c['karana'].update({'61': 'karana.bava'}),
            lambda c: c['karana'].update({'7': 'panchanga_yoga.vajra'}),       # wrong type
            lambda c: c['yoga'].update({'5': 'karana.bava'}),
            lambda c: c['tithi']['4'].update(name='karana.gara'),
            lambda c: c['terms'].pop('panchanga_yoga.siddhi'),
            lambda c: c['terms']['karana.naga'].update(id='karana.nag'),
            lambda c: c['terms']['karana.naga']['display'].pop('hi'),
            lambda c: c['terms']['karana.naga']['display'].update(hi='Naga'),   # wrong script
            lambda c: c['terms']['karana.naga']['display'].update(en='नाग'),
            lambda c: c['terms']['tithi_name.navami']['display'].update(en='Nave\u0301mi'),   # not NFC
            lambda c: c['terms']['tithi_name.navami']['review'].update(hi_display='APPROVED_BY_DEVELOPER'),
            lambda c: c['paksha_prefix']['krishna']['display'].pop('en'),
            lambda c: c['strings']['card.yoga_sub'].update(hi='{other}'),
        ]
        for i, fn in enumerate(cases):
            with self.subTest(case=i):
                self.assertTrue(pn.catalog_problems(broken(fn)))
                with self.assertRaises(pn.NamesError):
                    pn.check_mode(QA, broken(fn))

    def test_modes(self):
        self.assertIsNone(pn.check_mode(None))
        self.assertEqual(pn.check_mode(QA), QA)
        for mode in ('customer', 'QA_PREVIEW', 'preview', 'on', True, 1, ''):
            with self.assertRaises(pn.NamesError):
                pn.check_mode(mode)

    def test_release_gate(self):
        """Customer display needs every layer ACCEPTED and an owner release recorded in GitHub."""
        def approved(record='https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/80#issuecomment-1'):
            catalog = copy.deepcopy(pn.CATALOG)
            for _, entry in pn._reviewed_entries(catalog):
                entry['review'] = {layer: 'ACCEPTED' for layer in pn.REVIEW_LAYERS}
            catalog['customer_release'] = {'status': 'APPROVED', 'record': record}
            return catalog
        self.assertEqual(pn.release_problems(approved()), [])
        self.assertEqual(pn.check_mode('customer', approved()), 'customer')
        for record in (None, '', 'chat', 'https://github.com/other/repo/issues/1',
                       'https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/0'):
            self.assertTrue(pn.release_problems(approved(record)), record)
        one_missing = approved()
        one_missing['terms']['panchanga_yoga.indra']['review']['jyotish_terminology'] = 'PENDING_HUMAN_REVIEW'
        self.assertTrue(pn.release_problems(one_missing))
        revised = approved()
        revised['karana_kind_label']['fixed']['review']['hi_display'] = 'REVISED'
        self.assertTrue(pn.release_problems(revised))
        pending = approved()
        pending['customer_release']['status'] = 'PENDING'
        self.assertTrue(pn.release_problems(pending))


# ---------------------------------------------------------------------------
# The report.

_CACHE = {}


def render(case, locale, names=QA, synthetic=True):
    key = (case, locale, names, synthetic)
    if key not in _CACHE:
        data, audit = premium.render(SCENARIOS[case], synthetic, 'baseline', None, locale, panchanga=DOCS[case],
                                     names=names)
        _CACHE[key] = data, audit, fitz.open(stream=data, filetype='pdf')
    return _CACHE[key]


def squash(text):
    return ' '.join(text.split())


def all_name_forms(locale):
    forms = {t['display'][locale] for t in pn.CATALOG['terms'].values()}
    return forms - {'Shukla', 'शुक्ल'}   # the Paksha word, shown in every edition


def expected_forms(doc, locale):
    """The names the QA preview may show for this document: its own three, plus the Karana and
    Yoga names the method page cites (1, 2, 8, 58-60 and 1, 27)."""
    n, k, y = doc['tithi']['number'], doc['karana']['index'], doc['yoga']['index']
    out = {pn.name('tithi', n, locale), pn.name('karana', k, locale), pn.name('yoga', y, locale)}
    out |= {pn.name('karana', i, locale) for i in (1, 2, 8, 58, 59, 60)}
    out |= {pn.name('yoga', i, locale) for i in (1, 27)}
    return out


def tokens(text):
    return set(re.findall(r'[A-Za-zऀ-ॿ]+', text))


class DefaultUnchanged(unittest.TestCase):

    def test_thirteen_page_bytes_identical_to_f26dd10(self):
        self.assertEqual(len(PINNED), 52)
        for key, digest in PINNED.items():
            case, locale, marking = key.split('|')
            with self.subTest(key):
                pdf = premium.generate_extended(SCENARIOS[case], DOCS[case], synthetic=marking == 'sample',
                                                palette='baseline', locale=locale)
                self.assertEqual(hashlib.sha256(pdf).hexdigest(), digest)
                explicit = premium.generate_extended(SCENARIOS[case], DOCS[case], synthetic=marking == 'sample',
                                                     palette='baseline', locale=locale, names=None)
                self.assertEqual(explicit, pdf)

    def test_ten_page_edition_refuses_names(self):
        with self.assertRaises(ValueError):
            premium.render(SCENARIOS['s07-noon'], True, 'baseline', None, 'en', names=QA)

    def test_preview_server_and_prototype_do_not_use_names(self):
        for path in (ROOT / 'prototype').rglob('*.py'):
            text = path.read_text(encoding='utf-8')
            self.assertNotIn('qa_preview', text, path)
            self.assertNotIn('panchanga_names', text, path)


class QAPreview(unittest.TestCase):

    def test_customer_mode_and_unknown_modes_refused(self):
        for mode in ('customer', 'yes', 'QA', True):
            for locale in ('en', 'hi'):
                with self.assertRaises(pan.PanchangaReportError):
                    premium.generate_extended(SCENARIOS['s07-noon'], DOCS['s07-noon'], synthetic=True,
                                              palette='baseline', locale=locale, names=mode)

    def test_names_notice_and_unchanged_pages(self):
        for case in SCENARIOS:
            doc = DOCS[case]
            for locale in ('en', 'hi'):
                with self.subTest(case=case, locale=locale):
                    data, audit, pdf = render(case, locale)
                    base = fitz.open(stream=premium.generate_extended(SCENARIOS[case], doc, synthetic=True,
                                                                      palette='baseline', locale=locale))
                    self.assertEqual(pdf.page_count, 13)
                    for i in list(range(9)) + [12]:
                        self.assertEqual(pdf[i].get_text(), base[i].get_text(), (case, i + 1))
                    n, k, y = doc['tithi']['number'], doc['karana']['index'], doc['yoga']['index']
                    self.assertEqual(audit['panchanga']['names'],
                                     {'mode': QA, 'tithi': pn.term_id('tithi', n),
                                      'karana': pn.term_id('karana', k), 'yoga': pn.term_id('yoga', y)})
                    notice = squash(pn.text('qa.notice', locale))
                    p10, p11, p12 = (squash(pdf[i].get_text()) for i in (9, 10, 11))
                    for page in (p10, p11, p12):
                        self.assertIn(notice, page)
                    label = pn.tithi_label(n, locale)
                    self.assertIn(squash(pn.text('card.tithi_sub', locale, name=label, day=doc['tithi']['paksha_day'])), p10)
                    self.assertIn(squash(pn.text('card.karana_sub', locale, name=pn.name('karana', k, locale),
                                                 kind=pn.karana_kind(k, locale))), p10)
                    self.assertIn(squash(pn.text('card.yoga_sub', locale, name=pn.name('yoga', y, locale))), p10)
                    half = 'tr.karana_first' if k % 2 else 'tr.karana_second'
                    self.assertIn(squash(pn.text(half, locale, name=pn.name('karana', k, locale))), p11)
                    self.assertIn(label, p11)
                    # Only the expected names are added anywhere in the document. Words the default
                    # edition already prints (the Paksha, शुभ in "auspicious times") are not names.
                    added = tokens(' '.join(p.get_text() for p in pdf)) - tokens(' '.join(p.get_text() for p in base))
                    words = {w for form in all_name_forms(locale) for w in form.split()}
                    allowed = {w for form in expected_forms(doc, locale) for w in form.split()}
                    self.assertEqual((added & words) - allowed, set(), (case, locale))
                    self.assertTrue(allowed & added, (case, locale))
                    self.assertEqual(pdf.metadata['subject'], pn.text('qa.subject', locale))
                    # Numbers stay as before.
                    self.assertIn(squash(pan.STRINGS['pan.karana_value'][locale].format(index=k)), p10)
                    self.assertIn(squash(pan.STRINGS['pan.yoga_value'][locale].format(index=y)), p10)
            _CACHE.clear()

    def test_method_page_cites_the_imd_order(self):
        for locale in ('en', 'hi'):
            _, _, pdf = render('s07-noon', locale)
            method = squash(pdf[11].get_text())
            k = lambda i: pn.name('karana', i, locale)
            self.assertIn(squash(pn.text('pm.karana_value', locale, first=k(1), rep_first=k(2), rep_last=k(8),
                                         k58=k(58), k59=k(59), k60=k(60))), method)
            self.assertIn(squash(pn.text('pm.exc3', locale)), method)
            without_notice = method.replace(squash(pn.text('qa.notice', locale)), '')
            self.assertNotIn(squash(pan.STRINGS['pm.exc3'][locale]), without_notice)

    def test_layout_fonts_and_privacy(self):
        checks = base_tests.PremiumPDFTests()
        for case in SCENARIOS:
            for locale in ('en', 'hi'):
                with self.subTest(case=case, locale=locale):
                    data, audit, pdf = render(case, locale)
                    checks._assert_no_text_overlap(pdf, case)
                    checks._assert_inside_margins(pdf, case)
                    for number, page in enumerate(pdf, 1):
                        for span in base_tests.spans(page):
                            self.assertGreaterEqual(round(span['size'], 2), premium.MIN_TEXT, (case, number))
                        for _, fext, _, font, *_ in page.get_fonts(full=True):
                            self.assertEqual(fext, 'ttf', font)
                            self.assertTrue(font.split('+')[-1].startswith(('Poppins', 'Inter')), font)
                    blob = json.dumps(pdf.metadata, ensure_ascii=False) + json.dumps(audit['panchanga']['names'])
                    info = SCENARIOS[case]['input']
                    for secret in (info['local_date'], info['local_time'], info['place']['name']):
                        self.assertNotIn(secret, blob)
                    self.assertEqual(b'/Lang (hi)' in data, locale == 'hi')
            _CACHE.clear()

    def test_hindi_names_are_shaped_with_the_approved_fonts(self):
        """Every Hindi form is drawn through the Devanagari shaping path, never as raw codepoints."""
        for case in ('s07-noon', 's13-remaining-lagna'):
            _, audit, _ = render(case, 'hi')
            drawn = ' '.join(text for _, text, _ in audit['texts'])
            for form in expected_forms(DOCS[case], 'hi'):
                self.assertIn(form, drawn, (case, form))
            self.assertTrue(audit['devanagari_runs'])
            self.assertTrue(audit['glyph_forms'])
            _CACHE.clear()

    def test_inputs_not_mutated_and_deterministic(self):
        response, doc = copy.deepcopy(SCENARIOS['s07-noon']), copy.deepcopy(DOCS['s07-noon'])
        a = premium.generate_extended(response, doc, synthetic=True, palette='baseline', locale='hi', names=QA)
        b = premium.generate_extended(response, doc, synthetic=True, palette='baseline', locale='hi', names=QA)
        self.assertEqual(a, b)
        self.assertEqual((response, doc), (SCENARIOS['s07-noon'], DOCS['s07-noon']))

    def test_cli_flag_needs_the_extended_edition(self):
        run = subprocess.run([sys.executable, str(ROOT / 'report/phase1/premium_report.py'),
                              str(HERE / 'fixtures/premium/s07-noon.json'), os.devnull, '--names-qa-preview'],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('--names-qa-preview needs --panchanga-json', run.stderr)


@unittest.skipUnless(os.environ.get('SABPUJA_TEST_EPHE_PATH'), 'set SABPUJA_TEST_EPHE_PATH for the live IMD cross-check')
class LiveIMDCrossCheck(unittest.TestCase):
    """At the middle of every IMD-printed span of the Kartika 1948 month, the engine's own index
    names the element IMD printed. IST times are to the minute; every span is hours long."""

    @classmethod
    def setUpClass(cls):
        from sabpuja_kundali import panchanga
        cls.panchanga = panchanga
        cls.ephe = os.environ['SABPUJA_TEST_EPHE_PATH']

    def at(self, moment):
        local = moment.astimezone(IST)
        return self.panchanga.calculate({'birth_datetime': local.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
                                         'timezone': 'Asia/Kolkata', 'latitude': 22.57, 'longitude': 88.36},
                                        self.ephe)

    def test_engine_indices_carry_the_imd_names(self):
        checked = 0
        for element, key in (('tithi', 'number'), ('karana', 'index'), ('yoga', 'index')):
            seq = collapse(daily(element))
            for (_, start), (printed, end) in zip(seq, seq[1:]):
                if start is None or end is None:
                    continue
                middle = start + (end - start) / 2
                doc = self.at(middle.replace(second=0, microsecond=0))
                index = doc[element][key]
                with self.subTest(element=element, printed=printed, middle=middle.isoformat()):
                    if element == 'tithi':
                        self.assertEqual(index, printed)
                    else:
                        self.assertTrue(spelling_matches(element, index, printed), (index, printed))
                checked += 1
        self.assertGreater(checked, 120)


if __name__ == '__main__':
    unittest.main(verbosity=2)
