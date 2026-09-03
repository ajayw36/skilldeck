import unittest

from skilldeck.evals.stats import sign_test


class TestSignTest(unittest.TestCase):
    def test_no_data_is_p1(self):
        self.assertEqual(sign_test(0, 0), 1.0)

    def test_even_split_is_p1(self):
        self.assertAlmostEqual(sign_test(5, 5), 1.0, places=2)

    def test_clean_sweep_10(self):
        # P(10/10 one way) * 2 = 2/1024
        self.assertAlmostEqual(sign_test(10, 0), 2 / 1024, places=6)

    def test_symmetry(self):
        self.assertEqual(sign_test(8, 2), sign_test(2, 8))


if __name__ == "__main__":
    unittest.main()
