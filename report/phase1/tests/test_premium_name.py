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

# SHA-256 of generate(fixture, synthetic, palette='baseline') at c57747a (PR #56 head, before
# this feature), as [synthetic=False, synthetic=True]. The anonymous report must not change.
BEFORE = {
    's01-first-supported-date': ['2792c9280e4463a86e45ff0592723132efc5c47786db3a6fae7d56d7b72a6b6b',
                                 'dbdae3c0000a982157a1ee1c330d1fc9cd5d4af8cf1ef70338d84ad695d32082'],
    's02-last-supported-date': ['fa60786cff080e5b2a959e410f01a5a71ebb973e5070bc64c84dad578e1ca117',
                                '2d20d96a7399058152f41f1c35e54ed934c5ef514744a883d84d0eaf643959a2'],
    's03-crowded-d1-house': ['e8d4677cbf46883e1b473804e38ad8d41f2363662791ffa82fd6f73ef23335d0',
                             'a5caf86aab1d6ced720ee348448be684676e7f28400d8b1fcf99e0c846c05b57'],
    's04-crowded-d9-house': ['690078d6590944ffbe9109ed9ae0694d4466e18ad3cedb5c88ad6c5a1baa5b5f',
                             '0af0ade1580542007835a7926003d764bebd239a36b5335308d80106f6d90c40'],
    's05-graha-near-boundary': ['58b277d65c28122c65aaa55d582dd8db7f06aeb4cd4482d9a204d08588d9958d',
                                '422e1ec8132e766cc60b4897598f288a86ea617a3843f65c64ffd07f8ae7bce1'],
    's06-lagna-near-boundary': ['3b45bc64acf25b2d0a7b52d37a766e5273ef9c6a0e81450ad922969585e942a1',
                                'ecfe57b3a56439eb8f6d25060cd49f4c5a141d7ca8b5c6b71728d85bc689169f'],
    's07-noon': ['ad7a1166a9efa0103bb5bd0f17a33d9b3dfd82f43ca8a85dfef59dc077bef6e4',
                 '86695b9fa7c8b47f8cd6afa6dea16992ff9d85e4f6701f591a23688fe37f02d5'],
    's08-dawn': ['485c2b422b6966c1e45abdbfadee59d37e04e89bce4b990a899f59116edbf53f',
                 'db11cac4084f4cb84305aba36369303d09ac3afd35eef15d41b1e161aeae4963'],
    's09-evening': ['e3efa9674763c8deefd3ea5059804ba0c4adc54be6b2706dfe4e43b578d4eb0b',
                    '968db823e7121141aad6abdbc931667067f0fdb9e406a37421f5af0fea39879e'],
    's10-late-night': ['dc196d5c49faa1f297860687bec067b48a1bf586cc402d57d976050514c08884',
                       'c1b0a5c2e7f8212e4ec95c148780abe614ada88c22b3489c905c0785f53135dd'],
    's11-afternoon': ['fd29641cd07a46ed90a65ceb9fbaea937edc807b2ec20f901f6a75c703025c39',
                      '37b77f9a4013d5fb6ccfa379ac71c2bcd186f28428f1b010ff52ee63426010ea'],
    's12-morning': ['aff5b8f8b3e7203e2ec0dee1ebb9157034a4eb3aef616b29014f1857eb09d2b8',
                    'bc3c4d826ca5acf09107c3ff576edf971409e9c621cb3632294dc1fc06f85c7b'],
    's13-remaining-lagna': ['9ce7406a55a10fa63062e8b3d4ced78c2d9ea11981f9ace643d3e9349d5d681d',
                            'f6fa9600670c65740fd40ac28069cca3226dd3028ab34eb7111029c1cf2a0dee'],
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
