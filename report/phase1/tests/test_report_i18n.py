"""KUN-I18N-001: English / Hindi premium report. Synthetic engine fixtures and names only.

Checks that the English report is unchanged (omitted and explicit 'en' locale), that the Hindi
report renders all 13 scenarios as ten searchable A4 pages with the same engine values, that
every string drawn is extractable exactly as the catalog Unicode, that Devanagari is shaped
(against an independent libraqm rendering), that nothing is clipped, overlapping, under 8 pt or
outside the page, that only the approved palette and Poppins/Inter faces are used, and that
values the terminology register does not know fail closed instead of appearing in English.
"""
import copy
import hashlib
import io
import json
import re
import string
import sys
import unicodedata
import unittest
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from report.phase1 import premium_report as premium  # noqa: E402
from report.phase1 import report_locale as loc  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_premium_name as name_tests  # noqa: E402  (pinned PR #56/#58 English hashes, IoU helper)
import test_premium_report as base_tests  # noqa: E402  (overlap, margin and line-strike checks)

SCENARIOS = name_tests.SCENARIOS
BEFORE = name_tests.BEFORE
HINDI_NAME = 'क्षत्रिय प्रियंका सिद्धार्थ'
LATIN_NAME = 'Zoë-Anne O’Brien'
PRIMARY = 's11-afternoon'
_CACHE = {}
# The ten sections exactly as written in the PR #58 renderer.
PR58_PAGES = [
    ('cover', 'Cover', ''),
    ('overview', 'Overview', 'Key placements at a glance and the contents of this report'),
    ('guide', 'Reading guide', 'Terms, abbreviations and how longitudes are written'),
    ('birth', 'Birth details', 'Birth record, time conversion and calculation context'),
    ('d1', 'D1 Lagna chart', 'North Indian birth chart with whole-sign houses'),
    ('d9', 'D9 Navamsa chart', 'North Indian Navamsa chart from the engine D9 data'),
    ('positions', 'Planetary positions', 'Rashi, house and exact sidereal longitude of each graha'),
    ('navamsa', 'Navamsa placements', 'D9 Rashi and D9 house of each graha'),
    ('houses', 'House directory', 'All twelve houses with their D1 and D9 Rashis and grahas'),
    ('method', 'Methodology', 'Conventions, provenance, validation status and licences'),
]
# Latin words allowed in the Hindi report: proper names of software, data and licences,
# identifiers and codes (catalog conventions.latin_kept). Tokens with digits are values.
LATIN_ALLOWED = set(('Sabpuja Kundali Engine Swiss Ephemeris pyswisseph IANA tzdata GeoNames Natural Earth AGPL SIL Open '
                     'Font License Poppins Inter CC BY UTC SHA IAE SE SIDM LAHIRI SIDBIT UNVERIFIED GOLDEN CHARTS Asia '
                     'Kolkata github com sabpuja Apache tz km calculation metadata').split())


def hi(case, name=None, synthetic=True):
    key = (case, name, synthetic)
    if key not in _CACHE:
        data, audit = premium.render(SCENARIOS[case], synthetic=synthetic, palette='baseline', display_name=name, locale='hi')
        _CACHE[key] = data, audit, fitz.open(stream=data, filetype='pdf')
    return _CACHE[key]


def squash(text):
    return ' '.join(text.split())


class Catalog(unittest.TestCase):
    def test_catalogs_are_consistent(self):
        self.assertEqual(loc.check_catalogs(), [])
        for key, entry in loc.STRINGS.items():
            self.assertEqual(set(entry), {'en', 'hi'}, key)
            if entry['en']:
                self.assertTrue(entry['hi'], key)
        ui = loc.REGISTER['ui']
        for key, entry in ui.items():
            self.assertEqual(set(entry), {'en', 'hi'}, key)
            fields = lambda t: {f for _, f, _, _ in string.Formatter().parse(t) if f}
            self.assertEqual(fields(entry['en']), fields(entry['hi']), key)

    def test_every_string_is_nfc_and_drawable(self):
        cmaps = premium._register_fonts()
        deva = premium._deva_face(400)['cmap']
        def texts():
            for section in (loc.STRINGS, loc.REGISTER['ui'], loc.ENGINE_TEXT):
                for key, entry in section.items():
                    yield key, entry['hi']
            for key, entry in loc.TERMS['rashi'].items():
                yield key, entry['hi']
            for key, entry in loc.TERMS['graha'].items():
                yield key, entry['hi'] + entry['hi_abbr'] + entry['hi_long']
            for key, value in loc.TERMS['nakshatra'].items():
                yield key, value
            for key, entry in loc.TERMS['place'].items():
                yield key, ''.join(entry['hi'])
            yield 'months', ''.join(loc.TERMS['month']['hi'])
        for key, text in texts():
            self.assertEqual(unicodedata.normalize('NFC', text), text, key)
            for ch in text:
                cp = ord(ch)
                ok = cp in deva if 0x900 <= cp <= 0x97F else cp in cmaps['SP2-Body'] or cp in (0x200C, 0x200D)
                self.assertTrue(ok, (key, ch))

    def test_register_covers_every_engine_value(self):
        from sabpuja_kundali.rules import NAKSHATRAS, SIGNS
        self.assertEqual(sorted(loc.TERMS['rashi']), sorted(SIGNS))
        self.assertEqual(sorted(loc.TERMS['nakshatra']), sorted(NAKSHATRAS))
        self.assertEqual(sorted(loc.TERMS['graha']), sorted(premium.GRAHAS))
        self.assertEqual(loc.TERMS['month']['en'], premium.MONTHS)
        places = json.loads((ROOT / 'prototype/kundali_prototype/places.json').read_text())['places']
        self.assertEqual(sorted(loc.TERMS['place']), sorted(p['id'] for p in places))
        for p in places:
            self.assertEqual(loc.TERMS['place'][p['id']]['en'], [p['name'], p['region'], p['country']], p['id'])
        # Fixed engine sentences: exactly the engine's current text, so a change fails closed.
        from sabpuja_kundali import provenance
        source = Path(provenance.__file__).read_text()
        for key, entry in loc.ENGINE_TEXT.items():
            words = entry['en'].split()
            self.assertIn(' '.join(words[:4]), ' '.join(source.split()), key)

    def test_english_pages_are_the_pr58_sections(self):
        self.assertEqual(premium.PAGES, PR58_PAGES)
        self.assertEqual([k for k, _, _ in premium.pages('hi')], [k for k, _, _ in PR58_PAGES])

    def test_terms_are_used_consistently(self):
        """The same Hindi term in the interface and the report for the core vocabulary."""
        ui = loc.REGISTER['ui']
        for word in ('राशि', 'भाव', 'लग्न', 'नवांश', 'निरयन', 'भोगांश', 'चरण', 'नक्षत्र', 'ग्रह'):
            self.assertTrue(any(word in e['hi'] for e in ui.values()), word)
            self.assertTrue(any(word in e['hi'] for e in loc.STRINGS.values()), word)
        everything = ' '.join(e['hi'] for s in (ui, loc.STRINGS) for e in s.values())
        # Avoided forms (terminology register): tithi is a Panchanga term, not a calendar date;
        # pada is chaaran; the Sanskrit half-nasal spellings are not mixed in.
        for avoided in ('तिथि', 'पद ', 'कुण्डली', 'चन्द्र', 'पंचम भाव'):
            self.assertNotIn(avoided, everything, avoided)


class EnglishUnchanged(unittest.TestCase):
    def test_explicit_en_equals_omitted_and_pr58_for_every_scenario(self):
        for case, (plain, sample) in BEFORE.items():
            with self.subTest(case):
                data = premium.generate(SCENARIOS[case], synthetic=False, palette='baseline', locale='en')
                self.assertEqual(hashlib.sha256(data).hexdigest(), plain)
                data = premium.generate(SCENARIOS[case], synthetic=True, palette='baseline', locale='en')
                self.assertEqual(hashlib.sha256(data).hexdigest(), sample)

    def test_english_after_hindi_is_still_identical(self):
        hi(PRIMARY)
        data = premium.generate(SCENARIOS[PRIMARY], synthetic=False, palette='baseline')
        self.assertEqual(hashlib.sha256(data).hexdigest(), BEFORE[PRIMARY][0])
        named = premium.generate(SCENARIOS[PRIMARY], palette='baseline', display_name='Asha Verma')
        self.assertEqual(named, premium.generate(SCENARIOS[PRIMARY], palette='baseline', display_name='Asha Verma', locale='en'))

    def test_unsupported_locales_refused(self):
        for bad in ('HI', 'hi-IN', 'fr', '', None, 1, 'en '):
            with self.subTest(bad), self.assertRaises(ValueError):
                premium.generate(SCENARIOS[PRIMARY], locale=bad)


class HindiReport(unittest.TestCase):
    def test_every_scenario_ten_a4_pages_deterministic_and_bounded(self):
        for case in SCENARIOS:
            with self.subTest(case):
                data, audit, pdf = hi(case)
                self.assertEqual(len(pdf), 10)
                for page in pdf:
                    self.assertAlmostEqual(page.rect.width, premium.W, 3)
                    self.assertAlmostEqual(page.rect.height, premium.H, 3)
                self.assertLess(len(data), premium.MAX_PDF_BYTES)
                self.assertEqual(audit['locale'], 'hi')
        a = premium.generate(SCENARIOS[PRIMARY], synthetic=True, locale='hi')
        self.assertEqual(a, premium.generate(SCENARIOS[PRIMARY], synthetic=True, locale='hi'))

    def test_with_and_without_names(self):
        for name in (None, HINDI_NAME, LATIN_NAME, 'Ravi रवि Kumār'):
            with self.subTest(name):
                data, audit, pdf = hi(PRIMARY, name)
                self.assertEqual(len(pdf), 10)
                cover, birth = squash(pdf[0].get_text()), squash(pdf[3].get_text())
                if name is None:
                    self.assertNotIn(loc.STRINGS['cover.prepared_for']['hi'], cover)
                    self.assertNotIn(loc.STRINGS['birth.name']['hi'], birth)
                else:
                    self.assertIn(name, cover)
                    self.assertIn(name, birth)
                    self.assertIn(loc.STRINGS['birth.name']['hi'], birth)
                    for number in (2, 3, 5, 6, 7, 8, 9, 10):
                        self.assertNotIn(name, pdf[number - 1].get_text(), number)
                    self.assertNotIn(name.encode('utf-16-be'), data)
                    self.assertNotIn(name.encode(), data)
                    meta = ' '.join(str(v) for v in pdf.metadata.values())
                    self.assertNotIn(name.split()[0], meta)

    def test_longest_names_fit(self):
        for label in ('au80', 'ksha40', 'W80', 'hindi-words'):
            name = name_tests.LONGEST[label]
            with self.subTest(label):
                _, audit, pdf = hi(PRIMARY, name)
                for page, x0, y0, x1, y1 in audit['name_boxes']:
                    self.assertGreaterEqual(x0, premium.M - 0.5)
                    self.assertLessEqual(x1, premium.W - premium.M + 0.5)
                    self.assertGreater(y0, premium.FOOTER_Y + 14)
                base_tests.PremiumPDFTests()._assert_no_text_overlap(pdf, label)

    def test_every_drawn_string_extracts_as_the_catalog_unicode(self):
        """Copy, search and extraction return the exact Unicode drawn: each string the renderer
        drew on a page is found, whitespace-normalised, in that page's extracted text."""
        for case in ('s01-first-supported-date', 's03-crowded-d1-house', PRIMARY):
            _, audit, pdf = hi(case)
            texts = [squash(p.get_text()) for p in pdf]
            for page, text, _ in audit['texts']:
                with self.subTest(case=case, page=page, text=text):
                    self.assertIn(squash(text), texts[page - 1])
        # Every catalog sentence that a report always contains appears in full.
        _, _, pdf = hi(PRIMARY)
        whole = squash(' '.join(p.get_text() for p in pdf))
        always = [k for k, e in loc.STRINGS.items() if e['hi'] and '{' not in e['hi'] and not k.startswith('page.cover')
                  and k not in ('cover.prepared_for', 'birth.name', 'birth.not_verified', 'birth.not_supplied',
                                'birth.offset_repeated', 'birth.offset_supplied', 'meta.title', 'meta.subject')]
        missing = [k for k in always if squash(loc.STRINGS[k]['hi']) not in whole]
        self.assertEqual(missing, [])

    def test_extraction_in_other_readers(self):
        data, _, _ = hi(PRIMARY, HINDI_NAME)
        try:
            import pypdf
        except ImportError:
            self.skipTest('pypdf not installed (optional cross-check)')
        reader = pypdf.PdfReader(io.BytesIO(data))
        text = ''.join(reader.pages[9].extract_text().split())
        self.assertIn(''.join(loc.STRINGS['method.title']['hi'].split()), text)
        self.assertIn(''.join(HINDI_NAME.split()), ''.join(reader.pages[0].extract_text().split()))

    def test_no_english_only_fragments(self):
        for case in (PRIMARY, 's02-last-supported-date'):
            _, audit, _ = hi(case)
            stray = set()
            for _, text, _ in audit['texts']:
                for token in text.split():
                    if re.search('[0-9]', token):
                        continue
                    stray |= set(re.findall('[A-Za-z]{2,}', token)) - LATIN_ALLOWED
            self.assertEqual(stray, set(), case)

    def test_same_engine_values_as_english(self):
        """Every longitude, within-Rashi position, house number and D9 house is the same text in
        both languages, page by page, and every chart label is in the same house."""
        number = re.compile(r'\d+\.\d{8}°|\d+°\d{2}′\d{2}″|\d+°|UTC[+-]\d{2}:\d{2}|\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2}')
        for case in SCENARIOS:
            with self.subTest(case):
                en_data, en_audit = premium.render(SCENARIOS[case], synthetic=True, palette='baseline')
                en = fitz.open(stream=en_data, filetype='pdf')
                _, hi_audit, hpdf = hi(case)
                for p in range(10):
                    if p == 1:
                        continue  # the overview card subtitles put the same values in another word order
                    self.assertEqual(sorted(number.findall(en[p].get_text())), sorted(number.findall(hpdf[p].get_text())), p + 1)
                for mode in ('d1', 'd9'):
                    a, b = en_audit['charts'][mode], hi_audit['charts'][mode]
                    self.assertEqual(a['lagna'], b['lagna'])
                    self.assertEqual({h: len(v) for h, v in a['labels'].items()}, {h: len(v) for h, v in b['labels'].items()})
                    for h in a['labels']:
                        for (*_, x), (*_, y) in zip(a['labels'][h], b['labels'][h]):
                            ex = {**{premium.DISPLAY[g][1]: g for g in premium.GRAHAS}, 'Asc': 'lagna'}[x]
                            hx = {**{loc.TERMS['graha'][g]['hi_abbr']: g for g in premium.GRAHAS}, 'लग्न': 'lagna'}[y]
                            self.assertEqual(ex, hx, (mode, h))

    def test_tables_match_engine(self):
        _, _, pdf = hi(PRIMARY)
        chart = SCENARIOS[PRIMARY]['chart']
        text = squash(pdf[premium.PAGE_OF['positions'] - 1].get_text())
        for g in premium.GRAHAS:
            body = chart['planets'][g]
            self.assertIn(f'{body["longitude_deg"]:.8f}°', text)
            self.assertIn(loc.TERMS['graha'][g]['hi'], text)
            self.assertIn(loc.TERMS['rashi'][body['rashi']]['hi'], text)
        self.assertIn(loc.TERMS['nakshatra'][chart['moon_nakshatra']['name']], text)
        nav = squash(pdf[premium.PAGE_OF['navamsa'] - 1].get_text())
        for g in premium.GRAHAS:
            self.assertIn(loc.TERMS['rashi'][chart['planets'][g]['navamsa_rashi']]['hi'], nav)

    def test_layout_no_overlap_clipping_or_struck_text_and_min_size(self):
        checks = base_tests.PremiumPDFTests()
        for case in SCENARIOS:
            with self.subTest(case):
                _, audit, pdf = hi(case)
                checks._assert_no_text_overlap(pdf, case)
                checks._assert_inside_margins(pdf, case)
                for number, page in enumerate(pdf, 1):
                    for span in base_tests.spans(page):
                        self.assertGreaterEqual(round(span['size'], 2), premium.MIN_TEXT, (case, number, span['text']))
                    lines = []
                    for drawing in page.get_drawings():
                        if 's' not in drawing['type']:
                            continue   # filled paths: the Devanagari glyph outlines themselves
                        for item in drawing['items']:
                            if item[0] == 'l':
                                lines.append((item[1].x, item[1].y, item[2].x, item[2].y))
                            elif item[0] == 're' and item[1].height < 1.2 and item[1].width > 4:
                                r = item[1]
                                lines.append((r.x0, (r.y0 + r.y1) / 2, r.x1, (r.y0 + r.y1) / 2))
                    for drawing in page.get_drawings():   # thin filled rules
                        if drawing['type'] == 'f':
                            for item in drawing['items']:
                                if item[0] == 're' and item[1].height < 1.2 and item[1].width > 4:
                                    r = item[1]
                                    lines.append((r.x0, (r.y0 + r.y1) / 2, r.x1, (r.y0 + r.y1) / 2))
                    for span in base_tests.spans(page):
                        x0, y0, x1, y1 = span['bbox']
                        h = y1 - y0
                        body = (x0 + 0.5, y0 + h * 0.28, x1 - 0.5, y1 - h * 0.12)
                        for seg in lines:
                            self.assertFalse(base_tests.segment_hits_rect(seg, body), (case, number, span['text']))
                for _, _, size in audit['texts']:
                    self.assertGreaterEqual(size, premium.MIN_TEXT)

    def test_glyph_ink_stays_inside_the_page_and_footer(self):
        """Outlines (not only the invisible text) stay in the page body: rasterise and check that
        no ink of the page body crosses the footer rule or the side margins."""
        _, _, pdf = hi(PRIMARY, HINDI_NAME)
        for number, page in enumerate(pdf, 1):
            for clip in (fitz.Rect(0, 0, premium.M - 4, premium.H - 40), fitz.Rect(premium.W - premium.M + 4, 80, premium.W, premium.H - 40)):
                if number == 1:
                    continue  # the cover frame and its corner diamonds sit in the margins by design
                pix = page.get_pixmap(dpi=72, clip=clip, colorspace=fitz.csGRAY)
                dark = sum(1 for v in pix.samples if v < 120)
                self.assertEqual(dark, 0, (number, clip))

    def test_fonts_are_embedded_brand_faces_only(self):
        _, _, pdf = hi(PRIMARY, HINDI_NAME)
        names = set()
        for page in pdf:
            for xref, ext, ftype, name, *_ in page.get_fonts(full=True):
                self.assertEqual(ext, 'ttf', name)
                base = name.split('+')[-1]
                self.assertTrue(base.startswith(('Poppins', 'Inter')), name)
                names.add(base)
        self.assertTrue(any('Devanagari' in n for n in names), names)
        self.assertTrue(any(n.startswith('Inter') for n in names), names)

    def test_only_the_approved_palette(self):
        """No colour appears in the Hindi report that the approved English report does not use."""
        for case in (PRIMARY, 's04-crowded-d9-house'):
            en = fitz.open(stream=premium.generate(SCENARIOS[case], synthetic=True, palette='baseline'), filetype='pdf')
            _, _, hpdf = hi(case)
            def colours(pdf):
                out = set()
                for p in pdf:
                    for d in p.get_drawings():
                        for k in ('fill', 'color'):
                            if d.get(k):
                                out.add(tuple(round(v, 3) for v in d[k]))
                    for span in base_tests.spans(p):   # visible text colours (Hindi Devanagari is outlines)
                        if span.get('alpha', 255) == 0:
                            continue                   # the invisible text layer (render mode 3)
                        rgb = span['color']
                        out.add(tuple(round(v / 255, 3) for v in ((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255)))
                return out
            self.assertLessEqual(colours(hpdf), colours(en))
            self.assertEqual(premium.Palette('baseline').hex['primary'], '#D35400')

    def test_document_language_is_hindi(self):
        _, _, pdf = hi(PRIMARY)
        self.assertIn('hi', pdf.xref_get_key(pdf.pdf_catalog(), 'Lang')[1])
        self.assertEqual(pdf.metadata['title'], loc.STRINGS['meta.title']['hi'])


class Shaping(unittest.TestCase):
    def test_conjuncts_reph_and_vowel_reordering(self):
        for weight in (400, 500, 600, 700):
            glyphs, _ = premium._shape_units(weight, 'क्षत्रिय')
            names = [g[0] for g in glyphs]
            self.assertIn('dvK_SSA', names, weight)
            self.assertIn('dvT_RA', names, weight)
            self.assertLess(len(names), len('क्षत्रिय'))
        names = [g[0] for g in premium._shape_units(400, 'पूर्वाषाढ़ा')[0]]
        self.assertTrue(any('RA' in n or 'reph' in n.lower() for n in names), names)   # reph of र्
        names = [g[0] for g in premium._shape_units(400, 'कुंडली')[0]]
        self.assertFalse(any(n == 'uni25CC' for n in names))    # no dotted-circle fallback

    def test_hindi_text_matches_an_independent_raqm_rendering(self):
        """Report drawing (glyph forms) of catalog phrases at each weight matches Pillow's libraqm
        (HarfBuzz + FreeType) rendering of the same phrase and font; an unshaped rendering does not."""
        from PIL import Image, ImageDraw, ImageFont, features
        from reportlab.pdfgen import canvas
        if not features.check('raqm'):
            self.skipTest('Pillow without libraqm')
        phrases = [('Body', 400, loc.TERMS['nakshatra']['Purva Ashadha']), ('Medium', 500, 'स्थानीय नागरिक दिनांक'),
                   ('Strong', 600, 'वृश्चिक निरयन भोगांश'), ('HeadBold', 700, 'जन्म कुंडली'),
                   ('Body', 400, 'उच्च स्थिति और अवस्था'), ('Body', 400, 'क्षत्रिय सिद्धार्थ हृषीकेश')]
        for face, weight, text in phrases:
            with self.subTest(text):
                def pdf_raster(shaped):
                    out = io.BytesIO()
                    c = canvas.Canvas(out, pagesize=(700, 120), invariant=1)
                    d = premium.Doc(c, premium.Palette('baseline'), premium._register_fonts(), False, 'hi')
                    d.page = 1
                    if shaped:
                        d.text(20, 40, text, 40, face, 'ink')
                    else:
                        c.setFont(premium._deva_face(weight)['name'], 40)
                        c.drawString(20, 40, text)
                    c.save()
                    pix = fitz.open(stream=out.getvalue(), filetype='pdf')[0].get_pixmap(dpi=216, colorspace=fitz.csGRAY)
                    return Image.frombytes('L', (pix.width, pix.height), pix.samples)

                path = premium.FONT_DIR / f'poppins-devanagari-{weight}-normal.woff2'
                from fontTools.ttLib import TTFont
                tt = TTFont(str(path)); tt.flavor = None
                buf = io.BytesIO(); tt.save(buf); buf.seek(0)
                font = ImageFont.truetype(buf, 120, layout_engine=ImageFont.Layout.RAQM)
                ref = Image.new('L', (2400, 400), 255)
                ImageDraw.Draw(ref).text((50, 100), text, font=font, fill=0)
                shaped = name_tests._ink_iou(pdf_raster(True), ref)
                unshaped = name_tests._ink_iou(pdf_raster(False), ref)
                self.assertGreater(shaped, 0.85, shaped)
                self.assertLess(unshaped, shaped - 0.1, (shaped, unshaped))


class FailClosed(unittest.TestCase):
    def test_unknown_values_raise_in_hindi_but_not_in_english(self):
        mutations = {
            'unknown place id': lambda d: d['input']['place'].__setitem__('id', 'in-unknown'),
            'renamed place': lambda d: d['input']['place'].__setitem__('name', 'Delhi'),
            'changed ayanamsa definition': lambda d: d['chart']['calculation_metadata']['conventions']['ayanamsa'].__setitem__('definition', 'Lahiri, other text'),
            'changed claim boundary': lambda d: d['chart']['calculation_metadata']['validation'].__setitem__('claim_boundary', 'other'),
            'place source format': lambda d: d['input']['place'].__setitem__('source', 'Some other source'),
        }
        for label, mutate in mutations.items():
            data = copy.deepcopy(SCENARIOS[PRIMARY])
            mutate(data)
            with self.subTest(label):
                premium.generate(data)  # English shows engine values as given
                with self.assertRaises(loc.ReportLocaleError):
                    premium.generate(data, locale='hi')

    def test_missing_glyph_refused_not_substituted(self):
        doc = premium.Doc(None, premium.Palette('baseline'), premium._register_fonts(), False, 'hi')
        for text in ('த', '\u0951', '☃'):
            with self.subTest(text), self.assertRaises(premium.MissingGlyphError):
                doc.runs('राशि ' + text, 'Body')

    def test_locale_does_not_change_the_engine_response(self):
        data = copy.deepcopy(SCENARIOS[PRIMARY])
        before = json.dumps(data, sort_keys=True)
        premium.generate(data, locale='hi', display_name=HINDI_NAME)
        self.assertEqual(json.dumps(data, sort_keys=True), before)


if __name__ == '__main__':
    unittest.main()
