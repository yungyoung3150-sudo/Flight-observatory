"""컴플레인 가드레일(비대칭·인당 임계 경보) 테스트.

기본 임계: 안전 < 5만 / 🟠주의 5만~10만(이슈) / 🔴경보 ≥ 10만(컴플레인).
초과액(인당) = (우리2인 - 시장2인) / 2.
"""

import unittest
from datetime import date

from macau_fare_monitor import alert_for_row, classify, load_fares
from macau_fare_monitor.alert import AlertLevel
from macau_fare_monitor.models import FareRow, Product


class TestClassify(unittest.TestCase):
    def test_we_cheaper_is_safe(self):
        a = classify(1_000_000, 1_200_000)   # 인당 -100,000
        self.assertIs(a.level, AlertLevel.SAFE)
        self.assertEqual(a.surcharge_pp, -100_000)
        self.assertTrue(a.margin_review)     # 과하게 쌈 → 인상 검토(정보)

    def test_slightly_pricier_is_safe(self):
        a = classify(1_080_000, 1_000_000)   # 인당 +40,000 (<5만)
        self.assertIs(a.level, AlertLevel.SAFE)
        self.assertEqual(a.surcharge_pp, 40_000)

    def test_just_below_issue_is_safe(self):
        a = classify(1_099_996, 1_000_000)   # 인당 +49,998 (<5만)
        self.assertIs(a.level, AlertLevel.SAFE)

    def test_issue_threshold_is_watch_orange(self):
        # 5만원 이상 = 이슈(🟠 주의)
        a = classify(1_100_000, 1_000_000)   # 인당 +50,000
        self.assertIs(a.level, AlertLevel.WATCH)
        self.assertIn("🟠 주의", a.label)

    def test_complaint_threshold_is_alarm_red(self):
        # 10만원 이상 = 컴플레인(🔴 경보)
        a = classify(1_200_000, 1_000_000)   # 인당 +100,000
        self.assertIs(a.level, AlertLevel.ALARM)
        self.assertTrue(a.is_alarm)
        self.assertIn("🔴 경보", a.label)

    def test_no_market_is_manual_check_not_safe(self):
        a = classify(900_000, None)
        self.assertIs(a.level, AlertLevel.NO_MARKET)
        self.assertTrue(a.needs_manual_check)
        self.assertNotIn("안전", a.label)

    def test_reference_only_is_non_comparable(self):
        a = classify(900_000, 1_000_000, comparable=False)
        self.assertIs(a.level, AlertLevel.NON_COMPARABLE)

    def test_no_our_price(self):
        self.assertIs(classify(None, 1_000_000).level, AlertLevel.NO_OUR_PRICE)

    def test_asymmetry_cheaper_never_alarms(self):
        # 아무리 싸도 경보 아님(가드레일은 '우리가 비싼 쪽'만)
        self.assertIs(classify(500_000, 2_000_000).level, AlertLevel.SAFE)

    def test_dumping_suspect_only_with_outlier_signal(self):
        a = classify(1_300_000, 1_000_000, outlier_suspected=True)  # ALARM + 이상치
        self.assertTrue(a.dumping_suspect)
        b = classify(1_300_000, 1_000_000, outlier_suspected=False)
        self.assertFalse(b.dumping_suspect)


class TestAlertOnRealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_fares()

    def test_no_alarms_on_prelaunch_snapshot(self):
        # 검증된 사실: 최악 초과액(에어마카오 2박3일 8/1) = 인당 86,441 < 100,000 → 경보 0
        alarms = [r for r in self.rows if alert_for_row(r).level is AlertLevel.ALARM]
        self.assertEqual(alarms, [])

    def test_worst_case_is_watch_8_1(self):
        row = next(r for r in self.rows
                   if r.product is Product.AIRMACAU_2N3D and r.depart_date == date(2026, 8, 1))
        a = alert_for_row(row)
        self.assertIs(a.level, AlertLevel.WATCH)
        self.assertEqual(a.surcharge_pp, 86_441)

    def test_reference_rows_excluded(self):
        # 7/10~7/17 에어마카오 2박3일 = NX825 미운항(참고가) → 비교불가
        ref = next(r for r in self.rows
                   if r.product is Product.AIRMACAU_2N3D and r.depart_date == date(2026, 7, 10))
        self.assertIs(alert_for_row(ref).level, AlertLevel.NON_COMPARABLE)

    def test_air_busan_routes_to_manual_check(self):
        busan = [r for r in self.rows if r.product is Product.AIRBUSAN_2N3D]
        self.assertTrue(busan)
        for r in busan:
            self.assertIs(alert_for_row(r).level, AlertLevel.NO_MARKET)


if __name__ == "__main__":
    unittest.main()
