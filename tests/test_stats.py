import unittest

from skilldeck.evals.stats import net_lift, sign_test, summarize


class TestNetLift(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(net_lift(0, 0, 0), 0.0)

    def test_user_run(self):
        # 5W/1L/3T -> (5-1)/9
        self.assertAlmostEqual(net_lift(5, 1, 3), 4 / 9)

    def test_ties_dilute(self):
        self.assertGreater(net_lift(5, 1, 0), net_lift(5, 1, 6))

    def test_summary_format(self):
        s = summarize(5, 1, 3)
        self.assertIn("+44% net lift", s)
        self.assertIn("5W / 1L / 3T", s)
        self.assertIn("p=0.219", s)


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
