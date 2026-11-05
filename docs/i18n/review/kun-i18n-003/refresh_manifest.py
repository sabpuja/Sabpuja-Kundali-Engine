"""Refresh the packet's reproducible assets and hashes after an approved catalog change.

Run from the repository root:  PYTHONPATH=src:prototype python docs/i18n/review/kun-i18n-003/refresh_manifest.py
1. Regenerates the three sample PDFs from the synthetic fixture `s11-afternoon` with the current
   renderer and catalogs (Change A, for example, changes the English one).
2. Rewrites every "`assets/...` SHA-256 `<hash>`" statement in the packet documents.
3. Rewrites the file table in EVIDENCE-MANIFEST.md from the files on disk, except the live
   decision record editorial-acceptance-register.json (KUN-GOV-SIMPLE-001).
Options (facts read from git, never a decision):
  --pin-source COMMIT         after an approved catalog change is committed as COMMIT, re-pin the
                              register's reviewed_source (commit, tree, catalog SHA-256, blob IDs)
                              in a follow-up commit; earlier decisions then show as stale, by design.
  --release-candidate COMMIT  fill customer_release.release_candidate from COMMIT for the owner;
                              status, commit and the owner's GitHub-recorded release directive are
                              recorded separately, only on the owner's explicit instruction.
Both refuse a commit whose catalogs differ from the catalogs in this tree.
It records no review and changes no catalog. Page images (assets/en-hi-page-NN.png) are not
regenerated here; after Change A, regenerate en-hi-page-10.png before asking for review.
`report/phase1/tests/test_review_packet_assets.py` fails until this has been run.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'report/phase1/tests')]
from report.phase1 import premium_report as premium  # noqa: E402
import test_premium_name as fixtures  # noqa: E402
from test_review_packet_assets import DOCS, LIVE_RECORD, SAMPLES  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(commit):
    """commit, tree, and the SHA-256 and blob ID of both catalogs at COMMIT, read from git."""
    def git(*args, raw=False):
        out = subprocess.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True).stdout
        return out if raw else out.decode().strip()
    full = git('rev-parse', '--verify', f'{commit}^{{commit}}')
    snap = {'commit': full, 'tree': git('rev-parse', f'{full}^{{tree}}')}
    for key, rel in (('ui', 'prototype/kundali_prototype/static/i18n.json'), ('pdf', 'report/phase1/report_i18n.json')):
        data = git('cat-file', 'blob', f'{full}:{rel}', raw=True)
        if data != (ROOT / rel).read_bytes():
            raise SystemExit(f'{rel} at {full} differs from this tree; refusing')
        snap[f'{key}_catalog_blob'] = git('rev-parse', f'{full}:{rel}')
        snap[f'{key}_catalog_sha256'] = hashlib.sha256(data).hexdigest()
    return snap


args = argparse.ArgumentParser()
args.add_argument('--pin-source')
args.add_argument('--release-candidate')
args = args.parse_args()
if args.pin_source or args.release_candidate:
    reg_path = PACKET / 'editorial-acceptance-register.json'
    register = json.loads(reg_path.read_text(encoding='utf-8'))
    if args.pin_source:
        register['reviewed_source'].update(snapshot(args.pin_source))
    if args.release_candidate:
        register['customer_release']['release_candidate'] = snapshot(args.release_candidate)
    reg_path.write_text(json.dumps(register, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


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
               if p.is_file() and p != manifest and p.name != LIVE_RECORD and '__pycache__' not in p.parts)
rows = ''.join(f'| `{sha(PACKET / f)}` | `{f}` |\n' for f in files)
manifest.write_text(re.sub(r'(\| SHA-256 \| File \|\n\|---\|---\|\n)(?:\| `[0-9a-f]{64}` \| `[^`]+` \|\n)+',
                           lambda m: m[1] + rows, manifest.read_text(encoding='utf-8')), encoding='utf-8')
print(f'refreshed {len(SAMPLES)} sample PDFs and {len(files)} manifest rows')
