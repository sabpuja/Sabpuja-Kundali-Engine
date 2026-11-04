"""Build the synthetic scenario matrix for the Phase 2A report tests (reproducible, synthetic only).

Every case is an invented birth record (a supported fixture city, a date and a time) chosen by a
seeded search so the matrix covers all twelve D1 Lagnas plus the hard layout and display cases.
The engine responses are captured through the prototype server's own handle_chart path with the
pinned ephemeris, exactly as the preview would produce them. Nothing here is a real person.

    SABPUJA_TEST_EPHE_PATH=/abs/ephe python report/phase1/tools/make_premium_scenarios.py
"""
from __future__ import annotations

import json
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / 'prototype'), str(REPO / 'src')]
from kundali_prototype import server  # noqa: E402
from kundali_prototype.places import load_places  # noqa: E402

OUT = REPO / 'report/phase1/tests/fixtures/premium'
INDIA = ['in-new-delhi', 'in-mumbai', 'in-kolkata', 'in-chennai', 'in-bengaluru',
         'in-hyderabad', 'in-jaipur', 'in-lucknow', 'in-varanasi', 'in-guwahati']
FIRST, LAST = date(1970, 1, 1), date(2100, 12, 31)


def compute(places, ephe, place_id, day, clock):
    body = {'place_id': place_id, 'birth_date': day, 'birth_time': clock}
    status, response = server.handle_chart(json.dumps(body).encode(), places, ephe)
    return response if status == 200 else None


def within(chart, key='longitude_deg'):
    return {n: b[key] % 30 for n, b in chart['planets'].items()}


def max_house(chart, key):
    counts = {}
    for b in chart['planets'].values():
        counts[b[key]] = counts.get(b[key], 0) + 1
    return max(counts.values())


def near_boundary(chart, limit):
    values = list(within(chart).values())
    return any(v < limit or v > 30 - limit for v in values)


# (id, description, fixed fields, predicate)
CASES = [
    ('s01-first-supported-date', 'First supported local date, 00:00:00', {'day': FIRST.isoformat(), 'clock': '00:00:00'}, None),
    ('s02-last-supported-date', 'Last supported local date, 23:59:59', {'day': LAST.isoformat(), 'clock': '23:59:59'}, None),
    ('s03-crowded-d1-house', 'At least five grahas in one D1 house', {}, lambda c: max_house(c, 'whole_sign_house') >= 5),
    ('s04-crowded-d9-house', 'At least four grahas in one D9 house', {}, lambda c: max_house(c, 'navamsa_whole_sign_house') >= 4),
    ('s05-graha-near-boundary', 'A graha within 0.005 deg of a Rashi boundary', {}, lambda c: near_boundary(c, 0.005)),
    ('s06-lagna-near-boundary', 'Lagna within 0.02 deg of a Rashi boundary', {},
     lambda c: min(c['lagna']['longitude_deg'] % 30, 30 - c['lagna']['longitude_deg'] % 30) < 0.02),
    ('s07-noon', 'Local noon', {'clock': '12:00:00'}, None),
    ('s08-dawn', 'Early morning time with seconds', {'clock': '05:07:33'}, None),
    ('s09-evening', 'Evening time', {'clock': '19:45:00'}, None),
    ('s10-late-night', 'Late night time', {'clock': '23:10:00'}, None),
    ('s11-afternoon', 'Afternoon time', {'clock': '15:20:10'}, None),
    ('s12-morning', 'Morning time', {'clock': '08:30:00'}, None),
    ('s13-remaining-lagna', 'Any time; completes the twelve D1 Lagnas', {}, None),
]


def main():
    ephe = os.environ.get('SABPUJA_TEST_EPHE_PATH')
    if not ephe:
        raise SystemExit('SABPUJA_TEST_EPHE_PATH must point to the pinned ephemeris directory')
    places = load_places()
    rng = random.Random(20261029)
    span = (LAST - FIRST).days
    used_lagnas, out = set(), []
    for index, (case_id, description, fixed, predicate) in enumerate(CASES):
        if 'day' in fixed:
            # One fixed date and time: only the place varies. Prefer a Lagna not yet covered.
            options = [(p, compute(places, ephe, p, fixed['day'], fixed['clock'])) for p in INDIA]
            options = [(p, r) for p, r in options if r is not None]
            fresh = [(p, r) for p, r in options if r['chart']['lagna']['rashi'] not in used_lagnas]
            place, response = (fresh or options)[0]
        else:
            for attempt in range(200_000):
                day = (FIRST + timedelta(days=rng.randrange(span + 1))).isoformat()
                clock = fixed.get('clock') or f'{rng.randrange(24):02d}:{rng.randrange(60):02d}:{rng.randrange(60):02d}'
                place = INDIA[(index + attempt) % len(INDIA)] if predicate else INDIA[index % len(INDIA)]
                response = compute(places, ephe, place, day, clock)
                if response is None or response['chart']['lagna']['rashi'] in used_lagnas:
                    continue
                if predicate and not predicate(response['chart']):
                    continue
                break
            else:
                raise SystemExit(f'no candidate for {case_id}')
        used_lagnas.add(response['chart']['lagna']['rashi'])
        out.append((case_id, description, response))
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case_id, description, response in out:
        (OUT / f'{case_id}.json').write_text(json.dumps(response, indent=1, ensure_ascii=False) + '\n')
        chart = response['chart']
        manifest.append({'id': case_id, 'description': description, 'synthetic': True,
                         'request': {'place_id': response['input']['place']['id'],
                                     'birth_date': response['input']['local_date'],
                                     'birth_time': response['input']['local_time']},
                         'd1_lagna': chart['lagna']['rashi'], 'd9_lagna': chart['d9']['lagna_rashi'],
                         'max_d1_house': max_house(chart, 'whole_sign_house'),
                         'max_d9_house': max_house(chart, 'navamsa_whole_sign_house')})
    (OUT / 'manifest.json').write_text(json.dumps({
        'purpose': 'Synthetic Phase 2A report scenarios. Invented birth records; no real person.',
        'generator': 'report/phase1/tools/make_premium_scenarios.py (seed 20261029)',
        'cases': manifest}, indent=1, ensure_ascii=False) + '\n')
    for m in manifest:
        print(m['id'], m['request'], m['d1_lagna'], m['d9_lagna'], m['max_d1_house'], m['max_d9_house'])


if __name__ == '__main__':
    main()
