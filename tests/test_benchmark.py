"""견고한 benchmark 산출 테스트."""

import unittest
from datetime import date

from macau_fare_monitor import compute_benchmark
from macau_fare_monitor.benchmark import MarketQuote
from macau_fare_monitor.models import Product

D = date(2026, 7, 18)
P = Product.AIRMACAU_2N3D


def q(price, **kw):
    return MarketQuote(product=P, depart_date=D, price=price, **kw)


class TestBenchmark(unittest.TestCase):
    def test_empty(self):
        self.assertIsNone(compute_benchmark([]))

    def test_single_2p(self):
        b = compute_benchmark([q(1000000, pax=2)])
        self.assertEqual(b.used_2p, 1000000)
        self.assertEqual(b.n, 1)
        self.assertFalse(b.outlier_suspected)
        self.assertTrue(b.comparable)

    def test_one_person_quote_doubled_and_flagged(self):
        b = compute_benchmark([q(500000, pax=1)])
        self.assertEqual(b.used_2p, 1000000)
        self.assertTrue(b.approx_2p)  # 1인×2 근사 표시

    def test_two_normal_quotes_use_min(self):
        b = compute_benchmark([q(1000000), q(1100000)])
        self.assertEqual(b.used_2p, 1000000)
        self.assertFalse(b.outlier_suspected)

    def test_outlier_guard_uses_second_min(self):
        # 최저가 2번째보다 30% 더 쌈(≥25%) → 글리치 의심 → 2번째 채택
        b = compute_benchmark([q(700000), q(1000000)])
        self.assertTrue(b.outlier_suspected)
        self.assertEqual(b.used_2p, 1000000)
        self.assertIn("second_min", b.basis)

    def test_comparable_filter(self):
        # 더 싼 견적이 비교불가면 제외하고 비교가능 견적만 사용
        b = compute_benchmark([
            q(800000, comparable=False),  # 더 싸지만 비교불가
            q(1000000, comparable=True),
        ])
        self.assertEqual(b.used_2p, 1000000)
        self.assertEqual(b.comparable_n, 1)


if __name__ == "__main__":
    unittest.main()
