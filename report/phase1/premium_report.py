"""Sabpuja premium Kundali PDF, Phase 2A layout. Display of schema 0.3.0 engine output only.

The Phase 1 renderer (generate_report.py) stays unchanged as the reproducible baseline
and is still what the preview server calls. This module is a separate, versioned layout:

    generate(response, synthetic=False, palette='baseline', display_name=None) -> bytes

It computes no astronomy. Every value shown comes from the engine response; the only
derived display values are degrees within the engine's own Rashi (premium_layout.sign_position),
a calendar-formatted date, and label positions. Any disagreement raises before a page is drawn.

display_name (KUN-UX-NAME-001) is an optional, separately validated presentation value: it
is drawn on the cover ("Prepared for") and in the page-4 Birth record ("Name on report") and
nowhere else. It is never read from the engine response and never written to the PDF
metadata. Without a name the output is byte-identical to the renderer before this option.

locale (KUN-I18N-001) is a separate presentation parameter: 'en' (default) or 'hi'. Every
sentence comes from report_i18n.json and every term from the shared terminology register
(report_locale.py). With locale 'en' the output is byte-identical to the renderer before this
option. In Hindi, Devanagari runs are shaped with HarfBuzz and drawn as glyph outlines (one
form per glyph, reused), with the same words as invisible logical-order text on top, so copy,
search and extraction return the catalog Unicode. Latin runs (digits, codes, proper names)
keep the brand Latin faces. Values, longitudes, houses and statuses are the same engine values
in both languages.

generate_extended(response, panchanga, ...) (KUN-PAN-RPT-001) is the separate, opt-in extended
edition: the ten pages plus three birth-instant Panchanga pages before the methodology, drawn by
panchanga_report.py from a validated `sabpuja-panchanga/1` document. Contents, page numbers and
cross-references follow the page plan held by each Doc. Without a Panchanga document the output
is the standard ten-page edition, byte-identical to the renderer before this option.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
from pathlib import Path

from fontTools.ttLib import TTFont as FontToolsTTFont
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import STATE_DEFAULTS
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg

ROOT = Path(__file__).resolve().parent
try:
    from . import display_name as names
    from . import generate_report as phase1
    from . import premium_layout as layout
    from . import report_locale as loc
except ImportError:  # loaded by path or run as a script
    sys.path.insert(0, str(ROOT))
    import display_name as names
    import generate_report as phase1
    import premium_layout as layout
    import report_locale as loc

LAYOUT_ID = 'phase2a-premium'
THEMES = json.loads((ROOT / 'premium_theme.json').read_text())
REPO = ROOT.parents[1]
LOGO_PATH = REPO / 'prototype/kundali_prototype/static/brand/sabpuja-logo-horizontal-color.svg'
# Approved October 2026 horizontal logo, used unchanged (same file as Phase 1).
LOGO_SHA256 = '2f9acce59b19cac8e1abed203686cb791b82fa97678005189416ccf7e10f7b14'
FONT_DIR = REPO / 'prototype/kundali_prototype/static/fonts'
FONTS = {
    'Body': 'inter-latin-400-normal.woff2',
    'Medium': 'inter-latin-500-normal.woff2',
    'Strong': 'inter-latin-600-normal.woff2',
    'Head': 'poppins-latin-600-normal.woff2',
    'HeadBold': 'poppins-latin-700-normal.woff2',
}
# Report-name faces (registered only when a name is drawn): for each brand face, the same
# family and weight in its Latin, Latin Extended and Devanagari subsets. Inter has no
# Devanagari, so Devanagari is always Poppins 600, from the same @fontsource 5.3.0 package.
NAME_FONTS = {
    'Head': ('poppins-latin-600-normal.woff2', 'poppins-latin-ext-600-normal.woff2'),
    'Strong': ('inter-latin-600-normal.woff2', 'inter-latin-ext-600-normal.woff2'),
}
DEVANAGARI_FONT = 'poppins-devanagari-600-normal.woff2'
# Hindi report (KUN-I18N-001): the Poppins Devanagari weight drawn for each brand face. Inter
# has no Devanagari, so Inter roles take the Poppins Devanagari face of the same weight.
DEVANAGARI_WEIGHTS = {'Body': 400, 'Medium': 500, 'Strong': 600, 'Head': 600, 'HeadBold': 700}
METADATA_SCHEMA = 'sabpuja-calculation-metadata/3'
MAX_PDF_BYTES = 1024 * 1024  # same bound as the preview server
MIN_TEXT = 8.0              # smallest type anywhere in the report, for legible A4 print
W, H = A4
M = 48                      # side margin
CW = W - 2 * M
FOOTER_Y = 34
GRAHAS = list(phase1.NAMES)  # sun ... ketu_mean, engine keys in canonical order
# English chart names and abbreviations, from the shared terminology register.
DISPLAY = {key: (loc.TERMS['graha'][key]['en'], loc.TERMS['graha'][key]['en_abbr']) for key in GRAHAS}
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']
PAGE_KEYS = ['cover', 'overview', 'guide', 'birth', 'd1', 'd9', 'positions', 'navamsa', 'houses', 'method']


def pages(locale='en'):
    """(key, title, description) of the ten sections in one locale, from the catalog."""
    tr = loc.Translator(locale)
    return [(key, tr.t(f'page.{key}.title'), tr.t(f'page.{key}.desc')) for key in PAGE_KEYS]


PAGES = pages('en')
PAGE_OF = {key: i + 1 for i, (key, _, _) in enumerate(PAGES)}
# KUN-PAN-RPT-001: the ten-page report is the standard edition and stays the default, byte for
# byte. The extended edition adds the birth-instant Panchanga M1 pages before the methodology.
EDITION_STANDARD = 'standard-10'
EDITION_PANCHANGA = 'extended-panchanga-m1/1'
EXTENDED_LAYOUT_ID = LAYOUT_ID + '+' + EDITION_PANCHANGA


class Palette:
    def __init__(self, name: str):
        spec = THEMES['palettes'].get(name)
        if spec is None:
            raise ValueError('Unknown palette')
        if 'roles' in spec:
            roles = dict(spec['roles'])
        else:
            base = phase1.THEME['colors']
            roles = {role: base[token] for role, token in spec['brand_tokens'].items()}
            roles.setdefault('tint_soft', base['cream'])
        self.name = name
        self.hex = roles
        self.col = {k: HexColor(v) for k, v in roles.items()}

    def __getitem__(self, role):
        return self.col[role]


def _register_fonts():
    """Embed the approved Poppins and Inter files; fail closed, never substitute."""
    cmaps = {}
    for name, file in FONTS.items():
        font_name = 'SP2-' + name
        path = FONT_DIR / file
        if not path.is_file():
            raise RuntimeError('Required approved brand font missing: ' + file)
        font = FontToolsTTFont(str(path))
        cmaps[font_name] = frozenset(font.getBestCmap())
        if font_name not in pdfmetrics.getRegisteredFontNames():
            font.flavor = None
            # Keep the approved file's head.modified: fontTools would stamp the current time,
            # and the embedded subsets (so the PDF bytes) would then change on every start.
            font.recalcTimestamp = False
            out = io.BytesIO()
            font.save(out)
            out.seek(0)
            pdfmetrics.registerFont(TTFont(font_name, out))
    return cmaps


def _font_bytes(file, postscript_suffix):
    """A name-run face as TrueType bytes. The subsets share PostScript names (Poppins-SemiBold
    for latin, latin-ext and devanagari), and ReportLab treats fonts with one PostScript name
    as one face, so each gets a distinct suffix; the glyphs and metrics are unchanged."""
    path = FONT_DIR / file
    if not path.is_file():
        raise RuntimeError('Required approved brand font missing: ' + file)
    font = FontToolsTTFont(str(path))
    font.flavor = None
    font.recalcTimestamp = False
    for record in font['name'].names:
        if record.nameID == 6:
            record.string = record.toUnicode() + '-' + postscript_suffix
    out = io.BytesIO()
    font.save(out)
    return font, out.getvalue()


_NAME_FONT_CACHE = {}


def _register_name_fonts():
    """Latin Extended and Devanagari faces for the report name; fail closed, never substitute.

    Returns {face: [(font name, cmap), ...]} in fallback order, and the Devanagari shaper.
    """
    if not _NAME_FONT_CACHE:
        import uharfbuzz
        chains = {}
        for face, (_, ext_file) in NAME_FONTS.items():
            ext_name = 'SP2N-' + face + 'Ext'
            font, data = _font_bytes(ext_file, 'LatinExt')
            if ext_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(ext_name, io.BytesIO(data)))
            chains[face] = ext_name, frozenset(font.getBestCmap())
        font, data = _font_bytes(DEVANAGARI_FONT, 'Devanagari')
        if 'SP2N-Deva' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('SP2N-Deva', io.BytesIO(data)))
        hb_font = uharfbuzz.Font(uharfbuzz.Face(uharfbuzz.Blob(data)))
        _NAME_FONT_CACHE.update(ext=chains, deva=(frozenset(font.getBestCmap()), font, hb_font))
    return _NAME_FONT_CACHE


_DEVA_FACES = {}
_SHAPED = {}


def _deva_face(weight):
    """A Poppins Devanagari weight for the Hindi report: ReportLab font name (for the invisible
    text layer), cmap, fontTools font, glyph set and HarfBuzz font. 600 is the face already
    registered for report names. Fail closed: a missing file raises, nothing is substituted."""
    if weight not in _DEVA_FACES:
        if weight == 600:
            cmap, font, hb_font = _register_name_fonts()['deva']
            name = 'SP2N-Deva'
        else:
            import uharfbuzz
            font, data = _font_bytes(f'poppins-devanagari-{weight}-normal.woff2', 'Devanagari')
            name = f'SP2H-Deva{weight}'
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, io.BytesIO(data)))
            cmap = frozenset(font.getBestCmap())
            hb_font = uharfbuzz.Font(uharfbuzz.Face(uharfbuzz.Blob(data)))
        head = font['head']
        _DEVA_FACES[weight] = {'name': name, 'cmap': cmap, 'font': font, 'hb': hb_font,
                               'glyphs': font.getGlyphSet(), 'upem': head.unitsPerEm,
                               'bbox': (head.xMin, head.yMin, head.xMax, head.yMax)}
    return _DEVA_FACES[weight]


def _shape_units(weight, run):
    """HarfBuzz shaping of one Devanagari run in font units: ((glyph, x, y), ...), advance."""
    key = (weight, run)
    if key not in _SHAPED:
        import uharfbuzz
        face = _deva_face(weight)
        buf = uharfbuzz.Buffer()
        buf.add_str(run)
        buf.guess_segment_properties()
        uharfbuzz.shape(face['hb'], buf, {})
        glyphs, x = [], 0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            glyphs.append((face['font'].getGlyphName(info.codepoint), x + pos.x_offset, pos.y_offset))
            x += pos.x_advance
        _SHAPED[key] = (tuple(glyphs), x)
    return _SHAPED[key]


def _logo_drawing():
    data = LOGO_PATH.read_bytes() if LOGO_PATH.is_file() else None
    if data is None:
        raise RuntimeError('Approved logo missing from source checkout')
    if hashlib.sha256(data).hexdigest() != LOGO_SHA256:
        raise RuntimeError('Logo file differs from the approved logo')
    drawing = svg2rlg(str(LOGO_PATH))
    if drawing is None or not drawing.width:
        raise RuntimeError('Approved logo SVG cannot be rendered')
    return drawing


class MissingGlyphError(RuntimeError):
    pass


class _CanvasPathPen:
    """fontTools pen that appends a glyph outline to a ReportLab path at (x, y), scaled."""

    def __init__(self, glyph_set, path, x, y, scale):
        from fontTools.pens.basePen import BasePen

        outer = self

        class Pen(BasePen):
            def _moveTo(self, pt):
                outer.path.moveTo(*outer.map(pt))

            def _lineTo(self, pt):
                outer.path.lineTo(*outer.map(pt))

            def _curveToOne(self, p1, p2, p3):
                outer.path.curveTo(*outer.map(p1), *outer.map(p2), *outer.map(p3))

            def _closePath(self):
                outer.path.close()

        self.path, self.x, self.y, self.scale = path, x, y, scale
        self.pen = Pen(glyph_set)

    def map(self, pt):
        return self.x + pt[0] * self.scale, self.y + pt[1] * self.scale

    def __getattr__(self, name):
        return getattr(self.pen, name)


# ---------------------------------------------------------------------------
# Validation: Phase 1 rules plus the fields this layout displays.

def validate(response):
    phase1.validate_engine_response(response)
    chart, info = response['chart'], response['input']
    meta = chart.get('calculation_metadata')
    if not isinstance(meta, dict) or meta.get('metadata_schema') != METADATA_SCHEMA:
        raise ValueError('Calculation metadata /3 required for the provenance page')
    if not isinstance(meta.get('validation'), dict) or meta['validation'].get('status') != chart['validation_status']:
        raise ValueError('Validation status disagreement')
    for key in ('swiss_ephemeris', 'ephemeris_data', 'timezone_data', 'conventions'):
        if not isinstance(meta.get(key), dict):
            raise ValueError('Calculation provenance incomplete')
    place = info['place']
    for key in ('name', 'region', 'country'):
        value = place.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > 120:
            raise ValueError('Birthplace text missing or too long')
    for key in ('latitude', 'longitude'):
        value = chart['birth'].get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError('Birth coordinates missing')
    if place.get('timezone') != chart['birth'].get('timezone'):
        raise ValueError('Timezone disagreement between input and chart')
    _date_text(info['local_date'])
    if not isinstance(info.get('utc_offset'), str) or not isinstance(chart['birth'].get('utc'), str):
        raise ValueError('UTC offset and instant required')
    moon = chart['moon_nakshatra']
    if len(moon['name']) > 40:
        raise ValueError('Moon Nakshatra name too long')
    lagna = chart['lagna']
    positions = {'lagna': layout.sign_position(lagna.get('longitude_deg'), lagna['rashi'])}
    for name in GRAHAS:
        body = chart['planets'][name]
        positions[name] = layout.sign_position(body['longitude_deg'], body['rashi'])
    return positions


def _date_text(value):
    try:
        year, month, day = (int(p) for p in value.split('-'))
        if not (1 <= month <= 12 and 1 <= day <= 31 and len(value) == 10):
            raise ValueError
    except (AttributeError, ValueError):
        raise ValueError('Local date must be YYYY-MM-DD') from None
    return f'{day} {MONTHS[month - 1]} {year}'


# ---------------------------------------------------------------------------
# Drawing primitives with a glyph guard: every string is checked against the font's cmap.

class Doc:
    def __init__(self, c, pal, cmaps, synthetic, locale='en'):
        self.c, self.pal, self.cmaps, self.synthetic = c, pal, cmaps, synthetic
        self.page = 0
        self.chart_boxes = {}
        self.name_boxes = []
        self.name_drawn = []
        self.tr = loc.Translator(locale)
        self.locale = self.tr.locale
        self.hindi = self.tr.hindi
        self.glyph_forms = set()
        self.deva_runs = []
        self.drawn = []      # Hindi only: (page, text, size) of every string drawn, for the tests
        # Page plan (KUN-PAN-RPT-001). The standard ten-page edition uses the module PAGES and
        # PAGE_OF unchanged; the extended edition replaces them in render().
        self.edition = EDITION_STANDARD
        self.extension = None
        self.contents = pages(self.locale)
        self.page_of = dict(PAGE_OF)
        self.total = len(PAGES)

    def t(self, key, **values):
        return self.tr.t(key, **values)

    def date_text(self, value):
        """The local date as '5 September 2038' in the report language (digits stay Latin)."""
        _date_text(value)
        year, month, day = (int(p) for p in value.split('-'))
        return self.t('date.format', day=day, month=self.tr.month(month - 1), year=year)

    def _font(self, face, size, color):
        name = 'SP2-' + face
        self.c.setFont(name, size)
        self.c.setFillColor(self.pal[color])
        return name

    def check(self, text, face):
        if self.hindi:
            self.runs(str(text), face)
            return
        cmap = self.cmaps['SP2-' + face]
        missing = {ch for ch in str(text) if ord(ch) not in cmap}
        if missing:
            raise MissingGlyphError(f'{face} has no glyph for {sorted(missing)!r}')

    def width(self, text, face, size):
        if self.hindi:
            return self._mixed_width(str(text), face, size)
        return pdfmetrics.stringWidth(str(text), 'SP2-' + face, size)

    def split(self, text, face, size, width):
        """Lines of at most `width` points, broken at spaces."""
        if not self.hindi:
            return simpleSplit(str(text), 'SP2-' + face, size, width)
        lines, line = [], ''
        for word in str(text).split(' '):
            trial = f'{line} {word}' if line else word
            if not line or self.width(trial, face, size) <= width:
                line = trial
            else:
                lines.append(line)
                line = word
            if self.width(line, face, size) > width:
                raise layout.LayoutError('A word is wider than its line')
        lines.append(line)
        return lines

    # -- Hindi text (KUN-I18N-001) -------------------------------------------------------
    # A string is split into runs of one face: the brand face's Latin subset (digits, codes,
    # proper names, punctuation), its Latin Extended subset for report names, or the Poppins
    # Devanagari weight of the role. Devanagari runs are shaped with HarfBuzz, drawn as glyph
    # outlines, and overlaid with the same text as invisible logical-order text.

    def runs(self, text, face):
        base = ('SP2-' + face, self.cmaps['SP2-' + face])
        ext = _register_name_fonts()['ext'].get(face) if face in NAME_FONTS else None
        weight = DEVANAGARI_WEIGHTS[face]
        deva = _deva_face(weight)
        out = []
        for ch in text:
            cp = ord(ch)
            if names.is_devanagari(cp) or cp in (names.ZWJ, names.ZWNJ):
                if cp not in deva['cmap']:
                    raise MissingGlyphError(f'Devanagari {weight} has no glyph for {ch!r}')
                kind = ('deva', weight)
            elif cp == names.SPACE and out:
                kind = out[-1][0]
            elif cp in base[1]:
                kind = base[0]
            elif ext is not None and cp in ext[1]:
                kind = ext[0]
            else:
                raise MissingGlyphError(f'{face} has no glyph for {ch!r}')
            if out and out[-1][0] == kind:
                out[-1][1] += ch
            else:
                out.append([kind, ch])
        return [(kind, run) for kind, run in out]

    def _mixed_width(self, text, face, size):
        total = 0.0
        for kind, run in self.runs(text, face):
            if isinstance(kind, tuple):
                total += _shape_units(kind[1], run)[1] * size / _deva_face(kind[1])['upem']
            else:
                total += pdfmetrics.stringWidth(run, kind, size)
        return total

    def _glyph_form(self, weight, glyph):
        name = f'g{weight}_' + ''.join(ch if ch.isalnum() else '_' for ch in glyph)
        if name not in self.glyph_forms:
            face = _deva_face(weight)
            c = self.c
            x0, y0, x1, y1 = face['bbox']
            c.beginForm(name, x0, y0, x1, y1)
            path = c.beginPath()
            face['glyphs'][glyph].draw(_CanvasPathPen(face['glyphs'], path, 0, 0, 1))
            c.drawPath(path, stroke=0, fill=1, fillMode=0)
            c.endForm()
            self.glyph_forms.add(name)
        return name

    def _mixed_text(self, x, y, text, size, face, color, align):
        width = self._mixed_width(text, face, size)
        if align == 'right':
            x -= width
        elif align == 'center':
            x -= width / 2
        c = self.c
        for kind, run in self.runs(text, face):
            if not isinstance(kind, tuple):
                c.setFont(kind, size)
                c.setFillColor(self.pal[color])
                c.drawString(x, y, run)
                x += pdfmetrics.stringWidth(run, kind, size)
                continue
            weight = kind[1]
            deva = _deva_face(weight)
            glyphs, advance = _shape_units(weight, run)
            scale = size / deva['upem']
            glyf = deva['font']['glyf']
            forms = [(self._glyph_form(weight, g), gx, gy) for g, gx, gy in glyphs
                     if glyf[g].numberOfContours != 0]
            c.setFillColor(self.pal[color])
            # One scaled coordinate system per run; each glyph form is placed by a relative move.
            c.saveState()
            c.transform(scale, 0, 0, scale, x, y)
            px = py = 0
            for form, gx, gy in forms:
                c.translate(gx - px, gy - py)
                px, py = gx, gy
                c.doForm(form)
            c.restoreState()
            # Invisible logical-order text (render mode 3) over the outlines, spaced to the
            # shaped width, for copy, search, screen readers and extraction.
            plain = pdfmetrics.stringWidth(run, deva['name'], size)
            shaped = advance * scale
            t = c.beginText(x, y)
            t.setFont(deva['name'], size)
            t.setTextRenderMode(3)
            # One spacing for the run, the largest that keeps every character box (each one is
            # its unshaped advance wide) inside the shaped width, so the text layer never
            # reaches into the next run however the shaping contracts the conjuncts.
            spacing = 0.0
            if len(run) > 1:
                spacing = (shaped - plain) / (len(run) - 1)
                end = 0.0
                for i, ch in enumerate(run):
                    end += pdfmetrics.stringWidth(ch, deva['name'], size)
                    if i:
                        spacing = min(spacing, (shaped - end) / i)
            t.setFillColor(self.pal[color])
            if abs(spacing) > 1e-6:
                t.setCharSpace(spacing)
            t.textOut(run)
            t.setTextRenderMode(0)
            if abs(spacing) > 1e-6:
                t.setCharSpace(0)
            c.drawText(t)
            self.deva_runs.append((self.page, run))
            x += shaped
        return width

    def text(self, x, y, text, size=10, face='Body', color='ink', align='left', tracking=0):
        text = str(text)
        if self.hindi:
            # Letter-spacing is not applied in Hindi: tracking breaks the Devanagari headline.
            self._mixed_text(x, y, text, size, face, color, align)
            self.drawn.append((self.page, text, size))
            return
        self.check(text, face)
        name = self._font(face, size, color)
        if tracking:
            width = pdfmetrics.stringWidth(text, name, size) + tracking * (len(text) - 1)
            if align == 'right':
                x -= width
            elif align == 'center':
                x -= width / 2
            t = self.c.beginText(x, y)
            t.setFont(name, size)
            t.setCharSpace(tracking)
            t.textOut(text)
            t.setCharSpace(0)
            self.c.drawText(t)
            return
        if align == 'right':
            self.c.drawRightString(x, y, text)
        elif align == 'center':
            self.c.drawCentredString(x, y, text)
        else:
            self.c.drawString(x, y, text)

    def kicker(self, x, y, text, color='primary_text', align='left', size=MIN_TEXT):
        self.text(x, y, text.upper(), size, 'Strong', color, align, tracking=0.6)

    def wrap(self, x, y, text, width, size=9.5, leading=None, face='Body', color='ink', max_lines=None):
        leading = leading or size * 1.5
        lines = self.split(text, face, size, width)
        if max_lines is not None and len(lines) > max_lines:
            raise layout.LayoutError('Text exceeds its box')
        for line in lines:
            self.text(x, y, line, size, face, color)
            y -= leading
        return y

    def fit(self, text, face, size, width, minimum):
        while size >= minimum:
            if self.width(text, face, size) <= width:
                return size
            size -= 0.25
        return None

    def fitted(self, x, y, text, width, size, face='Body', color='ink', minimum=None, leading=None, max_lines=2):
        """One line at the largest size down to `minimum`, else wrapped at `minimum`."""
        minimum = minimum or size * 0.8
        fit = self.fit(text, face, size, width, minimum)
        if fit is not None:
            self.text(x, y, text, fit, face, color)
            return y - (leading or fit * 1.45)
        return self.wrap(x, y, text, width, minimum, leading or minimum * 1.35, face, color, max_lines)

    def rect(self, x, y, w, h, fill=None, stroke=None, width=0.6, radius=0):
        c = self.c
        if fill:
            c.setFillColor(self.pal[fill])
        if stroke:
            c.setStrokeColor(self.pal[stroke])
            c.setLineWidth(width)
        if radius:
            c.roundRect(x, y, w, h, radius, stroke=1 if stroke else 0, fill=1 if fill else 0)
        else:
            c.rect(x, y, w, h, stroke=1 if stroke else 0, fill=1 if fill else 0)

    def line(self, x1, y1, x2, y2, color='rule', width=0.6):
        self.c.setStrokeColor(self.pal[color])
        self.c.setLineWidth(width)
        self.c.line(x1, y1, x2, y2)

    def diamond(self, x, y, r, color='accent', fill=True):
        p = self.c.beginPath()
        p.moveTo(x, y + r); p.lineTo(x + r, y); p.lineTo(x, y - r); p.lineTo(x - r, y); p.close()
        self.c.setFillColor(self.pal[color]); self.c.setStrokeColor(self.pal[color]); self.c.setLineWidth(0.6)
        self.c.drawPath(p, fill=1 if fill else 0, stroke=0 if fill else 1)

    def logo(self, x, y, width):
        self.c.saveState()
        self.c.translate(x, y)
        s = width / self.logo_width
        self.c.scale(s, s)
        self.c.doForm('sabpuja_logo')
        self.c.restoreState()

    # -- Report name (KUN-UX-NAME-001) ---------------------------------------------------
    # A name is split into runs of one font each: the brand face's Latin subset, its Latin
    # Extended subset, or Poppins Devanagari. Devanagari is shaped with HarfBuzz (conjuncts,
    # reph, vowel-sign reordering), drawn as glyph outlines, and overlaid with the same
    # words as invisible text in logical order, so copy, search and text extraction return
    # exactly the Unicode that was typed. A character no face can draw raises; it is never
    # dropped, replaced or transliterated.

    def name_runs(self, text, face):
        fonts = _register_name_fonts()
        base = ('SP2-' + face, self.cmaps['SP2-' + face])
        ext = fonts['ext'][face]
        deva_cmap = fonts['deva'][0]
        runs = []
        for ch in text:
            cp = ord(ch)
            if names.is_devanagari(cp) or cp in (names.ZWJ, names.ZWNJ):
                kind = 'deva'
                if cp not in deva_cmap:
                    raise MissingGlyphError('report name has a character the Devanagari face cannot draw')
            elif cp == names.SPACE and runs:
                kind = runs[-1][0]
            elif cp in base[1]:
                kind = base[0]
            elif cp in ext[1]:
                kind = ext[0]
            else:
                raise MissingGlyphError('report name has a character the brand faces cannot draw')
            if runs and runs[-1][0] == kind:
                runs[-1][1] += ch
            else:
                runs.append([kind, ch])
        return [(kind, run) for kind, run in runs]

    @staticmethod
    def _shape(run, size):
        import uharfbuzz
        _, font, hb_font = _register_name_fonts()['deva']
        buf = uharfbuzz.Buffer()
        buf.add_str(run)
        buf.guess_segment_properties()
        uharfbuzz.shape(hb_font, buf, {})
        scale = size / font['head'].unitsPerEm
        glyphs, x = [], 0.0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            glyphs.append((font.getGlyphName(info.codepoint), x + pos.x_offset * scale, pos.y_offset * scale))
            x += pos.x_advance * scale
        return glyphs, x, scale

    def name_width(self, text, face, size):
        if self.hindi:
            return self.width(text, face, size)
        total = 0.0
        for kind, run in self.name_runs(text, face):
            total += self._shape(run, size)[1] if kind == 'deva' else pdfmetrics.stringWidth(run, kind, size)
        return total

    def name_text(self, x, y, text, size, face='Head', color='ink', align='left'):
        if self.hindi:
            width = self.width(text, face, size)
            left = x - (width / 2 if align == 'center' else width if align == 'right' else 0)
            before = len(self.deva_runs)
            self._mixed_text(x, y, text, size, face, color, align)
            self.name_drawn.extend(run for _, run in self.deva_runs[before:])
            self.name_boxes.append((self.page, left, y - size * 0.45, left + width, y + size))
            return
        width = self.name_width(text, face, size)
        if align == 'center':
            x -= width / 2
        elif align == 'right':
            x -= width
        c = self.c
        for kind, run in self.name_runs(text, face):
            if kind != 'deva':
                c.setFont(kind, size)
                c.setFillColor(self.pal[color])
                c.drawString(x, y, run)
                x += pdfmetrics.stringWidth(run, kind, size)
                continue
            glyphs, advance, scale = self._shape(run, size)
            glyph_set = _register_name_fonts()['deva'][1].getGlyphSet()
            c.setFillColor(self.pal[color])
            path = c.beginPath()
            for name, gx, gy in glyphs:
                glyph_set[name].draw(_CanvasPathPen(glyph_set, path, x + gx, y + gy, scale))
            c.drawPath(path, stroke=0, fill=1, fillMode=0)
            # Invisible logical-order text over the outlines (render mode 3), horizontally
            # scaled to the shaped width, for copy, search, screen readers and extraction.
            plain = pdfmetrics.stringWidth(run, 'SP2N-Deva', size)
            t = c.beginText(x, y)
            t.setFont('SP2N-Deva', size)
            t.setTextRenderMode(3)
            # Character spacing spreads the difference, so the text keeps its true size.
            spacing = (advance - plain) / len(run)
            if abs(spacing) > 1e-6:
                t.setCharSpace(spacing)
            t.textOut(run)
            # Render mode and character spacing are graphics-state text parameters that
            # outlive BT/ET; restore both so no later text on the page is affected.
            t.setTextRenderMode(0)
            if abs(spacing) > 1e-6:
                t.setCharSpace(0)
            c.drawText(t)
            self.name_drawn.append(run)
            x += advance
        self.name_boxes.append((self.page, x - width, y - size * 0.45, x, y + size))

    def name_lines(self, text, face, width, size, minimum, max_lines):
        """(lines, size): one line at the largest size from `size` down to `minimum`, else wrapped
        at `minimum` on spaces (a word longer than a line breaks between clusters, never inside
        a letter with its signs or a Devanagari conjunct). LayoutError beyond max_lines."""
        fit = size
        while fit >= minimum:
            if self.name_width(text, face, fit) <= width:
                return [text], fit
            fit -= 0.25
        lines, line = [], ''
        for word in text.split(' '):
            for piece in self._break_word(word, face, minimum, width):
                trial = f'{line} {piece}' if line else piece
                if self.name_width(trial, face, minimum) <= width:
                    line = trial
                else:
                    lines.append(line)
                    line = piece
        lines.append(line)
        if len(lines) > max_lines:
            raise layout.LayoutError('Report name does not fit')
        return lines, minimum

    def _break_word(self, word, face, size, width):
        if self.name_width(word, face, size) <= width:
            return [word]
        # Clusters: a letter with its signs, and consonants joined by a virama or joiner stay together.
        clusters = []
        for i, ch in enumerate(word):
            cp, prev = ord(ch), (ord(word[i - 1]) if i else None)
            joined = (names.is_mark(cp) or cp in (names.ZWJ, names.ZWNJ)
                      or prev in (names.VIRAMA, names.ZWJ, names.ZWNJ))
            if clusters and joined:
                clusters[-1] += ch
            else:
                clusters.append(ch)
        pieces, piece = [], ''
        for cluster in clusters:
            if piece and self.name_width(piece + cluster, face, size) > width:
                pieces.append(piece)
                piece = ''
            piece += cluster
        pieces.append(piece)
        return pieces


# ---------------------------------------------------------------------------
# Page furniture.

def _background(d):
    d.rect(0, 0, W, H, fill='page')
    d.rect(0, H - 5, W, 5, fill='primary')


def _header(d, key):
    _background(d)
    d.logo(M, H - 58, 88)
    number = d.page_of[key]
    title = next(t for k, t, _ in d.contents if k == key)
    d.kicker(W - M, H - 44, d.t('header.kicker', title=title), 'muted', 'right')
    d.line(M, H - 70, W - M, H - 70, 'accent', 0.6)
    _footer(d, number)


def _footer(d, number):
    d.line(M, FOOTER_Y + 14, W - M, FOOTER_Y + 14, 'accent', 0.5)
    d.text(M, FOOTER_Y, d.t('footer.brand'), MIN_TEXT, 'Medium', 'muted')
    if d.synthetic:
        d.text(W / 2, FOOTER_Y, d.t('footer.sample'), MIN_TEXT, 'Medium', 'muted', 'center')
    d.text(W - M, FOOTER_Y, d.t('footer.page', number=number, total=d.total), MIN_TEXT, 'Medium', 'muted', 'right')


def _title(d, key, title, intro):
    number = d.page_of[key]
    d.kicker(M, H - 104, d.t('title.section', number=number - 1), 'primary_text')
    d.text(M, H - 132, title, 23, 'Head', 'ink')
    d.diamond(M + d.width(title, 'Head', 23) + 12, H - 124, 3.2)
    return d.wrap(M, H - 154, intro, CW * 0.86, 9.6, 14.5, 'Body', 'muted') - 8


def _kv_layout(d, rows, width, size, minimum, max_lines=3):
    """Measure label/value rows: one line at the largest size that fits, else wrapped at minimum."""
    out = []
    for label, value in rows:
        fit = d.fit(value, 'Strong', size, width, minimum)
        if fit is not None:
            lines, fs = [value], fit
        else:
            lines, fs = d.split(value, 'Strong', minimum, width), minimum
            if len(lines) > max_lines:
                raise layout.LayoutError('Birth detail value too long')
        out.append((label, lines, fs, 38 + 11 * (len(lines) - 1)))
    return out


def _card(d, x, y, w, h, fill='surface'):
    d.rect(x, y, w, h, fill=fill, stroke='rule', width=0.7, radius=6)


def _note(d, x, y_top, w, title, body, size=8.8):
    lines = d.split(body, 'Body', size, w - 28)
    h = 34 + len(lines) * size * 1.5
    d.rect(x, y_top - h, w, h, fill='tint_soft', radius=6)
    d.rect(x, y_top - h, 3, h, fill='accent')
    d.kicker(x + 14, y_top - 17, title, 'primary_text')
    y = y_top - 32
    for line in lines:
        d.text(x + 14, y, line, size, 'Body', 'ink')
        y -= size * 1.5
    return y_top - h


def _table(d, x, y_top, columns, rows, row_h=30, header_h=26, zebra=True):
    """columns: (title, width, align). rows: lists of cells; a cell is a str or a
    callable(d, x, baseline, width, align). Returns the bottom y."""
    total = sum(c[1] for c in columns)
    d.rect(x, y_top - header_h, total, header_h, fill='tint', radius=0)
    cx = x
    for title, width, align in columns:
        tx = cx + 10 if align == 'left' else (cx + width - 10 if align == 'right' else cx + width / 2)
        d.kicker(tx, y_top - header_h + 9.5, title, 'ink', align)
        cx += width
    y = y_top - header_h
    for i, row in enumerate(rows):
        if zebra and i % 2 == 1:
            d.rect(x, y - row_h, total, row_h, fill='tint_soft')
        cx = x
        base = y - row_h / 2 - 3.4
        for (title, width, align), cell in zip(columns, row):
            if callable(cell):
                cell(d, cx, base, width, align)
            else:
                tx = cx + 10 if align == 'left' else (cx + width - 10 if align == 'right' else cx + width / 2)
                size = d.fit(cell, 'Body', 9.6, width - 20, MIN_TEXT)
                if size is None:
                    raise layout.LayoutError('Table cell text too long')
                d.text(tx, base, cell, size, 'Body', 'ink', align)
            cx += width
        y -= row_h
        d.line(x, y, x + total, y, 'rule', 0.6)
    d.line(x, y_top, x + total, y_top, 'accent', 0.9)
    d.line(x, y, x + total, y, 'accent', 0.9)
    return y


def _cell(text, face='Body', color='ink', size=9.6, minimum=MIN_TEXT):
    def draw(d, x, base, width, align):
        tx = x + 10 if align == 'left' else (x + width - 10 if align == 'right' else x + width / 2)
        fit = d.fit(text, face, size, width - 20, minimum)
        if fit is None:
            raise layout.LayoutError('Table cell text too long')
        d.text(tx, base, text, fit, face, color, align)
    return draw


def _members_cell(tokens):
    """Graha abbreviations for a house; two lines when one would be too small to read."""
    def draw(d, x, base, width, align):
        if not tokens:
            d.text(x + 10, base, '–', 9.2, 'Strong', 'muted')
            return
        text = '  '.join(tokens)
        size = d.fit(text, 'Strong', 9.2, width - 20, 8)
        if size is not None:
            d.text(x + 10, base, text, size, 'Strong', 'ink')
            return
        half = (len(tokens) + 1) // 2
        first, second = '  '.join(tokens[:half]), '  '.join(tokens[half:])
        size = min(d.fit(first, 'Strong', 8.6, width - 20, 6.5) or 0, d.fit(second, 'Strong', 8.6, width - 20, 6.5) or 0)
        if not size:
            raise layout.LayoutError('House members do not fit')
        d.text(x + 10, base + size * 0.62, first, size, 'Strong', 'ink')
        d.text(x + 10, base - size * 0.62, second, size, 'Strong', 'ink')
    return draw


def _graha_cell(name, abbr):
    def draw(d, x, base, width, align):
        d.rect(x + 10, base - 4.6, 22, 15, fill='tint', radius=3)
        d.text(x + 21, base, abbr, MIN_TEXT, 'Strong', 'primary_text', 'center')
        d.text(x + 40, base, name, 9.8, 'Strong', 'ink')
    return draw


def _rashi_cell(rashi, face='Body', color='ink'):
    number = layout.SIGNS.index(rashi) + 1
    def draw(d, x, base, width, align):
        d.text(x + 10, base, f'{number:>2}', 8.2, 'Strong', 'muted')
        d.text(x + 26, base, d.tr.rashi(rashi), 9.6, face, color)
    return draw


# ---------------------------------------------------------------------------
# North Indian chart.

def _chart_tokens(chart, positions, mode, tr):
    key = 'whole_sign_house' if mode == 'd1' else 'navamsa_whole_sign_house'
    houses = {h: [] for h in range(1, 13)}
    houses[1].append((tr.lagna()[1], positions['lagna'].short() if mode == 'd1' else None, 'lagna'))
    for name in GRAHAS:
        body = chart['planets'][name]
        houses[body[key]].append((tr.graha(name)[1], positions[name].short() if mode == 'd1' else None, 'graha'))
    return houses


def _detail_size(size):
    return max(MIN_TEXT, size * 0.78)


def _token_widths(d, tokens):
    def widths(size, with_detail):
        out = []
        for main, detail, _ in tokens:
            w = d.width(main, 'Strong', size)
            if with_detail and detail:
                w += size * 0.18 + d.width(detail, 'Body', _detail_size(size))
            out.append(w)
        return out
    return widths


def draw_chart(d, x, y, size, lagna_rashi, houses, line_color='primary', emblem=False):
    """North Indian chart, lower-left corner at (x, y). Returns placed label boxes in points."""
    s = size / 600
    px = lambda ux: x + ux * s
    py = lambda uy: y + (600 - uy) * s
    c = d.c
    d.rect(x, y, size, size, fill='surface')
    # Lagna house shading.
    p = c.beginPath()
    for i, (ux, uy) in enumerate(layout.HOUSES[1]):
        (p.moveTo if i == 0 else p.lineTo)(px(ux), py(uy))
    p.close()
    c.setFillColor(d.pal['tint_soft' if emblem else 'tint']); c.drawPath(p, fill=1, stroke=0)
    # Lines: frame, diagonals, inner diamond.
    inner = 1.0 if not emblem else 0.9
    c.setStrokeColor(d.pal[line_color]); c.setLineWidth(inner); c.setLineJoin(1); c.setLineCap(1)
    c.line(px(0), py(0), px(600), py(600)); c.line(px(600), py(0), px(0), py(600))
    p = c.beginPath(); p.moveTo(px(300), py(0)); p.lineTo(px(600), py(300)); p.lineTo(px(300), py(600))
    p.lineTo(px(0), py(300)); p.close(); c.drawPath(p, stroke=1, fill=0)
    c.setLineWidth(1.8 if not emblem else 1.2); c.rect(x, y, size, size, stroke=1, fill=0)
    c.setStrokeColor(d.pal['accent']); c.setLineWidth(0.6)
    c.rect(x - 5, y - 5, size + 10, size + 10, stroke=1, fill=0)
    start = layout.SIGNS.index(lagna_rashi)
    number_size = 10.5 if not emblem else 8
    placed_boxes = {}
    for h in range(1, 13):
        nx, ny = layout.number_position(h)
        d.text(px(nx), py(ny) - number_size * 0.36, str((start + h - 1) % 12 + 1),
               number_size, 'Head', 'primary_text', 'center')
        tokens = houses.get(h, [])
        if not tokens:
            continue
        placed = layout.layout_house(h, _token_widths(d, tokens), s,
                                     sizes=(8.5, 8) if emblem else (12, 11.5, 11, 10.5, 10, 9.5, 9, 8.5, 8))
        boxes = []
        for item in placed:
            main, detail, kind = tokens[item.index]
            fs = item.size
            left = px(item.x)
            top = py(item.y)
            base = top - (item.height * s + fs * 0.70) / 2
            color = 'primary_text' if kind == 'lagna' else 'ink'
            d.text(left, base, main, fs, 'Strong', color)
            if item.with_detail and detail:
                d.text(left + d.width(main, 'Strong', fs) + fs * 0.18, base, detail, _detail_size(fs), 'Body', 'muted')
            boxes.append((left, top - item.height * s, left + item.width * s, top, main))
        placed_boxes[h] = boxes
    return placed_boxes


# ---------------------------------------------------------------------------
# Pages.

def _page_cover(d, response, positions):
    chart, info = response['chart'], response['input']
    place = info['place']
    _background(d)
    # Double gold frame with diamond corner marks.
    d.c.setStrokeColor(d.pal['accent']); d.c.setLineWidth(0.8)
    d.c.rect(20, 20, W - 40, H - 45, stroke=1, fill=0)
    d.c.setLineWidth(0.4)
    d.c.rect(25, 25, W - 50, H - 55, stroke=1, fill=0)
    for cx, cy in ((20, 20), (W - 20, 20), (20, H - 25), (W - 20, H - 25)):
        d.diamond(cx, cy, 4.5)
    d.logo(W / 2 - 84, H - 120, 168)
    d.kicker(W / 2, H - 162, d.t('cover.kicker'), 'primary_text', 'center', 8.4)
    d.text(W / 2, H - 214, d.t('cover.title'), 46, 'HeadBold', 'primary', 'center')
    d.line(W / 2 - 70, H - 236, W / 2 - 10, H - 236, 'accent', 0.8)
    d.diamond(W / 2, H - 236, 3.2)
    d.line(W / 2 + 10, H - 236, W / 2 + 70, H - 236, 'accent', 0.8)
    subtitle_y, size = H - 258, 216
    if d.display_name is not None:
        # "Prepared for" and the name under the title; the subtitle and the emblem move down
        # and the emblem shrinks, so the caption and the birth panel keep their places.
        d.kicker(W / 2, H - 262, d.t('cover.prepared_for'), 'primary_text', 'center', 8.4)
        lines, fs = d.name_lines(d.display_name, 'Head', CW - 40, 22, 11, 4)
        y = H - 288
        for line in lines:
            d.name_text(W / 2, y, line, fs, 'Head', 'ink', 'center')
            y -= fs * 1.25
        subtitle_y = y + fs * 1.25 - 24
        size = (subtitle_y - 18) - (H - 520)
    d.text(W / 2, subtitle_y, d.t('cover.subtitle'), 10.5, 'Body', 'muted', 'center')
    # Emblem: this chart's own house and Rashi layout.
    houses = {1: [(d.tr.lagna()[1], None, 'lagna')]}
    draw_chart(d, W / 2 - size / 2, H - 520, size, chart['lagna']['rashi'], houses, 'accent', emblem=True)
    d.text(W / 2, H - 546, d.t('cover.caption', lagna=d.tr.rashi(chart['lagna']['rashi']),
                               nakshatra=d.tr.nakshatra(chart['moon_nakshatra']['name'])),
           9, 'Medium', 'muted', 'center')
    # Birth panel.
    top, h = 262, 128
    d.rect(M + 12, top - h, CW - 24, h, fill='surface', stroke='accent', width=0.7, radius=8)
    col = (CW - 24) / 3
    place_name, region, country = d.tr.place(place)
    fields = [
        (d.t('cover.birthplace'), place_name, d.t('cover.region', region=region, country=country)),
        (d.t('cover.date'), d.date_text(info['local_date']), d.t('cover.date_sub')),
        (d.t('cover.time'), info['local_time'], d.t('cover.time_sub', offset=info['utc_offset'],
                                                       zone=chart['birth']['timezone'])),
    ]
    for i, (label, value, sub) in enumerate(fields):
        x = M + 12 + i * col + 18
        if i:
            d.line(M + 12 + i * col, top - h + 20, M + 12 + i * col, top - 20, 'rule', 0.7)
        d.kicker(x, top - 30, label, 'primary_text')
        y = d.fitted(x, top - 56, value, col - 32, 15, 'Head', 'ink', minimum=10.5, leading=13, max_lines=3)
        d.wrap(x, min(y, top - 76) - 2, sub, col - 32, 8.2, 11, 'Body', 'muted', max_lines=3)
    y = 104
    if d.synthetic:
        d.text(W / 2, y + 18, d.t('cover.sample'), MIN_TEXT, 'Strong', 'primary_text', 'center')
    d.text(W / 2, y, d.t('cover.disclaimer'), 8.6, 'Body', 'muted', 'center')
    d.text(W / 2, 52, d.t('cover.site'), 8.4, 'Strong', 'primary_text', 'center')


def _page_overview(d, response, positions):
    chart = response['chart']
    _header(d, 'overview')
    y = _title(d, 'overview', d.t('overview.title'), d.t('overview.intro'))
    pl = chart['planets']
    tr = d.tr
    cards = [
        (d.t('overview.d1_lagna'), tr.rashi(chart['lagna']['rashi']), d.t('overview.within', dms=positions['lagna'].dms()), d.page_of['positions']),
        (d.t('overview.moon_rashi'), tr.rashi(pl['moon']['rashi']), d.t('overview.dms_house', dms=positions['moon'].dms(), house=pl['moon']['whole_sign_house']), d.page_of['positions']),
        (d.t('overview.moon_nakshatra'), tr.nakshatra(chart['moon_nakshatra']['name']), d.t('overview.pada_of', pada=chart['moon_nakshatra']['pada']), d.page_of['positions']),
        (d.t('overview.sun_rashi'), tr.rashi(pl['sun']['rashi']), d.t('overview.dms_house', dms=positions['sun'].dms(), house=pl['sun']['whole_sign_house']), d.page_of['positions']),
        (d.t('overview.d9_lagna'), tr.rashi(chart['d9']['lagna_rashi']), d.t('overview.navamsa_house1'), d.page_of['d9']),
        (d.t('overview.calculation'), d.t('overview.lahiri'), d.t('overview.method_sub'), d.page_of['method']),
    ]
    cw, ch, gap = (CW - 2 * 12) / 3, 84, 12
    top = y - 6
    for i, (label, value, sub, page) in enumerate(cards):
        x = M + (i % 3) * (cw + gap)
        yy = top - (i // 3) * (ch + gap) - ch
        _card(d, x, yy, cw, ch)
        d.rect(x, yy + ch - 3, cw, 3, fill='accent')
        d.kicker(x + 14, yy + ch - 22, label, 'primary_text')
        d.text(x + cw - 14, yy + ch - 22, d.t('overview.page_ref', page=page), MIN_TEXT, 'Medium', 'muted', 'right')
        d.fitted(x + 14, yy + ch - 47, value, cw - 28, 16, 'Head', 'ink', minimum=11, max_lines=1)
        d.fitted(x + 14, yy + 15, sub, cw - 28, 8.6, 'Body', 'muted', minimum=MIN_TEXT, max_lines=1)
    y = top - 2 * (ch + gap) - 22
    d.text(M, y, d.t('overview.contents'), 15, 'Head', 'ink')
    y -= 12
    d.line(M, y, W - M, y, 'accent', 0.8)
    # The ten-page edition keeps its original rows; the extended edition lists more pages in
    # the same space, so its rows are closer together (same type sizes).
    step = 34 if d.edition == EDITION_STANDARD else 23
    for key, title, desc in d.contents[1:]:
        n = d.page_of[key]
        y -= step
        d.text(M, y + 4, f'{n - 1:02d}', 12, 'Head', 'primary_text')
        d.text(M + 34, y + 9, title, 10.6, 'Strong', 'ink')
        d.text(M + 34, y - 4.5, desc, 8.6, 'Body', 'muted')
        d.text(W - M, y + 4, str(n), 10, 'Strong', 'ink', 'right')
        d.c.setDash(1, 2.4)
        d.line(M + 34 + d.width(title, 'Strong', 10.6) + 8, y + 9, W - M - 18, y + 9, 'rule', 0.8)
        d.c.setDash()
        y -= 6
        d.line(M, y - 4, W - M, y - 4, 'rule', 0.5)


def _page_guide(d, response, positions):
    chart = response['chart']
    _header(d, 'guide')
    y = _title(d, 'guide', d.t('guide.title'), d.t('guide.intro'))
    terms = [(d.t(f'guide.term.{k}'), d.t(f'guide.def.{k}'))
             for k in ('rashi', 'graha', 'lagna', 'd1', 'd9', 'whole_sign', 'nakshatra')]
    tw = 118
    for term, text in terms:
        d.text(M, y, term, 9.8, 'Strong', 'primary_text')
        y2 = d.wrap(M + tw, y, text, CW - tw, 9.2, 13.4, 'Body', 'ink', max_lines=3)
        rule = y2 + 13.4 - 8
        d.line(M, rule, W - M, rule, 'rule', 0.5)
        y = rule - 16
    y -= 8
    sun, pos = chart['planets']['sun'], positions['sun']
    example = d.t('guide.example', longitude=sun['longitude_deg'], dms=pos.dms(), rashi=d.tr.rashi(sun['rashi']),
                  number=pos.rashi_number, start=30 * (pos.rashi_number - 1))
    y = _note(d, M, y, CW, d.t('guide.example_title'), example) - 22
    # Rashi reference and abbreviations side by side.
    d.text(M, y, d.t('guide.rashis'), 12, 'Head', 'ink')
    d.text(M + 300, y, d.t('guide.abbreviations'), 12, 'Head', 'ink')
    y -= 10
    d.line(M, y, M + 280, y, 'accent', 0.8)
    d.line(M + 300, y, W - M, y, 'accent', 0.8)
    for i, sign in enumerate(layout.SIGNS):
        col, row = divmod(i, 6)
        x = M + col * 140
        yy = y - 18 - row * 17.5
        d.text(x, yy, f'{i + 1:>2}', 8.6, 'Strong', 'primary_text')
        shown = d.tr.rashi(sign)
        d.text(x + 18, yy, shown, 9, 'Medium', 'ink')
        if not d.hindi:
            # Hindi readers get the Rashi names only; the English equivalents are an English reading aid.
            d.text(x + 18 + d.width(shown, 'Medium', 9) + 5, yy, layout.SIGN_ENGLISH[i], MIN_TEXT, 'Body', 'muted')
    abbr = [(d.tr.lagna()[1], d.t('guide.lagna_name'))] + [d.tr.graha(n)[::-1] for n in GRAHAS]
    for i, (a, name) in enumerate(abbr):
        col, row = divmod(i, 5)
        x = M + 300 + col * 98
        yy = y - 18 - row * 21
        d.rect(x, yy - 4.6, 26, 15, fill='tint', radius=3)
        d.text(x + 13, yy, a, MIN_TEXT, 'Strong', 'primary_text', 'center')
        d.text(x + 32, yy, name, 9, 'Medium', 'ink')
    d.wrap(M + 300, y - 18 - 5 * 21 + 4, d.t('guide.sign_note'),
           W - M - (M + 300), MIN_TEXT, 10.5, 'Body', 'muted', max_lines=2)


def _page_birth(d, response, positions):
    chart, info = response['chart'], response['input']
    place, birth, meta = info['place'], chart['birth'], chart['calculation_metadata']
    _header(d, 'birth')
    tr = d.tr
    y = _title(d, 'birth', d.t('birth.title'), d.t('birth.intro'))
    utc = birth['utc'].replace('T', '  ').replace('Z', '  UTC')
    place_name, region, country = tr.place(place)
    rows = [
        (d.t('birth.place'), place_name),
        (d.t('birth.region'), d.t('cover.region', region=region, country=country)),
        (d.t('birth.latitude'), layout.coordinate(birth['latitude'], tr.hemisphere('N'), tr.hemisphere('S'))),
        (d.t('birth.longitude'), layout.coordinate(birth['longitude'], tr.hemisphere('E'), tr.hemisphere('W'))),
        (d.t('birth.local_date'), d.t('birth.local_date_value', date=d.date_text(info['local_date']), iso=info['local_date'])),
        (d.t('birth.local_time'), info['local_time']),
        (d.t('birth.zone'), birth['timezone']),
        (d.t('birth.offset'), 'UTC' + info['utc_offset']),
        (d.t('birth.utc'), utc),
    ]
    conv = meta['conventions']
    ayanamsa = conv['ayanamsa']['name']
    rows2 = [
        (d.t('birth.zodiac'), d.t('birth.zodiac_value')),
        (d.t('birth.ayanamsa'), d.t('birth.ayanamsa_lahiri', name=tr.ayanamsa(ayanamsa)) if ayanamsa == 'Lahiri' else tr.ayanamsa(ayanamsa)),
        (d.t('birth.positions'), d.t('birth.positions_value')),
        (d.t('birth.nodes'), d.t('birth.nodes_value')),
        (d.t('birth.houses'), d.t('birth.houses_value')),
        (d.t('birth.ephemeris'), d.t('birth.ephemeris_value', version=meta['swiss_ephemeris']['library_version'])),
        (d.t('birth.ephemeris_data'), d.t('birth.verified') if meta['ephemeris_data'].get('verified_before_calculation') else d.t('birth.not_verified')),
        (d.t('birth.tz_data'), d.t('birth.tz_value', package=meta['timezone_data']['package_version'], iana=meta['timezone_data']['iana_version'])),
        (d.t('birth.place_source'), tr.place_source(place['source']) if 'source' in place else d.t('birth.not_supplied')),
    ]
    half = CW / 2 - 8
    top = y
    left = _kv_layout(d, rows, half - 32, 10.8, MIN_TEXT)
    if d.display_name is not None:
        lines, fs = d.name_lines(d.display_name, 'Strong', half - 32, 10.8, MIN_TEXT, 5)
        left.insert(0, (d.t('birth.name'), lines, fs, 38 + 11 * (len(lines) - 1)))
    right = _kv_layout(d, rows2, half - 32, 10.2, MIN_TEXT)
    height = 38 + max(sum(h for *_, h in left), sum(h for *_, h in right))
    for x, title, items in ((M, d.t('birth.record'), left), (M + half + 16, d.t('birth.context'), right)):
        _card(d, x, top - height, half, height)
        d.kicker(x + 16, top - 22, title, 'primary_text')
        ry = top - 28
        for i, (label, lines, size, h) in enumerate(items):
            ry -= h
            d.text(x + 16, ry + h - 13, label, MIN_TEXT, 'Medium', 'muted')
            yy = ry + h - 26
            is_name = d.display_name is not None and items is left and i == 0
            for line in lines:
                if is_name:
                    d.name_text(x + 16, yy, line, size, 'Strong', 'ink')
                else:
                    d.text(x + 16, yy, line, size, 'Strong', 'ink')
                yy -= 11
            if i < len(items) - 1:
                d.line(x + 16, ry + 1, x + half - 16, ry + 1, 'rule', 0.5)
    y = top - height - 24
    resolution = info.get('offset_resolution')
    offset_text = (d.t('birth.offset_unique') if resolution == 'unique'
                   else d.t('birth.offset_repeated')
                   if resolution == 'user_selected_repeated_hour' else d.t('birth.offset_supplied'))
    y = _note(d, M, y, CW, d.t('birth.conversion_title'),
              d.t('birth.conversion', zone=birth['timezone'], offset_text=offset_text)) - 14
    d.wrap(M, y, d.t('birth.method_ref', page=d.page_of['method']), CW, 8.4, 12, 'Body', 'muted')


def _page_chart(d, response, positions, mode):
    chart = response['chart']
    key = 'd1' if mode == 'd1' else 'd9'
    _header(d, key)
    if mode == 'd1':
        lagna = chart['lagna']['rashi']
        y = _title(d, key, d.t('chart.d1_title'), d.t('chart.d1_intro'))
    else:
        lagna = chart['d9']['lagna_rashi']
        y = _title(d, key, d.t('chart.d9_title'), d.t('chart.d9_intro'))
    size = 404
    x0 = (W - size) / 2
    y0 = y - 14 - size
    tokens = _chart_tokens(chart, positions, mode, d.tr)
    d.chart_boxes[mode] = {'origin': (x0, y0), 'size': size, 'lagna': lagna,
                           'labels': draw_chart(d, x0, y0, size, lagna, tokens)}
    # Key band.
    y = y0 - 30
    lag_label = d.t('chart.d1_lagna_label') if mode == 'd1' else d.t('chart.d9_lagna_label')
    d.kicker(M, y, lag_label, 'primary_text')
    if mode == 'd1':
        lagna_value = d.t('chart.d1_lagna_value', rashi=d.tr.rashi(lagna), dms=positions['lagna'].dms())
    else:
        lagna_value = d.t('chart.d9_lagna_value', rashi=d.tr.rashi(lagna), number=layout.SIGNS.index(lagna) + 1)
    d.text(M + 110, y, lagna_value, 9.8, 'Strong', 'ink')
    y -= 22
    d.kicker(M, y, d.t('chart.abbreviations'), 'primary_text')
    x = M + 110
    for name in GRAHAS:
        full, abbr = d.tr.graha(name)
        item = d.width(abbr, 'Strong', 8.6) + 4 + d.width(full, 'Body', 8.6) + 13
        if x + item > W - M:
            y -= 15
            x = M + 110
        d.text(x, y, abbr, 8.6, 'Strong', 'primary_text')
        d.text(x + d.width(abbr, 'Strong', 8.6) + 4, y, full, 8.6, 'Body', 'ink')
        x += item
    y -= 26
    if mode == 'd1':
        body = d.t('chart.d1_note', page=d.page_of['positions'])
    else:
        body = d.t('chart.d9_note', page=d.page_of['navamsa'])
    _note(d, M, y, CW, d.t('chart.note_title'), body)


def _page_positions(d, response, positions):
    chart = response['chart']
    pl = chart['planets']
    _header(d, 'positions')
    y = _title(d, 'positions', d.t('positions.title'), d.t('positions.intro'))
    columns = [(d.t('col.graha'), 116, 'left'), (d.t('col.d1_rashi'), 104, 'left'), (d.t('col.house'), 52, 'center'),
               (d.t('col.within'), 92, 'right'), (d.t('col.longitude'), 135, 'right')]
    lag = chart['lagna']
    rows = [[_graha_cell(*d.tr.lagna()), _rashi_cell(lag['rashi'], 'Strong', 'primary_text'),
             _cell('1', 'Strong', 'primary_text'), _cell(positions['lagna'].dms(), 'Medium'),
             _cell(f'{lag["longitude_deg"]:.8f}°', 'Body', 'muted', 9.2)]]
    for name in GRAHAS:
        body = pl[name]
        rows.append([_graha_cell(*d.tr.graha(name)), _rashi_cell(body['rashi']),
                     _cell(str(body['whole_sign_house']), 'Strong', 'primary_text'),
                     _cell(positions[name].dms(), 'Medium'),
                     _cell(f'{body["longitude_deg"]:.8f}°', 'Body', 'muted', 9.2)])
    y = _table(d, M, y - 4, columns, rows, row_h=34, header_h=28) - 20
    moon = chart['moon_nakshatra']
    _card(d, M, y - 52, CW, 52, 'surface')
    d.rect(M, y - 52, 3, 52, fill='accent')
    d.kicker(M + 16, y - 18, d.t('positions.moon_title'), 'primary_text')
    moon_name = d.tr.nakshatra(moon['name'])
    d.text(M + 16, y - 38, moon_name, 14, 'Head', 'ink')
    d.text(M + 16 + d.width(moon_name, 'Head', 14) + 12, y - 38, d.t('positions.pada', pada=moon['pada']), 11, 'Strong', 'primary_text')
    d.wrap(M + 250, y - 22, d.t('positions.moon_only'), CW - 266, 8.2, 11.5, 'Body', 'muted', max_lines=3)
    y -= 72
    _note(d, M, y, CW, d.t('positions.notes_title'), d.t('positions.notes'))


def _page_navamsa(d, response, positions):
    chart = response['chart']
    pl = chart['planets']
    _header(d, 'navamsa')
    y = _title(d, 'navamsa', d.t('navamsa.title'), d.t('navamsa.intro'))
    columns = [(d.t('col.graha'), 140, 'left'), (d.t('col.d1_rashi'), 125, 'left'), (d.t('col.d9_rashi'), 125, 'left'),
               (d.t('col.d9_house'), 109, 'center')]
    l9 = chart['d9']['lagna_rashi']
    rows = [[_graha_cell(*d.tr.lagna()), _rashi_cell(chart['lagna']['rashi']),
             _rashi_cell(l9, 'Strong', 'primary_text'), _cell('1', 'Strong', 'primary_text')]]
    for name in GRAHAS:
        body = pl[name]
        rows.append([_graha_cell(*d.tr.graha(name)), _rashi_cell(body['rashi']),
                     _rashi_cell(body['navamsa_rashi'], 'Strong'),
                     _cell(str(body['navamsa_whole_sign_house']), 'Strong', 'primary_text')])
    y = _table(d, M, y - 4, columns, rows, row_h=38, header_h=28) - 24
    _note(d, M, y, CW, d.t('navamsa.note_title'), d.t('navamsa.note', lagna=d.tr.rashi(l9), page=d.page_of['d9']))


def _page_houses(d, response, positions):
    chart = response['chart']
    pl = chart['planets']
    _header(d, 'houses')
    y = _title(d, 'houses', d.t('houses.title'), d.t('houses.intro'))
    abbr = {name: d.tr.graha(name)[1] for name in GRAHAS}
    lagna_abbr = d.tr.lagna()[1]
    l1 = layout.SIGNS.index(chart['lagna']['rashi'])
    l9 = layout.SIGNS.index(chart['d9']['lagna_rashi'])
    d1 = {h: [] for h in range(1, 13)}
    d9 = {h: [] for h in range(1, 13)}
    for name in GRAHAS:
        d1[pl[name]['whole_sign_house']].append(abbr[name])
        d9[pl[name]['navamsa_whole_sign_house']].append(abbr[name])
    # Same membership as the engine's own D9 list (already enforced in validation).
    for row in chart['d9']['houses']:
        if sorted(abbr[n] for n in row['grahas']) != sorted(d9[row['house']]):
            raise layout.ReportDataError('D9 house directory disagrees with engine D9 houses')
    columns = [(d.t('col.house'), 52, 'center'), (d.t('col.d1_rashi'), 106, 'left'), (d.t('col.d1_grahas'), 128, 'left'),
               (d.t('col.d9_rashi'), 106, 'left'), (d.t('col.d9_grahas'), 107, 'left')]
    rows = []
    for h in range(1, 13):
        g1 = ([lagna_abbr] if h == 1 else []) + d1[h]
        g9 = ([lagna_abbr] if h == 1 else []) + d9[h]
        rows.append([_cell(str(h), 'Head', 'primary_text', 11), _rashi_cell(layout.SIGNS[(l1 + h - 1) % 12]),
                     _members_cell(g1), _rashi_cell(layout.SIGNS[(l9 + h - 1) % 12]), _members_cell(g9)])
    y = _table(d, M, y - 4, columns, rows, row_h=34, header_h=28) - 22
    _note(d, M, y, CW, d.t('houses.key_title'), d.t('houses.key', page=d.page_of['guide']))


def _page_method(d, response, positions):
    chart = response['chart']
    meta = chart['calculation_metadata']
    _header(d, 'method')
    y = _title(d, 'method', d.t('method.title'), d.t('method.intro'))
    eph = meta['ephemeris_data']
    swiss = meta['swiss_ephemeris']
    tz = meta['timezone_data']
    rows = [
        (d.t('method.zodiac'), d.tr.engine_text('ayanamsa_definition', meta['conventions']['ayanamsa']['definition'])),
        (d.t('method.nodes'), d.t('method.nodes_value')),
        (d.t('method.houses'), d.t('method.houses_value')),
        (d.t('method.precision'), d.t('method.precision_value')),
        (d.t('method.ephemeris'), d.t('method.ephemeris_value', library=swiss['library_version'],
                                      binding=swiss['python_binding_version'],
                                      files=', '.join(f['name'] for f in eph['required_files']),
                                      commit=eph['source_commit'][:12])),
        (d.t('method.zones'), d.t('method.zones_value', iana=tz['iana_version'], package=tz['package_version'])),
        (d.t('method.output'), d.t('method.output_value', schema=chart['schema_version'], metadata=meta['metadata_schema'])),
    ]
    tw = 112
    for label, text in rows:
        d.text(M, y, label, 9.2, 'Strong', 'primary_text')
        y2 = d.wrap(M + tw, y, text, CW - tw, 8.6, 12.4, 'Body', 'ink', max_lines=4)
        rule = y2 + 12.4 - 7
        d.line(M, rule, W - M, rule, 'rule', 0.5)
        y = rule - 15
    y -= 10
    status = chart['validation_status']
    boundary = meta['validation'].get('claim_boundary', '')
    y = _note(d, M, y, CW, d.t('method.status_title', status=status),
              d.t('method.status') +
              (d.t('method.boundary', boundary=d.tr.engine_text('claim_boundary', boundary)) if boundary else '')) - 18
    half = CW / 2 - 10
    d.text(M, y, d.t('method.included'), 11, 'Head', 'ink')
    d.text(M + half + 20, y, d.t('method.excluded'), 11, 'Head', 'ink')
    if d.edition == EDITION_STANDARD:
        inc = [d.t(f'method.inc{i}') for i in range(1, 6)]
        exc = [d.t(f'method.exc{i}') for i in range(1, 6)]
    else:
        inc, exc = d.extension.method_lists(d)
    yy = y - 18
    for a, b in zip(inc, exc):
        d.diamond(M + 3, yy + 3, 2.4)
        d.text(M + 12, yy, a, 8.6, 'Body', 'ink')
        d.diamond(M + half + 23, yy + 3, 2.4, 'muted', fill=False)
        d.text(M + half + 32, yy, b, 8.6, 'Body', 'ink')
        yy -= 14.5
    # Licences sit at the foot of the page, above the footer rule.
    y = min(yy - 12, 128)
    d.line(M, y + 6, W - M, y + 6, 'accent', 0.6)
    d.kicker(M, y - 8, d.t('method.licences_title'), 'primary_text')
    d.wrap(M, y - 22, d.t('method.licences'), CW, MIN_TEXT, 11, 'Body', 'muted', max_lines=5)


def _new_page(d):
    d.page += 1
    if d.page > 1:
        d.c.showPage()


def generate(response: dict, synthetic: bool = False, palette: str | None = None,
             display_name: str | None = None, locale: str = loc.DEFAULT_LOCALE) -> bytes:
    """Searchable A4 PDF in memory. Writes no file, keeps no copy and makes no network request.

    display_name is the optional report name, presentation only; None (the default) draws
    the anonymous report. It must already be the output of display_name.normalize().
    locale is 'en' (default, byte-identical to the renderer before KUN-I18N-001) or 'hi'.
    """
    return render(response, synthetic, palette, display_name, locale)[0]


def generate_extended(response: dict, panchanga: dict, synthetic: bool = False, palette: str | None = None,
                      display_name: str | None = None, locale: str = loc.DEFAULT_LOCALE,
                      names: str | None = None) -> bytes:
    """The extended edition (KUN-PAN-RPT-001): the ten pages plus the birth-instant Panchanga
    pages. `panchanga` must be the `sabpuja-panchanga/1` document computed for the same request
    as `response`; any mismatch, unsupported value or unaudited field raises before drawing.

    names=None (the default) keeps the numeric M1 display byte for byte. names='qa_preview' draws
    Tithi, Karana and Yoga names for internal QA only, marked as not for customers;
    names='customer' is refused until panchanga_names.release_problems() is empty
    (KUN-PAN-M2-NAMES-001)."""
    return render(response, synthetic, palette, display_name, locale, panchanga=panchanga, panchanga_names=names)[0]


def render(response: dict, synthetic: bool = False, palette: str | None = None,
           display_name: str | None = None, locale: str = loc.DEFAULT_LOCALE, *, panchanga=None,
           panchanga_names=None):
    """generate() plus an audit of where chart labels were drawn, for the report tests.

    panchanga=None (the default) renders the standard ten-page edition exactly as before.
    A `sabpuja-panchanga/1` document renders the extended edition instead."""
    locale = loc.validate_locale(locale)
    if display_name is not None and names.normalize(display_name) != display_name:
        raise ValueError('report name must be validated and normalized before rendering')
    response = copy.deepcopy(response)
    positions = validate(response)
    extension = None
    if panchanga_names is not None and panchanga is None:
        raise ValueError('Panchanga names need the extended edition')
    if panchanga is not None:
        try:
            from . import panchanga_report
        except ImportError:  # loaded by path or run as a script
            import panchanga_report
        extension = panchanga_report.Extension(response, copy.deepcopy(panchanga), locale,
                                                   names=panchanga_names)
    pal = Palette(palette or THEMES['default_palette'])
    cmaps = _register_fonts()
    drawing = _logo_drawing()
    memory = io.BytesIO()
    # The document language is declared only for Hindi; the English call is unchanged.
    lang = {} if locale == loc.DEFAULT_LOCALE else {'lang': locale}
    c = canvas.Canvas(memory, pagesize=A4, pageCompression=1, invariant=1, initialFontName='SP2-Body', **lang)
    tr = loc.Translator(locale)
    c.setTitle(tr.t('meta.title'))
    c.setAuthor('Sabpuja')
    c.setSubject(tr.t('meta.subject') if extension is None else extension.subject())
    c.setCreator('Sabpuja Kundali report generator')
    c.setKeywords('')
    d = Doc(c, pal, cmaps, synthetic, locale)
    d.display_name = display_name
    if extension is not None:
        extension.apply(d)
    c.beginForm('sabpuja_logo', 0, 0, drawing.width, drawing.height)
    # The logo is paths only; keep the renderer's default font from adding an unembedded Times-Roman.
    default_font = STATE_DEFAULTS['fontName']
    STATE_DEFAULTS['fontName'] = 'SP2-Body'
    try:
        renderPDF.draw(drawing, c, 0, 0)
    finally:
        STATE_DEFAULTS['fontName'] = default_font
    c.endForm()
    d.logo_width = drawing.width
    pages = [_page_cover, _page_overview, _page_guide, _page_birth,
             lambda d, r, p: _page_chart(d, r, p, 'd1'), lambda d, r, p: _page_chart(d, r, p, 'd9'),
             _page_positions, _page_navamsa, _page_houses, _page_method]
    if extension is not None:
        at = pages.index(_page_method)
        pages[at:at] = extension.page_drawers()
    for draw in pages:
        _new_page(d)
        draw(d, response, positions)
    if d.page != d.total:
        raise layout.LayoutError('Page plan and drawn pages disagree')
    c.save()
    data = memory.getvalue()
    if len(data) > MAX_PDF_BYTES:
        raise RuntimeError('controlled PDF size exceeded')
    audit = {'charts': d.chart_boxes, 'palette': pal.name}
    if extension is not None:
        audit.update(edition=d.edition, layout=EXTENDED_LAYOUT_ID, page_keys=[k for k, _, _ in d.contents],
                     panchanga=extension.audit)
    if locale != loc.DEFAULT_LOCALE:
        audit.update(locale=locale, devanagari_runs=d.deva_runs, glyph_forms=len(d.glyph_forms), texts=d.drawn)
    if display_name is not None:
        audit.update(name_boxes=d.name_boxes, name_runs_drawn=d.name_drawn)
    return data, audit


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Render the Phase 2A premium Kundali PDF from an engine response.')
    parser.add_argument('chart_json')
    parser.add_argument('output_pdf')
    parser.add_argument('--sample', action='store_true', help='mark the report as synthetic sample data')
    parser.add_argument('--palette', choices=sorted(THEMES['palettes']), default=THEMES['default_palette'])
    parser.add_argument('--display-name', help='optional report name (synthetic names only in examples)')
    parser.add_argument('--locale', choices=loc.LOCALES, default=loc.DEFAULT_LOCALE)
    parser.add_argument('--panchanga-json', help='extended edition: the sabpuja-panchanga/1 document for the '
                                                 'same request (KUN-PAN-RPT-001)')
    parser.add_argument('--names-qa-preview', action='store_true',
                        help='internal QA only: draw Tithi, Karana and Yoga names marked "not for customers" '
                             '(KUN-PAN-M2-NAMES-001); needs --panchanga-json')
    args = parser.parse_args()
    response = json.loads(Path(args.chart_json).read_text())
    name = names.normalize(args.display_name)
    options = dict(synthetic=args.sample, palette=args.palette, display_name=name, locale=args.locale)
    if args.panchanga_json:
        pdf = generate_extended(response, json.loads(Path(args.panchanga_json).read_text()), **options,
                                names='qa_preview' if args.names_qa_preview else None)
    elif args.names_qa_preview:
        parser.error('--names-qa-preview needs --panchanga-json')
    else:
        pdf = generate(response, **options)
    Path(args.output_pdf).write_bytes(pdf)
