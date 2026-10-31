"""Sabpuja premium Kundali PDF, Phase 2A layout. Display of schema 0.3.0 engine output only.

The Phase 1 renderer (generate_report.py) stays unchanged as the reproducible baseline
and is still what the preview server calls. This module is a separate, versioned layout:

    generate(response, synthetic=False, palette='baseline') -> bytes

It computes no astronomy. Every value shown comes from the engine response; the only
derived display values are degrees within the engine's own Rashi (premium_layout.sign_position),
a calendar-formatted date, and label positions. Any disagreement raises before a page is drawn.
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
    from . import generate_report as phase1
    from . import premium_layout as layout
except ImportError:  # loaded by path or run as a script
    sys.path.insert(0, str(ROOT))
    import generate_report as phase1
    import premium_layout as layout

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
METADATA_SCHEMA = 'sabpuja-calculation-metadata/3'
MAX_PDF_BYTES = 1024 * 1024  # same bound as the preview server
MIN_TEXT = 8.0              # smallest type anywhere in the report, for legible A4 print
W, H = A4
M = 48                      # side margin
CW = W - 2 * M
FOOTER_Y = 34
GRAHAS = list(phase1.NAMES)  # sun ... ketu_mean, engine keys in canonical order
DISPLAY = {
    'sun': ('Sun', 'Su'), 'moon': ('Moon', 'Mo'), 'mars': ('Mars', 'Ma'),
    'mercury': ('Mercury', 'Me'), 'jupiter': ('Jupiter', 'Ju'), 'venus': ('Venus', 'Ve'),
    'saturn': ('Saturn', 'Sa'), 'rahu_mean': ('Rahu', 'Ra'), 'ketu_mean': ('Ketu', 'Ke'),
}
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']
PAGES = [
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
PAGE_OF = {key: i + 1 for i, (key, _, _) in enumerate(PAGES)}


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
    def __init__(self, c, pal, cmaps, synthetic):
        self.c, self.pal, self.cmaps, self.synthetic = c, pal, cmaps, synthetic
        self.page = 0
        self.chart_boxes = {}

    def _font(self, face, size, color):
        name = 'SP2-' + face
        self.c.setFont(name, size)
        self.c.setFillColor(self.pal[color])
        return name

    def check(self, text, face):
        cmap = self.cmaps['SP2-' + face]
        missing = {ch for ch in str(text) if ord(ch) not in cmap}
        if missing:
            raise MissingGlyphError(f'{face} has no glyph for {sorted(missing)!r}')

    def width(self, text, face, size):
        return pdfmetrics.stringWidth(str(text), 'SP2-' + face, size)

    def text(self, x, y, text, size=10, face='Body', color='ink', align='left', tracking=0):
        text = str(text)
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
        lines = simpleSplit(str(text), 'SP2-' + face, size, width)
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


# ---------------------------------------------------------------------------
# Page furniture.

def _background(d):
    d.rect(0, 0, W, H, fill='page')
    d.rect(0, H - 5, W, 5, fill='primary')


def _header(d, key):
    _background(d)
    d.logo(M, H - 58, 88)
    number = PAGE_OF[key]
    title = PAGES[number - 1][1]
    d.kicker(W - M, H - 44, f'Janma Kundali  ·  {title}', 'muted', 'right')
    d.line(M, H - 70, W - M, H - 70, 'accent', 0.6)
    _footer(d, number)


def _footer(d, number):
    d.line(M, FOOTER_Y + 14, W - M, FOOTER_Y + 14, 'accent', 0.5)
    d.text(M, FOOTER_Y, 'Sabpuja  ·  Janma Kundali', MIN_TEXT, 'Medium', 'muted')
    if d.synthetic:
        d.text(W / 2, FOOTER_Y, 'Sample report  ·  synthetic birth details', MIN_TEXT, 'Medium', 'muted', 'center')
    d.text(W - M, FOOTER_Y, f'Page {number} of {len(PAGES)}', MIN_TEXT, 'Medium', 'muted', 'right')


def _title(d, key, title, intro):
    number = PAGE_OF[key]
    d.kicker(M, H - 104, f'Section {number - 1:02d}', 'primary_text')
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
            lines, fs = simpleSplit(value, 'SP2-Strong', minimum, width), minimum
            if len(lines) > max_lines:
                raise layout.LayoutError('Birth detail value too long')
        out.append((label, lines, fs, 38 + 11 * (len(lines) - 1)))
    return out


def _card(d, x, y, w, h, fill='surface'):
    d.rect(x, y, w, h, fill=fill, stroke='rule', width=0.7, radius=6)


def _note(d, x, y_top, w, title, body, size=8.8):
    lines = simpleSplit(body, 'SP2-Body', size, w - 28)
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
        d.text(x + 26, base, rashi, 9.6, face, color)
    return draw


# ---------------------------------------------------------------------------
# North Indian chart.

def _chart_tokens(chart, positions, mode):
    key = 'whole_sign_house' if mode == 'd1' else 'navamsa_whole_sign_house'
    houses = {h: [] for h in range(1, 13)}
    houses[1].append(('Asc', positions['lagna'].short() if mode == 'd1' else None, 'lagna'))
    for name in GRAHAS:
        body = chart['planets'][name]
        houses[body[key]].append((DISPLAY[name][1], positions[name].short() if mode == 'd1' else None, 'graha'))
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
    d.kicker(W / 2, H - 162, 'Vedic birth chart', 'primary_text', 'center', 8.4)
    d.text(W / 2, H - 214, 'Janma Kundali', 46, 'HeadBold', 'primary', 'center')
    d.line(W / 2 - 70, H - 236, W / 2 - 10, H - 236, 'accent', 0.8)
    d.diamond(W / 2, H - 236, 3.2)
    d.line(W / 2 + 10, H - 236, W / 2 + 70, H - 236, 'accent', 0.8)
    d.text(W / 2, H - 258, 'D1 Lagna and D9 Navamsa charts, planetary positions and houses',
           10.5, 'Body', 'muted', 'center')
    # Emblem: this chart's own house and Rashi layout.
    size = 216
    houses = {1: [('Asc', None, 'lagna')]}
    draw_chart(d, W / 2 - size / 2, H - 520, size, chart['lagna']['rashi'], houses, 'accent', emblem=True)
    d.text(W / 2, H - 546, f'Lagna  {chart["lagna"]["rashi"]}  ·  Moon Nakshatra  '
           f'{chart["moon_nakshatra"]["name"]}', 9, 'Medium', 'muted', 'center')
    # Birth panel.
    top, h = 262, 128
    d.rect(M + 12, top - h, CW - 24, h, fill='surface', stroke='accent', width=0.7, radius=8)
    col = (CW - 24) / 3
    fields = [
        ('Birthplace', place['name'], f'{place["region"]}, {place["country"]}'),
        ('Date of birth', _date_text(info['local_date']), 'Local civil date'),
        ('Time of birth', info['local_time'], f'UTC{info["utc_offset"]}  ·  {chart["birth"]["timezone"]}'),
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
        d.text(W / 2, y + 18, 'SAMPLE REPORT  ·  SYNTHETIC BIRTH DETAILS, NOT A REAL PERSON',
               MIN_TEXT, 'Strong', 'primary_text', 'center')
    d.text(W / 2, y, 'A calculation summary of the birth chart. It is not a prediction or professional advice.',
           8.6, 'Body', 'muted', 'center')
    d.text(W / 2, 52, 'sabpuja.com', 8.4, 'Strong', 'primary_text', 'center')


def _page_overview(d, response, positions):
    chart = response['chart']
    _header(d, 'overview')
    y = _title(d, 'overview', 'Your Kundali at a glance',
               'The main placements calculated for this birth, followed by a guide to every section. '
               'Each value below is repeated with its full precision on the page shown.')
    pl = chart['planets']
    cards = [
        ('D1 Lagna', chart['lagna']['rashi'], f'{positions["lagna"].dms()} within the Rashi', PAGE_OF['positions']),
        ('Moon Rashi', pl['moon']['rashi'], f'{positions["moon"].dms()}  ·  D1 house {pl["moon"]["whole_sign_house"]}', PAGE_OF['positions']),
        ('Moon Nakshatra', chart['moon_nakshatra']['name'], f'Pada {chart["moon_nakshatra"]["pada"]} of 4', PAGE_OF['positions']),
        ('Sun Rashi', pl['sun']['rashi'], f'{positions["sun"].dms()}  ·  D1 house {pl["sun"]["whole_sign_house"]}', PAGE_OF['positions']),
        ('D9 Lagna', chart['d9']['lagna_rashi'], 'Navamsa house 1', PAGE_OF['d9']),
        ('Calculation', 'Lahiri sidereal', 'Whole-sign houses  ·  mean Rahu', PAGE_OF['method']),
    ]
    cw, ch, gap = (CW - 2 * 12) / 3, 84, 12
    top = y - 6
    for i, (label, value, sub, page) in enumerate(cards):
        x = M + (i % 3) * (cw + gap)
        yy = top - (i // 3) * (ch + gap) - ch
        _card(d, x, yy, cw, ch)
        d.rect(x, yy + ch - 3, cw, 3, fill='accent')
        d.kicker(x + 14, yy + ch - 22, label, 'primary_text')
        d.text(x + cw - 14, yy + ch - 22, f'p. {page}', MIN_TEXT, 'Medium', 'muted', 'right')
        d.fitted(x + 14, yy + ch - 47, value, cw - 28, 16, 'Head', 'ink', minimum=11, max_lines=1)
        d.fitted(x + 14, yy + 15, sub, cw - 28, 8.6, 'Body', 'muted', minimum=MIN_TEXT, max_lines=1)
    y = top - 2 * (ch + gap) - 22
    d.text(M, y, 'In this report', 15, 'Head', 'ink')
    y -= 12
    d.line(M, y, W - M, y, 'accent', 0.8)
    for key, title, desc in PAGES[1:]:
        n = PAGE_OF[key]
        y -= 34
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
    y = _title(d, 'guide', 'How to read this report',
               'A short reference for the terms used on the following pages. These are definitions of how '
               'the report is laid out, not interpretations of the chart.')
    terms = [
        ('Rashi', 'One of the twelve 30° signs of the sidereal zodiac, counted from Mesha (1) to Meena (12).'),
        ('Graha', 'A body placed in the chart: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, and the lunar nodes Rahu and Ketu.'),
        ('Lagna', 'The Rashi rising on the eastern horizon at the birth time and place. It is house 1 and is marked Asc.'),
        ('D1 chart', 'The Rashi chart. Each graha is shown in the Rashi it occupies; houses are counted from the Lagna.'),
        ('D9 chart', 'The Navamsa divisional chart: each Rashi is divided into nine parts of 3°20′. Placements come from the engine.'),
        ('Whole-sign house', 'A house is one whole Rashi. House 1 is the Lagna Rashi, house 2 the next Rashi, and so on.'),
        ('Nakshatra and Pada', 'One of 27 equal lunar mansions of 13°20′, each in four Padas. Shown here for the Moon.'),
    ]
    tw = 118
    for term, text in terms:
        d.text(M, y, term, 9.8, 'Strong', 'primary_text')
        y2 = d.wrap(M + tw, y, text, CW - tw, 9.2, 13.4, 'Body', 'ink', max_lines=3)
        rule = y2 + 13.4 - 8
        d.line(M, rule, W - M, rule, 'rule', 0.5)
        y = rule - 16
    y -= 8
    sun, pos = chart['planets']['sun'], positions['sun']
    example = (f'An absolute sidereal longitude counts from 0° Mesha around the full 360° circle. '
               f'The sign-relative form names the Rashi and the distance into it. In this chart the Sun is at '
               f'{sun["longitude_deg"]:.8f}° absolute, which is {pos.dms()} within {sun["rashi"]} '
               f'(Rashi {pos.rashi_number}, which begins at {30 * (pos.rashi_number - 1)}°). Within-sign values are '
               f'truncated to whole arc-seconds, never rounded up, so a graha is never shown past the edge of its Rashi.')
    y = _note(d, M, y, CW, 'Absolute and sign-relative longitude', example) - 22
    # Rashi reference and abbreviations side by side.
    d.text(M, y, 'Rashis', 12, 'Head', 'ink')
    d.text(M + 300, y, 'Chart abbreviations', 12, 'Head', 'ink')
    y -= 10
    d.line(M, y, M + 280, y, 'accent', 0.8)
    d.line(M + 300, y, W - M, y, 'accent', 0.8)
    for i, sign in enumerate(layout.SIGNS):
        col, row = divmod(i, 6)
        x = M + col * 140
        yy = y - 18 - row * 17.5
        d.text(x, yy, f'{i + 1:>2}', 8.6, 'Strong', 'primary_text')
        d.text(x + 18, yy, sign, 9, 'Medium', 'ink')
        d.text(x + 18 + d.width(sign, 'Medium', 9) + 5, yy, layout.SIGN_ENGLISH[i], MIN_TEXT, 'Body', 'muted')
    abbr = [('Asc', 'Lagna')] + [(DISPLAY[n][1], DISPLAY[n][0]) for n in GRAHAS]
    for i, (a, name) in enumerate(abbr):
        col, row = divmod(i, 5)
        x = M + 300 + col * 98
        yy = y - 18 - row * 21
        d.rect(x, yy - 4.6, 26, 15, fill='tint', radius=3)
        d.text(x + 13, yy, a, MIN_TEXT, 'Strong', 'primary_text', 'center')
        d.text(x + 32, yy, name, 9, 'Medium', 'ink')
    d.wrap(M + 300, y - 18 - 5 * 21 + 4, 'English sign names are conventional equivalents for the sidereal Rashis.',
           W - M - (M + 300), MIN_TEXT, 10.5, 'Body', 'muted', max_lines=2)


def _page_birth(d, response, positions):
    chart, info = response['chart'], response['input']
    place, birth, meta = info['place'], chart['birth'], chart['calculation_metadata']
    _header(d, 'birth')
    y = _title(d, 'birth', 'Birth details',
               'The birth record exactly as the chart was calculated. Please check these values against the '
               'birth record before reading the charts: every placement depends on them.')
    utc = birth['utc'].replace('T', '  ').replace('Z', '  UTC')
    rows = [
        ('Birthplace', place['name']),
        ('Region and country', f'{place["region"]}, {place["country"]}'),
        ('Latitude', layout.coordinate(birth['latitude'], 'N', 'S')),
        ('Longitude', layout.coordinate(birth['longitude'], 'E', 'W')),
        ('Local date', f'{_date_text(info["local_date"])}  ({info["local_date"]})'),
        ('Local time', info['local_time']),
        ('Time zone (IANA)', birth['timezone']),
        ('UTC offset applied', 'UTC' + info['utc_offset']),
        ('Exact UTC instant', utc),
    ]
    conv = meta['conventions']
    rows2 = [
        ('Zodiac', 'Sidereal'),
        ('Ayanamsa', f'{conv["ayanamsa"]["name"]} (Chitrapaksha)' if conv['ayanamsa']['name'] == 'Lahiri' else conv['ayanamsa']['name']),
        ('Positions', 'Geocentric, apparent'),
        ('Lunar nodes', 'Mean Rahu; Ketu exactly opposite'),
        ('Houses', 'Whole-sign, D1 and D9'),
        ('Ephemeris', f'Swiss Ephemeris {meta["swiss_ephemeris"]["library_version"]}, local files'),
        ('Ephemeris data', 'Verified by SHA-256 before calculation' if meta['ephemeris_data'].get('verified_before_calculation') else 'Not verified'),
        ('Time zone data', f'tzdata {meta["timezone_data"]["package_version"]} (IANA {meta["timezone_data"]["iana_version"]})'),
        ('Place source', place.get('source', 'Not supplied')),
    ]
    half = CW / 2 - 8
    top = y
    left = _kv_layout(d, rows, half - 32, 10.8, MIN_TEXT)
    right = _kv_layout(d, rows2, half - 32, 10.2, MIN_TEXT)
    height = 38 + max(sum(h for *_, h in left), sum(h for *_, h in right))
    for x, title, items in ((M, 'Birth record', left), (M + half + 16, 'Calculation context', right)):
        _card(d, x, top - height, half, height)
        d.kicker(x + 16, top - 22, title, 'primary_text')
        ry = top - 28
        for i, (label, lines, size, h) in enumerate(items):
            ry -= h
            d.text(x + 16, ry + h - 13, label, MIN_TEXT, 'Medium', 'muted')
            yy = ry + h - 26
            for line in lines:
                d.text(x + 16, yy, line, size, 'Strong', 'ink')
                yy -= 11
            if i < len(items) - 1:
                d.line(x + 16, ry + 1, x + half - 16, ry + 1, 'rule', 0.5)
    y = top - height - 24
    resolution = info.get('offset_resolution')
    offset_text = ('The local time occurs once at this place, so exactly one UTC offset applies.' if resolution == 'unique'
                   else 'The local time occurs twice at this place; the occurrence chosen with the request was used.'
                   if resolution == 'user_selected_repeated_hour' else 'The UTC offset was supplied with the request.')
    y = _note(d, M, y, CW, 'How the time was converted',
              f'The local civil time is read in the IANA time zone {birth["timezone"]}. {offset_text} '
              'No time, place or time zone is guessed: an unknown or impossible birth time is refused instead '
              'of being charted. Coordinates are the reference point of the chosen city.') - 14
    d.wrap(M, y, 'Technical details of the method, data versions and validation status are on page '
           f'{PAGE_OF["method"]}.', CW, 8.4, 12, 'Body', 'muted')


def _page_chart(d, response, positions, mode):
    chart = response['chart']
    key = 'd1' if mode == 'd1' else 'd9'
    _header(d, key)
    if mode == 'd1':
        lagna = chart['lagna']['rashi']
        y = _title(d, key, 'D1 Lagna chart',
                   'The birth chart in North Indian form. The top diamond is house 1, the Lagna; houses follow '
                   'counter-clockwise. Numbers give the Rashi in each house.')
    else:
        lagna = chart['d9']['lagna_rashi']
        y = _title(d, key, 'D9 Navamsa chart',
                   'The Navamsa chart in the same North Indian form. House 1 is the D9 Lagna; every graha is '
                   'placed in the D9 house reported by the engine.')
    size = 404
    x0 = (W - size) / 2
    y0 = y - 14 - size
    tokens = _chart_tokens(chart, positions, mode)
    d.chart_boxes[mode] = {'origin': (x0, y0), 'size': size, 'lagna': lagna,
                           'labels': draw_chart(d, x0, y0, size, lagna, tokens)}
    # Key band.
    y = y0 - 30
    lag_label = 'Lagna (Asc)' if mode == 'd1' else 'D9 Lagna (Asc)'
    d.kicker(M, y, lag_label, 'primary_text')
    if mode == 'd1':
        lagna_value = f'{lagna}  ·  {positions["lagna"].dms()} within the Rashi  ·  house 1 (shaded)'
    else:
        lagna_value = f'{lagna}  ·  Rashi {layout.SIGNS.index(lagna) + 1}  ·  house 1 (shaded)'
    d.text(M + 110, y, lagna_value, 9.8, 'Strong', 'ink')
    y -= 22
    d.kicker(M, y, 'Abbreviations', 'primary_text')
    x = M + 110
    for name in GRAHAS:
        full, abbr = DISPLAY[name]
        item = d.width(abbr, 'Strong', 8.6) + 4 + d.width(full, 'Body', 8.6) + 13
        if x + item > W - M:
            y -= 15
            x = M + 110
        d.text(x, y, abbr, 8.6, 'Strong', 'primary_text')
        d.text(x + d.width(abbr, 'Strong', 8.6) + 4, y, full, 8.6, 'Body', 'ink')
        x += item
    y -= 26
    if mode == 'd1':
        body = ('Small figures beside each graha are whole degrees within its Rashi, truncated. Exact values, to the '
                f'arc-second and as absolute longitude, are in Planetary positions on page {PAGE_OF["positions"]}. '
                f'The Rashi and house of every graha are as calculated by the Sabpuja engine.')
    else:
        body = ('The D9 chart shows Navamsa Rashis and houses only; degrees are not shown because the engine reports '
                f'D9 placements, not D9 longitudes. The table on page {PAGE_OF["navamsa"]} lists the same placements, '
                'and each graha in this chart was checked against the engine D9 house list before drawing.')
    _note(d, M, y, CW, 'Reading this chart', body)


def _page_positions(d, response, positions):
    chart = response['chart']
    pl = chart['planets']
    _header(d, 'positions')
    y = _title(d, 'positions', 'Planetary positions',
               'Each graha with its D1 Rashi, whole-sign house and position. The within-Rashi column is the '
               'readable form; the sidereal longitude is the engine value at its full printed precision.')
    columns = [('Graha', 116, 'left'), ('D1 Rashi', 104, 'left'), ('House', 52, 'center'),
               ('Within Rashi', 92, 'right'), ('Sidereal longitude', 135, 'right')]
    lag = chart['lagna']
    rows = [[_graha_cell('Lagna', 'Asc'), _rashi_cell(lag['rashi'], 'Strong', 'primary_text'),
             _cell('1', 'Strong', 'primary_text'), _cell(positions['lagna'].dms(), 'Medium'),
             _cell(f'{lag["longitude_deg"]:.8f}°', 'Body', 'muted', 9.2)]]
    for name in GRAHAS:
        body = pl[name]
        rows.append([_graha_cell(*DISPLAY[name]), _rashi_cell(body['rashi']),
                     _cell(str(body['whole_sign_house']), 'Strong', 'primary_text'),
                     _cell(positions[name].dms(), 'Medium'),
                     _cell(f'{body["longitude_deg"]:.8f}°', 'Body', 'muted', 9.2)])
    y = _table(d, M, y - 4, columns, rows, row_h=34, header_h=28) - 20
    moon = chart['moon_nakshatra']
    _card(d, M, y - 52, CW, 52, 'surface')
    d.rect(M, y - 52, 3, 52, fill='accent')
    d.kicker(M + 16, y - 18, 'Moon Nakshatra and Pada', 'primary_text')
    d.text(M + 16, y - 38, moon['name'], 14, 'Head', 'ink')
    d.text(M + 16 + d.width(moon['name'], 'Head', 14) + 12, y - 38, f'Pada {moon["pada"]}', 11, 'Strong', 'primary_text')
    d.wrap(M + 250, y - 22, 'Nakshatra is reported by the engine for the Moon only, so it is not shown for other grahas.',
           CW - 266, 8.2, 11.5, 'Body', 'muted', max_lines=3)
    y -= 72
    _note(d, M, y, CW, 'Notes on these values',
          'Within-Rashi values are the sidereal longitude minus the start of the engine-reported Rashi, truncated to '
          'whole arc-seconds. Rahu is the mean lunar node; Ketu is exactly opposite the unrounded Rahu. Retrograde '
          'motion, dignity and strength are not calculated in this edition and are not shown.')


def _page_navamsa(d, response, positions):
    chart = response['chart']
    pl = chart['planets']
    _header(d, 'navamsa')
    y = _title(d, 'navamsa', 'Navamsa placements',
               'The D9 Rashi and D9 whole-sign house of each graha, as returned by the engine. The D1 Rashi is '
               'repeated for comparison.')
    columns = [('Graha', 140, 'left'), ('D1 Rashi', 125, 'left'), ('D9 Rashi', 125, 'left'), ('D9 house', 109, 'center')]
    l9 = chart['d9']['lagna_rashi']
    rows = [[_graha_cell('Lagna', 'Asc'), _rashi_cell(chart['lagna']['rashi']),
             _rashi_cell(l9, 'Strong', 'primary_text'), _cell('1', 'Strong', 'primary_text')]]
    for name in GRAHAS:
        body = pl[name]
        rows.append([_graha_cell(*DISPLAY[name]), _rashi_cell(body['rashi']),
                     _rashi_cell(body['navamsa_rashi'], 'Strong'),
                     _cell(str(body['navamsa_whole_sign_house']), 'Strong', 'primary_text')])
    y = _table(d, M, y - 4, columns, rows, row_h=38, header_h=28) - 24
    _note(d, M, y, CW, 'About the D9 placements',
          f'The D9 Lagna is {l9}, so D9 house 1 is {l9} and the houses continue in Rashi order. Each graha\'s D9 '
          'Rashi and house in this table were checked against the engine D9 house list before the report was '
          f'drawn. The chart on page {PAGE_OF["d9"]} shows the same placements.')


def _page_houses(d, response, positions):
    chart = response['chart']
    pl = chart['planets']
    _header(d, 'houses')
    y = _title(d, 'houses', 'Twelve-house directory',
               'One row per house position. The D1 columns repeat the D1 chart and the D9 columns the D9 chart, '
               'so the Rashi and the grahas of any house can be read in one line.')
    l1 = layout.SIGNS.index(chart['lagna']['rashi'])
    l9 = layout.SIGNS.index(chart['d9']['lagna_rashi'])
    d1 = {h: [] for h in range(1, 13)}
    d9 = {h: [] for h in range(1, 13)}
    for name in GRAHAS:
        d1[pl[name]['whole_sign_house']].append(DISPLAY[name][1])
        d9[pl[name]['navamsa_whole_sign_house']].append(DISPLAY[name][1])
    # Same membership as the engine's own D9 list (already enforced in validation).
    for row in chart['d9']['houses']:
        if sorted(DISPLAY[n][1] for n in row['grahas']) != sorted(d9[row['house']]):
            raise layout.ReportDataError('D9 house directory disagrees with engine D9 houses')
    columns = [('House', 52, 'center'), ('D1 Rashi', 106, 'left'), ('D1 grahas', 128, 'left'),
               ('D9 Rashi', 106, 'left'), ('D9 grahas', 107, 'left')]
    rows = []
    for h in range(1, 13):
        g1 = (['Asc'] if h == 1 else []) + d1[h]
        g9 = (['Asc'] if h == 1 else []) + d9[h]
        rows.append([_cell(str(h), 'Head', 'primary_text', 11), _rashi_cell(layout.SIGNS[(l1 + h - 1) % 12]),
                     _members_cell(g1), _rashi_cell(layout.SIGNS[(l9 + h - 1) % 12]), _members_cell(g9)])
    y = _table(d, M, y - 4, columns, rows, row_h=34, header_h=28) - 22
    _note(d, M, y, CW, 'Reading key',
          'House numbers count from each chart\'s own Lagna: D1 house 1 is the D1 Lagna Rashi and D9 house 1 the D9 '
          'Lagna Rashi, so the same house number usually holds different Rashis in the two charts. Each Rashi is shown '
          'with its number (1 Mesha to 12 Meena). A dash means no graha occupies that house. Abbreviations are listed '
          f'on page {PAGE_OF["guide"]}. This directory describes placements only; it does not interpret them.')


def _page_method(d, response, positions):
    chart = response['chart']
    meta = chart['calculation_metadata']
    _header(d, 'method')
    y = _title(d, 'method', 'Methodology and provenance',
               'How the positions in this report were calculated, where the data comes from, and what the '
               'report does and does not claim.')
    eph = meta['ephemeris_data']
    swiss = meta['swiss_ephemeris']
    tz = meta['timezone_data']
    rows = [
        ('Sidereal zodiac', meta['conventions']['ayanamsa']['definition']),
        ('Lunar nodes', 'Mean node for Rahu; Ketu exactly opposite the unrounded Rahu longitude.'),
        ('Houses', 'Whole-sign houses for D1 and D9: house = Rashi count from the Lagna Rashi.'),
        ('Precision', 'Absolute longitudes are printed to eight decimals. Positions within a Rashi are truncated to the arc-second. Rashi, Navamsa, Nakshatra, Pada and houses are classified from unrounded longitudes.'),
        ('Ephemeris', f'Swiss Ephemeris {swiss["library_version"]} via pyswisseph {swiss["python_binding_version"]}, '
                      f'local files {", ".join(f["name"] for f in eph["required_files"])} '
                      f'(source commit {eph["source_commit"][:12]}), checked by SHA-256 before calculation.'),
        ('Time zones', f'IANA time zone database {tz["iana_version"]} from tzdata {tz["package_version"]}, checked by SHA-256.'),
        ('Engine output', f'Chart schema {chart["schema_version"]}; {meta["metadata_schema"]}.'),
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
    y = _note(d, M, y, CW, f'Validation status: {status}',
              'The engine\'s calculations are checked by its own conformance tests against Swiss Ephemeris. They '
              'have not yet been certified against an independent set of golden reference charts. ' +
              (f'Engine claim boundary: {boundary}.' if boundary else '')) - 18
    half = CW / 2 - 10
    d.text(M, y, 'Included in this report', 11, 'Head', 'ink')
    d.text(M + half + 20, y, 'Not included in this edition', 11, 'Head', 'ink')
    inc = ['D1 Lagna and D9 Navamsa charts', 'Sidereal longitudes of nine grahas and the Lagna',
           'D1 and D9 whole-sign houses', 'Moon Nakshatra and Pada', 'Birth time conversion and data provenance']
    exc = ['Panchanga, Vimshottari Dasha and other timing', 'Other divisional charts, Yogas, Doshas and strengths',
           'Retrograde status and dignities', 'Interpretations, predictions and remedies', 'Hindi edition']
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
    d.kicker(M, y - 8, 'Source and licences', 'primary_text')
    d.wrap(M, y - 22,
           'Sabpuja Kundali Engine source: github.com/sabpuja/Sabpuja-Kundali-Engine (AGPL-3.0). Swiss Ephemeris is '
           'used under its AGPL licence option. Time zone data: IANA tz database (public domain) via the tzdata '
           'package (Apache-2.0). Place coordinates: GeoNames (CC BY 4.0), cross-checked with Natural Earth. '
           'Typefaces: Poppins and Inter (SIL Open Font License 1.1).',
           CW, MIN_TEXT, 11, 'Body', 'muted', max_lines=5)


def _new_page(d):
    d.page += 1
    if d.page > 1:
        d.c.showPage()


def generate(response: dict, synthetic: bool = False, palette: str | None = None) -> bytes:
    """Searchable A4 PDF in memory. Writes no file, keeps no copy and makes no network request."""
    return render(response, synthetic, palette)[0]


def render(response: dict, synthetic: bool = False, palette: str | None = None):
    """generate() plus an audit of where chart labels were drawn, for the report tests."""
    response = copy.deepcopy(response)
    positions = validate(response)
    pal = Palette(palette or THEMES['default_palette'])
    cmaps = _register_fonts()
    drawing = _logo_drawing()
    memory = io.BytesIO()
    c = canvas.Canvas(memory, pagesize=A4, pageCompression=1, invariant=1, initialFontName='SP2-Body')
    c.setTitle('Sabpuja Janma Kundali')
    c.setAuthor('Sabpuja')
    c.setSubject('Vedic birth chart: D1 and D9')
    c.setCreator('Sabpuja Kundali report generator')
    c.setKeywords('')
    d = Doc(c, pal, cmaps, synthetic)
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
    for draw in pages:
        _new_page(d)
        draw(d, response, positions)
    c.save()
    data = memory.getvalue()
    if len(data) > MAX_PDF_BYTES:
        raise RuntimeError('controlled PDF size exceeded')
    return data, {'charts': d.chart_boxes, 'palette': pal.name}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Render the Phase 2A premium Kundali PDF from an engine response.')
    parser.add_argument('chart_json')
    parser.add_argument('output_pdf')
    parser.add_argument('--sample', action='store_true', help='mark the report as synthetic sample data')
    parser.add_argument('--palette', choices=sorted(THEMES['palettes']), default=THEMES['default_palette'])
    args = parser.parse_args()
    response = json.loads(Path(args.chart_json).read_text())
    Path(args.output_pdf).write_bytes(generate(response, synthetic=args.sample, palette=args.palette))
