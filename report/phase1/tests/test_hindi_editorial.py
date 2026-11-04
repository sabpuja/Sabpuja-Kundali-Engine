"""KUN-I18N-002: Hindi editorial corrections. Synthetic engine fixtures only.

One test per corrected defect (docs/i18n/TERMINOLOGY.md, "Item dispositions" and "Additional
corrections"), plus guards that the terminology register stays in step with the catalogs and
keeps the human editorial gate open. These are developer checks of objective defects; they do
not stand in for a human Hindi review.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from report.phase1 import report_locale as loc  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_report_i18n as i18n_tests  # noqa: E402  (shared Hindi render cache)

REGISTER_DOC = ROOT / 'docs/i18n/TERMINOLOGY.md'
UI = loc.REGISTER['ui']
PDF = loc.STRINGS
ENGINE = loc.ENGINE_TEXT
PRIMARY = i18n_tests.PRIMARY


def all_hindi():
    for name, section in (('ui', UI), ('pdf', PDF), ('engine', ENGINE)):
        for key, entry in section.items():
            yield f'{name}:{key}', entry['en'], entry['hi']


def squash(text):
    return ' '.join(text.split())


class CorrectedDefects(unittest.TestCase):
    def test_item8_dinank_is_masculine(self):
        """दिनांक is masculine: plural दिनांक / oblique दिनांकों, never the feminine दिनांकें."""
        for key, _, hi in all_hindi():
            self.assertNotIn('दिनांकें', hi, key)
        self.assertIn('तक के स्थानीय दिनांक।', UI['date.help']['hi'])
        self.assertIn('के बाद के स्थानीय दिनांक।', UI['limit.2']['hi'])

    def test_item4_lunar_nodes_have_one_hindi_form(self):
        for key, en, hi in all_hindi():
            if re.search(r'lunar nodes?', en, re.I):
                with self.subTest(key):
                    self.assertIn('चंद्र पात', hi)
            self.assertNotIn('चंद्रमा के पात', hi, key)
            self.assertNotIn('चंद्रमा का मध्यम पात', hi, key)

    def test_item4_same_english_same_hindi_across_web_and_pdf(self):
        """A sentence that is identical in English on the web page and in the PDF is identical
        in Hindi, except for these documented exceptions."""
        exceptions = {
            'Prepared for',  # item 1: open reviewer choice (जातक vs "… के लिए तैयार")
            'Lagna',         # the PDF abbreviation legend deliberately adds "(भाव 1)"
            'Longitude',     # celestial भोगांश on the web, geographic देशांतर on the birth page
        }
        seen = {}
        for key, en, hi in all_hindi():
            if key.startswith('engine:') or not en.strip():
                continue
            seen.setdefault(en.strip(), set()).add(hi.strip())
        differing = {en for en, his in seen.items() if len(his) > 1}
        self.assertEqual(differing, exceptions)
        self.assertEqual(UI['m.nodes_value']['hi'], PDF['birth.nodes_value']['hi'])

    def test_item9_ellipsis_character(self):
        for key, _, hi in all_hindi():
            self.assertNotIn('...', hi, key)
        self.assertTrue(UI['download.preparing']['hi'].endswith('…'))
        self.assertTrue(UI['status.pdf_creating']['hi'].endswith('…'))

    def test_a1_high_latitude_note_covers_both_hemispheres(self):
        entry = ENGINE['disclosure.HIGH_LATITUDE_TIME_SENSITIVITY']
        self.assertTrue(entry['en'].startswith('Absolute latitude above 60 deg'))
        self.assertTrue(entry['hi'].startswith('अक्षांश 60° उत्तर या दक्षिण से अधिक:'))

    def test_a2_assumption_is_dharana_not_manyata(self):
        self.assertIn('धारणा', ENGINE['ut1_assumption']['hi'])
        for key, _, hi in all_hindi():
            self.assertNotIn('मान्यता', hi, key)  # reads as recognition / approval

    def test_a3_d9_note_is_unambiguous(self):
        text = PDF['chart.d9_note']['hi']
        self.assertNotIn('हर ग्रह बनाने से पहले', text)
        self.assertIn('कुंडली बनाने से पहले इसके हर ग्रह को', text)

    def test_a5_internal_message_does_not_claim_review(self):
        tr = loc.Translator('hi')
        with self.assertRaises(loc.ReportLocaleError) as caught:
            tr.engine_text('ut1_assumption', 'changed engine text')
        self.assertNotIn('review', str(caught.exception).lower())


class HindiPdfCarriesTheCorrections(unittest.TestCase):
    """The corrected sentences are drawn, extractable, on their pages; the old ones nowhere."""

    def test_corrected_sentences_on_their_pages(self):
        from report.phase1 import premium_report as premium
        _, _, pdf = i18n_tests.hi(PRIMARY)
        self.assertEqual(len(pdf), 10)
        pages = [squash(p.get_text()) for p in pdf]
        expect = {
            premium.PAGE_OF['guide']: ['और चंद्र पात राहु व केतु।'],
            premium.PAGE_OF['d9']: ['कुंडली बनाने से पहले इसके हर ग्रह को इंजन की D9 भाव सूची से जाँचा गया।'],
            premium.PAGE_OF['positions']: ['राहु मध्यम चंद्र पात है;'],
        }
        for page, phrases in expect.items():
            for phrase in phrases:
                with self.subTest(page=page, phrase=phrase):
                    self.assertIn(squash(phrase), pages[page - 1])
        whole = ' '.join(pages)
        for old in ('चंद्रमा के पात', 'चंद्रमा का मध्यम पात', 'हर ग्रह बनाने से पहले', 'मान्यता', 'दिनांकें'):
            self.assertNotIn(old, whole, old)


class TerminologyRegister(unittest.TestCase):
    doc = REGISTER_DOC.read_text(encoding='utf-8')

    def test_engine_sentence_table_matches_the_catalog(self):
        for key, entry in ENGINE.items():
            row = f'| {key} | {entry["en"]} | {entry["hi"]} |'
            self.assertIn(row, self.doc, key)

    def test_all_eighteen_items_have_a_disposition(self):
        section = self.doc.split('## Item dispositions (KUN-I18N-002)', 1)[1].split('### Additional corrections', 1)[0]
        rows = re.findall(r'^\| (\d+) \|(.+)$', section, re.M)
        self.assertEqual([int(n) for n, _ in rows], list(range(1, 19)))
        allowed = ('CORRECTED', 'KEPT', 'REVIEWER', 'OWNER')
        for number, rest in rows:
            cells = [c.strip() for c in rest.split('|')]
            self.assertTrue(cells[3].startswith(allowed), (number, cells[3]))

    def test_human_gate_stays_open_and_nothing_claims_review(self):
        self.assertIn('Pending independent human Hindi editorial review. Not owner-approved.', self.doc)
        self.assertIn('**PENDING: independent human Hindi / Jyotish editorial review. Not performed. Not owner-approved.**', self.doc)
        for text in (self.doc, loc.REGISTER['status'], loc.REPORT_CATALOG['status']):
            self.assertIsNone(re.search(r'human[- ]approved|human[- ]reviewed|editorially approved', text, re.I))
        self.assertIn('pending independent human Hindi editorial review', loc.REGISTER['status'])
        self.assertIn('pending independent human Hindi editorial review', loc.REPORT_CATALOG['status'])


if __name__ == '__main__':
    unittest.main()
