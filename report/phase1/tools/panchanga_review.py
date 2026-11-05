"""Write the KUN-PAN-RPT-001 review set outside Git: extended EN/HI PDFs and page images.

    python report/phase1/tools/panchanga_review.py OUT_DIR [--cases s07-noon s01-first-supported-date ...]

Synthetic scenarios only (tests/fixtures/premium with tests/fixtures/panchanga). Every PDF is
marked as a sample. Also writes the matching ten-page PDFs and a SHA-256 list, so reviewers can
compare the two editions page by page. Never write the output inside the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO), str(REPO / 'src')]
from report.phase1 import premium_report as premium  # noqa: E402

FIXTURES = REPO / 'report/phase1/tests/fixtures'
DEFAULT_CASES = ['s07-noon', 's01-first-supported-date', 's12-morning', 's02-last-supported-date']
NAMES = {'en': 'Asha Verma', 'hi': 'आशा वर्मा'}   # synthetic names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('out_dir')
    parser.add_argument('--cases', nargs='*', default=DEFAULT_CASES)
    parser.add_argument('--dpi', type=int, default=110)
    args = parser.parse_args()
    out = Path(args.out_dir).resolve()
    if REPO in out.parents or out == REPO:
        raise SystemExit('write the review set outside the repository')
    out.mkdir(parents=True, exist_ok=True)
    import fitz
    lines = []
    for case in args.cases:
        response = json.loads((FIXTURES / 'premium' / f'{case}.json').read_text())
        doc = json.loads((FIXTURES / 'panchanga' / f'{case}.json').read_text())
        for locale in ('en', 'hi'):
            for named in (False, True):
                name = NAMES[locale] if named else None
                tag = f'{case}-{locale}' + ('-named' if named else '')
                ext = premium.generate_extended(response, doc, synthetic=True, palette='baseline',
                                                display_name=name, locale=locale)
                std = premium.generate(response, synthetic=True, palette='baseline', display_name=name, locale=locale)
                for label, data in (('extended', ext), ('standard10', std)):
                    path = out / f'{tag}-{label}.pdf'
                    path.write_bytes(data)
                    lines.append(f'{hashlib.sha256(data).hexdigest()}  {path.name}  pages={len(fitz.open(stream=data, filetype="pdf"))}')
                if not named:
                    pdf = fitz.open(stream=ext, filetype='pdf')
                    for i in (1, 9, 10, 11, 12):
                        pdf[i].get_pixmap(dpi=args.dpi).save(out / f'{tag}-extended-p{i + 1:02d}.png')
    (out / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
