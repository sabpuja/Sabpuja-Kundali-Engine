"""KUN-UX-NAME-001: the optional report name rule (report/phase1/display_name.py).

Pure validation tests, the font-coverage proof for every accepted character, and the
parity check that the browser (static/app.js) applies the same rule as the server.
Synthetic names only.
"""
import json
import shutil
import subprocess
import sys
import unicodedata
import unittest
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from report.phase1 import display_name as dn  # noqa: E402
from report.phase1.display_name import DisplayNameError, normalize  # noqa: E402

FONTS = ROOT / 'prototype/kundali_prototype/static/fonts'
APP_JS = ROOT / 'prototype/kundali_prototype/static/app.js'

ACCEPTED = {
    'Asha Verma': 'Asha Verma',
    '  Asha Verma  ': 'Asha Verma',
    ' Asha　': 'Asha',
    "O'Brien": "O'Brien",
    'D’Souza': 'D’Souza',
    'Mary-Jane Fernandes': 'Mary-Jane Fernandes',
    'R. K. Sharma': 'R. K. Sharma',
    'Ramesh Jr.': 'Ramesh Jr.',
    'Zoë Ñúñez': 'Zoë Ñúñez',
    'Ākash Śarmā': 'Ākash Śarmā',
    'Ștefan Țurcanu': 'Ștefan Țurcanu',
    'José': 'José',                       # NFC composes the accent
    'प्रियंका शर्मा': 'प्रियंका शर्मा',
    'क्षत्रिय सिद्धार्थ': 'क्षत्रिय सिद्धार्थ',
    'श्री राम': 'श्री राम',
    'अर्जुन हृषीकेश': 'अर्जुन हृषीकेश',
    'संजय ठाकुर': 'संजय ठाकुर',
    'क्‍ष': 'क्‍ष',                   # explicit half form (ZWJ after virama)
    'क्‌ष': 'क्‌ष',                   # explicit virama (ZWNJ after virama)
    'Ravi रवि Kumar': 'Ravi रवि Kumar',
    'क़': 'क़',                   # क़ is a composition exclusion: NFC is क + nukta
}

REFUSED_422 = [
    'Asha\nVerma', 'Asha\rVerma', 'Asha\tVerma', 'Asha Verma\n', '\nAsha', '\x00Asha', 'Asha\x7f',
    '‮amreV ahsA', 'Asha‭Verma', '⁦Asha⁩', 'Asha​Verma', 'Asha Verma',
    '﻿Asha', '­Asha', 'Asha',
    '<script>alert(1)</script>', '<b>Asha</b>', 'Asha & Ravi', '"Asha"', 'javascript:alert(1)',
    '${7*7}', '{{name}}', 'Asha; DROP TABLE', 'Asha/Ravi', 'Asha=1', '(Asha)', 'Asha_Verma', '@asha', '#asha',
    'Asha 2', '१२३', 'Asha😀', 'Аша', 'Ασα', 'آشا', 'アシャ', '张伟', 'অশা', 'ਆਸ਼ਾ',
    'ॐ नमः', 'राम।', 'Asha…', 'ṛṣi', 'Ẁales',
    "'Asha", "Asha'", '-Asha', 'Asha-', '.Asha', 'Asha--Verma', "Asha'-Verma", 'Asha  Verma', 'Asha.Verma',
    'ि', 'aि', 'é́', 'क‍', '‍क', 'क‍ष', 'क्‍ ',
]


class Rule(unittest.TestCase):
    def test_accepted_names_are_returned_normalized(self):
        for raw, want in ACCEPTED.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize(raw), want)

    def test_no_name(self):
        for raw in (None, '', ' ', '   ', ' 　'):
            with self.subTest(raw=raw):
                self.assertIsNone(normalize(raw))

    def test_refused_names(self):
        for raw in REFUSED_422:
            with self.subTest(raw=raw):
                with self.assertRaises(DisplayNameError) as cm:
                    normalize(raw)
                self.assertEqual(cm.exception.status, 422)
                self.assertIn(cm.exception.code, ('DISPLAY_NAME_INVALID', 'DISPLAY_NAME_TOO_LONG'))
                # The refusal never carries the submitted text.
                for part in (raw, raw.strip()):
                    if part.strip():
                        self.assertNotIn(part, cm.exception.message)
                        self.assertNotIn(part, str(cm.exception))

    def test_non_string_is_a_request_error(self):
        for raw in (1, 1.5, True, ['Asha'], {'n': 'Asha'}):
            with self.subTest(raw=raw):
                with self.assertRaises(DisplayNameError) as cm:
                    normalize(raw)
                self.assertEqual((cm.exception.status, cm.exception.code), (400, 'REQUEST_INVALID'))

    def test_eighty_visible_characters(self):
        self.assertEqual(normalize('A' * 80), 'A' * 80)
        self.assertEqual(normalize(' '.join(['Abcdefghi'] * 8)), ' '.join(['Abcdefghi'] * 8))  # 79
        # Signs and joiners do not count; each consonant does: 'क्ष' is two.
        self.assertEqual(dn.visible_length('क्ष'), 2)
        self.assertEqual(dn.visible_length('श्री'), 2)
        self.assertEqual(normalize('क्ष' * 40), 'क्ष' * 40)
        self.assertEqual(normalize('कि' * 80), 'कि' * 80)
        for raw in ('A' * 81, 'क्ष' * 40 + 'क', 'कि' * 81, 'Ab ' * 27 + 'A'):
            with self.subTest(n=len(raw)):
                with self.assertRaises(DisplayNameError) as cm:
                    normalize(raw)
                self.assertEqual(cm.exception.code, 'DISPLAY_NAME_TOO_LONG')

    def test_raw_input_is_bounded_before_any_other_work(self):
        self.assertEqual(normalize(' ' * 100 + 'Asha' + ' ' * 100), 'Asha')
        with self.assertRaises(DisplayNameError) as cm:
            normalize(' ' * 317 + 'Asha')
        self.assertEqual(cm.exception.code, 'DISPLAY_NAME_TOO_LONG')
        with self.assertRaises(DisplayNameError):
            normalize('ि' * 100000)

    def test_allowed_set_has_no_controls_symbols_digits_or_markup(self):
        for cp in dn.ALLOWED:
            cat = unicodedata.category(chr(cp))
            self.assertFalse(cat.startswith(('C', 'S', 'N')) and cp not in (dn.ZWJ, dn.ZWNJ), hex(cp))
            self.assertNotIn(chr(cp), '<>&"/\\:;=(){}[]`$%#@!?*+|~^_\t\n\r')


class FontCoverage(unittest.TestCase):
    """Every accepted letter has a glyph in every face that can draw a name, in the PDF
    (Poppins 600, Inter 600, Poppins Devanagari 600) and on the page (all bundled weights)."""

    def cmap(self, *files):
        out = set()
        for f in files:
            out |= set(TTFont(str(FONTS / f)).getBestCmap())
        return out

    def test_latin_letters_in_every_latin_face(self):
        for fam, weights in (('inter', (400, 500, 600)), ('poppins', (500, 600, 700))):
            for w in weights:
                cmap = self.cmap(f'{fam}-latin-{w}-normal.woff2', f'{fam}-latin-ext-{w}-normal.woff2')
                missing = sorted(hex(c) for c in dn.LATIN | dn.SEPARATORS if c not in cmap)
                self.assertEqual(missing, [], f'{fam} {w}')

    def test_devanagari_in_every_poppins_devanagari_weight(self):
        for w in (500, 600, 700):
            cmap = self.cmap(f'poppins-devanagari-{w}-normal.woff2')
            missing = sorted(hex(c) for c in dn.DEVANAGARI | {dn.ZWJ, dn.ZWNJ, dn.SPACE} if c not in cmap)
            self.assertEqual(missing, [], w)

    def test_devanagari_faces_carry_shaping_tables(self):
        for w in (500, 600, 700):
            font = TTFont(str(FONTS / f'poppins-devanagari-{w}-normal.woff2'))
            self.assertIn('GSUB', font)
            self.assertIn('GPOS', font)
            scripts = {r.ScriptTag for r in font['GSUB'].table.ScriptList.ScriptRecord}
            self.assertTrue(scripts & {'dev2', 'deva'}, scripts)

    def test_devanagari_files_are_the_fontsource_5_3_0_originals(self):
        import hashlib
        want = {
            500: 'f018c9ad67dc6c2ca9743ba407d879a251e778bfb3f1cced9dd59a9214ea0350',
            600: '58dba357cb1e89bf36e83f19227293f35d5d7de91215d0fcf394e705634837b5',
            700: 'de10eb6f1f452594080f69e1e4925fc68f2d594b4837c70b6c8e6ac0e8384916',
        }
        for w, digest in want.items():
            data = (FONTS / f'poppins-devanagari-{w}-normal.woff2').read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest)


@unittest.skipUnless(shutil.which('node'), 'node unavailable')
class BrowserParity(unittest.TestCase):
    """The NAME rule in static/app.js gives the same answer as the server for every case."""

    def test_app_js_rule_matches_server_rule(self):
        source = APP_JS.read_text()
        start = source.index('  var NAME = (function () {')
        end = source.index('  }());', start) + len('  }());')
        cases = list(ACCEPTED) + REFUSED_422 + ['', ' ', 'A' * 80, 'A' * 81, 'क्ष' * 40, 'क्ष' * 40 + 'क',
                                               ' ' * 317 + 'Asha', 'कि' * 81]
        script = (source[start:end] + '\nconst cases = JSON.parse(process.argv[1]);\n'
                  'console.log(JSON.stringify(cases.map((c) => NAME.check(c))));')
        out = subprocess.run(['node', '-e', script, json.dumps(cases)], capture_output=True, text=True, check=True)
        browser = json.loads(out.stdout)
        for raw, got in zip(cases, browser):
            with self.subTest(raw=raw):
                try:
                    want = {'name': normalize(raw)}
                except DisplayNameError as exc:
                    want = {'error': exc.code}
                self.assertEqual(got, want)


if __name__ == '__main__':
    unittest.main()
