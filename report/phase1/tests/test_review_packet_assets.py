"""KUN-I18N-003: every reviewer asset the packet points to is committed and matches its manifest.

The packet (`docs/i18n/review/kun-i18n-003/`) tells reviewers to open sample PDFs, page images and
screenshots. This guard fails if any referenced asset is absent from the tree (for example hidden
by the root `.gitignore` `*.pdf` rule), if a file is missing from `EVIDENCE-MANIFEST.md`, if a
SHA-256 stated in the manifest or next to a path in the packet differs from the file, or if the
three sample PDFs are not exactly what the current renderer produces from the synthetic fixture
`s11-afternoon`. Removing a reference does not satisfy it: the manifest must list every file in
the package and every listed file must exist.
"""
import hashlib
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
PACKET = ROOT / 'docs/i18n/review/kun-i18n-003'
MANIFEST = PACKET / 'EVIDENCE-MANIFEST.md'
DOCS = ('README.md', 'REVIEW-PACKET.md', 'EVIDENCE-MANIFEST.md', 'DECISION-SHEET.md',
        'EDITORIAL-ACCEPTANCE-REGISTER.md', 'CHANGE-A-ENGLISH-PAGE10.md', 'CHANGE-B-SCHEMA-WORDING.md')
ROW = re.compile(r'^\| `([0-9a-f]{64})` \| `([^`]+)` \|$')
REF = re.compile(r'assets/[\w./*-]+')
INLINE = re.compile(r'`(assets/[\w./-]+)` SHA-256 `([0-9a-f]{64})`')
SAMPLES = {'assets/sample-en-anonymous.pdf': ('en', None),
           'assets/sample-hi-anonymous.pdf': ('hi', None),
           'assets/sample-hi-named-devanagari.pdf': ('hi', 'क्षत्रिय प्रियंका सिद्धार्थ')}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    rows = [ROW.match(line) for line in MANIFEST.read_text(encoding='utf-8').splitlines()]
    return {m[2]: m[1] for m in rows if m}


class PacketAssets(unittest.TestCase):
    def test_manifest_lists_every_package_file_and_only_those(self):
        on_disk = {p.relative_to(PACKET).as_posix() for p in PACKET.rglob('*')
                   if p.is_file() and p != MANIFEST and '__pycache__' not in p.parts}
        self.assertEqual(set(manifest()), on_disk)

    def test_every_manifest_hash_matches(self):
        for name, digest in manifest().items():
            with self.subTest(name):
                self.assertTrue((PACKET / name).is_file(), f'{name} is not in this tree')
                self.assertEqual(sha256(PACKET / name), digest)

    def test_every_referenced_asset_exists_and_is_in_the_manifest(self):
        listed = manifest()
        for doc in DOCS:
            for ref in REF.findall((PACKET / doc).read_text(encoding='utf-8')):
                ref = ref.rstrip('.')
                with self.subTest(doc=doc, ref=ref):
                    if ref.endswith('/'):
                        matches = [p for p in (PACKET / ref).glob('*') if p.is_file()]
                    else:
                        matches = [p for p in PACKET.glob(ref.replace('NN', '[0-9][0-9]')) if p.is_file()]
                    self.assertTrue(matches, f'{doc} refers to {ref}, which is not in this tree')
                    for path in matches:
                        self.assertIn(path.relative_to(PACKET).as_posix(), listed)

    def test_inline_hashes_in_the_packet_match(self):
        for doc in DOCS:
            for ref, digest in INLINE.findall((PACKET / doc).read_text(encoding='utf-8')):
                with self.subTest(doc=doc, ref=ref):
                    self.assertEqual(sha256(PACKET / ref), digest)

    def test_assets_are_tracked_by_git_when_run_in_a_checkout(self):
        """In a working tree, an ignored or untracked asset fails here (a `git archive` run has no
        .git; there the existence checks above already fail for anything not committed)."""
        if not (ROOT / '.git').exists():
            self.skipTest('not a git checkout; existence checks cover a git archive')
        tracked = set(subprocess.run(['git', 'ls-files', '--', str(PACKET.relative_to(ROOT))], cwd=ROOT,
                                     capture_output=True, text=True, check=True).stdout.split())
        for name in manifest():
            with self.subTest(name):
                self.assertIn((PACKET / name).relative_to(ROOT).as_posix(), tracked)

    def test_sample_pdfs_are_the_current_renderer_output_from_the_synthetic_fixture(self):
        import fitz
        from report.phase1 import premium_report as premium
        import test_premium_name as fixtures
        for name, (locale, display_name) in SAMPLES.items():
            with self.subTest(name):
                data = premium.generate(fixtures.SCENARIOS['s11-afternoon'], synthetic=True, palette='baseline',
                                        display_name=display_name, locale=locale)
                self.assertEqual(hashlib.sha256(data).hexdigest(), sha256(PACKET / name))
                self.assertEqual(fitz.open(stream=data, filetype='pdf').page_count, 10)


if __name__ == '__main__':
    unittest.main()
