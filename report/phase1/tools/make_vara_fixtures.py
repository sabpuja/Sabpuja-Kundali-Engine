"""Capture the `sabpuja-panchanga-vara/1` documents for the sunrise and Vara edition (KUN-PAN-RPT-002).

Two sets, all synthetic (nothing here is a real person or a real birth record):

* fixtures/vara/<scenario>.json: the document for each of the 13 existing report scenarios
  (fixtures/premium), for the same engine request the prototype server builds.
* fixtures/vara-cases/<case>.json: further synthetic boundary cases, each a complete set
  {"response", "panchanga", "vara"} computed through the prototype server's own handle_chart path
  (response), the unchanged Panchanga M1 module (panchanga) and panchanga.vara (vara). Two cases use
  synthetic test coordinates outside the supported place list (a high-latitude point and a point on
  Kiritimati, UTC+14); their place `source` says so.

Near-sunrise births are placed relative to the computed sunrise, so the fixtures stay correct if
re-run: the sunrise is computed first, then the birth second is chosen from it.

    SABPUJA_TEST_EPHE_PATH=/abs/ephe python report/phase1/tools/make_vara_fixtures.py
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / 'prototype'), str(REPO / 'src'), str(Path(__file__).resolve().parent)]
from kundali_prototype import server  # noqa: E402
from kundali_prototype.places import load_places  # noqa: E402
from sabpuja_kundali import panchanga  # noqa: E402
from sabpuja_kundali.panchanga import vara  # noqa: E402
from sabpuja_kundali.timezones import get_zone  # noqa: E402
import make_panchanga_fixtures as maker  # noqa: E402

FIXTURES = REPO / 'report/phase1/tests/fixtures'
SYNTHETIC_SOURCE = 'Synthetic test coordinates for KUN-PAN-RPT-002; not a supported birthplace record'
SYNTHETIC_PLACES = {
    'zz-high-latitude-65n': {'id': 'zz-high-latitude-65n', 'name': 'Synthetic point 65.95° N', 'region': 'Test',
                             'country': 'Finland', 'latitude': 65.95, 'longitude': 25.0,
                             'timezone': 'Europe/Helsinki'},
    'zz-kiritimati': {'id': 'zz-kiritimati', 'name': 'Synthetic point, Kiritimati', 'region': 'Line Islands',
                      'country': 'Kiribati', 'latitude': 1.87, 'longitude': -157.4,
                      'timezone': 'Pacific/Kiritimati'},
}


# Test-only Hindi display forms for the two synthetic points. The production terminology register is not
# changed, so a real Hindi report for these coordinates is refused (ReportLocaleError); tests and the review
# samples add these forms in memory only, inside synthetic_hindi_places().
SYNTHETIC_HINDI = {
    'zz-high-latitude-65n': ('कृत्रिम बिंदु 65.95° उत्तर', 'परीक्षण', 'फ़िनलैंड'),
    'zz-kiritimati': ('कृत्रिम बिंदु, किरितिमाती', 'लाइन द्वीपसमूह', 'किरिबाती'),
}
SYNTHETIC_SOURCE_HI = 'KUN-PAN-RPT-002 के लिए कृत्रिम परीक्षण निर्देशांक; समर्थित जन्म स्थान रिकॉर्ड नहीं'


class synthetic_hindi_places:
    """Context manager: Hindi forms of the synthetic points in the report's register, in memory only."""

    def __enter__(self):
        sys.path.insert(0, str(REPO))
        from report.phase1 import report_locale as loc
        self.loc, self.saved = loc, (dict(loc.TERMS['place']), loc.Translator.place_source)
        for pid, hi in SYNTHETIC_HINDI.items():
            row = SYNTHETIC_PLACES[pid]
            loc.TERMS['place'][pid] = {'en': [row['name'], row['region'], row['country']], 'hi': list(hi)}
        original = self.saved[1]

        def place_source(tr, text):
            return SYNTHETIC_SOURCE_HI if tr.hindi and text == SYNTHETIC_SOURCE else original(tr, text)
        loc.Translator.place_source = place_source
        return self

    def __exit__(self, *exc):
        self.loc.TERMS['place'].clear()
        self.loc.TERMS['place'].update(self.saved[0])
        self.loc.Translator.place_source = self.saved[1]


def _places(base):
    out = dict(base)
    for pid, row in SYNTHETIC_PLACES.items():
        out[pid] = {**row, 'provenance': {'geonames_id': 'none', 'cross_check': {'distance_km': 0}}}
    return out


def compute(places, ephe, place_id, day, clock, utc_offset=None):
    body = {'place_id': place_id, 'birth_date': day, 'birth_time': clock}
    if utc_offset:
        body['utc_offset'] = utc_offset
    status, response = server.handle_chart(json.dumps(body).encode(), places, ephe)
    if status != 200:
        raise SystemExit(f'{place_id} {day} {clock}: chart refused {response}')
    if place_id in SYNTHETIC_PLACES:
        response['input']['place']['source'] = SYNTHETIC_SOURCE
    request = maker.engine_request(response)
    return {'response': response, 'panchanga': panchanga.calculate(request, ephe),
            'vara': vara.calculate(request, ephe)}


def sunrise_local(ephe, place, day):
    """The SUN-D-IMD-47 sunrise of a local date at a place, as an aware local datetime (microseconds)."""
    from sabpuja_kundali.panchanga import sun
    row = SYNTHETIC_PLACES.get(place) or load_places()[place]
    out = sun.sun_day(day, row['latitude'], row['longitude'], row['timezone'], convention=vara.CONVENTION,
                      ephe_path=ephe)
    utc = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=out['sunrise']['utc_us'])
    return utc.astimezone(get_zone(row['timezone']))


def clock(moment):
    return moment.strftime('%H:%M:%S')


def cases(ephe):
    jaipur = sunrise_local(ephe, 'in-jaipur', '2039-07-31')
    up = jaipur.replace(microsecond=0) + timedelta(seconds=1)      # first whole second at or after sunrise
    down = jaipur.replace(microsecond=0)                             # last whole second before sunrise
    if jaipur.microsecond == 0:
        down -= timedelta(seconds=1)
    return [
        # (id, description, place, date, clock, utc_offset)
        ('v01-typical-afternoon', 'Typical daytime birth, Vara equals the civil weekday',
         'in-jaipur', '2039-07-31', '15:20:00', None),
        ('v02-pre-sunrise-previous-vara', 'Night birth before sunrise: previous Vara, civil weekday differs',
         'in-lucknow', '1978-12-12', '03:15:00', None),
        ('v03-first-second-after-sunrise', 'First whole second after the computed sunrise: near-sunrise warning',
         'in-jaipur', '2039-07-31', clock(up), None),
        ('v04-last-second-before-sunrise', 'Last whole second before the computed sunrise: previous Vara, warning',
         'in-jaipur', '2039-07-31', clock(down), None),
        ('v05-inside-band-after', 'About 4 min 59 s after sunrise: inside the 5-minute band',
         'in-jaipur', '2039-07-31', clock(up + timedelta(seconds=299)), None),
        ('v06-outside-band-after', 'About 5 min 01 s after sunrise: just outside the 5-minute band',
         'in-jaipur', '2039-07-31', clock(down + timedelta(seconds=301)), None),
        ('v07-london-clocks-forward', 'London, the night clocks go forward: pre-sunrise birth across the change',
         'gb-london', '2031-03-30', '00:30:00', None),
        ('v08-london-repeated-hour', 'London, second occurrence of the repeated hour',
         'gb-london', '2031-10-26', '01:30:00', '+00:00'),
        ('v09-dateline-kiritimati', 'UTC+14, the first time zone of the day, just after local midnight',
         'zz-kiritimati', '2030-01-01', '00:20:00', None),
        ('v10-polar-day-unavailable', 'Polar day at 65.95° N: no sunrise, Vara not given',
         'zz-high-latitude-65n', '2044-06-21', '12:00:00', None),
        ('v11-vara-day-end-undefined', 'Last sunrise before polar day: the next sunrise does not occur',
         'zz-high-latitude-65n', '2044-06-13', '12:00:00', None),
        ('v12-sunset-after-midnight', 'Sunset after local midnight, 27 minutes before the next sunrise',
         'zz-high-latitude-65n', '2044-06-12', '12:00:00', None),
    ]


def main():
    ephe = os.environ.get('SABPUJA_TEST_EPHE_PATH')
    if not ephe:
        raise SystemExit('SABPUJA_TEST_EPHE_PATH must point to the pinned ephemeris directory')
    out = FIXTURES / 'vara'
    out.mkdir(exist_ok=True)
    for path in sorted((FIXTURES / 'premium').glob('s*.json')):
        response = json.loads(path.read_text())
        doc = vara.calculate(maker.engine_request(response), ephe)
        (out / path.name).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print(path.stem, doc['vara'].get('vara_id', doc['vara'].get('condition')), doc['boundary'].get('near_sunrise'))
    out = FIXTURES / 'vara-cases'
    out.mkdir(exist_ok=True)
    places = _places(load_places())
    for case_id, description, place, day, at, offset in cases(ephe):
        record = {'case': case_id, 'description': description, **compute(places, ephe, place, day, at, offset)}
        (out / f'{case_id}.json').write_text(json.dumps(record, ensure_ascii=False, indent=1) + '\n')
        v = record['vara']
        print(case_id, v['vara'].get('vara_id', v['vara'].get('condition')), v['boundary'].get('near_sunrise'))


if __name__ == '__main__':
    main()
