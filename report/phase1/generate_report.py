"""Sabpuja Phase 1 Kundali PDF: schema 0.3.0 display only; no new astrology calculation."""
from __future__ import annotations
import io
import json
import math
from pathlib import Path

from fontTools.ttLib import TTFont as FontToolsTTFont
from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from svglib.svglib import svg2rlg

ROOT = Path(__file__).resolve().parent
THEME = json.loads((ROOT / 'theme.json').read_text())
COL = {k: HexColor(v) for k, v in THEME['colors'].items()}
W, H = A4
PAD = 44
CW = W - PAD * 2
NAMES = {
    'sun': ('Sun', 'Su'), 'moon': ('Moon', 'Mo'), 'mars': ('Mars', 'Ma'),
    'mercury': ('Mercury', 'Me'), 'jupiter': ('Jupiter', 'Ju'),
    'venus': ('Venus', 'Ve'), 'saturn': ('Saturn', 'Sa'),
    'rahu_mean': ('Rahu (mean)', 'Ra'), 'ketu_mean': ('Ketu (mean)', 'Ke'),
}
SIGNS = ['Mesha', 'Vrishabha', 'Mithuna', 'Karka', 'Simha', 'Kanya',
         'Tula', 'Vrischika', 'Dhanu', 'Makara', 'Kumbha', 'Meena']

# Fixed North Indian house geometry copied from reviewed prototype chart.js.
HOUSES = [None,
 ((300,0),(450,150),(300,300),(150,150)), ((0,0),(300,0),(150,150)),
 ((0,0),(150,150),(0,300)), ((0,300),(150,150),(300,300),(150,450)),
 ((0,300),(150,450),(0,600)), ((0,600),(150,450),(300,600)),
 ((300,600),(150,450),(300,300),(450,450)), ((300,600),(450,450),(600,600)),
 ((600,600),(450,450),(600,300)), ((600,300),(450,450),(300,300),(450,150)),
 ((600,300),(450,150),(600,0)), ((600,0),(450,150),(300,0))]
SIGN_POS = [None,(300,250),(150,125),(125,150),(250,300),(125,450),
 (150,475),(300,350),(450,475),(475,450),(350,300),(475,150),(450,125)]
LABEL_POS = [None,(300,130),(150,42),(43,150),(140,290),(43,450),
 (150,555),(300,465),(450,555),(557,450),(460,290),(557,150),(450,42)]

def _fonts():
    """Embed real approved Poppins and Inter; fail closed rather than using a fallback."""
    srcdir = ROOT.parents[1] / 'prototype/kundali_prototype/static/fonts'
    fonts = {
        'Body': 'inter-latin-400-normal.woff2',
        'Strong': 'inter-latin-600-normal.woff2',
        'Heading': 'poppins-latin-600-normal.woff2',
    }
    for name, file in fonts.items():
        font_name = 'SP-' + name
        if font_name in pdfmetrics.getRegisteredFontNames():
            continue
        path = srcdir / file
        if not path.is_file():
            raise RuntimeError('Required approved brand font missing: ' + file)
        font = FontToolsTTFont(str(path))
        font.flavor = None
        output = io.BytesIO()
        font.save(output)
        output.seek(0)
        pdfmetrics.registerFont(TTFont(font_name, output))

def validate_engine_response(result):
    if not isinstance(result, dict) or not isinstance(result.get('chart'), dict) or not isinstance(result.get('input'), dict):
        raise ValueError('Complete engine response required')
    chart = result['chart']
    if chart.get('schema_version') != '0.3.0' or chart.get('validation_status') != 'UNVERIFIED_GOLDEN_CHARTS':
        raise ValueError('Expected current chart schema and unverified accuracy status')
    pl = chart.get('planets')
    d9 = chart.get('d9')
    if not isinstance(pl, dict) or set(pl) != set(NAMES) or not isinstance(d9, dict):
        raise ValueError('Complete nine-body and D9 data required')
    if d9.get('house_system') != 'whole_sign' or not isinstance(d9.get('houses'), list) or len(d9['houses']) != 12:
        raise ValueError('Invalid D9 house structure')
    lagna = chart.get('lagna')
    if not isinstance(lagna, dict) or lagna.get('rashi') not in SIGNS or lagna.get('navamsa_rashi') not in SIGNS:
        raise ValueError('Lagna missing or unknown')
    if d9.get('lagna_rashi') != lagna['navamsa_rashi']:
        raise ValueError('D9 Lagna mismatch')
    i1 = SIGNS.index(lagna['rashi'])
    i9 = SIGNS.index(d9['lagna_rashi'])
    seen = set()
    for i, row in enumerate(d9['houses']):
        if not isinstance(row, dict) or row.get('house') != i + 1 or row.get('rashi') != SIGNS[(i9 + i) % 12]:
            raise ValueError('Incorrect D9 house numbering or sign')
        members = row.get('grahas')
        if not isinstance(members, list):
            raise ValueError('D9 grahas must be a list')
        for name in members:
            if name not in pl or name in seen:
                raise ValueError('Duplicated or unknown D9 graha')
            seen.add(name)
            if pl[name].get('navamsa_whole_sign_house') != i + 1 or pl[name].get('navamsa_rashi') != row['rashi']:
                raise ValueError('D9 field disagreement')
    if seen != set(pl):
        raise ValueError('Incomplete D9 graha house membership')
    for name, body in pl.items():
        h1 = body.get('whole_sign_house')
        h9 = body.get('navamsa_whole_sign_house')
        lon = body.get('longitude_deg')
        if type(h1) is not int or not 1 <= h1 <= 12 or type(h9) is not int or not 1 <= h9 <= 12:
            raise ValueError('House outside 1 to 12')
        if SIGNS[(i1 + h1 - 1) % 12] != body.get('rashi'):
            raise ValueError('D1 house/sign disagreement')
        if SIGNS[(i9 + h9 - 1) % 12] != body.get('navamsa_rashi'):
            raise ValueError('D9 house/sign disagreement')
        if isinstance(lon, bool) or not isinstance(lon, (float, int)) or not math.isfinite(lon) or not 0 <= lon < 360:
            raise ValueError('Invalid planetary longitude')
    moon = chart.get('moon_nakshatra')
    if not isinstance(moon, dict) or not isinstance(moon.get('name'), str) or type(moon.get('pada')) is not int or not 1 <= moon['pada'] <= 4:
        raise ValueError('Moon Nakshatra/Pada missing')
    info = result['input']
    if not isinstance(info.get('place'), dict) or not info['place'].get('name') or not info.get('local_date') or not info.get('local_time'):
        raise ValueError('Complete birthplace and time required')
    if not isinstance(chart.get('birth'), dict) or not isinstance(chart.get('method'), dict):
        raise ValueError('Calculation provenance required')
    return result

def _text(c, x, y, text, size=10, face='Body', color='text'):
    c.setFillColor(COL[color]); c.setFont('SP-' + face, size); c.drawString(x, y, str(text))

def _right(c, x, y, text, size=10, face='Body', color='text'):
    c.setFillColor(COL[color]); c.setFont('SP-' + face, size); c.drawRightString(x, y, str(text))

def _center(c, x, y, text, size=10, face='Body', color='text'):
    c.setFillColor(COL[color]); c.setFont('SP-' + face, size); c.drawCentredString(x, y, str(text))

def _box(c, x, y, w, h, background='white', border='border', radius=12):
    c.setFillColor(COL[background]); c.setStrokeColor(COL[border]); c.setLineWidth(.65)
    c.roundRect(x, y, w, h, radius, stroke=1, fill=1)

def _wrapped(c, value, x, y, width, size=10, leading=16, face='Body', color='text'):
    for segment in simpleSplit(str(value), 'SP-' + face, size, width):
        _text(c, x, y, segment, size, face, color); y -= leading
    return y

def _line(c, x1, y1, x2, y2):
    c.setStrokeColor(COL['border']); c.setLineWidth(.65); c.line(x1, y1, x2, y2)

def _logo(c, x, y, width=132):
    # Approved October 2026 logo. No modifications or raster approximation.
    path = ROOT.parents[1] / 'prototype/kundali_prototype/static/brand/sabpuja-logo-horizontal-color.svg'
    if not path.is_file():
        raise RuntimeError('Approved logo missing from source checkout')
    drawing = svg2rlg(str(path))
    if drawing is None or not drawing.width:
        raise RuntimeError('Approved logo SVG cannot be rendered')
    scale = width / drawing.width
    c.saveState(); c.translate(x, y); c.scale(scale, scale)
    renderPDF.draw(drawing, c, 0, 0); c.restoreState()

def _background(c):
    c.setFillColor(COL['ivory']); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(COL['saffron']); c.rect(0, H - 7, W, 7, fill=1, stroke=0)

def _header(c, section, page):
    _background(c); _logo(c, PAD, H - 81, 104)
    _right(c, W - PAD, H - 60, 'JANAM KUNDALI  /  ' + section.upper(), 8, 'Strong', 'muted')
    _line(c, PAD, H - 95, W - PAD, H - 95)
    _line(c, PAD, 53, W - PAD, 53)
    _text(c, PAD, 35, 'SABPUJA  /  ENGINE-GENERATED REPORT', 7.4, 'Strong', 'muted')
    _right(c, W - PAD, 35, str(page).zfill(2) + ' / 08', 8, 'Strong', 'muted')

def _title(c, main, sub):
    _text(c, PAD, H - 140, main, 22, 'Heading')
    _wrapped(c, sub, PAD, H - 166, CW, 9.5, 15, 'Body', 'muted')

def _kv(c, x, y, title, value, width=202):
    _text(c, x, y, title.upper(), 8.2, 'Strong', 'muted')
    _wrapped(c, str(value), x, y - 20, width, 12, 18, 'Strong')

def _tag(c, x, y, value):
    width = pdfmetrics.stringWidth(value, 'SP-Strong', 8.5) + 22
    _box(c, x, y - 10, width, 24, 'cream', 'cream', 12)
    _text(c, x + 11, y - 2, value, 8.5, 'Strong', 'brown')

def _chart(c, x, y, size, lagna_sign, planets, mode):
    scale = size / 600
    _box(c, x - 8, y - 8, size + 16, size + 16)
    for house in range(1, 13):
        path = c.beginPath()
        for i, (xx, yy) in enumerate(HOUSES[house]):
            px, py = x + xx * scale, y + (600 - yy) * scale
            if i == 0: path.moveTo(px, py)
            else: path.lineTo(px, py)
        path.close(); c.setStrokeColor(COL['border']); c.setLineWidth(.8)
        c.drawPath(path, stroke=1, fill=0)
    start = SIGNS.index(lagna_sign)
    key = 'whole_sign_house' if mode == 'd1' else 'navamsa_whole_sign_house'
    for h in range(1, 13):
        xx, yy = SIGN_POS[h]
        _center(c, x + xx * scale, y + (600 - yy) * scale, str((start + h - 1) % 12 + 1), 8, 'Strong', 'saffron')
        labels = [NAMES[name][1] for name, body in planets.items() if body[key] == h]
        if h == 1: labels.insert(0, 'Asc')
        if not labels: continue
        cols = 2 if len(labels) > 3 else 1
        rows = math.ceil(len(labels) / cols)
        xx, yy = LABEL_POS[h]
        for idx, name in enumerate(labels):
            offset_x = (idx % cols - (cols - 1) / 2) * 36
            offset_y = ((rows - 1) / 2 - idx // cols) * 22
            _center(c, x + (xx + offset_x) * scale, y + (600 - (yy + offset_y)) * scale,
                    name, 9 if size >= 350 else 8, 'Strong', 'brown_deep')

def _next(c):
    c.showPage()

def generate(response: dict, synthetic: bool = False) -> bytes:
    """Produce an in-memory searchable PDF. Does not store or contact any external service."""
    validate_engine_response(response)
    _fonts()
    chart = response['chart']; person = response['input']; pl = chart['planets']
    place = person['place']['name']
    memory = io.BytesIO()
    c = canvas.Canvas(memory, pagesize=A4, pageCompression=1)
    c.setTitle('Sabpuja - Janam Kundali')
    c.setAuthor('Sabpuja')

    # 01 / Cover.
    _background(c); _logo(c, PAD, H - 120, 160)
    _tag(c, PAD, H - 203, 'ENGINE-GENERATED  /  SCHEMA 0.3.0')
    _text(c, PAD, H - 284, 'Your Janam', 34, 'Heading')
    _text(c, PAD, H - 330, 'Kundali', 42, 'Heading', 'saffron')
    _wrapped(c, 'Your birth-chart calculation, presented clearly and with the method recorded.',
             PAD, H - 371, 405, 13, 20, 'Body', 'muted')
    _box(c, PAD, 220, CW, 192, 'white', 'border', 18)
    _kv(c, PAD + 24, 373, 'Birth location', place, 220)
    _kv(c, PAD + 280, 373, 'Birth date', person['local_date'], 150)
    _kv(c, PAD + 24, 300, 'Birth time', person['local_time'], 170)
    _kv(c, PAD + 280, 300, 'Timezone', chart['birth']['timezone'], 150)
    _line(c, PAD, 181, W - PAD, 181)
    note = ('DEMONSTRATION ONLY - SYNTHETIC BIRTH DETAILS. ' if synthetic else '')
    note += 'This is a calculation summary, not a prediction or professional advice.'
    _wrapped(c, note, PAD, 163, CW, 9.5, 14, 'Strong', 'muted')
    _right(c, W - PAD, 36, 'SABPUJA  /  PHASE 1', 8, 'Strong', 'muted')
    _next(c)

    # 02 / Confirmed birth details.
    _header(c, 'Birth details', 2)
    _title(c, 'Birth details', 'Confirmed inputs and computation context. Values come from the chart engine.')
    items = [('Birthplace', place), ('Civil date', person['local_date']),
             ('Local time', person['local_time']), ('Time zone', chart['birth']['timezone']),
             ('Latitude', str(round(chart['birth']['latitude'], 5)) + ' deg'),
             ('Longitude', str(round(chart['birth']['longitude'], 5)) + ' deg'),
             ('UTC instant', chart['birth']['utc']), ('Output schema', '0.3.0')]
    for i, (label, value) in enumerate(items):
        x = PAD + (i % 2) * 260
        y = 560 - (i // 2) * 102
        _box(c, x, y, 246, 86)
        _kv(c, x + 16, y + 60, label, value, 210)
    _box(c, PAD, 118, CW, 68, 'cream')
    _wrapped(c, 'A chart is calculated only from an exact birth time and a supported birthplace. '
             'Phase 1 does not infer missing values.', PAD + 17, 160, CW - 34)
    _next(c)

    # 03 / D1.
    _header(c, 'D1 Rashi', 3)
    _title(c, 'D1 Lagna chart', 'North Indian whole-sign houses, with placements directly from the engine.')
    _chart(c, 120, 255, 350, chart['lagna']['rashi'], pl, 'd1')
    _tag(c, PAD, 210, 'LAGNA  /  ' + chart['lagna']['rashi'])
    _wrapped(c, 'Sign numbers correspond to the twelve Rashis. Grahas use their engine-reported '
             'house numbers; Asc marks the Lagna.', PAD, 171, CW, 9.2, 15, 'Body', 'muted')
    _next(c)

    # 04 / D9.
    _header(c, 'D9 Navamsa', 4)
    _title(c, 'D9 Navamsa chart', 'Whole-sign Navamsa houses counted from the engine-computed D9 Lagna.')
    _chart(c, 120, 255, 350, chart['d9']['lagna_rashi'], pl, 'd9')
    _tag(c, PAD, 210, 'D9 LAGNA  /  ' + chart['d9']['lagna_rashi'])
    _wrapped(c, 'D9 house signs and placements are cross-checked against d9.houses. '
             'This renderer performs no astronomical calculations.', PAD, 171, CW, 9.2, 15, 'Body', 'muted')
    _next(c)

    # 05 / Planet positions.
    _header(c, 'Planet positions', 5)
    _title(c, 'Planetary positions', 'Sidereal longitudes, D1 Rashis and engine-reported D1 whole-sign houses.')
    y = 615
    _box(c, PAD, y, CW, 37, 'cream', 'border', 9)
    for x, label in [(PAD + 13, 'GRAHA'), (PAD + 193, 'D1 RASHI'), (PAD + 352, 'HOUSE')]:
        _text(c, x, y + 13, label, 8.2, 'Strong', 'brown')
    for i, (name, (display, _)) in enumerate(NAMES.items()):
        body = pl[name]; yy = y - 56 - i * 45
        _box(c, PAD, yy, CW, 43, 'white', 'border', 8)
        _text(c, PAD + 13, yy + 25, display, 10, 'Strong')
        _text(c, PAD + 193, yy + 25, body['rashi'])
        _text(c, PAD + 352, yy + 25, body['whole_sign_house'], 11, 'Strong', 'saffron')
        _right(c, W - PAD - 14, yy + 11, f"{body['longitude_deg']:.5f} deg", 7.7, 'Body', 'muted')
    _wrapped(c, 'Rahu is the configured mean lunar node. Ketu is opposite the unrounded Rahu longitude.',
             PAD, 145, CW, 8.8, 14, 'Body', 'muted')
    _next(c)

    # 06 / D9 positions.
    _header(c, 'Navamsa placements', 6)
    _title(c, 'D9 planetary placements', 'D9 Rashis and whole-sign house positions returned by schema 0.3.0.')
    y = 615
    _box(c, PAD, y, CW, 37, 'cream', 'border', 9)
    for x, label in [(PAD + 13, 'GRAHA'), (PAD + 204, 'D9 RASHI'), (PAD + 376, 'D9 HOUSE')]:
        _text(c, x, y + 13, label, 8.2, 'Strong', 'brown')
    for i, (name, (display, _)) in enumerate(NAMES.items()):
        body = pl[name]; yy = y - 56 - i * 45
        _box(c, PAD, yy, CW, 43, 'white', 'border', 8)
        _text(c, PAD + 13, yy + 17, display, 10, 'Strong')
        _text(c, PAD + 204, yy + 17, body['navamsa_rashi'])
        _text(c, PAD + 376, yy + 17, body['navamsa_whole_sign_house'], 11, 'Strong', 'saffron')
    _wrapped(c, 'These placements are a direct display of authoritative calculation fields, '
             'not an interpretation.', PAD, 145, CW, 9, 14, 'Body', 'muted')
    _next(c)

    # 07 / Houses and Moon Nakshatra.
    _header(c, 'House directory', 7)
    _title(c, 'Twelve-house directory', 'Reference mapping of D1 and D9 signs, Moon Nakshatra and Pada.')
    moon = chart['moon_nakshatra']
    _box(c, PAD, 606, CW, 62, 'cream')
    _text(c, PAD + 16, 645, 'MOON NAKSHATRA', 8, 'Strong', 'muted')
    _text(c, PAD + 16, 622, moon['name'], 16, 'Heading')
    _right(c, W - PAD - 16, 626, 'Pada ' + str(moon['pada']), 12, 'Strong', 'saffron')
    l1 = SIGNS.index(chart['lagna']['rashi'])
    l9 = SIGNS.index(chart['d9']['lagna_rashi'])
    for i in range(12):
        x, y = PAD + (i % 2) * 260, 580 - (i // 2) * 68
        _box(c, x, y - 62, 246, 58)
        _text(c, x + 13, y - 20, f"HOUSE {i + 1:02d}", 8, 'Strong', 'saffron')
        _text(c, x + 13, y - 42, SIGNS[(l1 + i) % 12] + '  /  ' + SIGNS[(l9 + i) % 12], 9.6, 'Strong')
    _text(c, PAD, 133, 'FIRST RASHI / SECOND RASHI = D1 / D9', 8.4, 'Strong', 'muted')
    _next(c)

    # 08 / Method and limits.
    _header(c, 'Method and boundaries', 8)
    _title(c, 'Calculation methodology', 'Astronomical method and Phase 1 scope, without predictive claims.')
    method = chart['method']
    values = [('Sidereal method', method['ayanamsa']), ('Lunar nodes', method['nodes']),
              ('House model', method['houses']), ('Ephemeris', method['ephemeris'])]
    for i, (label, value) in enumerate(values):
        x = PAD + (i % 2) * 260; y = 607 - (i // 2) * 103
        _box(c, x, y - 78, 246, 88)
        _kv(c, x + 15, y - 17, label, value, 212)
    _text(c, PAD, 388, 'What this report includes', 13, 'Heading')
    _wrapped(c, 'D1 and D9 whole-sign charts, birth details, nine planetary placements, '
             'sidereal longitudes, Moon Nakshatra/Pada and calculation provenance.',
             PAD, 362, CW, 10, 17)
    _text(c, PAD, 295, 'What this report does not claim', 13, 'Heading')
    _wrapped(c, 'No Panchang, Vimshottari Dasha, Yoga/Dosha, gemstones, remedies, interpretations, '
             'strength scores or predictions are produced. Validation status: ' +
             chart['validation_status'] + '.', PAD, 269, CW, 10, 17)
    _line(c, PAD, 176, W - PAD, 176)
    _wrapped(c, 'Method: Lahiri, mean Rahu, opposite Ketu, Swiss Ephemeris with pinned local '
             'files. Every placement is supplied by the Sabpuja engine.',
             PAD, 153, CW, 8.7, 14, 'Body', 'muted')
    _wrapped(c, 'Source and licensing: github.com/sabpuja/Sabpuja-Kundali-Engine (AGPL-3.0); '
             'Swiss Ephemeris AGPL option; Poppins and Inter SIL OFL; GeoNames CC BY 4.0.',
             PAD, 106, CW - 10, 8, 12, 'Body', 'muted')
    _right(c, W - PAD, 83, 'sabpuja.com', 9, 'Strong', 'saffron')
    c.save()
    return memory.getvalue()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('chart_json')
    parser.add_argument('output_pdf')
    parser.add_argument('--sample', action='store_true')
    args = parser.parse_args()
    response = json.loads(Path(args.chart_json).read_text())
    Path(args.output_pdf).write_bytes(generate(response, synthetic=args.sample))
