"""KUN-I18N-003 owner copy Change B, applied in KUN-I18N-COPY-005 (issue #73, owner chat approval for
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


class ChangeBNeutralSchemaWording(unittest.TestCase):
    """Owner-approved Change B (KUN-I18N-003 spec): the customer D9 footnote names the schema
    version only. Schema 0.3.0 itself and its engineering approvals are unchanged."""

    def test_footnote_names_schema_without_approval_wording(self):
        entry = UI['d9.footnote']
        self.assertTrue(entry['en'].endswith('The D9 house fields use chart schema 0.3.0.'))
        self.assertTrue(entry['hi'].endswith('D9 भाव के फ़ील्ड चार्ट स्कीमा 0.3.0 के अनुसार हैं।'))
        html = (ROOT / 'prototype/kundali_prototype/static/index.html').read_text(encoding='utf-8')
        self.assertNotIn('owner-approved chart schema', html)
        self.assertEqual(html.count(f'<p class="footnote" data-i18n="d9.footnote">{entry["en"]}</p>'), 1)
        self.assertEqual(entry['en'], 'D9 signs come from the unrounded sidereal longitudes in 3°20′ divisions; '
                         'D9 houses are counted from the D9 Lagna sign, so a D9 house number is not a D1 house '
                         'number. The D9 house fields use chart schema 0.3.0.')
        self.assertEqual(entry['hi'], 'D9 राशियाँ बिना पूर्णांकन वाले निरयन भोगांशों के 3°20′ के विभागों से '
                         'निकलती हैं; D9 भाव D9 लग्न राशि से गिने जाते हैं, इसलिए D9 भाव संख्या D1 भाव संख्या '
                         'नहीं है। D9 भाव के फ़ील्ड चार्ट स्कीमा 0.3.0 के अनुसार हैं।')
        for key, entry in UI.items():
            self.assertNotIn('owner-approved', entry['en'], key)
            self.assertNotIn('स्वीकृत', entry['hi'], key)


if __name__ == '__main__':
    unittest.main()
