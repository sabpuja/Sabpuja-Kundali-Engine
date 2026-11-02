"""Refresh the packet's reproducible assets and hashes after an approved catalog change.

Run from the repository root:  PYTHONPATH=src:prototype python docs/i18n/review/kun-i18n-003/refresh_manifest.py
1. Regenerates the three sample PDFs from the synthetic fixture `s11-afternoon` with the current
   renderer and catalogs (Change A, for example, changes the English one).
2. Rewrites every "`assets/...` SHA-256 `<hash>`" statement in the packet documents.
3. Rewrites the file table in EVIDENCE-MANIFEST.md from the files on disk.
It records no review and changes no catalog. Page images (assets/en-hi-page-NN.png) are not
regenerated here; after Change A, regenerate en-hi-page-10.png before asking for review.
`report/phase1/tests/test_review_packet_assets.py` fails until this has been run.
"""
import hashlib
import re
import sys
from pathlib import Path

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'report/phase1/tests')]
from report.phase1 import premium_report as premium  # noqa: E402
import test_premium_name as fixtures  # noqa: E402
from test_review_packet_assets import DOCS, SAMPLES  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for name, (locale, display_name) in SAMPLES.items():
    (PACKET / name).write_bytes(premium.generate(fixtures.SCENARIOS['s11-afternoon'], synthetic=True,
                                                 palette='baseline', display_name=display_name, locale=locale))
for doc in DOCS:
    path = PACKET / doc
    text = re.sub(r'`(assets/[\w./-]+)` SHA-256 `[0-9a-f]{64}`',
                  lambda m: f'`{m[1]}` SHA-256 `{sha(PACKET / m[1])}`', path.read_text(encoding='utf-8'))
    path.write_text(text, encoding='utf-8')
manifest = PACKET / 'EVIDENCE-MANIFEST.md'
files = sorted(p.relative_to(PACKET).as_posix() for p in PACKET.rglob('*')
               if p.is_file() and p != manifest and '__pycache__' not in p.parts)
rows = ''.join(f'| `{sha(PACKET / f)}` | `{f}` |\n' for f in files)
manifest.write_text(re.sub(r'(\| SHA-256 \| File \|\n\|---\|---\|\n)(?:\| `[0-9a-f]{64}` \| `[^`]+` \|\n)+',
                           lambda m: m[1] + rows, manifest.read_text(encoding='utf-8')), encoding='utf-8')
print(f'refreshed {len(SAMPLES)} sample PDFs and {len(files)} manifest rows')
