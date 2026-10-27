"""Noncanonical arithmetic tests; independent astronomical reference QA remains pending."""
import unittest
from fractions import Fraction
from research.kun04.provisional_math import (
    NAKSHATRA_WIDTH, PADA_WIDTH, VIMSHOTTARI_ORDER,
    VIMSHOTTARI_NOMINAL_YEARS, longitude, rational,
    panchanga_segment_numbers, natal_vimshottari_nominal_balance,
    nominal_subperiods,
)

EPS = Fraction(1, 10**10)

class Segments(unittest.TestCase):
    def test_zero_wrap_negative_inputs(self):
        self.assertEqual(longitude(-360), 0)
        self.assertEqual(longitude(360), 0)
        self.assertEqual(longitude("-1/3"), Fraction(1079,3))
        self.assertEqual(panchanga_segment_numbers(0,0)['tithi_number'],1)
        self.assertEqual(panchanga_segment_numbers(0,360)['tithi_number'],1)
        self.assertEqual(panchanga_segment_numbers(0,-EPS)['tithi_number'],30)

    def test_all_thirty_tithi_start_boundaries(self):
        for k in range(30):
            with self.subTest(k=k):
                boundary = 12*k
                self.assertEqual(panchanga_segment_numbers(0,boundary)['tithi_number'],k+1)
                self.assertEqual(panchanga_segment_numbers(0,boundary+EPS)['tithi_number'],k+1)
                self.assertEqual(panchanga_segment_numbers(0,boundary-EPS)['tithi_number'],(k if k else 30))

    def test_all_sixty_half_tithi_boundaries(self):
        for k in range(60):
            boundary = 6*k
            self.assertEqual(panchanga_segment_numbers(0,boundary)['karana_half_tithi_slot'],k+1)
            self.assertEqual(panchanga_segment_numbers(0,boundary-EPS)['karana_half_tithi_slot'],(k if k else 60))

    def test_all_108_pada_boundaries(self):
        for k in range(108):
            boundary = PADA_WIDTH*k
            result = panchanga_segment_numbers(0,boundary)
            self.assertEqual(result['nakshatra_number'],k//4 + 1)
            self.assertEqual(result['pada'],k%4+1)
            previous = panchanga_segment_numbers(0,boundary-EPS)
            self.assertEqual(previous['nakshatra_number'],((k-1)%108)//4+1)
            self.assertEqual(previous['pada'],((k-1)%108)%4+1)

    def test_all_yoga_boundaries(self):
        for k in range(27):
            boundary = NAKSHATRA_WIDTH*k
            self.assertEqual(panchanga_segment_numbers(0,boundary)['yoga_number'],k+1)
            self.assertEqual(panchanga_segment_numbers(0,boundary-EPS)['yoga_number'],(k if k else 27))
            self.assertEqual(panchanga_segment_numbers(0,boundary+EPS)['yoga_number'],k+1)

    def test_solar_lunar_elon_wrap(self):
        self.assertEqual(panchanga_segment_numbers(350, 2)['tithi_number'],2)
        self.assertEqual(panchanga_segment_numbers(2, 350)['tithi_number'],30)
        self.assertEqual(panchanga_segment_numbers(180,180)['karana_half_tithi_slot'],1)

    def test_invalid_values_refused(self):
        for item in [True, False, 'nan', 'inf', float('nan'), float('inf'), '', 'not number', '1/0', '1'*80]:
            with self.subTest(item=item), self.assertRaises(ValueError):
                rational(item)

class NominalDasha(unittest.TestCase):
    def test_cycle(self):
        self.assertEqual(sum(VIMSHOTTARI_NOMINAL_YEARS),120)
        self.assertEqual(len(set(VIMSHOTTARI_ORDER)),9)

    def test_each_nakshatra_starts_its_lord(self):
        for n in range(27):
            result = natal_vimshottari_nominal_balance(NAKSHATRA_WIDTH*n)
            self.assertEqual(result['nakshatra_number'],n+1)
            self.assertEqual(result['lord'],VIMSHOTTARI_ORDER[n%9])
            self.assertEqual(result['fraction_elapsed'],0)
            self.assertEqual(result['balance_nominal_years'],result['nominal_years'])

    def test_half_elapsed_ashwini(self):
        result = natal_vimshottari_nominal_balance(Fraction(20,3))
        self.assertEqual(result['lord'],'ketu')
        self.assertEqual(result['fraction_elapsed'],Fraction(1,2))
        self.assertEqual(result['balance_nominal_years'],Fraction(7,2))

    def test_early_late_boundary_transition(self):
        left=natal_vimshottari_nominal_balance(NAKSHATRA_WIDTH-EPS)
        right=natal_vimshottari_nominal_balance(NAKSHATRA_WIDTH)
        self.assertEqual(left['lord'],'ketu')
        self.assertGreater(left['balance_nominal_years'],0)
        self.assertLess(left['balance_nominal_years'],Fraction(7,10**8))
        self.assertEqual(right['lord'],'venus')
        self.assertEqual(right['balance_nominal_years'],20)

    def test_all_nine_nested_partitions_contiguous(self):
        for lord in VIMSHOTTARI_ORDER:
            for duration in [0, Fraction(1,2), 7, 17, 20, 120]:
                with self.subTest(lord=lord,duration=duration):
                    result=nominal_subperiods(duration,lord)
                    self.assertEqual(len(result),9)
                    self.assertEqual(result[0]['lord'],lord)
                    self.assertEqual(result[0]['start'],0)
                    self.assertEqual(result[-1]['end'],duration)
                    for a,b in zip(result,result[1:]):
                        self.assertEqual(a['end'],b['start'])
                        self.assertLessEqual(a['start'],a['end'])

    def test_refuse_invalid_subperiods(self):
        for duration, lord in [(-1,'ketu'),(1,'unknown'),('nan','moon')]:
            with self.assertRaises(ValueError):
                nominal_subperiods(duration,lord)

if __name__ == '__main__':
    unittest.main()
