"""KUN-I18N-003: the Hindi editorial acceptance register stays traceable and honest.

`docs/i18n/review/kun-i18n-003/editorial-acceptance-register.json` keeps separate layers per item
(developer correction, engineering rendering verification, human Hindi language, human Jyotish
terminology, owner copy) plus the final customer release. `register_problems()` is the gate: it
decides nothing, it refuses a register in which

* a layer the canonical matrix below requires is missing, NOT_APPLICABLE or has an unknown status,
  or a layer it does not require is anything but NOT_APPLICABLE;
* a decided human or owner layer is unattributed, attributed to an AI, lacks the exact reviewed
  commit and catalog SHA-256, or has no GitHub record (an issue, PR or comment URL in this
  repository) where the decision is written down;
* a decision was made against catalog bytes that have since changed (stale);
* customer release is anything but PENDING or APPROVED, or is APPROVED without every required
  layer of every item positively ACCEPTED against the current catalogs and a separate, explicit
  owner release directive recorded in GitHub (an owner copy decision is never a release);
* a git SHA is only well formed rather than the exact object (KUN-I18N-003B): every decision's
  `reviewed_commit` must equal `reviewed_source.commit`; `reviewed_source` (commit, tree, catalog
  SHA-256 and git blob IDs) must match the catalogs in this tree and, where the git object database
  is present, the commit, its tree and the catalog blobs inside it; a release must name an explicit
  `release_candidate` (commit, tree, catalog hashes and blobs) that exists in git, contains the
  reviewed source and carries the reviewed catalog bytes, and `customer_release.commit` must equal it.

KUN-GOV-SIMPLE-001 (issue #75): no signed sheet, attestation form, signature or qualification
statement is required. The owner decides in chat; the decision is recorded accurately in a GitHub
issue or PR, and the register cites that record. A GitHub record relaying a chat decision is an
audit note, not proof of identity; an AI may record a decision (`recorded_by`) but is never the
decider. Human Hindi and Jyotish reviewers may give their feedback as GitHub comments.

In a `git archive` run there is no object database: the catalogs are still bound by blob ID and an
approved release is refused as unverifiable. No release SHA is hard-coded.

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
# A decision's audit record: an issue, PR or comment in this repository (KUN-GOV-SIMPLE-001).
RECORD_URL = re.compile(r'^https://github\.com/sabpuja/Sabpuja-Kundali-Engine/(issues|pull)/[1-9][0-9]*'
                        r'(#(issuecomment|pullrequestreview|discussion_r)-[0-9]+)?$')
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
# The owner's recorded approval of copy Changes A and B (KUN-GOV-SIMPLE-001, issue #75).
ISSUE_75 = 'https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/75'
OWNER_COPY_SOURCE = '84fe981c79573ab753b5d7baadf2ff4aa49e819c'
OWNER_COPY_WORDING = {'13': ('Hindi text (available as a separate edition)',),
                      '15': ('The D9 house fields use chart schema 0.3.0.', 'D9 भाव के फ़ील्ड चार्ट स्कीमा 0.3.0 के अनुसार हैं।')}


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

    def __init__(self, root, frozen=False, revision='HEAD'):
        self.root = Path(root).resolve()
        self._cache = {}
        self._frozen = frozen
        self.revision = revision  # the approval-record revision being validated

    def frozen(self, revision=None):
        """A view that also caches HEAD, index and toplevel lookups: one validation sees one state."""
        view = GitObjects(self.root, frozen=True, revision=revision or self.revision)
        view._cache = dict(self._cache)
        return view

    def read(self, rev, path):
        """The committed bytes of `path` at `rev`, or None (cached for full SHAs or a frozen view)."""
        key = ('read', rev, path)
        if key in self._cache:
            return self._cache[key]
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        res = subprocess.run(['git', '-C', str(self.root), 'cat-file', 'blob', f'{rev}:{path}'],
                             capture_output=True, env=env)
        result = res.stdout if res.returncode == 0 else None
        if self._frozen or HEX40.match(rev):
            self._cache[key] = result
        return result

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


def _record_problems(where, record):
    """The decision is written down in GitHub: an issue, PR or comment URL in this repository."""
    if not RECORD_URL.match(_text(record)):
        return [f'{where}: record must be the GitHub issue, PR or comment URL in this repository that '
                'records the decision']
    return []


def _person_problems(where, person):
    """A named human decider. No qualification, independence statement or signature is required."""
    name = _text(person.get('name')) if isinstance(person, dict) else _text(person)
    if not name:
        return [f'{where}: no named human decider']
    if AI_NAMES.search(name):
        return [f'{where}: an AI cannot decide a human or owner layer or the release']
    return []


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


def _decision_problems(where, entry, catalogs, owner):
    if owner:  # the owner's own decision, made in chat and recorded in GitHub
        problems = _person_problems(where, entry.get('decided_by'))
        if not _text(entry.get('decision_text')):
            problems.append(f'{where}: decision_text must state the owner\'s decision')
    else:
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
        problems.append(f'{where}: stale, the catalogs changed after this decision; the decider must re-confirm')
    problems += _record_problems(where, entry.get('record'))
    if entry['status'] in ('REVISED', 'REJECTED') and not _text(entry.get('decision_text')):
        problems.append(f'{where}: {entry["status"]} needs the replacement wording or the reason')
    return problems


def register_problems(register, catalogs=None, root=ROOT, git=None, blobs=None, revision='HEAD'):
    """Every reason this register is not an honest, traceable record (empty when sound).

    `root` is the tree checked and `git` the object database consulted: this tree in normal use; a
    temporary synthetic git repository in the adversarial tests, so that no stand-in decision is ever
    written into this repository."""
    catalogs = catalogs or current_catalogs()
    blobs = blobs or current_blobs(root if (Path(root) / UI_PATH).is_file() else ROOT)
    git = (git or GitObjects(root)).frozen(revision)
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
                problems += _decision_problems(where, entry, catalogs, owner=layer == O)
                if _text(entry.get('reviewed_commit')) != _text(src.get('commit')):
                    problems.append(f'{where}: reviewed_commit is not the register\'s reviewed_source commit')
    release = register.get('customer_release', {}) or {}
    status = release.get('status')
    # Decided layers are bound to the catalog bytes by SHA-256 and blob ID in every mode; the commit
    # itself is checked wherever git is present. Only an approved release needs git (its candidate).
    problems += _snapshot_problems('reviewed_source', src, catalogs, blobs, git, require_git=status == 'APPROVED')
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
        if not _text(release.get('decision_text')):
            problems.append('customer_release: decision_text must state the owner\'s release directive')
        problems += _record_problems('customer_release', release.get('record'))
        copy_records = {_text((items.get(iid) or {}).get(O, {}).get('record')) for iid in REQUIRED
                        if O in REQUIRED[iid]}
        if _text(release.get('record')) in copy_records:
            problems.append('customer_release: needs its own explicit owner release directive; an owner copy '
                            'decision is not a release')
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



REGISTER_REL = 'docs/i18n/review/kun-i18n-003/editorial-acceptance-register.json'


def committed_register_problems(revision, root=ROOT, git=None):
    """Validate the register exactly as committed at `revision`, the approval-record commit.

    The register is read from git, not from the working tree, and the catalogs at `revision` must be the
    catalogs being checked. No register ever names its own commit: `revision` is supplied by whoever
    validates (for a release, the owner's release candidate or a later commit)."""
    git = git or GitObjects(root)
    if not git.available():
        return [f'approval record {revision}: cannot be verified without the git object database (use a clone)']
    full = git._git('rev-parse', '--verify', '-q', f'{revision}^{{commit}}')
    if full is None:
        return [f'approval record {revision}: not a commit in the git object database']
    raw = git.read(full, REGISTER_REL)
    if raw is None:
        return [f'approval record {full}: has no {REGISTER_REL}']
    problems = []
    blobs = current_blobs(root if (Path(root) / UI_PATH).is_file() else ROOT)
    if (git.blob(full, UI_PATH), git.blob(full, PDF_PATH)) != blobs:
        problems.append(f'approval record {full}: its catalogs are not the catalogs being checked')
    try:
        register = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        return problems + [f'approval record {full}: register is not valid JSON']
    return problems + register_problems(register, root=root, git=git, blobs=blobs, revision=full)

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

    def test_owner_changes_a_and_b_are_the_recorded_owner_approval(self):
        """KUN-GOV-SIMPLE-001: items 13 and 15 `owner_copy` are PENDING or exactly the owner's approval of
        Changes A and B, made in chat (issue #73), merged on owner instruction (PR #74) and recorded in
        issue #75, against the reviewed source and the catalogs in this tree. No signature is involved."""
        src = REGISTER['reviewed_source']
        for item in REGISTER['items']:
            if item['id'] not in OWNER_COPY_WORDING:
                continue
            entry = item[O]
            with self.subTest(item=item['id']):
                if entry['status'] == 'PENDING':
                    continue
                self.assertEqual(entry['status'], 'ACCEPTED')
                self.assertEqual(entry['decided_by'], 'Sabpuja owner')
                self.assertEqual(entry['source'], 'chat owner instruction recorded in GitHub issue')
                self.assertEqual(entry['record'], ISSUE_75)
                self.assertEqual(entry['decision_date'], '2026-11-04')
                self.assertEqual(entry['reviewed_commit'], OWNER_COPY_SOURCE)
                self.assertEqual(src['commit'], OWNER_COPY_SOURCE)
                self.assertEqual((entry['reviewed_ui_catalog_sha256'], entry['reviewed_pdf_catalog_sha256']),
                                 current_catalogs())
                for text in OWNER_COPY_WORDING[item['id']] + ('issue #73', 'PR #74'):
                    self.assertIn(text, entry['decision_text'])
                self.assertNotIn('evidence', entry)
                self.assertEqual(item[L]['status'], 'PENDING', 'the owner decision is not the Hindi review')

    def test_owner_and_human_layers_stay_separate(self):
        """An owner decision never fills a human language or Jyotish layer, and no AI is the decider."""
        for item in REGISTER['items']:
            for layer in (L, J):
                entry = item[layer]
                if entry['status'] in DECISIONS:
                    self.assertNotIn('decided_by', entry, (item['id'], layer))
                    self.assertFalse(AI_NAMES.search(_text((entry.get('reviewer') or {}).get('name'))))
            owner = item[O]
            if owner['status'] in DECISIONS:
                self.assertFalse(AI_NAMES.search(_text(owner.get('decided_by'))), item['id'])

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

    def test_catalogs_still_declare_the_pending_human_review(self):
        for path in (UI_CATALOG, PDF_CATALOG):
            status = json.loads(path.read_text(encoding='utf-8'))['status']
            self.assertIn('pending independent human Hindi editorial review', status)


class SyntheticGitRepo(unittest.TestCase):
    """Shared fixture: a synthetic git repository and in-memory registers bound to it."""

    OWNER_RECORD = 'https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/9001'
    REVIEW_RECORD = 'https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/9002#issuecomment-1'
    RELEASE_RECORD = 'https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/9003'

    @classmethod
    def setUpClass(cls):
        """A throwaway synthetic git repository in a temporary directory: the two catalogs copied
        byte for byte (so their SHA-256 and blob IDs are the real ones), a 'reviewed source' commit, a
        later 'release candidate' commit, a commit that changes a catalog and an unrelated root
        commit. Real git objects, never this repository's history."""
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
        (cls.root / 'release-notes.txt').write_text('synthetic later commit\n')
        cls.candidate = commit('synthetic release candidate')
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
        """A human reviewer's decision given as a GitHub comment: no signature or qualification form."""
        entry = {'status': status, 'reviewer': {'name': name}, 'decision_date': '2026-11-03',
                 'reviewed_commit': self.source[0], 'reviewed_ui_catalog_sha256': self.catalogs[0],
                 'reviewed_pdf_catalog_sha256': self.catalogs[1], 'record': self.REVIEW_RECORD,
                 'decision_text': None}
        entry.update(over)
        return entry

    def owner_decision(self, status='ACCEPTED', **over):
        """The owner's chat decision as recorded in a GitHub issue (KUN-GOV-SIMPLE-001)."""
        entry = {'status': status, 'decided_by': 'Test Owner', 'source': 'chat owner instruction recorded in GitHub issue',
                 'record': self.OWNER_RECORD, 'decision_date': '2026-11-04', 'reviewed_commit': self.source[0],
                 'reviewed_ui_catalog_sha256': self.catalogs[0], 'reviewed_pdf_catalog_sha256': self.catalogs[1],
                 'decision_text': 'approve the change exactly as documented',
                 'recorded_by': 'Claude (developer), transcribing the GitHub record; not the decider'}
        entry.update(over)
        return entry

    def pending(self):
        reg = copy.deepcopy(REGISTER)
        reg['reviewed_source'].update(self.snapshot(self.source))
        for item in reg['items']:  # the in-memory baseline is all PENDING, whatever this tree records
            for layer in REQUIRED[item['id']]:
                item[layer] = {'status': 'PENDING'}
        reg['customer_release'] = {'status': 'PENDING', 'release_candidate': None, 'commit': None}
        return reg

    def fully_accepted(self):
        reg = self.pending()
        for item in reg['items']:
            for layer in REQUIRED[item['id']]:
                item[layer] = self.owner_decision() if layer == O else self.decision()
        reg['customer_release'] = {'status': 'APPROVED', 'approved_by': {'name': 'Test Owner'}, 'date': '2026-11-05',
                                   'source': 'chat owner instruction recorded in GitHub issue',
                                   'record': self.RELEASE_RECORD, 'decision_text': 'release this candidate',
                                   'commit': self.candidate[0], 'release_candidate': self.snapshot(self.candidate),
                                   'note': None}
        return reg

    def assertRefused(self, reg, fragment):
        problems = self.problems(reg)
        self.assertTrue(any(fragment in p for p in problems), problems[:8])


class AdversarialRegisters(SyntheticGitRepo):
    """Forged registers, built in memory only, that the gate must refuse."""

    def test_control_complete_register_passes_without_any_signature(self):
        reg = self.fully_accepted()
        self.assertEqual(self.problems(reg), [])
        records = json.dumps([[item[layer] for layer in GATED] for item in reg['items']] + [reg['customer_release']])
        for word in ('signed', 'signature', 'qualification', 'evidence', 'attestation'):
            self.assertNotIn(word, records)

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
                        fragment = 'customer_release APPROVED without ACCEPTED'
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
            reg['customer_release'] = {'status': 'PENDING', 'release_candidate': None, 'commit': None}
            self.assertEqual(self.problems(reg), [])  # a recorded decision, release pending

    def test_rejected_or_revised_without_text(self):
        reg = self.pending()
        reg['items'][0][L] = self.decision(status='REJECTED')
        self.assertRefused(reg, 'REJECTED needs the replacement wording or the reason')

    def test_decision_needs_a_github_record(self):
        """KUN-GOV-SIMPLE-001: the audit trail is a GitHub record in this repository, nothing else."""
        for record in (None, '', 'approved in chat', 'https://example.invalid/issues/1',
                       'http://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/75',
                       'https://github.com/someone/other-repo/issues/75',
                       'https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/75/../../evil',
                       'docs/i18n/review/kun-i18n-003/signed/sheet.pdf'):
            with self.subTest(record=record):
                for index, layer in ((0, L), (0, J), (12, O)):
                    reg = self.fully_accepted()
                    reg['items'][index][layer]['record'] = record
                    self.assertRefused(reg, f'{reg["items"][index]["id"]}/{layer}: record must be the GitHub')

    def test_no_signature_qualification_or_attestation_is_demanded(self):
        reg = self.pending()
        reg['items'][12][O] = self.owner_decision()  # Change A: decided_by, record, text; nothing else
        reg['items'][0][J] = self.decision()         # reviewer name and a GitHub comment only
        self.assertEqual(self.problems(reg), [])

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
                self.assertRefused(reg, '1/human_hindi_language: an AI cannot decide')
                reg = self.fully_accepted()
                reg['items'][14][O]['decided_by'] = name
                self.assertRefused(reg, '15/owner_copy: an AI cannot decide')
                reg = self.fully_accepted()
                reg['customer_release']['approved_by']['name'] = name
                self.assertRefused(reg, 'customer_release: an AI cannot decide')

    def test_ai_may_record_but_not_decide(self):
        reg = self.pending()
        reg['items'][14][O] = self.owner_decision(recorded_by='ChatGPT, transcribing the owner chat decision')
        self.assertEqual(self.problems(reg), [])

    def test_owner_decision_cannot_fill_a_human_layer(self):
        reg = self.pending()
        owner_as_reviewer = self.owner_decision()  # no `reviewer`: the owner is not the Hindi editor
        reg['items'][12][L] = owner_as_reviewer
        self.assertRefused(reg, '13/human_hindi_language: no named human decider')

    def test_unattributed_or_untraceable_decision(self):
        for field, value, fragment in (('reviewer', None, 'no named human decider'),
                                       ('decision_date', '3 Nov', 'decision_date'),
                                       ('reviewed_commit', 'c9f147b', '40-hex'),
                                       ('reviewed_pdf_catalog_sha256', None, 'catalog SHA-256 values missing')):
            with self.subTest(field=field):
                reg = self.fully_accepted()
                reg['items'][0][L][field] = value
                self.assertRefused(reg, fragment)
        for field, fragment in (('decided_by', 'no named human decider'), ('decision_text', 'decision_text')):
            with self.subTest(field=field):
                reg = self.fully_accepted()
                reg['items'][12][O][field] = ''
                self.assertRefused(reg, f'13/owner_copy: {fragment}')

    def test_release_needs_its_own_owner_directive(self):
        """Owner copy approvals (Changes A and B) never approve the release by themselves."""
        reg = self.fully_accepted()
        reg['customer_release']['record'] = self.OWNER_RECORD  # the copy decision's record reused
        self.assertRefused(reg, 'customer_release: needs its own explicit owner release directive')
        reg = self.fully_accepted()
        del reg['customer_release']['record']
        self.assertRefused(reg, 'customer_release: record must be the GitHub')
        reg = self.fully_accepted()
        reg['customer_release']['decision_text'] = ''
        self.assertRefused(reg, "customer_release: decision_text")
        reg = self.fully_accepted()
        reg['customer_release']['commit'] = None
        self.assertRefused(reg, 'customer_release: commit')

    def test_owner_copy_approvals_alone_never_release(self):
        reg = self.pending()
        reg['items'][12][O] = self.owner_decision()
        reg['items'][14][O] = self.owner_decision()
        reg['customer_release'].update(status='APPROVED')
        self.assertRefused(reg, 'customer_release APPROVED without ACCEPTED')
        self.assertRefused(reg, 'customer_release: record must be the GitHub')

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

    def test_without_git_objects_decisions_are_bound_by_catalog_bytes_and_a_release_fails_closed(self):
        no_git = GitObjects(Path(tempfile.mkdtemp(dir=self.root.parent)))
        self.addCleanup(shutil.rmtree, no_git.root)
        self.assertFalse(no_git.available())
        self.assertEqual(register_problems(self.pending(), self.catalogs, self.root, no_git), [])
        decided = self.fully_accepted()
        decided['customer_release'] = {'status': 'PENDING', 'release_candidate': None, 'commit': None}
        self.assertEqual(register_problems(decided, self.catalogs, self.root, no_git), [])
        problems = register_problems(decided, (self.catalogs[0], 'f' * 64), self.root, no_git)
        self.assertTrue(any('stale' in p for p in problems))  # still bound to the catalog bytes
        problems = register_problems(self.fully_accepted(), self.catalogs, self.root, no_git)
        self.assertIn('reviewed_source: provenance cannot be verified without the git object database (use a clone)',
                      problems)
        self.assertTrue(any(p.startswith('customer_release.release_candidate: provenance cannot') for p in problems))

    def test_positive_control_is_bound_to_real_objects(self):
        reg = self.fully_accepted()
        self.assertEqual(self.problems(reg), [])
        self.assertTrue(self.git.is_ancestor(self.source[0], self.candidate[0]))
        self.assertNotEqual(self.source[0], self.candidate[0])  # the candidate may differ from the source


class ApprovalRecordCommit(SyntheticGitRepo):
    """The register is validated as committed at the approval-record revision; no register names its
    own commit."""

    def record(self, register, branch):
        """Commit `register` on a synthetic branch from the candidate."""
        self.run_git('checkout', '-q', '-b', branch, self.candidate[0])
        self.addCleanup(self.run_git, 'checkout', '-q', '-f', self.candidate[0])
        path = self.root / REGISTER_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(register, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        self.run_git('add', '-A')
        self.run_git('commit', '-q', '--no-gpg-sign', '-m', f'synthetic approval record ({branch})')
        return self.run_git('rev-parse', 'HEAD')

    def test_genuine_approval_record_commit(self):
        register = self.fully_accepted()
        revision = self.record(register, 'approval-record')
        self.assertEqual(committed_register_problems(revision, self.root, self.git), [])
        self.assertNotIn(revision, json.dumps(register))  # no self-reference

    def test_committed_record_with_a_bad_github_record_is_refused(self):
        register = self.fully_accepted()
        register['items'][12][O]['record'] = 'approved in chat'
        revision = self.record(register, 'record-without-github')
        self.assertTrue(any(p.startswith('13/owner_copy: record must be the GitHub')
                            for p in committed_register_problems(revision, self.root, self.git)))

    def test_revision_without_register_or_not_a_commit(self):
        self.assertIn(f'approval record {self.source[0]}: has no {REGISTER_REL}',
                      committed_register_problems(self.source[0], self.root, self.git))
        self.assertIn(f'approval record {"f" * 40}: not a commit in the git object database',
                      committed_register_problems('f' * 40, self.root, self.git))

    def test_objectless_archive_with_an_approved_release_fails_closed(self):
        archive = Path(tempfile.mkdtemp(dir=self.root.parent))
        self.addCleanup(shutil.rmtree, archive)
        revision = self.record(self.fully_accepted(), 'record-for-archive')
        tar = subprocess.run(['git', '-C', str(self.root), 'archive', revision], capture_output=True, check=True)
        subprocess.run(['tar', '-x', '-C', str(archive)], input=tar.stdout, check=True)
        no_git = GitObjects(archive)
        self.assertFalse(no_git.available())
        self.assertEqual(committed_register_problems(revision, archive, no_git),
                         [f'approval record {revision}: cannot be verified without the git object database (use a clone)'])
        register = json.loads((archive / REGISTER_REL).read_text(encoding='utf-8'))
        problems = register_problems(register, self.catalogs, archive, no_git)
        self.assertIn('reviewed_source: provenance cannot be verified without the git object database (use a clone)',
                      problems)


if __name__ == '__main__':
    unittest.main()
