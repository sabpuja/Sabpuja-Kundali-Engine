"""Pin the SHA-256 of every Essentials edition PDF in the test matrix (KUN-RC-ESS-001).

The 25 synthetic cases of test_vara_report (13 report scenarios and 12 sunrise boundary cases), each rendered by
essentials.generate without a name, plus the primary scenario with one synthetic name. Developer tool; the tests
compare against the committed file, so any change to the frozen edition is visible in review.

    python report/phase1/tools/make_essentials_pins.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO), str(REPO / 'src'), str(REPO / 'report/phase1/tests'), str(Path(__file__).resolve().parent)]
import test_essentials as t  # noqa: E402

OUT = REPO / 'report/phase1/tests/fixtures/essentials-en-sha256.json'


def main():
    pins = {}
    for case, name in t.matrix():
        pins[f'{case}|{name or "-"}'] = hashlib.sha256(t.render(case, name)[0]).hexdigest()
    doc = {'note': 'SHA-256 of essentials.generate(response, panchanga, vara, display_name) for every synthetic case of '
                   'test_essentials (KUN-RC-ESS-001). Regenerate with report/phase1/tools/make_essentials_pins.py only '
                   'for a deliberate, reviewed change to the frozen edition.',
           'edition': t.es.EDITION, 'sha256': pins}
    OUT.write_text(json.dumps(doc, indent=1) + '\n')
    print(len(pins), 'pins written')


if __name__ == '__main__':
    main()
