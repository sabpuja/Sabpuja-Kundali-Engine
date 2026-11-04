"""KUN-I18N-003 owner copy Change A, applied in KUN-I18N-COPY-005 (issue #73, owner chat approval for
implementation and independent QA; merged in PR #74; owner-accepted under KUN-GOV-SIMPLE-001, issue #75)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from report.phase1 import report_locale as loc  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_report_i18n as i18n_tests  # noqa: E402

UI = loc.REGISTER['ui']
PDF = loc.STRINGS


def squash(text):
    return ' '.join(text.split())


class ChangeAEnglishPage10(unittest.TestCase):
    """Owner-approved Change A (KUN-I18N-003 spec): English page 10 no longer lists the Hindi
    edition as unavailable. The Hindi value is unchanged."""

    def test_exact_wording_and_hindi_unchanged(self):
        self.assertEqual(PDF['method.exc5']['en'], 'Hindi text (available as a separate edition)')
        self.assertEqual(PDF['method.exc5']['hi'], 'अंग्रेज़ी पाठ (अलग संस्करण में उपलब्ध)')

    def test_page10_english_shows_the_new_line_once(self):
        from report.phase1 import premium_report as premium
        import fitz
        for case in i18n_tests.SCENARIOS:
            with self.subTest(case):
                pdf = fitz.open(stream=premium.generate(i18n_tests.SCENARIOS[case], synthetic=True, palette='baseline'), filetype='pdf')
                text = squash(pdf[premium.PAGE_OF['method'] - 1].get_text())
                self.assertEqual(text.count('Hindi text (available as a separate edition)'), 1)
                self.assertNotIn('Hindi edition', text)


if __name__ == '__main__':
    unittest.main()
