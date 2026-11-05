"""Capture the `sabpuja-panchanga/1` document for each existing synthetic report scenario.

The birth requests are exactly the 13 synthetic scenarios already in tests/fixtures/premium
(no new birth record). Each document comes from the unchanged Panchanga M1 module
(sabpuja_kundali.panchanga.calculate) with the pinned ephemeris, for the same engine request the
prototype server builds for that scenario. Nothing here is a real person.

    SABPUJA_TEST_EPHE_PATH=/abs/ephe python report/phase1/tools/make_panchanga_fixtures.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / 'src')]
from sabpuja_kundali import panchanga  # noqa: E402

SCENARIOS = REPO / 'report/phase1/tests/fixtures/premium'
OUT = REPO / 'report/phase1/tests/fixtures/panchanga'


def engine_request(response):
    """The request handle_chart sends to the engine for this response (server.compute)."""
    info = response['input']
    place = info['place']
    return {'birth_datetime': f"{info['local_date']}T{info['local_time']}{info['utc_offset']}",
            'timezone': place['timezone'], 'latitude': place['latitude'], 'longitude': place['longitude']}


def main():
    ephe = os.environ.get('SABPUJA_TEST_EPHE_PATH')
    if not ephe:
        raise SystemExit('SABPUJA_TEST_EPHE_PATH must point to the pinned ephemeris directory')
    OUT.mkdir(exist_ok=True)
    for path in sorted(SCENARIOS.glob('s*.json')):
        response = json.loads(path.read_text())
        doc = panchanga.calculate(engine_request(response), ephe)
        (OUT / path.name).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print(path.stem, doc['tithi']['number'], doc['karana']['index'], doc['yoga']['index'],
              doc['nakshatra']['name'], doc['nakshatra']['pada'])


if __name__ == '__main__':
    main()
