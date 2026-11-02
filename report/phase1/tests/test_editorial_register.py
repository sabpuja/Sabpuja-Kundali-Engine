"""KUN-I18N-003: the Hindi editorial acceptance register stays traceable and honest.

`docs/i18n/review/kun-i18n-003/editorial-acceptance-register.json` keeps five separate layers per
item (developer correction, engineering rendering verification, human Hindi language, human
Jyotish terminology, owner copy) plus the final customer release. These tests do not decide
anything; they refuse a register in which a human approval is unattributed, recorded by an AI,
detached from the exact reviewed catalog bytes, or in which release is approved early.
"""
import hashlib
import json
import re
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / 'docs/i18n/review/kun-i18n-003'
REGISTER = json.loads((PACKET / 'editorial-acceptance-register.json').read_text(encoding='utf-8'))
UI_CATALOG = ROOT / 'prototype/kundali_prototype/static/i18n.json'
PDF_CATALOG = ROOT / 'report/phase1/report_i18n.json'
HUMAN = ('human_hindi_language', 'human_jyotish_terminology')
DECIDED = {'ACCEPTED', 'REVISED', 'REJECTED'}
AI_NAMES = re.compile(r'claude|chatgpt|\bgpt|openai|anthropic|copilot|gemini|\bai\b|assistant|\bbot\b|llm', re.I)
HEX40, HEX64 = re.compile(r'^[0-9a-f]{40}$'), re.compile(r'^[0-9a-f]{64}$')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Structure(unittest.TestCase):
    def test_every_review_item_and_layer_is_present(self):
        ids = [item['id'] for item in REGISTER['items']]
        self.assertEqual(ids, [str(n) for n in range(1, 19)] + [f'C{n}' for n in range(1, 7)])
        for item in REGISTER['items']:
            for layer in REGISTER['layers']:
                self.assertIn(layer, item, (item['id'], layer))

    def test_reviewed_source_is_the_catalog_in_this_tree(self):
        """The packet describes these exact catalog bytes; a catalog edit must update the packet."""
        src = REGISTER['reviewed_source']
        self.assertEqual(src['ui_catalog_sha256'], sha256(UI_CATALOG))
        self.assertEqual(src['pdf_catalog_sha256'], sha256(PDF_CATALOG))

    def test_each_item_is_on_the_decision_sheet(self):
        sheet = (PACKET / 'DECISION-SHEET.csv').read_text(encoding='utf-8').splitlines()
        self.assertEqual([line.split(',')[0] for line in sheet[1:]], [i['id'] for i in REGISTER['items']])


class Attribution(unittest.TestCase):
    def test_human_layers_need_a_real_named_human_and_exact_revision(self):
        current = (sha256(UI_CATALOG), sha256(PDF_CATALOG))
        for item in REGISTER['items']:
            for layer in HUMAN:
                entry = item[layer]
                with self.subTest(item=item['id'], layer=layer):
                    self.assertIn(entry['status'], {'PENDING', 'NOT_APPLICABLE'} | DECIDED)
                    if entry['status'] not in DECIDED:
                        continue
                    reviewer = entry['reviewer'] or {}
                    for field in ('name', 'qualification', 'independence'):
                        self.assertTrue((reviewer.get(field) or '').strip(), field)
                    self.assertIsNone(AI_NAMES.search(reviewer['name']), 'a human layer cannot be signed by an AI')
                    date.fromisoformat(entry['decision_date'])
                    self.assertRegex(entry['reviewed_commit'], HEX40)
                    self.assertRegex(entry['reviewed_ui_catalog_sha256'], HEX64)
                    self.assertRegex(entry['reviewed_pdf_catalog_sha256'], HEX64)
                    self.assertTrue((entry['evidence'] or '').strip(), 'signed decision sheet reference')
                    if entry['status'] == 'REVISED':
                        self.assertTrue((entry['decision_text'] or '').strip(), 'replacement wording')
                    # Stale approvals: valid only for the catalog bytes the reviewer saw.
                    self.assertEqual((entry['reviewed_ui_catalog_sha256'], entry['reviewed_pdf_catalog_sha256']), current,
                                     'catalog changed after this review; the reviewer must re-confirm')

    def test_owner_copy_needs_owner_attribution(self):
        for item in REGISTER['items']:
            entry = item['owner_copy']
            if entry['status'] in DECIDED:
                with self.subTest(item=item['id']):
                    self.assertTrue((entry['reviewer'] or {}).get('name'))
                    self.assertIsNone(AI_NAMES.search(entry['reviewer']['name']))
                    date.fromisoformat(entry['decision_date'])
                    self.assertRegex(entry['reviewed_commit'], HEX40)
                    self.assertTrue((entry['evidence'] or '').strip())

    def test_developer_and_ai_qa_stay_in_their_own_layers(self):
        for item in REGISTER['items']:
            self.assertIn(item['developer_correction']['status'], {'CORRECTED', 'NO_CHANGE'})
            self.assertIn('not a review', item['developer_correction']['by'])
            eng = item['engineering_rendering_verification']
            self.assertIn('not a human language review', eng['verifier'])
            self.assertRegex(eng['verified_commit'], HEX40)


class ReleaseGate(unittest.TestCase):
    def test_release_cannot_be_approved_while_any_gate_is_open(self):
        open_gates = []
        for item in REGISTER['items']:
            for layer in HUMAN + ('owner_copy',):
                status = item[layer]['status']
                if status == 'PENDING' or (status == 'REJECTED' and not (item[layer]['decision_text'] or '').strip()):
                    open_gates.append((item['id'], layer))
        if open_gates:
            self.assertEqual(REGISTER['customer_release']['status'], 'PENDING', open_gates[:5])

    def test_catalogs_still_declare_the_pending_human_review(self):
        for path in (UI_CATALOG, PDF_CATALOG):
            status = json.loads(path.read_text(encoding='utf-8'))['status']
            self.assertIn('pending independent human Hindi editorial review', status)


if __name__ == '__main__':
    unittest.main()
