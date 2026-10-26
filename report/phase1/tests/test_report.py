"""Independent synthetic-only tests for the owner-approved Phase 1 PDF renderer."""
import copy
import importlib.util
import io
import json
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
spec=importlib.util.spec_from_file_location('sabpuja_pdf_phase1',PHASE/'generate_report.py')
report=importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)
FIXTURE=json.loads((HERE/'fixtures/synthetic-new-delhi.json').read_text())

class Phase1PDFTests(unittest.TestCase):
    def test_exact_schema_fixture(self):
        self.assertIs(report.validate_engine_response(FIXTURE),FIXTURE)
        self.assertEqual(len(FIXTURE['chart']['planets']),9)
        self.assertEqual(len(FIXTURE['chart']['d9']['houses']),12)

    def test_d1_house_mismatch_rejected(self):
        data=copy.deepcopy(FIXTURE)
        data['chart']['planets']['sun']['whole_sign_house']=1
        with self.assertRaises(ValueError):report.validate_engine_response(data)

    def test_d9_house_mismatch_rejected(self):
        data=copy.deepcopy(FIXTURE)
        data['chart']['planets']['venus']['navamsa_whole_sign_house']=2
        with self.assertRaises(ValueError):report.validate_engine_response(data)

    def test_d9_duplicated_graha_rejected(self):
        data=copy.deepcopy(FIXTURE)
        data['chart']['d9']['houses'][4]['grahas'].append('venus')
        with self.assertRaises(ValueError):report.validate_engine_response(data)

    def test_d9_wrong_house_order_rejected(self):
        data=copy.deepcopy(FIXTURE)
        data['chart']['d9']['houses'][0]['house']=12
        with self.assertRaises(ValueError):report.validate_engine_response(data)

    def test_d9_lagna_mismatch_rejected(self):
        data=copy.deepcopy(FIXTURE)
        data['chart']['d9']['lagna_rashi']='Mesha'
        with self.assertRaises(ValueError):report.validate_engine_response(data)

    def test_missing_planet_rejected(self):
        data=copy.deepcopy(FIXTURE)
        data['chart']['planets'].pop('venus')
        with self.assertRaises(ValueError):report.validate_engine_response(data)

    def test_nonfinite_longitude_rejected(self):
        data=copy.deepcopy(FIXTURE)
        data['chart']['planets']['sun']['longitude_deg']=float('nan')
        with self.assertRaises(ValueError):report.validate_engine_response(data)

    def test_wrong_schema_rejected(self):
        data=copy.deepcopy(FIXTURE)
        data['chart']['schema_version']='0.2.0'
        with self.assertRaises(ValueError):report.validate_engine_response(data)

    def test_no_golden_certification_claim(self):
        data=copy.deepcopy(FIXTURE)
        data['chart']['validation_status']='VERIFIED'
        with self.assertRaises(ValueError):report.validate_engine_response(data)

    def test_token_authority(self):
        c=report.THEME['colors']
        self.assertEqual(c['saffron'],'#D35400')
        self.assertEqual(c['gold'],'#F4B400')
        self.assertEqual(c['ivory'],'#FFFBEF')
        self.assertNotIn('#681E30',c.values())
        self.assertEqual(report.THEME['title_family'],'Poppins')
        self.assertEqual(report.THEME['body_family'],'Inter')

    def test_full_pdf_fonts_and_page_contents(self):
        try:import fitz
        except ImportError:self.skipTest('Install PyMuPDF for PDF visual-structure QA')
        data=report.generate(FIXTURE,synthetic=True)
        self.assertTrue(data.startswith(b'%PDF-'))
        pdf=fitz.open(stream=data,filetype='pdf')
        self.assertEqual(len(pdf),8)
        fulltext=' '.join(p.get_text() for p in pdf)
        for item in ['D1 Lagna chart','D9 Navamsa chart','Uttara Ashadha','0.3.0','UNVERIFIED_GOLDEN_CHARTS','DEMONSTRATION ONLY']:
            self.assertIn(item,fulltext)
        self.assertNotIn('Vikash Kumar',fulltext)
        self.assertNotIn('8527544394',fulltext)
        fontnames=' '.join(str(f[3]) for p in pdf for f in p.get_fonts(full=True))
        self.assertIn('Inter',fontnames,'Actual approved body font not embedded')
        self.assertIn('Poppins',fontnames,'Actual approved heading font not embedded')

if __name__=='__main__':unittest.main()
