import math
import unittest
from sabpuja_kundali.rules import normalize, sign, nakshatra, navamsa_sign, whole_sign_house

class PureRulesTests(unittest.TestCase):
    def test_normalized_zodiac(self):
        self.assertEqual(normalize(-1), 359)
        self.assertEqual(normalize(720), 0)
        with self.assertRaises(ValueError):
            normalize(math.nan)

    def test_rashi_boundaries(self):
        self.assertEqual(sign(0), "Mesha")
        self.assertEqual(sign(29.999), "Mesha")
        self.assertEqual(sign(30), "Vrishabha")
        self.assertEqual(sign(330), "Meena")

    def test_nakshatra_and_pada(self):
        self.assertEqual(nakshatra(0), {"index": 0, "name": "Ashwini", "pada": 1})
        self.assertEqual(nakshatra(12), {"index": 0, "name": "Ashwini", "pada": 4})
        self.assertEqual(nakshatra(359.999)["name"], "Revati")

    def test_navamsa_movable_fixed_dual(self):
        self.assertEqual(navamsa_sign(0), "Mesha")
        self.assertEqual(navamsa_sign(30), "Makara")
        self.assertEqual(navamsa_sign(60), "Tula")

    def test_whole_sign_houses(self):
        self.assertEqual(whole_sign_house(0, 0), 1)
        self.assertEqual(whole_sign_house(30, 0), 2)
        self.assertEqual(whole_sign_house(0, 330), 2)

if __name__ == "__main__":
    unittest.main()
