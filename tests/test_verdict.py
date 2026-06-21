"""마진 인지 판정(v2) 테스트."""

import unittest

from macau_fare_monitor import DEFAULT_CONFIG, classify
from macau_fare_monitor.verdict import Verdict

C = DEFAULT_CONFIG  # tie ±10,000 / over ≥150,000


class TestClassify(unittest.TestCase):
    def test_lose(self):
        # 에어마카오 2박3일 7/18: 우리 956,000 > 시장 926,668 → 열위
        r = classify(956000, 926668)
        self.assertIs(r.verdict, Verdict.LOSE)
        self.assertEqual(r.gap, -29332)
        self.assertEqual(r.label, "🔴 열위 -29,332")

    def test_win(self):
        r = classify(900000, 1000000)  # gap +100,000
        self.assertIs(r.verdict, Verdict.WIN)
        self.assertEqual(r.label, "✅ 우위 +100,000")

    def test_over_defended(self):
        r = classify(850000, 1050000)  # gap +200,000 ≥ 150,000
        self.assertIs(r.verdict, Verdict.OVER_DEFENDED)
        self.assertEqual(r.label, "🟦 과방어 +200,000")

    def test_tie_within_band(self):
        self.assertIs(classify(1000000, 1005000).verdict, Verdict.TIE)   # +5,000
        self.assertIs(classify(1000000, 995000).verdict, Verdict.TIE)    # -5,000

    def test_boundaries(self):
        # gap == tie_band → 아직 동률, +1 이면 우위
        self.assertIs(classify(1000000, 1010000).verdict, Verdict.TIE)   # +10,000
        self.assertIs(classify(1000000, 1010001).verdict, Verdict.WIN)   # +10,001
        # gap == over_defended → 과방어
        self.assertIs(classify(1000000, 1150000).verdict, Verdict.OVER_DEFENDED)

    def test_non_comparable(self):
        r = classify(900000, 1000000, comparable=False)
        self.assertIs(r.verdict, Verdict.NON_COMPARABLE)
        self.assertEqual(r.gap, 100000)  # 격차는 계산하되 승패는 안 매김

    def test_missing(self):
        self.assertIs(classify(None, 1000000).verdict, Verdict.NO_OUR_PRICE)
        self.assertIs(classify(900000, None).verdict, Verdict.NO_MARKET)


if __name__ == "__main__":
    unittest.main()
