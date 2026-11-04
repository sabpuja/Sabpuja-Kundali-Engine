"""KUN-UX-NAME-001: the optional report name in the ten-page premium PDF.

Synthetic engine fixtures and synthetic names only. Checks that the anonymous report is
byte-identical to the renderer before this feature, that a name appears on the cover and
the page-4 Birth record and nowhere else, that every other page (including all D1/D9
values) is unchanged, that Devanagari is shaped and extracts as the typed Unicode, and that
the longest accepted names stay inside the A4 layout at 8 pt or more.
"""
import hashlib
import io
import json
import re
import sys
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from report.phase1 import premium_report as premium  # noqa: E402
from report.phase1.display_name import DisplayNameError, normalize  # noqa: E402

HERE = Path(__file__).resolve().parent
SCENARIO_DIR = HERE / 'fixtures/premium'
MANIFEST = json.loads((SCENARIO_DIR / 'manifest.json').read_text())
SCENARIOS = {c['id']: json.loads((SCENARIO_DIR / f'{c["id"]}.json').read_text()) for c in MANIFEST['cases']}

# SHA-256 of generate(fixture, synthetic, palette='baseline'), as [synthetic=False, synthetic=True].
# Owner-approved English baseline after Change A (KUN-I18N-003 spec): page 10 method.exc5 reads
# "Hindi text (available as a separate edition)". Before that change these were the c57747a / PR #58
# values. The anonymous report must not change.
BEFORE = {
    's01-first-supported-date': ['faabd39e74f29ef5f1ae8486ea15d201cfd6e762656260c59e4e34921b2c6c4c',
                                'e421cb81bb0920757cd1f1e8ecc4d5ca22adb21dffaccd586ff69686a0ff1109'],
    's02-last-supported-date': ['69c308f3b697167c31f5826e6d2fba0c1f7ecd6f3d47002fa148f124bdd99539',
                               '26ff12fba637f00e3cb9a79e5cd894cee967f180c0ba7b19f487abd70ae9bcce'],
    's03-crowded-d1-house': ['4727f547d8d61afec0549f3c112bb08fd061c30f403fb74f9b7c3a8ef3b47040',
                            '8e8791b4b17fc42e8b62b02481582bcc76fc600d6a397ddbed1c471e12988b14'],
    's04-crowded-d9-house': ['e0ebd8028dfe27aa86171dc7711a59387310ef6ec0afb5e246d41ef076f6caf4',
                            'c865af51320e12ce2926231bb8507207e7de57943a7a97b8c387d07c8e36f2f3'],
    's05-graha-near-boundary': ['fbdd58ec8c52172a9209075a548706670ac1c710b6ea72049017f87bbad30af5',
                               'c09eaf9b15b6b4e69c069e2d8ba65df6eb5dd4faf42d36d102023b20b714d30b'],
    's06-lagna-near-boundary': ['3e749daede35a3a95c8c1faecf0d4915b351e4b22d7e7ffb58dbab5031f3c977',
                               'be84c18f880d9ce08bfc99d6d79c4daeffdbab1e8e5b9c3c885d5632d0f729f3'],
    's07-noon': ['24bb5af8c366654cee93792325ab41fab35dd7368cfeb48454dfe422b6c678c1',
                'dde07887faa4275bc55a321f56d53c1d844a5dc5c4952279bafb067c7547908c'],
    's08-dawn': ['de63595e8ce5921b15e241fb00dc9727c44b4b214e0ce4412757d6b529475917',
                'ea789a52984979da63dec8619fe7daf444f9e2c2ccfdfef5b23fec24bee0fea4'],
    's09-evening': ['8a30b45790d4bf7fc2e5ca1258744c74c0051d17b1c6be128bcb1eea4fb5e90a',
                   'd543252562971ac442087321651aaf18be7ce14994b621a0ff078bf6fcaf6cd0'],
    's10-late-night': ['7890f3c08b9341b97bc8b57fdfa55ae933ca58a5ee185801b75dc35a9e34aacb',
                      'e20d9503bfeae5f2e80329f002646cc792757effe16b10072be09e7e7125c1c5'],
    's11-afternoon': ['793f18b0900c7b4a02086c67106b3321e4de76fa61b34621ffa5848be7838ae3',
                     'c12c378b84839530e0267aad846253b9488fe89d3bfdb65a1ee256909f978278'],
    's12-morning': ['c388d8db6b36079359f02348d557b023c41ddce4bf416b4844fa6a5ae68254ac',
                   'e6e212d5c34f36613ed8c06cbbca1623ccd3603d2d262317b245fc524d48b942'],
    's13-remaining-lagna': ['45f4a4fa775a2a63bab1eec2b86d0959b963e0afe8e2b4055d036475ca496876',
                           'eb712dbd3b7c403b4d020683991dd1697d0fd707129c2425152c67fa4c8bfea8'],
}

NAMES = {
    'latin': 'Asha Verma',
    'accents': 'Zoë-Anne O’Brien Ñúñez',
    'latin-ext': 'Ākash Śarmā Ștefan',
    'hindi': 'क्षत्रिय प्रियंका सिद्धार्थ',
    'hindi-2': 'श्री अर्जुन हृषीकेश',
    'mixed': 'Ravi रवि Kumār',
    'initials': 'R. K. D’Souza-Iyer Jr.',
}
# Longest accepted names: 80 visible characters of the widest accepted glyphs, unbroken
# words and Devanagari clusters, which must wrap without leaving the page.
LONGEST = {
    'W80': 'W' * 80,
    'Ŵ80': 'Ŵ' * 80,
    'au80': 'औ' * 80,
    'nga-ga40': 'ङ्ग' * 40,
    'ksha40': 'क्ष' * 40,
    'words': ' '.join(['Mmmmmmmmm'] * 8),
    'hindi-words': ' '.join(['श्रीमती'] * 16),
}
PRIMARY = 's11-afternoon'
FOOTER_TOP = premium.FOOTER_Y + 14
_CACHE = {}


def render(case, name, synthetic=False):
    key = (case, name, synthetic)
    if key not in _CACHE:
        data, audit = premium.render(SCENARIOS[case], synthetic=synthetic, palette='baseline', display_name=name)
        _CACHE[key] = data, audit, fitz.open(stream=data, filetype='pdf')
    return _CACHE[key]


def squash(text):
    return ''.join(text.split())


class AnonymousReportUnchanged(unittest.TestCase):
    def test_no_name_is_byte_identical_to_c57747a_for_every_scenario(self):
        for case, (customer, sample) in BEFORE.items():
            with self.subTest(case):
                self.assertEqual(hashlib.sha256(premium.generate(SCENARIOS[case], synthetic=False,
                                                                 palette='baseline')).hexdigest(), customer)
                self.assertEqual(hashlib.sha256(premium.generate(SCENARIOS[case], synthetic=True,
                                                                 palette='baseline')).hexdigest(), sample)
                self.assertEqual(premium.generate(SCENARIOS[case], palette='baseline', display_name=None),
                                 premium.generate(SCENARIOS[case], palette='baseline'))

    def test_no_name_after_a_named_render_is_still_identical(self):
        # Registering the name faces must not change later anonymous output in the same process.
        render(PRIMARY, NAMES['mixed'])
        self.assertEqual(hashlib.sha256(premium.generate(SCENARIOS[PRIMARY], palette='baseline')).hexdigest(),
                         BEFORE[PRIMARY][0])


class NamedReport(unittest.TestCase):
    def test_name_on_cover_and_birth_record_only(self):
        for label, name in NAMES.items():
            data, audit, pdf = render(PRIMARY, name)
            with self.subTest(label):
                self.assertEqual(len(pdf), 10)
                cover, birth = pdf[0].get_text(), pdf[3].get_text()
                self.assertIn('PREPARED FOR', cover)
                self.assertIn(name, cover)
                self.assertIn('Name on report', birth)
                self.assertIn(name, birth)
                for number in (2, 3, 5, 6, 7, 8, 9, 10):
                    self.assertNotIn(squash(name), squash(pdf[number - 1].get_text()), number)
                self.assertEqual({p for p, *_ in audit['name_boxes']}, {1, 4})

    def test_name_never_in_metadata(self):
        for label, name in NAMES.items():
            data, _, pdf = render(PRIMARY, name)
            with self.subTest(label):
                self.assertEqual(pdf.metadata['title'], 'Sabpuja Janma Kundali')
                for value in pdf.metadata.values():
                    for word in name.split():
                        self.assertNotIn(word, value or '')
                self.assertIsNone(pdf.get_xml_metadata() or None)
                for enc in (name.encode('utf-8'), name.encode('utf-16-be')):
                    self.assertNotIn(enc, data)  # content streams are compressed; nothing in clear

    def test_other_pages_and_every_d1_d9_value_unchanged(self):
        """Pages 2, 3 and 5-10 carry the same words at the same positions and the same drawings
        as the anonymous report, so every D1/D9 Rashi, house and longitude is unchanged."""
        _, _, plain = render(PRIMARY, None)
        for case in (PRIMARY, 's03-crowded-d1-house', 's04-crowded-d9-house', 's05-graha-near-boundary'):
            _, _, base = render(case, None)
            for label in ('hindi', 'W80'):
                _, _, named = render(case, NAMES.get(label) or LONGEST[label])
                for number in (2, 3, 5, 6, 7, 8, 9, 10):
                    with self.subTest(case=case, name=label, page=number):
                        self.assertEqual(named[number - 1].get_text('words'), base[number - 1].get_text('words'))
                        self.assertEqual(len(named[number - 1].get_drawings()), len(base[number - 1].get_drawings()))
                # Page 4 keeps every anonymous row value (the name row is added above them).
                base_words = [w[4] for w in base[3].get_text('words')]
                named_words = [w[4] for w in named[3].get_text('words')]
                for word in base_words:
                    self.assertIn(word, named_words)
                # The cover keeps its birth panel and chart caption.
                for word in ('BIRTHPLACE', 'DATE', 'TIME', 'Lagna', 'Nakshatra'):
                    self.assertIn(word, named[0].get_text())

    def test_every_scenario_renders_named(self):
        for case in SCENARIOS:
            with self.subTest(case):
                _, _, pdf = render(case, NAMES['hindi'])
                self.assertEqual(len(pdf), 10)
                self.assertIn(NAMES['hindi'], pdf[0].get_text())

    def test_a4_pages_fonts_embedded_and_minimum_size(self):
        for label, name in list(NAMES.items()) + list(LONGEST.items()):
            _, _, pdf = render(PRIMARY, name)
            with self.subTest(label):
                self.assertEqual(len(pdf), 10)
                for page in pdf:
                    self.assertAlmostEqual(page.rect.width, 595.2756, 2)
                    self.assertAlmostEqual(page.rect.height, 841.8898, 2)
                    for xref, ext, *_ in page.get_fonts(full=True):
                        self.assertEqual(ext, 'ttf')
                        self.assertTrue(pdf.extract_font(xref)[3])
                    for b in page.get_text('dict')['blocks']:
                        for line in b.get('lines', []):
                            for span in line['spans']:
                                if span['text'].strip():
                                    self.assertGreaterEqual(span['size'], 7.99, span['text'])

    def test_name_fonts_are_the_brand_families_only(self):
        _, _, pdf = render(PRIMARY, NAMES['mixed'])
        names = {re.sub(r'^[A-Z]{6}\+', '', f[3]) for p in pdf for f in p.get_fonts(full=True)}
        self.assertEqual(names, {'Inter-Regular', 'Inter-Medium', 'Inter-SemiBold', 'Poppins-SemiBold', 'Poppins-Bold',
                                 'Poppins-SemiBold-LatinExt', 'Inter-SemiBold-LatinExt',
                                 'Poppins-SemiBold-Devanagari'})

    def test_longest_names_wrap_inside_the_layout(self):
        for label, name in LONGEST.items():
            self.assertEqual(normalize(name), name, label)
            _, audit, pdf = render(PRIMARY, name)
            with self.subTest(label):
                self.assertEqual(squash(name), squash(_name_text(pdf[0], 'PREPARED FOR', 'D1 Lagna and D9')))
                self.assertEqual(squash(name), squash(_name_text(pdf[3], 'Name on report', 'Birthplace')))
                for page, x0, y0, x1, y1 in audit['name_boxes']:
                    self.assertGreaterEqual(x0, premium.M - 0.01, label)
                    self.assertLessEqual(x1, premium.W - premium.M + 0.01, label)
                    if page == 4:
                        self.assertLessEqual(x1, premium.M + premium.CW / 2 - 8 - 16 + 0.01, 'inside the card')
                for number in (1, 4):
                    page = pdf[number - 1]
                    lowest = max(b[3] for b in page.get_text('blocks')
                                 if not re.search(r'Page \d+ of|Sabpuja  ·|sabpuja\.com|Sample', b[4]))
                    self.assertLess(lowest, premium.H - FOOTER_TOP - 10, (label, number))
                # Cover: the emblem and caption stay above the birth panel.
                self.assertLess(_y_of(pdf[0], 'Nakshatra'), premium.H - 262 - 8)

    def test_unvalidated_name_is_refused_by_the_renderer(self):
        for bad in ('', ' Asha', 'Asha\n', '<b>x</b>', 'A' * 81, 'José'):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    premium.generate(SCENARIOS[PRIMARY], display_name=bad)

    def test_missing_glyph_fails_closed(self):
        _, _, _ = render(PRIMARY, NAMES['latin'])
        d = premium.Doc(None, premium.Palette('baseline'), premium._register_fonts(), False)
        with self.assertRaises(premium.MissingGlyphError):
            d.name_runs('Asha ṛ', 'Head')       # IAST dot below: not in Poppins, refused not dropped
        with self.assertRaises(premium.MissingGlyphError):
            d.name_runs('राम ॿ', 'Strong')


class Devanagari(unittest.TestCase):
    def test_extracted_text_is_exactly_the_typed_unicode(self):
        for label in ('hindi', 'hindi-2', 'mixed'):
            name = NAMES[label]
            _, _, pdf = render(PRIMARY, name)
            with self.subTest(label):
                for number in (1, 4):
                    text = pdf[number - 1].get_text()
                    self.assertIn(name, text)
                    self.assertFalse(re.search('[-\x00]', text), 'no private-use or NUL characters')
                    self.assertEqual(pdf[number - 1].search_for(name.split()[0]) != [], True)

    def test_extraction_in_other_readers(self):
        data, _, _ = render(PRIMARY, NAMES['hindi'])
        try:
            import pypdf
        except ImportError:
            self.skipTest('pypdf not installed (optional cross-check)')
        text = ''.join(pypdf.PdfReader(io.BytesIO(data)).pages[0].extract_text().split())
        self.assertIn(squash(NAMES['hindi']), text)

    def test_shaping_forms_conjuncts_and_reorders_vowel_signs(self):
        """HarfBuzz output differs from a character-by-character cmap lookup: conjunct ligatures
        and a pre-base i-matra. cmap presence alone would draw क्‌षत्‌रयि."""
        _, _, _ = render(PRIMARY, NAMES['hindi'])
        glyphs, advance, _ = premium.Doc._shape('क्षत्रिय', 20)
        names = [g[0] for g in glyphs]
        self.assertIn('dvK_SSA', names)                       # क्ष conjunct
        self.assertIn('dvT_RA', names)                        # त्र conjunct
        self.assertLess(names.index([n for n in names if n.startswith('dvmI')][0]), names.index('dvT_RA'))
        self.assertLess(len(names), len('क्षत्रिय'))
        font = premium._register_name_fonts()['deva'][1]
        naive = [font.getBestCmap()[ord(ch)] for ch in 'क्षत्रिय']
        self.assertNotEqual(names, naive)
        glyphs, _, _ = premium.Doc._shape('श्री', 20)
        self.assertEqual(len(glyphs), 2)                      # श्र + ी

    def test_drawn_shapes_match_an_independent_raqm_rendering(self):
        """The renderer's name drawing (Doc.name_text, as used on the cover and page 4) matches
        Pillow's libraqm (FriBiDi + HarfBuzz, FreeType) rendering of the same text in the same
        font, and does not match an unshaped rendering."""
        from PIL import Image, ImageDraw, ImageFont, features
        from reportlab.pdfgen import canvas
        if not features.check('raqm'):
            self.skipTest('Pillow without libraqm')
        font_path = premium.FONT_DIR / premium.DEVANAGARI_FONT
        for name in ('क्षत्रिय', 'प्रियंका', 'सिद्धार्थ', 'हृषीकेश', 'श्री अर्जुन'):
            with self.subTest(name):
                def pdf_raster(shaped):
                    out = io.BytesIO()
                    c = canvas.Canvas(out, pagesize=(600, 120), invariant=1)
                    d = premium.Doc(c, premium.Palette('baseline'), premium._register_fonts(), False)
                    d.page = 1
                    if shaped:
                        d.name_text(20, 40, name, 40, 'Head', 'ink')
                    else:   # the same font, one cmap glyph per character: what cmap presence alone gives
                        c.setFont('SP2N-Deva', 40)
                        c.drawString(20, 40, name)
                    c.save()
                    pix = fitz.open(stream=out.getvalue(), filetype='pdf')[0].get_pixmap(dpi=216, colorspace=fitz.csGRAY)
                    return Image.frombytes('L', (pix.width, pix.height), pix.samples)

                pdf_img = pdf_raster(True)

                def draw(engine):
                    font = ImageFont.truetype(str(font_path), 120, layout_engine=engine)  # 40 pt at 216 dpi
                    img = Image.new('L', (2000, 400), 255)
                    ImageDraw.Draw(img).text((50, 100), name, font=font, fill=0)
                    return img

                shaped = _ink_iou(pdf_img, draw(ImageFont.Layout.RAQM))
                unshaped = _ink_iou(pdf_raster(False), draw(ImageFont.Layout.RAQM))
                self.assertGreater(shaped, 0.85, shaped)
                self.assertLess(unshaped, shaped - 0.2, (shaped, unshaped))


def _name_text(page, after, before):
    text = page.get_text()
    start = text.index(after) + len(after)
    return text[start:text.index(before, start)]


def _y_of(page, word):
    return max(w[3] for w in page.get_text('words') if word in w[4])


def _ink_iou(a, b):
    """Intersection over union of the ink of two renderings, cropped to their ink and brought
    to the first one's size (at equal pixel size this is a scale change of a few per cent)."""
    def crop(img):
        bw = img.point(lambda v: 255 if v < 128 else 0)
        return bw.crop(bw.getbbox())
    ca = crop(a)
    size = ca.size
    def mask(img):
        return img.resize(size).point(lambda v: 1 if v > 127 else 0).tobytes()
    ma, mb = mask(ca), mask(crop(b))
    inter = sum(1 for p, q in zip(ma, mb) if p and q)
    union = sum(1 for p, q in zip(ma, mb) if p or q)
    return inter / union


if __name__ == '__main__':
    unittest.main()
