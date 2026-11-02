"""KUN-I18N-003: the Hindi editorial acceptance register stays traceable and honest.

`docs/i18n/review/kun-i18n-003/editorial-acceptance-register.json` keeps separate layers per item
(developer correction, engineering rendering verification, human Hindi language, human Jyotish
terminology, owner copy) plus the final customer release. `register_problems()` is the gate: it
decides nothing, it refuses a register in which

* a layer the canonical matrix below requires is missing, NOT_APPLICABLE or has an unknown status,
  or a layer it does not require is anything but NOT_APPLICABLE;
* a decided human or owner layer is unattributed, signed by an AI, lacks the exact reviewed commit
  and catalog SHA-256, or cites evidence that is not a committed signed file with a matching hash;
* a decision was made against catalog bytes that have since changed (stale);
* customer release is anything but PENDING or APPROVED, or is APPROVED without every required
  layer of every item positively ACCEPTED against the current catalogs and a signed owner release.

REJECTED and REVISED are decisions, never approvals: a revision has to be applied and then
ACCEPTED against the new catalog bytes before release. The adversarial tests below feed the gate
forged registers in memory; nothing here records or fabricates a review.
"""
import copy
import hashlib
import json
import re
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


def _text(value):
    return value.strip() if isinstance(value, str) else ''


def _evidence_problems(where, evidence, root):
    """Evidence must be a committed signed file under signed/ whose SHA-256 is stated and matches."""
    if not isinstance(evidence, dict):
        return [f'{where}: evidence must be {{"path", "sha256"}} of a committed signed file']
    path, digest = _text(evidence.get('path')), _text(evidence.get('sha256'))
    if not path.startswith(SIGNED_DIR) or '..' in Path(path).parts:
        return [f'{where}: evidence path must be inside {SIGNED_DIR}']
    if not HEX64.match(digest):
        return [f'{where}: evidence sha256 missing or malformed']
    file = root / path
    if not file.is_file():
        return [f'{where}: evidence file {path} is not in this tree']
    if sha256(file) != digest:
        return [f'{where}: evidence file hash does not match']
    return []


def _person_problems(where, person):
    if not isinstance(person, dict):
        return [f'{where}: no reviewer']
    problems = [f'{where}: reviewer {field} missing' for field in ('name', 'qualification', 'independence')
                if not _text(person.get(field))]
    if AI_NAMES.search(_text(person.get('name'))):
        problems.append(f'{where}: an AI cannot sign a human or owner layer')
    return problems


def _decision_problems(where, entry, catalogs, root):
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
    problems += _evidence_problems(where, entry.get('evidence'), root)
    if entry['status'] in ('REVISED', 'REJECTED') and not _text(entry.get('decision_text')):
        problems.append(f'{where}: {entry["status"]} needs the replacement wording or the reason')
    return problems


def register_problems(register, catalogs=None, root=ROOT):
    """Every reason this register is not an honest, traceable record (empty when sound).

    `root` is where evidence paths resolve: this tree in normal use, a temporary directory in the
    adversarial tests so that no stand-in signed file is ever written into the repository."""
    catalogs = catalogs or current_catalogs()
    problems = []
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
                problems += _decision_problems(where, entry, catalogs, root)
    src = register.get('reviewed_source', {})
    if (src.get('ui_catalog_sha256'), src.get('pdf_catalog_sha256')) != catalogs:
        problems.append('reviewed_source does not match the catalogs in this tree')
    release = register.get('customer_release', {})
    status = release.get('status')
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
        problems += _evidence_problems('customer_release', release.get('evidence'), root)
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

    def test_catalogs_still_declare_the_pending_human_review(self):
        for path in (UI_CATALOG, PDF_CATALOG):
            status = json.loads(path.read_text(encoding='utf-8'))['status']
            self.assertIn('pending independent human Hindi editorial review', status)


class AdversarialRegisters(unittest.TestCase):
    """Forged registers, built in memory only, that the gate must refuse."""

    SIGNED = 'docs/i18n/review/kun-i18n-003/signed/_test-only-signed-sheet.txt'

    def setUp(self):
        self.catalogs = current_catalogs()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        signed = self.root / self.SIGNED
        signed.parent.mkdir(parents=True)
        signed.write_text('stand-in for a signed sheet, in a temporary directory only\n')
        self.digest = sha256(signed)

    def problems(self, reg):
        return register_problems(reg, self.catalogs, self.root)

    def decision(self, status='ACCEPTED', name='Test Reviewer', **over):
        entry = {'status': status, 'reviewer': {'name': name, 'qualification': 'test', 'independence': 'test'},
                 'decision_date': '2026-11-03', 'reviewed_commit': 'c9f147bad9b50c5eb85585b0e3e952e49fb5ac40',
                 'reviewed_ui_catalog_sha256': self.catalogs[0], 'reviewed_pdf_catalog_sha256': self.catalogs[1],
                 'evidence': {'path': self.SIGNED, 'sha256': self.digest}, 'decision_text': None}
        entry.update(over)
        return entry

    def fully_accepted(self):
        reg = copy.deepcopy(REGISTER)
        for item in reg['items']:
            for layer in REQUIRED[item['id']]:
                item[layer] = self.decision()
        reg['customer_release'] = {'status': 'APPROVED', 'approved_by': {'name': 'Test Owner', 'qualification': 'owner',
                                   'independence': 'owner'}, 'date': '2026-11-04',
                                   'commit': 'c9f147bad9b50c5eb85585b0e3e952e49fb5ac40',
                                   'evidence': {'path': self.SIGNED, 'sha256': self.digest}}
        return reg

    def assertRefused(self, reg, fragment):
        problems = self.problems(reg)
        self.assertTrue(any(fragment in p for p in problems), problems[:8])

    def test_control_complete_signed_register_passes(self):
        self.assertEqual(self.problems(self.fully_accepted()), [])

    def test_all_not_applicable_with_release_approved(self):
        reg = copy.deepcopy(REGISTER)
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

    def test_review_layers_field_cannot_relax_the_matrix(self):
        reg = self.fully_accepted()
        reg['items'][12]['review_layers'] = 'L'  # item 13 without its owner layer
        reg['items'][12][O] = {'status': 'NOT_APPLICABLE'}
        self.assertRefused(reg, '13/owner_copy')

    def test_unknown_statuses(self):
        reg = self.fully_accepted()
        reg['items'][1][J]['status'] = 'APPROVED'
        self.assertRefused(reg, "2/human_jyotish_terminology: required layer has status 'APPROVED'")
        reg = copy.deepcopy(REGISTER)
        reg['customer_release']['status'] = 'RELEASED'
        self.assertRefused(reg, "customer_release has status 'RELEASED'")
        reg = copy.deepcopy(REGISTER)
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
        reg = copy.deepcopy(REGISTER)
        reg['items'][0][L] = self.decision(status='REJECTED')
        self.assertRefused(reg, 'REJECTED needs the replacement wording or the reason')

    def test_forged_or_unverifiable_evidence(self):
        cases = [('not a dict', 'evidence must be'),
                 ({'path': 'https://example.invalid/sheet.pdf', 'sha256': '0' * 64}, f'inside {SIGNED_DIR}'),
                 ({'path': SIGNED_DIR + '../REVIEW-PACKET.md', 'sha256': '0' * 64}, f'inside {SIGNED_DIR}'),
                 ({'path': SIGNED_DIR + 'missing.pdf', 'sha256': '0' * 64}, 'is not in this tree'),
                 ({'path': self.SIGNED, 'sha256': '0' * 64}, 'hash does not match'),
                 ({'path': self.SIGNED, 'sha256': 'abc'}, 'sha256 missing or malformed')]
        for evidence, fragment in cases:
            with self.subTest(evidence=evidence):
                reg = self.fully_accepted()
                reg['items'][0][L]['evidence'] = evidence
                self.assertRefused(reg, fragment)

    def test_stale_catalog_hash(self):
        reg = self.fully_accepted()
        reg['items'][3][J]['reviewed_ui_catalog_sha256'] = '0' * 64
        self.assertRefused(reg, '4/human_jyotish_terminology: stale')

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
        reg = copy.deepcopy(REGISTER)
        reg['items'].pop()
        self.assertRefused(reg, 'items must be exactly')
        reg = copy.deepcopy(REGISTER)
        reg['reviewed_source']['pdf_catalog_sha256'] = '1' * 64
        self.assertRefused(reg, 'reviewed_source does not match')

    def test_developer_or_ai_qa_cannot_pose_as_review(self):
        reg = copy.deepcopy(REGISTER)
        reg['items'][0]['developer_correction']['by'] = 'Claude (reviewed)'
        self.assertRefused(reg, 'developer layer')
        reg = copy.deepcopy(REGISTER)
        reg['items'][0]['engineering_rendering_verification']['verifier'] = 'ChatGPT, Hindi review'
        self.assertRefused(reg, 'engineering layer')


if __name__ == '__main__':
    unittest.main()
