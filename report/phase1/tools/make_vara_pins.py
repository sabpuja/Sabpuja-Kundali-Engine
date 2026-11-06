"""Pin the SHA-256 of every 14-page sunrise and Vara edition PDF in the test matrix (KUN-PAN-RPT-002).

For the 13 report scenarios and the 12 synthetic boundary cases, in English and Hindi, as a sample and a
customer-mode render (palette "baseline", no report name). Developer tool; the tests compare against the
committed file so any change to the drawn edition is visible in review.

    python report/phase1/tools/make_vara_pins.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO), str(REPO / 'src'), str(REPO / 'report/phase1/tests'), str(Path(__file__).resolve().parent)]
import test_vara_report as t  # noqa: E402

OUT = REPO / 'report/phase1/tests/fixtures/extended-14-page-vara-sha256.json'


def main():
    pins = {}
    for case, *_ in t.all_cases():
        for locale in ('en', 'hi'):
            for mode in ('sample', 'customer'):
                data, _, _ = t.render(case, locale, synthetic=mode == 'sample')
                pins[f'{case}|{locale}|{mode}'] = hashlib.sha256(data).hexdigest()
            t._CACHE.clear()
    doc = {'note': 'SHA-256 of premium_report.generate_extended(response, panchanga, synthetic, palette="baseline", '
                   'locale, vara=doc) for every synthetic case of test_vara_report (KUN-PAN-RPT-002). Regenerate with '
                   'report/phase1/tools/make_vara_pins.py only for a deliberate, reviewed change to the edition.',
           'sha256': pins}
    OUT.write_text(json.dumps(doc, indent=1) + '\n')
    print(len(pins), 'pins written')


if __name__ == '__main__':
    main()
