"""방어 판정·신선도 로직 단위 테스트.

스프레드시트에 실제로 적혀 있던 '방어' 값과 코드 계산이 일치하는지 검증한다.
표준 라이브러리 unittest 만 사용 → `python -m unittest` 로 바로 실행.
"""

import unittest
from datetime import date

from macau_fare_monitor import evaluate
from macau_fare_monitor.defense import DefenseStatus
from macau_fare_monitor.staleness import check as check_staleness


class TestDefense(unittest.TestCase):
    def test_ok_when_we_are_cheaper(self):
        # 에어마카오 2박3일 7/10: 우리 956,000 ≤ 시장 1,298,772
        r = evaluate(956000, 1298772)
        self.assertIs(r.status, DefenseStatus.OK)
        self.assertEqual(r.gap, 342772)
        self.assertEqual(r.label, "✅ OK")
        self.assertEqual(r.shortfall, 0)

    def test_ok_when_equal(self):
        r = evaluate(1058200, 1058200)
        self.assertIs(r.status, DefenseStatus.OK)
        self.assertEqual(r.label, "✅ OK")

    def test_fail_small_gap(self):
        # 에어마카오 2박3일 7/18: 우리 956,000 > 시장 926,668 → -29,332
        r = evaluate(956000, 926668)
        self.assertIs(r.status, DefenseStatus.FAIL)
        self.assertEqual(r.gap, -29332)
        self.assertEqual(r.shortfall, 29332)
        self.assertEqual(r.label, "🔴 방어실패 -29,332")

    def test_fail_large_gap(self):
        # 에어마카오 2박3일 7/23: 우리 1,182,000 > 시장 1,058,200 → -123,800
        r = evaluate(1182000, 1058200)
        self.assertEqual(r.label, "🔴 방어실패 -123,800")

    def test_fail_worst_case(self):
        # 에어마카오 2박3일 8/1: 우리 1,182,000 > 시장 1,009,118 → -172,882
        r = evaluate(1182000, 1009118)
        self.assertEqual(r.shortfall, 172882)

    def test_no_our_price(self):
        r = evaluate(None, 1088800)
        self.assertIs(r.status, DefenseStatus.NO_OUR_PRICE)
        self.assertEqual(r.label, "")
        self.assertIsNone(r.gap)

    def test_no_market(self):
        # 에어부산: 우리요금만 있고 시장최저 미수집
        r = evaluate(573000, None)
        self.assertIs(r.status, DefenseStatus.NO_MARKET)
        self.assertEqual(r.label, "")


class TestStaleness(unittest.TestCase):
    def test_fresh_same_day(self):
        r = check_staleness(date(2026, 6, 19), date(2026, 6, 19))
        self.assertFalse(r.is_stale)
        self.assertEqual(r.message, "")

    def test_stale_one_day(self):
        # 로그 탭의 '1일 전(stale)' 재현
        r = check_staleness(date(2026, 6, 19), date(2026, 6, 20))
        self.assertTrue(r.is_stale)
        self.assertEqual(r.age_days, 1)
        self.assertEqual(r.freshness_label, "1일 전(stale)")
        self.assertIn("데이터 미갱신", r.message)


if __name__ == "__main__":
    unittest.main()
