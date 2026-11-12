"""KUN-RC-ESS-001: the frozen 14-page English Janam Kundali Essentials edition.

Synthetic data only (the 25 cases of test_vara_report). Covers: every Essentials PDF is pinned by SHA-256; the
10-, 13- and 14-page editions stay byte-identical, also after an Essentials render; the edition is 14 A4 pages in
English with no document language, names off and customer mode; the development-preview and pending-QA notices
and the "separate edition" Hindi line are replaced by catalog sentences and appear nowhere; the sunrise page carries
the KUN-PAN-VARA-COPY-001 customer wording (no internal convention code, no Swiss call count, no doubled "after",
no "Outside the supported dates" for a withheld in-range sunrise); the catalog
and the edition manifest are pinned; Hindi, names, a missing Panchanga or Vara document and a malformed overlay
are refused; nothing is written and no input is mutated; and, with SABPUJA_TEST_EPHE_PATH set, the in-memory
form pipeline returns the same bytes and refuses bad requests with fixed messages that never quote the input.
"""
import copy
import hashlib
import json
import os
import sys
import unittest
from unittest import mock
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'prototype')]
from report.phase1 import essentials as es  # noqa: E402
from report.phase1 import premium_report as premium  # noqa: E402
from report.phase1 import panchanga_report as pan  # noqa: E402
from report.phase1 import vara_report as vr  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(ROOT / 'report/phase1/tools')]
import test_vara_report as vt  # noqa: E402

PINS_PATH = HERE / 'fixtures/essentials-en-sha256.json'
PINS_14 = json.loads(vt.PINS_14_PATH.read_text())['sha256']
PRIMARY = vt.PRIMARY
NAME = 'Asha Verma'   # synthetic
FORBIDDEN = ('Development preview', 'not for customers', 'NOT_FOR_CUSTOMERS', 'OWNER_ADOPTED', 'PR #93', 'ENGINEERING_UNVERIFIED', 'PENDING_INDEPENDENT_QA',
             'not yet been independently verified', 'separate edition', 'await independent QA', 'human review')
_CACHE = {}
# SHA-256 of the canonical JSON of the 13 approved overlay strings at 30bdace (sorted keys, UTF-8).
APPROVED_STRINGS_SHA256 = '70f0972351baa619b3f1f176994c78b647a8cd0c8ece117ddd9e057e0fbd1b12'


def matrix():
    return [(case, None) for case, *_ in vt.all_cases()] + [(PRIMARY, NAME)]


def inputs(case):
    _, response, doc, v = next(x for x in vt.all_cases() if x[0] == case)
    return response, doc, v


def render(case, name=None):
    key = (case, name)
    if key not in _CACHE:
        response, doc, v = inputs(case)
        data, audit = es.render(response, doc, v, name)
        _CACHE[key] = data, audit, fitz.open(stream=data, filetype='pdf')
    return _CACHE[key]


def text(pdf):
    return ' '.join(' '.join(p.get_text() for p in pdf).split())


class Pinned(unittest.TestCase):
    def test_every_essentials_pdf_is_pinned(self):
        pins = json.loads(PINS_PATH.read_text())
        self.assertEqual(pins['edition'], es.EDITION)
        self.assertEqual(len(pins['sha256']), 26)
        for case, name in matrix():
            with self.subTest(case=case, name=name):
                self.assertEqual(hashlib.sha256(render(case, name)[0]).hexdigest(),
                                 pins['sha256'][f'{case}|{name or "-"}'])

    def test_catalog_pinned_and_english_only(self):
        self.assertEqual(hashlib.sha256(es.CATALOG_PATH.read_bytes()).hexdigest(), es.CATALOG_SHA256)
        self.assertEqual(tuple(sorted(es.OVERLAY)), es.OVERLAY_KEYS)
        for key, entry in es.OVERLAY.items():
            self.assertEqual(set(entry), {'en'}, key)
        # Each replaced key exists in the catalog it replaces, so the overlay never invents a slot.
        self.assertIn('v.status', vr.STRINGS)
        self.assertIn('pm.status', pan.STRINGS)
        self.assertIn('pm.status_title', pan.STRINGS)
        self.assertIn('method.exc5', json.loads((ROOT / 'report/phase1/report_i18n.json').read_text())['strings'])

    def test_edition_manifest_matches_sources(self):
        self.assertEqual(es.manifest_problems(), [])
        files = json.loads(es.MANIFEST_PATH.read_text())['files']
        for p in ('report/phase1/premium_report.py', 'report/phase1/essentials_en.json',
                  'src/sabpuja_kundali/panchanga/vara.py', 'src/sabpuja_kundali/engine.py',
                  'prototype/kundali_prototype/server.py'):
            self.assertIn(p, files)

    def test_wording_released_only_by_the_owner_approval(self):
        # KUN-PAN-VARA-G2-001: the owner approved the exact copy of PR #93 at 30bdace (comment 6822876554).
        self.assertEqual(es.CATALOG['wording_status'], 'APPROVED_FOR_CUSTOMER_RELEASE')
        self.assertEqual(es.release_problems(), [])
        # The gate itself still fails closed for any other status.
        for status in ('PROPOSED_PENDING_OWNER_AND_INDEPENDENT_ENGLISH_QA', 'APPROVED', '', None):
            with self.subTest(status=status), mock.patch.dict(es.CATALOG, {'wording_status': status}):
                self.assertEqual(es.release_problems(), [f'Essentials wording is {status}'])

    def test_approved_strings_are_the_reviewed_copy(self):
        # Every overlay string is byte-identical to PR #93 at 30bdace; only the status and note changed.
        self.assertEqual(hashlib.sha256(json.dumps(es.CATALOG['strings'], ensure_ascii=False, sort_keys=True)
                                        .encode('utf-8')).hexdigest(), APPROVED_STRINGS_SHA256)


class OtherEditionsUnchanged(unittest.TestCase):
    def test_14_page_pins_after_essentials(self):
        for case, *_ in vt.all_cases():
            render(case)
            response, doc, v = inputs(case)
            for locale in ('en', 'hi'):
                with self.subTest(case=case, locale=locale), vt.maker.synthetic_hindi_places():
                    data = premium.generate_extended(response, doc, synthetic=False, palette='baseline',
                                                     locale=locale, vara=v)
                    self.assertEqual(hashlib.sha256(data).hexdigest(), PINS_14[f'{case}|{locale}|customer'])

    def test_13_page_pins_after_essentials(self):
        render(PRIMARY)
        checked = 0
        for key, want in vt.PINS_13.items():
            case, locale, *rest = key.split('|')
            if case != PRIMARY:
                continue
            checked += 1
            with self.subTest(key=key):
                synthetic = 'sample' in rest
                with vt.maker.synthetic_hindi_places():
                    data = premium.generate_extended(vt.SCENARIOS[case], vt.DOCS[case], synthetic=synthetic,
                                                     palette='baseline', locale=locale)
                self.assertEqual(hashlib.sha256(data).hexdigest(), want)
        self.assertGreaterEqual(checked, 2)

    def test_overlay_needs_extended_edition(self):
        response, _, _ = inputs(PRIMARY)
        with self.assertRaises(ValueError):
            premium.render(response, False, 'baseline', catalog_overlay=es.OVERLAY)


class Edition(unittest.TestCase):
    def test_fourteen_pages_english_customer_mode(self):
        data, audit, pdf = render(PRIMARY)
        self.assertEqual(len(pdf), 14)
        self.assertEqual(audit['essentials'], es.EDITION)
        self.assertEqual(audit['edition'], premium.EDITION_VARA)
        self.assertEqual(len(audit['page_keys']), 14)
        self.assertNotIn(b'/Lang', data)
        self.assertNotIn('names', audit['panchanga'])
        for page in pdf:
            self.assertAlmostEqual(page.rect.width, 595.28, places=1)
            self.assertAlmostEqual(page.rect.height, 841.89, places=1)
        all_text = text(pdf)
        self.assertNotIn('SAMPLE', all_text)

    def test_forbidden_notices_absent_and_replacements_drawn(self):
        for case, name in matrix():
            _, audit, pdf = render(case, name)
            body = text(pdf)
            with self.subTest(case=case, name=name):
                for bad in FORBIDDEN:
                    self.assertNotIn(bad, body)
                pages = audit['page_keys']
                sunrise = ' '.join(pdf[pages.index('sunrise')].get_text().split())
                pmethod = ' '.join(pdf[pages.index('pmethod')].get_text().split())
                method = ' '.join(pdf[pages.index('method')].get_text().split())
                self.assertIn(' '.join(es.OVERLAY['v.status']['en'].split()), sunrise)
                self.assertIn(es.OVERLAY['pm.status_title']['en'].upper(), pmethod)
                self.assertIn(' '.join(es.OVERLAY['pm.status']['en'].split()), pmethod)
                self.assertIn(es.OVERLAY['method.exc5']['en'], method)
                for bad in ('SUN-D-IMD-47', 'Swiss calls', 'after after', 'before before', 'Outside the supported dates'):
                    self.assertNotIn(bad, sunrise)
                for key in ('v.m.convention_value', 'v.m.times_value', 'v.m.checks_value'):
                    self.assertIn(' '.join(es.OVERLAY[key]['en'].split()), sunrise)
                self.assertIn('Sunrise and sunset are calculated for the birthplace shown on page', sunrise)
                # The engine's own claim boundary on the last page is kept as it is on the live report.
                self.assertIn('UNVERIFIED_GOLDEN_CHARTS', method)

    def test_name_is_drawn_only_when_given(self):
        self.assertNotIn(NAME, text(render(PRIMARY)[2]))
        self.assertIn(NAME, text(render(PRIMARY, NAME)[2]))

    def test_no_files_written_and_inputs_not_mutated(self):
        import builtins
        real_open = builtins.open
        written = []

        def guard(file, mode='r', *a, **k):
            if any(m in mode for m in 'wax+'):
                written.append(str(file))
            return real_open(file, mode, *a, **k)
        original = inputs(PRIMARY)
        response, doc, v = (copy.deepcopy(x) for x in original)
        overlay = copy.deepcopy(es.OVERLAY)
        builtins.open = guard
        try:
            es.generate(response, doc, v, NAME)
        finally:
            builtins.open = real_open
        self.assertEqual(written, [])
        self.assertEqual((response, doc, v), original)
        self.assertEqual(es.OVERLAY, overlay)


class Refusals(unittest.TestCase):
    def test_other_locales_and_names_refused(self):
        response, doc, v = inputs(PRIMARY)
        for kwargs in ({'locale': 'hi'}, {'locale': 'HI'}, {'locale': None}, {'names': 'qa_preview'},
                       {'names': 'customer'}, {'names': ''}):
            with self.subTest(kwargs=kwargs), self.assertRaises(es.EssentialsError) as ctx:
                es.generate(response, doc, v, **kwargs)
            self.assertEqual(ctx.exception.status, 422)

    def test_missing_documents_refused(self):
        response, doc, v = inputs(PRIMARY)
        for args in ((response, None, v), (response, doc, None), (response, None, None)):
            with self.assertRaises(es.EssentialsError) as ctx:
                es.generate(*args)
            self.assertEqual(ctx.exception.code, 'EDITION_INPUT_MISSING')

    def test_mismatched_documents_refused_before_drawing(self):
        response, _, _ = inputs(PRIMARY)
        _, other_doc, other_v = inputs('s01-first-supported-date')
        with self.assertRaises((pan.PanchangaReportError, vr.VaraReportError)):
            es.generate(response, other_doc, inputs(PRIMARY)[2])
        with self.assertRaises((pan.PanchangaReportError, vr.VaraReportError)):
            es.generate(response, inputs(PRIMARY)[1], other_v)

    def test_unnormalized_name_refused(self):
        response, doc, v = inputs(PRIMARY)
        with self.assertRaises(ValueError):
            es.generate(response, doc, v, '  Asha  ')


@unittest.skipUnless(os.environ.get('SABPUJA_TEST_EPHE_PATH'), 'set SABPUJA_TEST_EPHE_PATH for the form pipeline')
class FormPipeline(unittest.TestCase):
    BODY = {'place_id': 'in-jaipur', 'birth_date': '1992-08-14', 'birth_time': '06:40'}

    @classmethod
    def setUpClass(cls):
        from kundali_prototype import server
        cls.server = server
        cls.ephe = os.environ['SABPUJA_TEST_EPHE_PATH']
        cls.places = server.startup_verify(cls.ephe)

    def test_same_bytes_as_generate(self):
        from sabpuja_kundali import panchanga
        from sabpuja_kundali.panchanga import vara
        pdf = es.render_for_form(dict(self.BODY), self.places, self.ephe)
        status, response = self.server.handle_chart(json.dumps(self.BODY).encode(), self.places, self.ephe)
        self.assertEqual(status, 200)
        req = es.engine_request(response)
        self.assertEqual(pdf, es.generate(response, panchanga.calculate(req, self.ephe),
                                          vara.calculate(req, self.ephe)))
        self.assertEqual(len(fitz.open(stream=pdf, filetype='pdf')), 14)
        self.assertEqual(es.render_for_form(dict(self.BODY, report_locale='en'), self.places, self.ephe), pdf)

    def test_repeated_hour_keeps_the_handler_code_and_choices(self):
        body = {'place_id': 'gb-london', 'birth_date': '2020-10-25', 'birth_time': '01:30'}
        with self.assertRaises(es.InputRefusal) as ctx:
            es.render_for_form(body, self.places, self.ephe)
        e = ctx.exception
        self.assertEqual((e.status, e.code, e.category), (409, 'TIME_AMBIGUOUS_LOCAL', 'ambiguous'))
        offsets = sorted(c['utc_offset'] for c in e.extra['choices'])
        self.assertEqual(offsets, ['+00:00', '+01:00'])
        chosen = es.render_for_form(dict(body, utc_offset='+01:00'), self.places, self.ephe)
        self.assertEqual(len(fitz.open(stream=chosen, filetype='pdf')), 14)

    def test_refusals_are_fixed_and_never_quote_the_input(self):
        secret = 'Zq7Unique'
        cases = [
            (dict(self.BODY, report_locale='hi'), None, 'REPORT_LOCALE_UNSUPPORTED'),
            (dict(self.BODY, edition='essentials'), None, 'REQUEST_INVALID'),
            (dict(self.BODY, names='customer'), None, 'REQUEST_INVALID'),
            (dict(self.BODY, vara=secret), None, 'REQUEST_INVALID'),
            (dict(self.BODY, place_id=secret), None, 'PLACE_UNKNOWN'),
            (dict(self.BODY, birth_date='1992-02-30'), None, 'BIRTH_DATE_INVALID'),
            (dict(self.BODY, birth_time=secret), None, 'BIRTH_TIME_INVALID'),
            (dict(self.BODY), '<' + secret + '>', None),
            ([secret], None, 'REQUEST_INVALID'),
        ]
        for body, name, code in cases:
            with self.subTest(body=body, name=name), self.assertRaises(es.EssentialsError) as ctx:
                es.render_for_form(body, self.places, self.ephe, name)
            e = ctx.exception
            if code:
                self.assertEqual(e.code, code)
            self.assertIn(e.status, (400, 422))
            for field in (e.code, e.message, e.category, str(e), repr(e.args)):
                self.assertNotIn(secret, field)
                self.assertNotIn('1992', field)


if __name__ == '__main__':
    unittest.main()
