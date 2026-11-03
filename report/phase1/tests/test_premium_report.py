"""Phase 2A premium report tests. Synthetic data only; PDFs are inspected and rendered with PyMuPDF.

Optional: SABPUJA_TEST_EPHE_PATH=/abs/ephe also re-runs every scenario through the engine and
requires the captured fixtures to be reproduced exactly (calculation preservation).
"""
import builtins
import copy
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent
PHASE = HERE.parent
REPO = PHASE.parents[1]
sys.path.insert(0, str(PHASE))
spec = importlib.util.spec_from_file_location('sabpuja_premium_report', PHASE / 'premium_report.py')
premium = importlib.util.module_from_spec(spec)
spec.loader.exec_module(premium)
layout = premium.layout
SCENARIO_DIR = HERE / 'fixtures/premium'
MANIFEST = json.loads((SCENARIO_DIR / 'manifest.json').read_text())
SCENARIOS = {c['id']: json.loads((SCENARIO_DIR / f'{c["id"]}.json').read_text()) for c in MANIFEST['cases']}
PHASE1_FIXTURE = json.loads((HERE / 'fixtures/synthetic-new-delhi.json').read_text())
PALETTES = ['baseline', 'od10-candidate']
W, H = premium.W, premium.H
_RENDERED = {}


def rendered(case, palette='od10-candidate'):
    key = (case, palette)
    if key not in _RENDERED:
        data, audit = premium.render(SCENARIOS[case], synthetic=True, palette=palette)
        _RENDERED[key] = (data, audit, fitz.open(stream=data, filetype='pdf'))
    return _RENDERED[key]


def all_rendered():
    for case in SCENARIOS:
        for palette in PALETTES:
            yield case, palette, *rendered(case, palette)


def rows(page):
    """Words grouped into table rows by baseline."""
    grouped = {}
    for x0, y0, x1, y1, word, *_ in page.get_text('words'):
        grouped.setdefault(round(y1), []).append((x0, word))
    merged = {}
    for y in sorted(grouped):
        target = next((k for k in merged if abs(k - y) <= 3), y)
        merged.setdefault(target, []).extend(grouped[y])
    return [' '.join(w for _, w in sorted(items)) for _, items in sorted(merged.items())]


def spans(page):
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            for span in line['spans']:
                if span['text'].strip():
                    yield span


def segment_hits_rect(seg, rect):
    """Liang-Barsky: does the segment pass through the rectangle's interior?"""
    ax, ay, bx, by = seg
    x0, y0, x1, y1 = rect
    if x1 <= x0 or y1 <= y0:
        return False
    dx, dy = bx - ax, by - ay
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
        if p == 0:
            if q <= 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 >= t1:
            return False
    return True


def point_in_polygon(x, y, poly):
    inside = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def crowded_response(house_sign_shift=0):
    """Synthetic layout stress record: eight grahas share one D1 house. Not an engine chart."""
    data = copy.deepcopy(SCENARIOS['s07-noon'])
    chart = data['chart']
    lagna = layout.SIGNS.index(chart['lagna']['rashi'])
    target = (lagna + house_sign_shift) % 12
    for i, name in enumerate(n for n in premium.GRAHAS if n != 'ketu_mean'):
        body = chart['planets'][name]
        body['rashi'] = layout.SIGNS[target]
        body['longitude_deg'] = round(30 * target + 1.5 + i * 3.4, 8)
        body['whole_sign_house'] = house_sign_shift + 1
    ketu = chart['planets']['ketu_mean']
    ketu['rashi'] = layout.SIGNS[(target + 6) % 12]
    ketu['longitude_deg'] = round(30 * ((target + 6) % 12) + 1.5 + 6 * 3.4, 8)
    ketu['whole_sign_house'] = (house_sign_shift + 6) % 12 + 1
    return data


class SignPositionTests(unittest.TestCase):
    """Degrees within the engine Rashi: truncation, boundaries, and refusal of disagreement."""

    def test_owner_example(self):
        self.assertEqual(layout.sign_position(48.2173, 'Vrishabha').dms(), '18°13′02″')

    def test_matches_exact_rational_arithmetic_for_every_scenario_value(self):
        for case, data in SCENARIOS.items():
            chart = data['chart']
            items = [(chart['lagna']['longitude_deg'], chart['lagna']['rashi'])]
            items += [(b['longitude_deg'], b['rashi']) for b in chart['planets'].values()]
            for lon, rashi in items:
                exact = Fraction(repr(lon)) - 30 * layout.SIGNS.index(rashi)
                self.assertTrue(0 <= exact < 30, case)
                seconds = math.floor(exact * 3600)
                pos = layout.sign_position(lon, rashi)
                self.assertEqual((pos.degrees * 3600 + pos.minutes * 60 + pos.seconds), seconds, (case, lon))
                self.assertEqual(pos.rashi, rashi)
                self.assertFalse(pos.at_display_boundary)

    def test_truncates_never_carries(self):
        self.assertEqual(layout.sign_position(59.9999999, 'Vrishabha').dms(), '29°59′59″')
        self.assertEqual(layout.sign_position(29.99999999, 'Mesha').dms(), '29°59′59″')
        self.assertEqual(layout.sign_position(30.0, 'Vrishabha').dms(), '0°00′00″')
        self.assertEqual(layout.sign_position(0.0, 'Mesha').dms(), '0°00′00″')
        self.assertEqual(layout.sign_position(359.99999999, 'Meena').dms(), '29°59′59″')

    def test_binary_float_does_not_lose_a_second(self):
        # 0.0175 deg is exactly 63 arc-seconds; float arithmetic gives 62.99999...
        self.assertEqual(layout.sign_position(0.0175, 'Mesha').seconds, 3)
        self.assertEqual(layout.sign_position(30.0175, 'Vrishabha').minutes, 1)
        self.assertEqual(layout.sign_position(120.5, 'Simha').dms(), '0°30′00″')

    def test_printed_value_on_boundary_keeps_engine_rashi(self):
        # The engine classifies unrounded values and prints 8 decimals, so 59.999999996 prints as 60.0.
        pos = layout.sign_position(60.0, 'Vrishabha')
        self.assertTrue(pos.at_display_boundary)
        self.assertEqual((pos.rashi, pos.dms()), ('Vrishabha', '29°59′59″'))
        pos = layout.sign_position(0.0, 'Meena')  # 360 is printed as 0
        self.assertTrue(pos.at_display_boundary)
        self.assertEqual(pos.dms(), '29°59′59″')

    def test_disagreement_with_engine_rashi_fails(self):
        for lon, rashi in [(30.00000001, 'Mesha'), (45.0, 'Mesha'), (29.9, 'Vrishabha'),
                           (0.00000001, 'Meena'), (359.0, 'Mesha'), (90.00000001, 'Mithuna'), (90.0, 'Vrishabha')]:
            with self.assertRaises(layout.ReportDataError, msg=(lon, rashi)):
                layout.sign_position(lon, rashi)

    def test_invalid_values_fail(self):
        for lon in [360.0, -0.0001, float('nan'), float('inf'), True, '12.0', None]:
            with self.assertRaises(layout.ReportDataError, msg=repr(lon)):
                layout.sign_position(lon, 'Mesha')
        with self.assertRaises(layout.ReportDataError):
            layout.sign_position(10.0, 'Aries')


class ChartLayoutTests(unittest.TestCase):

    def _widths(self, n, detail_chars=3):
        def widths(size, detail):
            return [size * (1.3 + (0.62 * detail_chars if detail else 0))] * n
        return widths

    def _assert_clean(self, house, placed):
        poly = layout.HOUSES[house]
        nx, ny = layout.number_position(house)
        for i, a in enumerate(placed):
            for corner in [(a.x, a.y), (a.x + a.width, a.y), (a.x, a.y + a.height), (a.x + a.width, a.y + a.height)]:
                self.assertTrue(point_in_polygon(*corner, poly), (house, a))
            # Rashi number keep-out.
            self.assertFalse(a.x - 12 < nx < a.x + a.width + 12 and a.y - 12 < ny < a.y + a.height + 12, (house, a))
            for b in placed[i + 1:]:
                e = 1e-6
                overlap = (a.x < b.x + b.width - e and b.x < a.x + a.width - e
                           and a.y < b.y + b.height - e and b.y < a.y + a.height - e)
                self.assertFalse(overlap, (house, a, b))

    def test_ten_labels_fit_every_house_at_print_size(self):
        for house in range(1, 13):
            placed = layout.layout_house(house, self._widths(10), 404 / 600)
            self.assertEqual(len(placed), 10)
            self.assertGreaterEqual(min(p.size for p in placed), 8, house)
            self._assert_clean(house, placed)

    def test_all_counts_every_house(self):
        for house in range(1, 13):
            for n in range(1, 11):
                self._assert_clean(house, layout.layout_house(house, self._widths(n), 404 / 600))

    def test_impossible_layout_raises(self):
        with self.assertRaises(layout.LayoutError):
            layout.layout_house(2, lambda size, detail: [400.0] * 3, 404 / 600)

    def test_rashi_numbers_inside_their_house(self):
        for house in range(1, 13):
            self.assertTrue(point_in_polygon(*layout.number_position(house), layout.HOUSES[house]))


class PremiumPDFTests(unittest.TestCase):

    def test_scenario_matrix_coverage(self):
        cases = MANIFEST['cases']
        self.assertGreaterEqual(len(cases), 12)
        self.assertEqual({c['d1_lagna'] for c in cases}, set(layout.SIGNS))
        self.assertGreaterEqual(len({c['d9_lagna'] for c in cases}), 8)
        self.assertGreaterEqual(len({c['request']['place_id'] for c in cases}), 6)
        self.assertGreaterEqual(max(c['max_d1_house'] for c in cases), 5)
        self.assertGreaterEqual(max(c['max_d9_house'] for c in cases), 4)
        dates = {c['request']['birth_date'] for c in cases}
        self.assertIn('1970-01-01', dates)
        self.assertIn('2100-12-31', dates)
        self.assertGreaterEqual(len({c['request']['birth_time'][:2] for c in cases}), 8)
        near = 0
        for data in SCENARIOS.values():
            for body in data['chart']['planets'].values():
                v = body['longitude_deg'] % 30
                near += v < 0.005 or v > 29.995
        self.assertGreaterEqual(near, 1)
        for data in SCENARIOS.values():
            self.assertTrue(data['input']['place']['id'].startswith('in-'))

    # 1, 2. Sections and generation.
    def test_all_sections_on_every_report(self):
        for case, palette, data, audit, pdf in all_rendered():
            self.assertTrue(data.startswith(b'%PDF-'))
            self.assertEqual(len(pdf), len(premium.PAGES), case)
            for number, (key, title, _) in enumerate(premium.PAGES, 1):
                text = pdf[number - 1].get_text()
                if key == 'cover':
                    self.assertIn('Janma Kundali', text)
                    continue
                self.assertIn(f'Page {number} of {len(premium.PAGES)}', text, (case, key))
                self.assertIn(title.upper(), text, (case, key))
            contents = pdf[1].get_text()
            for _, title, _ in premium.PAGES[1:]:
                self.assertIn(title, contents)
            self.assertEqual(audit['palette'], palette)

    def test_same_bytes_across_processes(self):
        # Embedded fonts must not carry the conversion time, so a checksum is reproducible.
        import subprocess
        code = ('import hashlib, json, sys; sys.path[:0] = [sys.argv[1]]; import premium_report as p; '
                'print(hashlib.sha256(p.generate(json.load(open(sys.argv[2])), synthetic=True)).hexdigest())')
        args = [sys.executable, '-c', code, str(PHASE), str(SCENARIO_DIR / 's11-afternoon.json')]
        first = subprocess.run(args, capture_output=True, text=True, check=True).stdout
        import time
        time.sleep(1.1)
        second = subprocess.run(args, capture_output=True, text=True, check=True).stdout
        self.assertRegex(first, r'^[0-9a-f]{64}\n$')
        self.assertEqual(first, second)

    def test_same_input_same_bytes(self):
        a = premium.generate(SCENARIOS['s01-first-supported-date'], synthetic=True)
        b = premium.generate(SCENARIOS['s01-first-supported-date'], synthetic=True)
        self.assertEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest())

    # 3. D1/D9 tables and charts match the engine JSON.
    def test_positions_table_matches_engine(self):
        for case in SCENARIOS:
            data, _, pdf = rendered(case)
            chart = SCENARIOS[case]['chart']
            table = rows(pdf[premium.PAGE_OF['positions'] - 1])
            for name in premium.GRAHAS:
                body = chart['planets'][name]
                full, abbr = premium.DISPLAY[name]
                row = next(r for r in table if r.startswith(f'{abbr} {full} '))
                pos = layout.sign_position(body['longitude_deg'], body['rashi'])
                expected = (f'{abbr} {full} {layout.SIGNS.index(body["rashi"]) + 1} {body["rashi"]} '
                            f'{body["whole_sign_house"]} {pos.dms()} {body["longitude_deg"]:.8f}°')
                self.assertEqual(row, expected, case)
                self.assertEqual(float(f'{body["longitude_deg"]:.8f}'), body['longitude_deg'], 'precision lost')
            lag = chart['lagna']
            row = next(r for r in table if r.startswith('Asc Lagna '))
            self.assertEqual(row, f'Asc Lagna {layout.SIGNS.index(lag["rashi"]) + 1} {lag["rashi"]} 1 '
                                  f'{layout.sign_position(lag["longitude_deg"], lag["rashi"]).dms()} '
                                  f'{lag["longitude_deg"]:.8f}°')

    def test_navamsa_table_matches_engine(self):
        for case in SCENARIOS:
            _, _, pdf = rendered(case)
            chart = SCENARIOS[case]['chart']
            d9_houses = {g: row['house'] for row in chart['d9']['houses'] for g in row['grahas']}
            table = rows(pdf[premium.PAGE_OF['navamsa'] - 1])
            for name in premium.GRAHAS:
                body = chart['planets'][name]
                full, abbr = premium.DISPLAY[name]
                row = next(r for r in table if r.startswith(f'{abbr} {full} '))
                self.assertEqual(d9_houses[name], body['navamsa_whole_sign_house'])
                self.assertEqual(row, f'{abbr} {full} {layout.SIGNS.index(body["rashi"]) + 1} {body["rashi"]} '
                                      f'{layout.SIGNS.index(body["navamsa_rashi"]) + 1} {body["navamsa_rashi"]} '
                                      f'{d9_houses[name]}', case)

    def test_house_directory_matches_engine(self):
        for case in SCENARIOS:
            _, _, pdf = rendered(case)
            chart = SCENARIOS[case]['chart']
            table = rows(pdf[premium.PAGE_OF['houses'] - 1])
            l1 = layout.SIGNS.index(chart['lagna']['rashi'])
            d9 = {row['house']: row for row in chart['d9']['houses']}
            for h in range(1, 13):
                d1_members = [premium.DISPLAY[n][1] for n in premium.GRAHAS if chart['planets'][n]['whole_sign_house'] == h]
                d9_members = [premium.DISPLAY[n][1] for n in premium.GRAHAS if n in d9[h]['grahas']]
                s1, s9 = layout.SIGNS[(l1 + h - 1) % 12], d9[h]['rashi']
                g1 = ' '.join((['Asc'] if h == 1 else []) + d1_members) or '–'
                g9 = ' '.join((['Asc'] if h == 1 else []) + d9_members) or '–'
                expected = f'{h} {layout.SIGNS.index(s1) + 1} {s1} {g1} {layout.SIGNS.index(s9) + 1} {s9} {g9}'
                self.assertIn(expected, table, (case, h))

    def test_chart_labels_drawn_in_engine_houses(self):
        """Every chart label found in the PDF lies inside the polygon of the engine's house."""
        for case in SCENARIOS:
            _, audit, pdf = rendered(case)
            chart = SCENARIOS[case]['chart']
            for mode, key, page_key in [('d1', 'whole_sign_house', 'd1'), ('d9', 'navamsa_whole_sign_house', 'd9')]:
                info = audit['charts'][mode]
                x0, y0 = info['origin']
                s = info['size'] / 600
                expected = {'Asc': 1, **{premium.DISPLAY[n][1]: chart['planets'][n][key] for n in premium.GRAHAS}}
                self.assertEqual(info['lagna'], chart['lagna']['rashi'] if mode == 'd1' else chart['d9']['lagna_rashi'])
                page = pdf[premium.PAGE_OF[page_key] - 1]
                found = {}
                chart_rect = fitz.Rect(x0, H - y0 - info['size'], x0 + info['size'], H - y0)
                for x_0, y_0, x_1, y_1, word, *_ in page.get_text('words', clip=chart_rect):
                    if word in expected:
                        ux = ((x_0 + x_1) / 2 - x0) / s
                        uy = ((y_0 + y_1) / 2 - (H - y0 - info['size'])) / s
                        houses = [h for h in range(1, 13) if point_in_polygon(ux, uy, layout.HOUSES[h])]
                        found[word] = houses
                self.assertEqual(set(found), set(expected), (case, mode))
                for word, houses in found.items():
                    self.assertEqual(houses, [expected[word]], (case, mode, word))
                # Rashi numbers: house h shows the engine's Rashi for that house.
                start = layout.SIGNS.index(info['lagna'])
                for h in range(1, 13):
                    nx, ny = layout.number_position(h)
                    clip = fitz.Rect(x0 + (nx - 14) * s, H - y0 - info['size'] + (ny - 12) * s,
                                     x0 + (nx + 14) * s, H - y0 - info['size'] + (ny + 12) * s)
                    self.assertEqual(page.get_text(clip=clip).split(), [str((start + h - 1) % 12 + 1)], (case, mode, h))
                if mode == 'd9':
                    for row in chart['d9']['houses']:
                        self.assertEqual(row['rashi'], layout.SIGNS[(start + row['house'] - 1) % 12])

    # 6, 7. Crowded houses and label collisions.
    def test_crowded_house_records_render_without_collision(self):
        for shift in (0, 1, 2):  # house 1 diamond, house 2 and house 3 triangles
            data = crowded_response(shift)
            pdf_bytes, audit = premium.render(data, synthetic=True, palette='od10-candidate')
            labels = audit['charts']['d1']['labels'][shift + 1]
            self.assertEqual(len(labels), 9 if shift == 0 else 8)
            self.assertGreaterEqual(min(b[3] - b[1] for b in labels), 8)  # rows at least 8 pt tall
            pdf = fitz.open(stream=pdf_bytes, filetype='pdf')
            self._assert_no_text_overlap(pdf, f'crowded-{shift}')

    def _assert_no_text_overlap(self, pdf, label):
        for number, page in enumerate(pdf, 1):
            boxes = []
            for span in spans(page):
                x0, y0, x1, y1 = span['bbox']
                # Tighten to the glyph body; span boxes include line gap.
                pad = span['size'] * 0.12
                boxes.append((x0 + 0.3, y0 + pad, x1 - 0.3, y1 - pad, span['text']))
            for i, a in enumerate(boxes):
                for b in boxes[i + 1:]:
                    if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                        self.fail(f'{label} page {number}: {a[4]!r} overlaps {b[4]!r}')

    def test_no_overlapping_text_on_any_page(self):
        for case, palette, _, _, pdf in all_rendered():
            self._assert_no_text_overlap(pdf, f'{case}/{palette}')

    def test_no_rule_or_chart_line_strikes_through_text(self):
        for case, palette, _, _, pdf in all_rendered():
            for number, page in enumerate(pdf, 1):
                lines = []
                for drawing in page.get_drawings():
                    for item in drawing['items']:
                        if item[0] == 'l':
                            (p, q) = item[1], item[2]
                            lines.append((p.x, p.y, q.x, q.y))
                        elif item[0] == 're' and item[1].height < 1.2 and item[1].width > 4:
                            r = item[1]
                            lines.append((r.x0, (r.y0 + r.y1) / 2, r.x1, (r.y0 + r.y1) / 2))
                for span in spans(page):
                    x0, y0, x1, y1 = span['bbox']
                    h = y1 - y0
                    body = (x0 + 0.5, y0 + h * 0.28, x1 - 0.5, y1 - h * 0.12)  # glyph body down to just below the baseline
                    for seg in lines:
                        if segment_hits_rect(seg, body):
                            self.fail(f'{case}/{palette} page {number}: line crosses {span["text"]!r}')

    # 8. Long names.
    def test_long_place_names_wrap_inside_boxes(self):
        data = copy.deepcopy(SCENARIOS['s12-morning'])
        place = data['input']['place']
        place['name'] = 'Thiruvananthapuram Cantonment North Extension'
        place['region'] = 'Kerala (synthetic long region name for layout testing only)'
        place['country'] = 'India'
        pdf = fitz.open(stream=premium.generate(data, synthetic=True, palette='baseline'), filetype='pdf')
        self._assert_no_text_overlap(pdf, 'long-name')
        self._assert_inside_margins(pdf, 'long-name')
        cover_words = ' '.join(pdf[0].get_text().split())
        self.assertIn('Thiruvananthapuram Cantonment', cover_words)
        self.assertIn('Thiruvananthapuram Cantonment North Extension', ' '.join(pdf[3].get_text().split()))
        data['input']['place']['name'] = 'X' * 121
        with self.assertRaises(ValueError):
            premium.generate(data)

    def test_longest_rashi_names_fit_tables(self):
        # Vrishabha and Vrischika are the longest names; every scenario table already passes the
        # overlap test, and these cells are checked to stay inside their columns here.
        for case in SCENARIOS:
            _, _, pdf = rendered(case)
            page = pdf[premium.PAGE_OF['houses'] - 1]
            for word in ('Vrishabha', 'Vrischika'):
                for rect in page.search_for(word):
                    self.assertLess(rect.x1, W - premium.M)

    # 9, 13. Fonts and glyphs.
    def test_only_embedded_brand_fonts(self):
        for case, palette, _, _, pdf in all_rendered():
            for page in pdf:
                for xref, ext, ftype, name, *_ in page.get_fonts(full=True):
                    self.assertEqual(ext, 'ttf', (case, name))
                    base = name.split('+')[-1]
                    self.assertTrue(base.startswith(('Poppins', 'Inter')), (case, name))
                    self.assertNotRegex(base, 'Helvetica|Times|Courier|DejaVu|Arial')
            names = ' '.join(f[3] for p in pdf for f in p.get_fonts(full=True))
            self.assertIn('Poppins', names)
            self.assertIn('Inter', names)

    def test_minimum_text_size(self):
        for case, palette, _, _, pdf in all_rendered():
            for number, page in enumerate(pdf, 1):
                for span in spans(page):
                    self.assertGreaterEqual(round(span['size'], 2), premium.MIN_TEXT, (case, number, span['text']))

    def test_method_page_states_precision_rules(self):
        _, _, pdf = rendered('s07-noon')
        text = ' '.join(pdf[premium.PAGE_OF['method'] - 1].get_text().split())
        self.assertIn('Absolute longitudes are printed to eight decimals', text)
        self.assertIn('truncated to the arc-second', text)
        self.assertNotIn('rounded for display', ' '.join(' '.join(p.get_text().split()) for p in pdf))

    def test_no_missing_glyphs(self):
        cmaps = premium._register_fonts()
        by_family = {'Inter': cmaps['SP2-Body'], 'Poppins': cmaps['SP2-Head']}
        for case, palette, _, _, pdf in all_rendered():
            for page in pdf:
                for span in spans(page):
                    self.assertNotIn('�', span['text'])
                    family = 'Poppins' if 'Poppins' in span['font'] else 'Inter'
                    for ch in span['text']:
                        self.assertIn(ord(ch), by_family[family], (case, span['font'], ch))

    def test_unsupported_characters_refused_not_substituted(self):
        data = copy.deepcopy(SCENARIOS['s07-noon'])
        data['input']['place']['name'] = 'दिल्ली'  # Devanagari: no shaping engine yet
        with self.assertRaises(premium.MissingGlyphError):
            premium.generate(data)

    # 10. Logo.
    def test_logo_is_the_approved_file_on_every_page(self):
        self.assertEqual(hashlib.sha256(premium.LOGO_PATH.read_bytes()).hexdigest(), premium.LOGO_SHA256)
        self.assertEqual(premium.LOGO_PATH, REPO / 'prototype/kundali_prototype/static/brand/sabpuja-logo-horizontal-color.svg')
        _, _, pdf = rendered('s01-first-supported-date', 'baseline')
        for number, page in enumerate(pdf, 1):
            clip = fitz.Rect(W / 2 - 90, 40, W / 2 + 90, 130) if number == 1 else fitz.Rect(premium.M - 2, 20, premium.M + 92, 64)
            pix = page.get_pixmap(dpi=144, clip=clip)
            samples = pix.samples
            reds = sum(1 for i in range(0, len(samples), pix.n)
                       if samples[i] > 150 and samples[i + 1] < 60 and samples[i + 2] < 60)
            oranges = sum(1 for i in range(0, len(samples), pix.n)
                          if samples[i] > 220 and 70 < samples[i + 1] < 190 and samples[i + 2] < 60)
            self.assertGreater(reds, 50, number)
            self.assertGreater(oranges, 50, number)

    def test_altered_logo_refused(self):
        original = premium.LOGO_SHA256
        premium.LOGO_SHA256 = '0' * 64
        try:
            with self.assertRaises(RuntimeError):
                premium.generate(SCENARIOS['s07-noon'])
        finally:
            premium.LOGO_SHA256 = original

    # 11, 12. Margins and page bounds.
    def _assert_inside_margins(self, pdf, label):
        page_rect = fitz.Rect(-0.01, -0.01, W + 0.01, H + 0.01)
        for number, page in enumerate(pdf, 1):
            for span in spans(page):
                x0, y0, x1, y1 = span['bbox']
                self.assertGreaterEqual(x0, premium.M - 0.5, (label, number, span['text']))
                self.assertLessEqual(x1, W - premium.M + 0.5, (label, number, span['text']))
                self.assertGreaterEqual(y0, 30, (label, number, span['text']))
                self.assertLessEqual(y1, H - premium.FOOTER_Y + 8, (label, number, span['text']))
            for drawing in page.get_drawings():
                r = drawing['rect']
                self.assertTrue(page_rect.contains(r) or r.is_empty, (label, number, r))

    def test_text_within_margins_and_page(self):
        for case, palette, _, _, pdf in all_rendered():
            self._assert_inside_margins(pdf, f'{case}/{palette}')
            for page in pdf:
                self.assertAlmostEqual(page.rect.width, W, 3)  # A4 portrait
                self.assertAlmostEqual(page.rect.height, H, 3)

    # 14. Branding tokens and contrast.
    def test_palette_tokens(self):
        cand = premium.Palette('od10-candidate').hex
        owner = premium.THEMES['palettes']['od10-candidate']['owner_tokens']
        self.assertEqual(owner, {'warm_ivory': '#FAF5EA', 'deep_maroon': '#681E30', 'antique_gold': '#BE9148',
                                 'champagne_beige': '#E9D9BA', 'charcoal': '#2F2926'})
        self.assertEqual((cand['page'], cand['primary'], cand['accent'], cand['tint'], cand['ink']),
                         ('#FAF5EA', '#681E30', '#BE9148', '#E9D9BA', '#2F2926'))
        base = premium.Palette('baseline').hex
        theme = premium.phase1.THEME['colors']
        self.assertEqual((base['page'], base['primary'], base['accent'], base['ink']),
                         (theme['ivory'], theme['saffron'], theme['gold'], theme['text']))
        self.assertEqual(premium.THEMES['default_palette'], 'baseline', 'OD-10: the owner approved the saffron baseline')
        self.assertEqual(premium.THEMES['palettes']['baseline']['status'], 'approved')
        self.assertEqual(premium.THEMES['palettes']['od10-candidate']['status'], 'not-selected')
        self.assertEqual(theme['saffron'], '#D35400', 'Phase 1 theme.json must stay unchanged')
        with self.assertRaises(ValueError):
            premium.Palette('maroon')

    def test_small_text_contrast(self):
        def lum(hex_):
            def ch(v):
                v /= 255
                return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
            r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
            return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)

        def ratio(a, b):
            la, lb = sorted((lum(a), lum(b)), reverse=True)
            return (la + 0.05) / (lb + 0.05)
        rules = premium.THEMES['role_rules']
        for name in PALETTES:
            pal = premium.Palette(name).hex
            for role in rules['small_text_roles']:
                for bg in ('page', 'surface', 'tint', 'tint_soft'):
                    self.assertGreaterEqual(ratio(pal[role], pal[bg]), rules['minimum_small_text_contrast'], (name, role, bg))

    def test_rendered_colours_follow_palette(self):
        for palette in PALETTES:
            _, _, pdf = rendered('s05-graha-near-boundary', palette)
            hexes = premium.Palette(palette).hex
            want = {k: tuple(round(int(hexes[k][i:i + 2], 16) / 255, 3) for i in (1, 3, 5)) for k in ('primary', 'accent', 'page')}
            fills = {tuple(round(v, 3) for v in d['fill']) for p in pdf for d in p.get_drawings() if d.get('fill')}
            strokes = {tuple(round(v, 3) for v in d['color']) for p in pdf for d in p.get_drawings() if d.get('color')}
            self.assertIn(want['page'], fills, palette)
            self.assertIn(want['primary'], fills | strokes, palette)
            self.assertIn(want['accent'], fills | strokes, palette)
            other = 'baseline' if palette != 'baseline' else 'od10-candidate'
            ohex = premium.Palette(other).hex['primary']
            self.assertNotIn(tuple(round(int(ohex[i:i + 2], 16) / 255, 3) for i in (1, 3, 5)), fills | strokes)

    # 15. Searchable text.
    def test_searchable_text(self):
        _, _, pdf = rendered('s09-evening')
        chart = SCENARIOS['s09-evening']['chart']
        self.assertTrue(pdf[0].search_for('Janma Kundali'))
        self.assertTrue(pdf[premium.PAGE_OF['positions'] - 1].search_for(chart['moon_nakshatra']['name']))
        self.assertTrue(pdf[premium.PAGE_OF['birth'] - 1].search_for(SCENARIOS['s09-evening']['input']['place']['name']))
        self.assertTrue(pdf[premium.PAGE_OF['method'] - 1].search_for('UNVERIFIED_GOLDEN_CHARTS'))

    # 16. Size.
    def test_output_size_bounded(self):
        for case, palette, data, _, _ in all_rendered():
            self.assertLess(len(data), 300 * 1024, (case, palette))
            self.assertLess(len(data), premium.MAX_PDF_BYTES)

    # 17. Missing and invalid data.
    def test_invalid_responses_refused(self):
        base = SCENARIOS['s07-noon']
        mutations = {
            'no chart': lambda d: d.pop('chart'),
            'old schema': lambda d: d['chart'].__setitem__('schema_version', '0.2.0'),
            'certified claim': lambda d: d['chart'].__setitem__('validation_status', 'VERIFIED'),
            'no metadata': lambda d: d['chart'].pop('calculation_metadata'),
            'metadata v2': lambda d: d['chart']['calculation_metadata'].__setitem__('metadata_schema', 'sabpuja-calculation-metadata/2'),
            'status mismatch': lambda d: d['chart']['calculation_metadata']['validation'].__setitem__('status', 'OTHER'),
            'rashi vs longitude': lambda d: d['chart']['planets']['sun'].__setitem__('longitude_deg', (d['chart']['planets']['sun']['longitude_deg'] + 40) % 360),
            'lagna longitude': lambda d: d['chart']['lagna'].__setitem__('longitude_deg', (d['chart']['lagna']['longitude_deg'] + 30) % 360),
            'lagna missing longitude': lambda d: d['chart']['lagna'].pop('longitude_deg'),
            'd1 house': lambda d: d['chart']['planets']['moon'].__setitem__('whole_sign_house', d['chart']['planets']['moon']['whole_sign_house'] % 12 + 1),
            'd9 house': lambda d: d['chart']['planets']['mars'].__setitem__('navamsa_whole_sign_house', d['chart']['planets']['mars']['navamsa_whole_sign_house'] % 12 + 1),
            'd9 list': lambda d: d['chart']['d9']['houses'][0]['grahas'].append('sun'),
            'nan longitude': lambda d: d['chart']['planets']['venus'].__setitem__('longitude_deg', float('nan')),
            'missing planet': lambda d: d['chart']['planets'].pop('saturn'),
            'no place region': lambda d: d['input']['place'].pop('region'),
            'zone mismatch': lambda d: d['input']['place'].__setitem__('timezone', 'Europe/London'),
            'bad date': lambda d: d['input'].__setitem__('local_date', '15/05/1990'),
            'month 13': lambda d: d['input'].__setitem__('local_date', '1990-13-01'),
            'no offset': lambda d: d['input'].pop('utc_offset'),
            'no time': lambda d: d['input'].pop('local_time'),
            'pada 5': lambda d: d['chart']['moon_nakshatra'].__setitem__('pada', 5),
            'bool house': lambda d: d['chart']['planets']['sun'].__setitem__('whole_sign_house', True),
        }
        for label, mutate in mutations.items():
            data = copy.deepcopy(base)
            mutate(data)
            with self.assertRaises((ValueError, KeyError, TypeError, AttributeError), msg=label):
                premium.generate(data)

    def test_engine_refusals_never_become_pdfs(self):
        refusals = [
            {'error': {'code': 'LATITUDE_OUTSIDE_SUPPORTED_BAND', 'category': 'unsupported'}},
            {'error': {'code': 'HISTORICAL_CLOCK_UNVERIFIED', 'category': 'unsupported'}},
            {'error': {'code': 'TIME_NONEXISTENT_LOCAL', 'category': 'input'}},
            {'error': {'code': 'BIRTH_TIME_REQUIRED', 'category': 'unknown_time'}},
            {'error': {'code': 'TIME_AMBIGUOUS_LOCAL', 'category': 'ambiguous'}},
            None, [], 'chart', {},
        ]
        for refusal in refusals:
            with self.assertRaises(ValueError):
                premium.generate(refusal)

    def test_phase1_fixture_without_provenance_refused(self):
        with self.assertRaises(ValueError):
            premium.generate(PHASE1_FIXTURE)

    # 18. No unsupported interpretation.
    def test_no_predictive_or_unapproved_content(self):
        banned = [r'\byou will\b', r'\bwill (marry|become|face|have)\b', r'\bfortune\b', r'\blucky\b', r'\bauspicious\b',
                  r'\bmalefic\b', r'\bbenefic\b', r'\bexalted\b', r'\bdebilitat', r'\bmanglik\b', r'\bgemstone',
                  r'\bshadbala\b', r'\bretrograde\b(?! (motion|status))', r'\bcertified\b(?! against)', r'\bguarantee']
        topical = ['Dasha', 'Panchanga', 'Yoga', 'Dosha', 'remed', 'predict', 'interpret']
        method_page = premium.PAGE_OF['method']
        for case in SCENARIOS:
            _, _, pdf = rendered(case)
            for number, page in enumerate(pdf, 1):
                text = ' '.join(page.get_text().split())
                for pattern in banned:
                    self.assertIsNone(re.search(pattern, text, re.I), (case, number, pattern))
                if number != method_page:
                    for word in topical:
                        for m in re.finditer(word, text, re.I):
                            window = text[max(0, m.start() - 160):m.end() + 40].lower()
                            self.assertTrue(re.search(r'\bnot\b|\bno\b|\bnot a\b', window), (case, number, word, window))
            method = ' '.join(pdf[method_page - 1].get_text().split())
            self.assertIn('Not included in this edition', method)
            self.assertIn('Panchanga, Vimshottari Dasha', method)
            self.assertIn('not yet been certified', method)

    # 19. No retained sensitive data.
    def test_no_birth_data_in_metadata_files_or_module_state(self):
        data = SCENARIOS['s11-afternoon']
        before = copy.deepcopy(data)
        writes = []
        real_open = builtins.open

        def guarded_open(file, mode='r', *a, **k):
            if any(m in mode for m in 'wax+'):
                writes.append(file)
            return real_open(file, mode, *a, **k)
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            builtins.open = guarded_open
            try:
                pdf_bytes = premium.generate(data, synthetic=False)
            finally:
                builtins.open = real_open
                os.chdir(cwd)
            self.assertEqual(os.listdir(tmp), [])
        self.assertEqual(writes, [])
        self.assertEqual(data, before, 'input response was modified')
        pdf = fitz.open(stream=pdf_bytes, filetype='pdf')
        meta = json.dumps(pdf.metadata)
        for secret in (data['input']['local_date'], data['input']['local_time'], data['input']['place']['name'],
                       str(data['chart']['birth']['latitude'])):
            self.assertNotIn(secret, meta)
            self.assertNotIn(secret.encode(), pdf_bytes)  # text streams are compressed and subset-encoded
        self.assertNotIn('Sample report', pdf[1].get_text())  # synthetic marker only when asked
        for value in vars(premium).values():
            self.assertIsNot(value, data)

    # 20. Schema and engine outputs untouched.
    def test_schema_shape_unchanged(self):
        for case, data in SCENARIOS.items():
            chart = data['chart']
            self.assertEqual(chart['schema_version'], '0.3.0')
            self.assertEqual(set(chart), {'schema_version', 'validation_status', 'method', 'birth', 'lagna',
                                          'moon_nakshatra', 'planets', 'calculation_metadata', 'd9'})
            self.assertEqual(chart['calculation_metadata']['metadata_schema'], 'sabpuja-calculation-metadata/3')
            self.assertEqual(set(chart['planets']), set(premium.GRAHAS))
            for body in chart['planets'].values():
                self.assertEqual(set(body), {'longitude_deg', 'rashi', 'navamsa_rashi', 'whole_sign_house',
                                             'navamsa_whole_sign_house'})
        self.assertEqual(premium.phase1.validate_engine_response(SCENARIOS['s07-noon']), SCENARIOS['s07-noon'])

    @unittest.skipUnless(os.environ.get('SABPUJA_TEST_EPHE_PATH'), 'set SABPUJA_TEST_EPHE_PATH for the live engine check')
    def test_engine_reproduces_every_scenario_exactly(self):
        sys.path[:0] = [str(REPO / 'prototype'), str(REPO / 'src')]
        from kundali_prototype import server
        from kundali_prototype.places import load_places
        places = load_places()
        for case in MANIFEST['cases']:
            status, response = server.handle_chart(json.dumps(case['request']).encode(), places,
                                                   os.environ['SABPUJA_TEST_EPHE_PATH'])
            self.assertEqual(status, 200)
            self.assertEqual(response, SCENARIOS[case['id']], case['id'])

    def test_server_renders_premium_saffron_and_phase1_kept_for_rollback(self):
        # KUN-RPT-002B: the preview route renders this layout in the approved saffron palette only.
        server_src = (REPO / 'prototype/kundali_prototype/server.py').read_text()
        self.assertIn('from report.phase1.premium_report import generate', server_src)
        self.assertIn('REPORT_PALETTE = "baseline"', server_src)
        self.assertNotIn('from report.phase1.generate_report import', server_src)
        self.assertNotIn('od10', server_src)
        pdf = fitz.open(stream=premium.phase1.generate(PHASE1_FIXTURE, synthetic=True), filetype='pdf')
        self.assertEqual(len(pdf), 8)


if __name__ == '__main__':
    unittest.main()
