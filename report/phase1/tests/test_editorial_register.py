"""KUN-I18N-003: the Hindi editorial acceptance register stays traceable and honest.

`docs/i18n/review/kun-i18n-003/editorial-acceptance-register.json` keeps separate layers per item
(developer correction, engineering rendering verification, human Hindi language, human Jyotish
terminology, owner copy) plus the final customer release. `register_problems()` is the gate: it
decides nothing, it refuses a register in which

* a layer the canonical matrix below requires is missing, NOT_APPLICABLE or has an unknown status,
  or a layer it does not require is anything but NOT_APPLICABLE;
* a decided human or owner layer is unattributed, signed by an AI, lacks the exact reviewed commit
  and catalog SHA-256, or cites evidence that is not the committed git blob of a signed file under
  signed/ (untracked, staged, modified, deleted, replaced and symlinked files fail; KUN-I18N-003C);
* a decision was made against catalog bytes that have since changed (stale);
* customer release is anything but PENDING or APPROVED, or is APPROVED without every required
  layer of every item positively ACCEPTED against the current catalogs and a signed owner release;
* a git SHA is only well formed rather than the exact object (KUN-I18N-003B): every decision's
  `reviewed_commit` must equal `reviewed_source.commit`; `reviewed_source` (commit, tree, catalog
  SHA-256 and git blob IDs) must match the catalogs in this tree and, where the git object database
  is present, the commit, its tree and the catalog blobs inside it; a release must name an explicit
  `release_candidate` (commit, tree, catalog hashes and blobs) that exists in git, contains the
  reviewed source and carries the reviewed catalog bytes, and `customer_release.commit` must equal it.

In a `git archive` run there is no object database: the catalogs are still bound by blob ID, and
a register with any decided layer or an approved release is refused as unverifiable there, so that
provenance is never assumed. No release SHA is hard-coded; the candidate is whatever the owner names.

The gate checks evidence paths, SHA-256 values and metadata only. It does not and cannot
authenticate a handwritten or electronic signature or a reviewer's identity; those remain
independently verifiable requirements for whoever accepts the release.

REJECTED and REVISED are decisions, never approvals: a revision has to be applied and then
ACCEPTED against the new catalog bytes before release. The adversarial tests below feed the gate
forged registers in memory; nothing here records or fabricates a review.
"""
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / 'docs/i18n/review/kun-i18n-003'
REGISTER_PATH = PACKET / 'editorial-acceptance-register.json'
REGISTER = json.loads(REGISTER_PATH.read_text(encoding='utf-8'))
UI_CATALOG = ROOT / 'prototype/kundali_prototype/static/i18n.json'
PDF_CATALOG = ROOT / 'report/phase1/report_i18n.json'
SIGNED_DIR = 'docs/i18n/review/kun-i18n-003/signed/'
UI_PATH, PDF_PATH = 'prototype/kundali_prototype/static/i18n.json', 'report/phase1/report_i18n.json'

L, J, O = 'human_hindi_language', 'human_jyotish_terminology', 'owner_copy'
GATED = (L, J, O)
# Canonical required-layer matrix, fixed here so that the register cannot relax it by editing
# its own `review_layers` field. Items 13 and 15 carry the owner copy decisions (Change A, B).
REQUIRED = {
    '1': {L, J}, '2': {J}, '3': {L, J}, '4': {J}, '5': {J}, '6': {J}, '7': {L, J},
    '8': {L}, '9': {L}, '10': {L}, '11': {L}, '12': {L}, '13': {L, O}, '14': {L},
    '15': {L, O}, '16': {L}, '17': {L}, '18': {L},
    'C1': {L}, 'C2': {L}, 'C3': {L}, 'C4': {L}, 'C5': {J}, 'C6': {L},
}
DECISIONS = {'ACCEPTED', 'REVISED', 'REJECTED'}
GATED_STATUSES = {'PENDING'} | DECISIONS
RELEASE_STATUSES = {'PENDING', 'APPROVED'}
AI_NAMES = re.compile(r'claude|chatgpt|\bgpt|openai|anthropic|copilot|gemini|\bai\b|assistant|\bbot\b|llm|language model', re.I)
HEX40, HEX64 = re.compile(r'^[0-9a-f]{40}$'), re.compile(r'^[0-9a-f]{64}$')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_catalogs():
    return sha256(UI_CATALOG), sha256(PDF_CATALOG)


def blob_id(path):
    """The git blob ID of a file's bytes, computable without a git object database."""
    data = path.read_bytes()
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def current_blobs(root=ROOT):
    return blob_id(root / UI_PATH), blob_id(root / PDF_PATH)


class GitObjects:
    """Read-only lookups in the git object database of `root` (absent in a `git archive` run)."""

    def __init__(self, root, frozen=False):
        self.root = Path(root).resolve()
        self._cache = {}
        self._frozen = frozen

    def frozen(self):
        """A view that also caches HEAD, index and toplevel lookups: one validation sees one state."""
        view = GitObjects(self.root, frozen=True)
        view._cache = dict(self._cache)
        return view

    def _git(self, *args):
        # Lookups of full SHAs are immutable and cached; anything naming HEAD or the index is not.
        immutable = all('HEAD' not in a for a in args) and args[0] in ('cat-file', 'rev-parse', 'merge-base') \
            and '--show-toplevel' not in args
        immutable = immutable or self._frozen
        if immutable and args in self._cache:
            return self._cache[args]
        result = self._git_uncached(*args)
        if immutable:
            self._cache[args] = result
        return result

    def _git_uncached(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        res = subprocess.run(['git', '-C', str(self.root), *args], capture_output=True, text=True, env=env)
        return res.stdout.strip() if res.returncode == 0 else None

    def available(self):
        if shutil.which('git') is None:
            return False
        top = self._git('rev-parse', '--show-toplevel')
        return top is not None and Path(top).resolve() == self.root

    def is_commit(self, sha):
        return HEX40.match(sha or '') is not None and self._git('cat-file', '-t', sha) == 'commit'

    def tree(self, commit):
        return self._git('rev-parse', '--verify', '-q', f'{commit}^{{tree}}')

    def blob(self, commit, path):
        return self._git('rev-parse', '--verify', '-q', f'{commit}:{path}')

    def is_ancestor(self, older, newer):
        return self._git('merge-base', '--is-ancestor', older, newer) is not None

    def index_blob(self, path):
        """The blob staged for `path` in the index, or None when untracked."""
        out = self._git('ls-files', '--stage', '--', path)
        return out.split()[1] if out and len(out.split()) >= 4 and '\n' not in out else None


def _text(value):
    return value.strip() if isinstance(value, str) else ''


def _evidence_problems(where, evidence, root, git):
    """Evidence is a signed file committed in git (KUN-I18N-003C), never merely present on disk.

    `{"path", "sha256", "commit"}`: `path` is a regular file (no symlink anywhere on the way)
    resolved inside signed/; `commit` is the commit that holds the signed file, in the history of
    the checked-out HEAD; the file's blob at that commit, at HEAD, in the index and in the working
    tree are one and the same, and its SHA-256 is the stated one. Untracked, staged-only, modified,
    deleted, replaced and symlinked files fail, and without the git object database a decided
    record fails closed."""
    if not isinstance(evidence, dict):
        return [f'{where}: evidence must be {{"path", "sha256", "commit"}} of a signed file committed in git']
    path, digest, commit = (_text(evidence.get(k)) for k in ('path', 'sha256', 'commit'))
    if not path.startswith(SIGNED_DIR) or '..' in Path(path).parts or path.endswith('/') or '\\' in path:
        return [f'{where}: evidence path must be inside {SIGNED_DIR}']
    if not HEX64.match(digest):
        return [f'{where}: evidence sha256 missing or malformed']
    if not HEX40.match(commit):
        return [f'{where}: evidence commit must be the full 40-hex SHA of the commit holding the signed file']
    root = Path(root)
    file = root / path
    walk = root
    for part in Path(path).parts:
        walk = walk / part
        if walk.is_symlink():
            return [f'{where}: evidence path goes through a symlink ({walk.relative_to(root).as_posix()})']
    if not file.is_file():
        return [f'{where}: evidence file {path} is not in this tree']
    if not file.resolve().is_relative_to((root / SIGNED_DIR).resolve()):
        return [f'{where}: evidence path must be inside {SIGNED_DIR}']
    if sha256(file) != digest:
        return [f'{where}: evidence file hash does not match']
    if not git.available():
        return [f'{where}: evidence cannot be verified without the git object database (use a clone)']
    if not git.is_commit(commit):
        return [f'{where}: evidence commit {commit} is not in the git object database']
    if not git.is_ancestor(commit, 'HEAD'):
        return [f'{where}: evidence commit {commit} is not in the history of this checkout']
    committed = git.blob(commit, path)
    if committed is None:
        return [f'{where}: evidence file is not in evidence commit {commit}']
    problems = []
    if git.blob('HEAD', path) != committed:
        problems.append(f'{where}: evidence file was removed or replaced after evidence commit {commit}')
    if git.index_blob(path) != committed:
        problems.append(f'{where}: evidence file is not tracked as committed (untracked, staged or removed)')
    if blob_id(file) != committed:
        problems.append(f'{where}: evidence file differs from its committed blob (modified)')
    return problems


def _person_problems(where, person):
    if not isinstance(person, dict):
        return [f'{where}: no reviewer']
    problems = [f'{where}: reviewer {field} missing' for field in ('name', 'qualification', 'independence')
                if not _text(person.get(field))]
    if AI_NAMES.search(_text(person.get('name'))):
        problems.append(f'{where}: an AI cannot sign a human or owner layer')
    return problems


def _snapshot_problems(where, snap, catalogs, blobs, git, require_git):
    """A named source revision: commit, tree, both catalog SHA-256 and git blob IDs, bound to the
    catalogs in this tree and, when the object database is present, to the git objects themselves."""
    if not isinstance(snap, dict):
        return [f'{where}: missing']
    fields = ('commit', 'tree', 'ui_catalog_blob', 'pdf_catalog_blob')
    bad = [f for f in fields if not HEX40.match(_text(snap.get(f)))]
    bad += [f for f in ('ui_catalog_sha256', 'pdf_catalog_sha256') if not HEX64.match(_text(snap.get(f)))]
    if bad:
        return [f'{where}: {", ".join(bad)} missing or malformed']
    problems = []
    if (snap['ui_catalog_sha256'], snap['pdf_catalog_sha256']) != catalogs:
        problems.append(f'{where} does not match the catalogs in this tree')
    if (snap['ui_catalog_blob'], snap['pdf_catalog_blob']) != blobs:
        problems.append(f'{where}: catalog blob IDs do not match the catalogs in this tree')
    if git.available():
        if not git.is_commit(snap['commit']):
            problems.append(f'{where}: commit {snap["commit"]} is not in the git object database')
        else:
            if git.tree(snap['commit']) != snap['tree']:
                problems.append(f'{where}: tree does not match commit {snap["commit"]}')
            if (git.blob(snap['commit'], UI_PATH), git.blob(snap['commit'], PDF_PATH)) != \
                    (snap['ui_catalog_blob'], snap['pdf_catalog_blob']):
                problems.append(f'{where}: the catalogs at commit {snap["commit"]} differ from the named blobs')
    elif require_git:
        problems.append(f'{where}: provenance cannot be verified without the git object database (use a clone)')
    return problems


def _decision_problems(where, entry, catalogs, root, git):
    problems = _person_problems(where, entry.get('reviewer'))
    try:
        date.fromisoformat(entry.get('decision_date') or '')
    except (TypeError, ValueError):
        problems.append(f'{where}: decision_date must be YYYY-MM-DD')
    if not HEX40.match(_text(entry.get('reviewed_commit'))):
        problems.append(f'{where}: reviewed_commit must be a full 40-hex SHA')
    reviewed = (_text(entry.get('reviewed_ui_catalog_sha256')), _text(entry.get('reviewed_pdf_catalog_sha256')))
    if not all(HEX64.match(h) for h in reviewed):
        problems.append(f'{where}: reviewed catalog SHA-256 values missing')
    elif reviewed != catalogs:
        problems.append(f'{where}: stale, the catalogs changed after this decision; the reviewer must re-confirm')
    problems += _evidence_problems(where, entry.get('evidence'), root, git)
    if entry['status'] in ('REVISED', 'REJECTED') and not _text(entry.get('decision_text')):
        problems.append(f'{where}: {entry["status"]} needs the replacement wording or the reason')
    return problems


def register_problems(register, catalogs=None, root=ROOT, git=None, blobs=None):
    """Every reason this register is not an honest, traceable record (empty when sound).

    `root` is where evidence paths resolve and `git` the object database consulted: this tree in
    normal use; a temporary synthetic git repository in the adversarial tests, so that no stand-in
    signed file or decision is ever written into this repository."""
    catalogs = catalogs or current_catalogs()
    blobs = blobs or current_blobs(root if (Path(root) / UI_PATH).is_file() else ROOT)
    git = (git or GitObjects(root)).frozen()
    problems = []
    src = register.get('reviewed_source', {}) or {}
    items = {item.get('id'): item for item in register.get('items', [])}
    if list(items) != list(REQUIRED):
        problems.append(f'items must be exactly {list(REQUIRED)}')
    for iid, required in REQUIRED.items():
        item = items.get(iid)
        if item is None:
            continue
        dev = item.get('developer_correction', {})
        if dev.get('status') not in ('CORRECTED', 'NO_CHANGE') or 'not a review' not in _text(dev.get('by')):
            problems.append(f'{iid}: developer layer must be CORRECTED/NO_CHANGE and say it is not a review')
        eng = item.get('engineering_rendering_verification', {})
        if eng.get('status') != 'PASS' or 'not a human language review' not in _text(eng.get('verifier')) \
                or not HEX40.match(_text(eng.get('verified_commit'))):
            problems.append(f'{iid}: engineering layer must be an attributed AI QA PASS, not a human review')
        for layer in GATED:
            entry = item.get(layer)
            where = f'{iid}/{layer}'
            if not isinstance(entry, dict):
                problems.append(f'{where}: missing')
                continue
            status = entry.get('status')
            if layer not in required:
                if status != 'NOT_APPLICABLE':
                    problems.append(f'{where}: not a required layer, must be NOT_APPLICABLE')
                continue
            if status not in GATED_STATUSES:
                problems.append(f'{where}: required layer has status {status!r}')
            elif status in DECISIONS:
                problems += _decision_problems(where, entry, catalogs, root, git)
                if _text(entry.get('reviewed_commit')) != _text(src.get('commit')):
                    problems.append(f'{where}: reviewed_commit is not the register\'s reviewed_source commit')
    release = register.get('customer_release', {}) or {}
    status = release.get('status')
    decided = status == 'APPROVED' or any(isinstance((items.get(iid) or {}).get(layer), dict)
                                          and items[iid][layer].get('status') in DECISIONS
                                          for iid in REQUIRED for layer in GATED)
    problems += _snapshot_problems('reviewed_source', src, catalogs, blobs, git, require_git=decided)
    if status not in RELEASE_STATUSES:
        problems.append(f'customer_release has status {status!r}')
    elif status == 'APPROVED':
        missing = [f'{iid}/{layer}' for iid, required in REQUIRED.items() for layer in sorted(required)
                   if (items.get(iid) or {}).get(layer, {}).get('status') != 'ACCEPTED']
        if missing:
            problems.append(f'customer_release APPROVED without ACCEPTED: {", ".join(missing[:6])}')
        problems += _person_problems('customer_release', release.get('approved_by'))
        try:
            date.fromisoformat(release.get('date') or '')
        except (TypeError, ValueError):
            problems.append('customer_release: date must be YYYY-MM-DD')
        if not HEX40.match(_text(release.get('commit'))):
            problems.append('customer_release: commit must be a full 40-hex SHA')
        problems += _evidence_problems('customer_release', release.get('evidence'), root, git)
        candidate = release.get('release_candidate')
        problems += _snapshot_problems('customer_release.release_candidate', candidate, catalogs, blobs, git,
                                       require_git=True)
        if isinstance(candidate, dict):
            if _text(release.get('commit')) != _text(candidate.get('commit')):
                problems.append('customer_release: commit is not the named release candidate')
            if git.available() and git.is_commit(_text(candidate.get('commit'))) \
                    and git.is_commit(_text(src.get('commit'))) \
                    and not git.is_ancestor(src['commit'], candidate['commit']):
                problems.append('customer_release: release candidate does not contain the reviewed source commit')
    elif release.get('release_candidate') is not None:
        problems += _snapshot_problems('customer_release.release_candidate', release['release_candidate'],
                                       catalogs, blobs, git, require_git=False)
    return problems


class RegisterInThisTree(unittest.TestCase):
    def test_register_is_sound(self):
        self.assertEqual(register_problems(REGISTER), [])

    def test_matrix_matches_the_review_layers_shown_to_reviewers(self):
        to_layers = {'L': L, 'J': J, 'Owner': O}
        for item in REGISTER['items']:
            shown = {to_layers[p] for p in re.split(r'\+', item['review_layers'])}
            self.assertEqual(shown, REQUIRED[item['id']], item['id'])

    def test_each_item_is_on_the_decision_sheet(self):
        sheet = (PACKET / 'DECISION-SHEET.csv').read_text(encoding='utf-8').splitlines()
        self.assertEqual([line.split(',')[0] for line in sheet[1:]], list(REQUIRED))

    def test_no_human_or_owner_decision_is_recorded_yet(self):
        """KUN-I18N-003 records no review. When an authentic signed decision arrives, update this
        test in the same commit that records it."""
        for item in REGISTER['items']:
            for layer in REQUIRED[item['id']]:
                self.assertEqual(item[layer]['status'], 'PENDING', (item['id'], layer))
        self.assertEqual(REGISTER['customer_release']['status'], 'PENDING')

    def test_reviewed_source_is_the_exact_git_commit_tree_and_catalog_blobs(self):
        """KUN-I18N-003B: the reviewed source is checked against git objects, not only its format."""
        git, src = GitObjects(ROOT), REGISTER['reviewed_source']
        self.assertEqual((src['ui_catalog_blob'], src['pdf_catalog_blob']), current_blobs())
        if not git.available():
            self.skipTest('git archive: catalogs bound by blob ID above; commit and tree need a clone')
        self.assertTrue(git.is_commit(src['commit']))
        self.assertEqual(git.tree(src['commit']), src['tree'])
        self.assertEqual(git.blob(src['commit'], UI_PATH), src['ui_catalog_blob'])
        self.assertEqual(git.blob(src['commit'], PDF_PATH), src['pdf_catalog_blob'])
        self.assertTrue(git.is_ancestor(src['commit'], 'HEAD'))

    def test_no_release_candidate_is_named_yet(self):
        self.assertIsNone(REGISTER['customer_release']['release_candidate'])
        self.assertIsNone(REGISTER['customer_release']['commit'])

    def test_catalogs_still_declare_the_pending_human_review(self):
        for path in (UI_CATALOG, PDF_CATALOG):
            status = json.loads(path.read_text(encoding='utf-8'))['status']
            self.assertIn('pending independent human Hindi editorial review', status)


class SyntheticGitRepo(unittest.TestCase):
    """Shared fixture: a synthetic git repository and in-memory registers bound to it."""

    SIGNED = 'docs/i18n/review/kun-i18n-003/signed/_test-only-signed-sheet.txt'

    @classmethod
    def setUpClass(cls):
        """A throwaway synthetic git repository in a temporary directory: the two catalogs copied
        byte for byte (so their SHA-256 and blob IDs are the real ones), a stand-in signed sheet,
        a 'reviewed source' commit, a later 'release candidate' commit, a commit that changes a
        catalog and an unrelated root commit. Real git objects, never this repository's history."""
        if shutil.which('git') is None:
            raise unittest.SkipTest('git is required for the provenance tests')
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.root = Path(tmp.name)
        cls.catalogs, cls.blobs = current_catalogs(), current_blobs()
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_AUTHOR_NAME='synthetic', GIT_AUTHOR_EMAIL='synthetic@example.invalid',
                   GIT_COMMITTER_NAME='synthetic', GIT_COMMITTER_EMAIL='synthetic@example.invalid',
                   GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')

        def git(*args):
            return subprocess.run(['git', '-C', str(cls.root), *args], check=True, capture_output=True,
                                  text=True, env=env).stdout.strip()

        def commit(message):
            git('add', '-A')
            git('commit', '-q', '--no-gpg-sign', '-m', message)
            return git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')

        git('init', '-q', '-b', 'synthetic')
        for rel, src in ((UI_PATH, UI_CATALOG), (PDF_PATH, PDF_CATALOG)):
            (cls.root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, cls.root / rel)
        cls.source = commit('synthetic reviewed source')
        signed = cls.root / cls.SIGNED
        signed.parent.mkdir(parents=True)
        signed.write_text('stand-in for a signed sheet, in a temporary directory only\n')
        cls.digest = sha256(signed)
        (cls.root / 'release-notes.txt').write_text('synthetic later commit\n')
        cls.candidate = commit('synthetic release candidate, holding the stand-in signed sheet')
        cls.run_git = staticmethod(git)
        with open(cls.root / PDF_PATH, 'ab') as fh:
            fh.write(b'\n')
        cls.changed = commit('synthetic catalog change')
        git('checkout', '-q', cls.candidate[0])  # working files back to the reviewed bytes
        git('checkout', '-q', '--orphan', 'unrelated')
        (cls.root / 'unrelated.txt').write_text('unrelated history\n')
        cls.unrelated = commit('synthetic unrelated root with the same catalogs')
        git('checkout', '-q', cls.candidate[0])
        cls.git = GitObjects(cls.root)

    def problems(self, reg, catalogs=None):
        return register_problems(reg, catalogs or self.catalogs, self.root, self.git)

    def snapshot(self, commit_tree):
        return {'commit': commit_tree[0], 'tree': commit_tree[1],
                'ui_catalog_blob': self.blobs[0], 'pdf_catalog_blob': self.blobs[1],
                'ui_catalog_sha256': self.catalogs[0], 'pdf_catalog_sha256': self.catalogs[1]}

    def decision(self, status='ACCEPTED', name='Test Reviewer', **over):
        entry = {'status': status, 'reviewer': {'name': name, 'qualification': 'test', 'independence': 'test'},
                 'decision_date': '2026-11-03', 'reviewed_commit': self.source[0],
                 'reviewed_ui_catalog_sha256': self.catalogs[0], 'reviewed_pdf_catalog_sha256': self.catalogs[1],
                 'evidence': self.evidence(), 'decision_text': None}
        entry.update(over)
        return entry

    def evidence(self, path=None, digest=None, commit=None):
        return {'path': path or self.SIGNED, 'sha256': digest or self.digest, 'commit': commit or self.candidate[0]}

    def pending(self):
        reg = copy.deepcopy(REGISTER)
        reg['reviewed_source'].update(self.snapshot(self.source))
        return reg

    def fully_accepted(self):
        reg = self.pending()
        for item in reg['items']:
            for layer in REQUIRED[item['id']]:
                item[layer] = self.decision()
        reg['customer_release'] = {'status': 'APPROVED', 'approved_by': {'name': 'Test Owner', 'qualification': 'owner',
                                   'independence': 'owner'}, 'date': '2026-11-04',
                                   'commit': self.candidate[0], 'release_candidate': self.snapshot(self.candidate),
                                   'evidence': self.evidence(), 'note': None}
        return reg

    def assertRefused(self, reg, fragment):
        problems = self.problems(reg)
        self.assertTrue(any(fragment in p for p in problems), problems[:8])



class AdversarialRegisters(SyntheticGitRepo):
    """Forged registers, built in memory only, that the gate must refuse."""

    def test_control_complete_signed_register_passes(self):
        self.assertEqual(self.problems(self.fully_accepted()), [])

    def test_all_not_applicable_with_release_approved(self):
        reg = self.pending()
        for item in reg['items']:
            for layer in GATED:
                item[layer] = {'status': 'NOT_APPLICABLE'}
        reg['customer_release']['status'] = 'APPROVED'
        self.assertRefused(reg, "required layer has status 'NOT_APPLICABLE'")
        self.assertRefused(reg, 'customer_release APPROVED without ACCEPTED')

    def test_partial_not_applicable(self):
        reg = self.fully_accepted()
        reg['items'][0][J] = {'status': 'NOT_APPLICABLE'}
        self.assertRefused(reg, "1/human_jyotish_terminology: required layer has status 'NOT_APPLICABLE'")
        reg = self.fully_accepted()
        reg['items'][14][O] = {'status': 'NOT_APPLICABLE'}  # item 15, owner Change B
        self.assertRefused(reg, "15/owner_copy: required layer has status 'NOT_APPLICABLE'")

    def test_one_mandatory_hindi_layer_not_applicable(self):
        reg = self.fully_accepted()
        reg['items'][7][L] = {'status': 'NOT_APPLICABLE'}  # item 8
        self.assertRefused(reg, "8/human_hindi_language: required layer has status 'NOT_APPLICABLE'")
        self.assertRefused(reg, 'customer_release APPROVED without ACCEPTED: 8/human_hindi_language')

    def test_one_mandatory_jyotish_layer_not_applicable(self):
        reg = self.fully_accepted()
        reg['items'][4][J] = {'status': 'NOT_APPLICABLE'}  # item 5
        self.assertRefused(reg, "5/human_jyotish_terminology: required layer has status 'NOT_APPLICABLE'")

    def test_owner_approval_missing_for_item_13_or_15(self):
        for index, iid in ((12, '13'), (14, '15')):
            for missing in ('deleted', 'pending', 'empty'):
                with self.subTest(item=iid, missing=missing):
                    reg = self.fully_accepted()
                    if missing == 'deleted':
                        del reg['items'][index][O]
                        fragment = f'{iid}/owner_copy: missing'
                    elif missing == 'pending':
                        reg['items'][index][O] = {'status': 'PENDING'}
                        fragment = f'customer_release APPROVED without ACCEPTED'
                    else:
                        reg['items'][index][O] = {}
                        fragment = f'{iid}/owner_copy: required layer has status None'
                    self.assertRefused(reg, fragment)
                    self.assertTrue(any(f'{iid}/owner_copy' in p for p in self.problems(reg)))

    def test_optional_layer_is_not_a_missing_mandatory_approval(self):
        """Item 2 needs only Jyotish; its language and owner layers are NOT_APPLICABLE and the
        complete control passes, so optional layers are never demanded."""
        reg = self.fully_accepted()
        self.assertEqual(reg['items'][1][L], {'status': 'NOT_APPLICABLE'})
        self.assertEqual(reg['items'][1][O], {'status': 'NOT_APPLICABLE'})
        self.assertEqual(self.problems(reg), [])

    def test_partial_approval_then_release(self):
        reg = self.fully_accepted()
        for item in reg['items'][9:]:
            for layer in REQUIRED[item['id']]:
                item[layer] = {'status': 'PENDING'}
        self.assertRefused(reg, 'customer_release APPROVED without ACCEPTED: 10/human_hindi_language')

    def test_review_layers_field_cannot_relax_the_matrix(self):
        reg = self.fully_accepted()
        reg['items'][12]['review_layers'] = 'L'  # item 13 without its owner layer
        reg['items'][12][O] = {'status': 'NOT_APPLICABLE'}
        self.assertRefused(reg, '13/owner_copy')

    def test_unknown_statuses(self):
        reg = self.fully_accepted()
        reg['items'][1][J]['status'] = 'APPROVED'
        self.assertRefused(reg, "2/human_jyotish_terminology: required layer has status 'APPROVED'")
        reg = self.pending()
        reg['customer_release']['status'] = 'RELEASED'
        self.assertRefused(reg, "customer_release has status 'RELEASED'")
        reg = self.pending()
        reg['items'][1][L] = {'status': 'PENDING'}  # item 2 has no language layer
        self.assertRefused(reg, '2/human_hindi_language: not a required layer')

    def test_rejected_or_revised_with_text_is_not_approval(self):
        for status in ('REJECTED', 'REVISED'):
            reg = self.fully_accepted()
            reg['items'][2][L] = self.decision(status=status, decision_text='a reason or replacement')
            self.assertRefused(reg, 'customer_release APPROVED without ACCEPTED: 3/human_hindi_language')
            reg['customer_release'] = copy.deepcopy(REGISTER['customer_release'])
            self.assertEqual(self.problems(reg), [])  # a recorded decision, release pending

    def test_rejected_or_revised_without_text(self):
        reg = self.pending()
        reg['items'][0][L] = self.decision(status='REJECTED')
        self.assertRefused(reg, 'REJECTED needs the replacement wording or the reason')

    def test_forged_or_unverifiable_evidence(self):
        cases = [('not a dict', 'evidence must be'),
                 ({'path': 'https://example.invalid/sheet.pdf', 'sha256': '0' * 64}, f'inside {SIGNED_DIR}'),
                 ({'path': SIGNED_DIR + '../REVIEW-PACKET.md', 'sha256': '0' * 64}, f'inside {SIGNED_DIR}'),
                 (self.evidence(path=SIGNED_DIR + 'missing.pdf'), 'is not in this tree'),
                 (self.evidence(digest='0' * 64), 'hash does not match'),
                 (self.evidence(digest='abc'), 'sha256 missing or malformed'),
                 ({'path': self.SIGNED, 'sha256': self.digest}, 'evidence commit must be the full 40-hex SHA')]
        for evidence, fragment in cases:
            with self.subTest(evidence=evidence):
                reg = self.fully_accepted()
                reg['items'][0][L]['evidence'] = evidence
                self.assertRefused(reg, fragment)

    def test_stale_ui_catalog_hash(self):
        reg = self.fully_accepted()
        reg['items'][3][J]['reviewed_ui_catalog_sha256'] = '0' * 64
        self.assertRefused(reg, '4/human_jyotish_terminology: stale')

    def test_stale_pdf_catalog_hash(self):
        reg = self.fully_accepted()
        reg['items'][12][O]['reviewed_pdf_catalog_sha256'] = '0' * 64  # owner Change A on old bytes
        self.assertRefused(reg, '13/owner_copy: stale')

    def test_catalog_change_after_review_makes_every_decision_stale(self):
        reg = self.fully_accepted()
        changed = (self.catalogs[0], 'f' * 64)  # as if the PDF catalog changed after the reviews
        problems = self.problems(reg, changed)
        self.assertTrue(any('stale' in p for p in problems))
        self.assertIn('reviewed_source does not match the catalogs in this tree', problems)

    def test_unauthorized_ai_approval(self):
        for name in ('Claude', 'ChatGPT QA', 'GPT-5', 'AI reviewer', 'review bot', 'Anthropic assistant'):
            with self.subTest(name=name):
                reg = self.fully_accepted()
                reg['items'][0][L]['reviewer']['name'] = name
                self.assertRefused(reg, 'an AI cannot sign')
                reg = self.fully_accepted()
                reg['customer_release']['approved_by']['name'] = name
                self.assertRefused(reg, 'customer_release: an AI cannot sign')

    def test_unattributed_or_untraceable_decision(self):
        for field, value, fragment in (('reviewer', None, 'no reviewer'), ('decision_date', '3 Nov', 'decision_date'),
                                       ('reviewed_commit', 'c9f147b', '40-hex'),
                                       ('reviewed_pdf_catalog_sha256', None, 'catalog SHA-256 values missing')):
            with self.subTest(field=field):
                reg = self.fully_accepted()
                reg['items'][0][L][field] = value
                self.assertRefused(reg, fragment)

    def test_release_needs_signed_owner_record(self):
        reg = self.fully_accepted()
        del reg['customer_release']['evidence']
        self.assertRefused(reg, 'customer_release: evidence')
        reg = self.fully_accepted()
        reg['customer_release']['commit'] = None
        self.assertRefused(reg, 'customer_release: commit')

    def test_missing_item_and_source_drift(self):
        reg = self.pending()
        reg['items'].pop()
        self.assertRefused(reg, 'items must be exactly')
        reg = self.pending()
        reg['reviewed_source']['pdf_catalog_sha256'] = '1' * 64
        self.assertRefused(reg, 'reviewed_source does not match')

    def test_developer_or_ai_qa_cannot_pose_as_review(self):
        reg = self.pending()
        reg['items'][0]['developer_correction']['by'] = 'Claude (reviewed)'
        self.assertRefused(reg, 'developer layer')
        reg = self.pending()
        reg['items'][0]['engineering_rendering_verification']['verifier'] = 'ChatGPT, Hindi review'
        self.assertRefused(reg, 'engineering layer')


class ExactCommitBinding(SyntheticGitRepo):
    """KUN-I18N-003B: well-formed but wrong SHAs, checked against real (synthetic) git objects."""

    def test_all_zero_or_wrong_review_sha(self):
        for sha in ('0' * 40, 'f' * 40, None):
            with self.subTest(sha=sha):
                reg = self.fully_accepted()
                reg['items'][0][L]['reviewed_commit'] = sha
                self.assertRefused(reg, "1/human_hindi_language: reviewed_commit is not the register's reviewed_source")
        for name, commit in (('release candidate', 'candidate'), ('catalog change', 'changed'),
                             ('unrelated root', 'unrelated')):
            with self.subTest(real_but_wrong=name):  # a real commit, just not the reviewed source
                reg = self.fully_accepted()
                reg['items'][12][O]['reviewed_commit'] = getattr(self, commit)[0]
                self.assertRefused(reg, "13/owner_copy: reviewed_commit is not the register's reviewed_source")

    def test_wrong_final_release_sha(self):
        for sha, fragment in (('f' * 40, 'commit is not the named release candidate'),
                              ('0' * 40, 'commit is not the named release candidate')):
            with self.subTest(sha=sha):
                reg = self.fully_accepted()
                reg['customer_release']['commit'] = sha
                self.assertRefused(reg, fragment)
        reg = self.fully_accepted()
        reg['customer_release']['commit'] = self.source[0]  # the reviewed source, not the named candidate
        self.assertRefused(reg, 'commit is not the named release candidate')

    def test_release_candidate_must_be_named_and_real(self):
        reg = self.fully_accepted()
        reg['customer_release']['release_candidate'] = None
        self.assertRefused(reg, 'customer_release.release_candidate: missing')
        for sha in ('f' * 40, '0' * 40):
            with self.subTest(sha=sha):
                reg = self.fully_accepted()
                reg['customer_release']['release_candidate']['commit'] = sha
                reg['customer_release']['commit'] = sha
                self.assertRefused(reg, f'commit {sha} is not in the git object database')

    def test_release_candidate_tree_catalogs_and_history(self):
        reg = self.fully_accepted()
        reg['customer_release']['release_candidate']['tree'] = self.source[1]
        self.assertRefused(reg, 'release_candidate: tree does not match commit')
        reg = self.fully_accepted()  # a real later commit whose PDF catalog is not the reviewed bytes
        reg['customer_release']['release_candidate'].update(commit=self.changed[0], tree=self.changed[1])
        reg['customer_release']['commit'] = self.changed[0]
        self.assertRefused(reg, f'the catalogs at commit {self.changed[0]} differ from the named blobs')
        reg = self.fully_accepted()  # same catalogs, but history that does not contain the review
        reg['customer_release']['release_candidate'].update(commit=self.unrelated[0], tree=self.unrelated[1])
        reg['customer_release']['commit'] = self.unrelated[0]
        self.assertRefused(reg, 'release candidate does not contain the reviewed source commit')
        reg = self.fully_accepted()
        reg['customer_release']['release_candidate']['pdf_catalog_sha256'] = '0' * 64
        self.assertRefused(reg, 'release_candidate does not match the catalogs in this tree')

    def test_tampered_reviewed_source(self):
        cases = (({'commit': '0' * 40}, 'is not in the git object database'),
                 ({'commit': self.candidate[0]}, 'reviewed_source: tree does not match commit'),
                 ({'tree': self.candidate[1]}, 'reviewed_source: tree does not match commit'),
                 ({'commit': self.changed[0], 'tree': self.changed[1]}, 'differ from the named blobs'),
                 ({'pdf_catalog_blob': '0' * 40}, 'catalog blob IDs do not match'),
                 ({'ui_catalog_blob': None}, 'ui_catalog_blob missing or malformed'),
                 ({'tree': 'abc'}, 'tree missing or malformed'))
        for change, fragment in cases:
            with self.subTest(change=change):
                reg = self.fully_accepted()
                reg['reviewed_source'].update(change)
                for item in reg['items']:  # decisions follow the tampered commit, so only provenance can fail
                    for layer in REQUIRED[item['id']]:
                        item[layer]['reviewed_commit'] = reg['reviewed_source']['commit']
                self.assertRefused(reg, fragment)

    def test_without_git_objects_a_decided_register_is_unverifiable(self):
        no_git = GitObjects(Path(tempfile.mkdtemp(dir=self.root.parent)))
        self.addCleanup(shutil.rmtree, no_git.root)
        self.assertFalse(no_git.available())
        self.assertEqual(register_problems(self.pending(), self.catalogs, self.root, no_git), [])
        problems = register_problems(self.fully_accepted(), self.catalogs, self.root, no_git)
        self.assertIn('reviewed_source: provenance cannot be verified without the git object database (use a clone)',
                      problems)
        self.assertTrue(any(p.startswith('customer_release.release_candidate: provenance cannot') for p in problems))

    def test_positive_control_is_bound_to_real_objects(self):
        reg = self.fully_accepted()
        self.assertEqual(self.problems(reg), [])
        self.assertTrue(self.git.is_ancestor(self.source[0], self.candidate[0]))
        self.assertNotEqual(self.source[0], self.candidate[0])  # the candidate may differ from the source



class SignedEvidenceInGit(SyntheticGitRepo):
    """KUN-I18N-003C: a signed file only on disk is not evidence; it must be the committed blob.
    Each test changes the synthetic repository and restores it."""

    def all_evidence(self, reg, evidence):
        for item in reg['items']:
            for layer in REQUIRED[item['id']]:
                item[layer]['evidence'] = dict(evidence)
        reg['customer_release']['evidence'] = dict(evidence)
        return reg

    def scratch(self, rel, text):
        path = self.root / rel
        path.write_text(text)
        self.addCleanup(lambda: path.unlink() if path.exists() or path.is_symlink() else None)
        return path

    def test_untracked_signed_file_is_refused(self):
        """QA reproduction: every evidence reference replaced by a never-committed file with its true hash."""
        rel = SIGNED_DIR + 'never-committed-approval.txt'
        path = self.scratch(rel, 'never committed\n')
        reg = self.all_evidence(self.fully_accepted(), self.evidence(path=rel, digest=sha256(path)))
        problems = self.problems(reg)
        self.assertIn(f'1/human_hindi_language: evidence file is not in evidence commit {self.candidate[0]}', problems)
        self.assertIn(f'customer_release: evidence file is not in evidence commit {self.candidate[0]}', problems)

    def test_staged_but_not_committed_is_refused(self):
        rel = SIGNED_DIR + 'staged-only.txt'
        path = self.scratch(rel, 'staged only\n')
        self.run_git('add', rel)
        self.addCleanup(self.run_git, 'rm', '-q', '--cached', rel)
        reg = self.fully_accepted()
        reg['items'][0][L]['evidence'] = self.evidence(path=rel, digest=sha256(path))
        self.assertRefused(reg, 'evidence file is not in evidence commit')

    def test_tracked_but_modified_is_refused(self):
        path = self.root / self.SIGNED
        original = path.read_bytes()
        self.addCleanup(path.write_bytes, original)
        path.write_text('altered after signing\n')
        reg = self.fully_accepted()
        reg['items'][0][L]['evidence'] = self.evidence(digest=sha256(path))  # hash of the altered bytes
        self.assertRefused(reg, '1/human_hindi_language: evidence file differs from its committed blob (modified)')
        reg['items'][0][L]['evidence'] = self.evidence()  # the signed hash no longer matches the file
        self.assertRefused(reg, '1/human_hindi_language: evidence file hash does not match')

    def test_deleted_is_refused(self):
        path = self.root / self.SIGNED
        self.addCleanup(self.run_git, 'checkout', '-q', 'HEAD', '--', self.SIGNED)
        path.unlink()
        self.assertRefused(self.fully_accepted(), f'evidence file {self.SIGNED} is not in this tree')
        self.run_git('rm', '-q', '--cached', self.SIGNED)
        self.addCleanup(self.run_git, 'reset', '-q', 'HEAD', '--', self.SIGNED)
        self.assertRefused(self.fully_accepted(), f'evidence file {self.SIGNED} is not in this tree')

    def test_replaced_after_the_evidence_commit_is_refused(self):
        path = self.root / self.SIGNED
        original = path.read_bytes()
        self.run_git('checkout', '-q', '-b', 'replaced', self.candidate[0])
        path.write_text('replaced in a later commit\n')
        self.run_git('commit', '-q', '--no-gpg-sign', '-am', 'synthetic replacement of the signed sheet')
        self.addCleanup(self.run_git, 'checkout', '-q', self.candidate[0])
        reg = self.fully_accepted()
        reg['items'][0][L]['evidence'] = self.evidence(digest=sha256(path))
        self.assertRefused(reg, 'evidence file was removed or replaced after evidence commit')
        self.assertTrue(original)

    def test_symlinks_and_escapes_are_refused(self):
        outside = self.root / 'outside.txt'
        outside.write_text('outside the signed directory\n')
        self.addCleanup(outside.unlink)
        for name, target in (('link-inside.txt', self.root / self.SIGNED), ('link-outside.txt', outside)):
            with self.subTest(name=name):
                rel = SIGNED_DIR + name
                (self.root / rel).symlink_to(target)
                self.addCleanup((self.root / rel).unlink)
                reg = self.fully_accepted()
                reg['items'][0][L]['evidence'] = self.evidence(path=rel, digest=sha256(target))
                self.assertRefused(reg, 'evidence path goes through a symlink')
        for rel in ('/etc/hostname', SIGNED_DIR + '../../REVIEW-PACKET.md', 'signed/x.txt', SIGNED_DIR):
            with self.subTest(path=rel):
                reg = self.fully_accepted()
                reg['items'][0][L]['evidence'] = self.evidence(path=rel)
                self.assertRefused(reg, f'evidence path must be inside {SIGNED_DIR}')

    def test_blob_missing_from_the_named_commit(self):
        reg = self.fully_accepted()  # the sheet was added after the reviewed source commit
        reg['items'][0][L]['evidence'] = self.evidence(commit=self.source[0])
        self.assertRefused(reg, f'evidence file is not in evidence commit {self.source[0]}')
        reg = self.fully_accepted()  # a commit holding the file, outside this checkout's history
        reg['items'][0][L]['evidence'] = self.evidence(commit=self.unrelated[0])
        self.assertRefused(reg, f'evidence commit {self.unrelated[0]} is not in the history of this checkout')
        reg = self.fully_accepted()
        reg['items'][0][L]['evidence'] = self.evidence(commit='f' * 40)
        self.assertRefused(reg, f'evidence commit {"f" * 40} is not in the git object database')

    def test_decided_evidence_without_git_fails_closed(self):
        no_git_root = Path(tempfile.mkdtemp(dir=self.root.parent))
        self.addCleanup(shutil.rmtree, no_git_root)
        (no_git_root / self.SIGNED).parent.mkdir(parents=True)
        shutil.copyfile(self.root / self.SIGNED, no_git_root / self.SIGNED)
        problems = register_problems(self.fully_accepted(), self.catalogs, no_git_root, GitObjects(no_git_root))
        self.assertIn('1/human_hindi_language: evidence cannot be verified without the git object database (use a clone)',
                      problems)

    def test_positive_control_uses_committed_evidence(self):
        self.assertEqual(self.git.blob(self.candidate[0], self.SIGNED), blob_id(self.root / self.SIGNED))
        self.assertEqual(self.git.index_blob(self.SIGNED), blob_id(self.root / self.SIGNED))
        self.assertEqual(self.problems(self.fully_accepted()), [])


if __name__ == '__main__':
    unittest.main()
