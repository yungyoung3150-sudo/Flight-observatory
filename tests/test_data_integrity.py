"""data/fares.csv 데이터 정합성 테스트.

- 에어마카오 두 상품은 2026-06-20 ~ 2026-10-31(=134일) 연속이어야 한다.
- 모든 행은 우리요금/시장최저 중 적어도 하나를 가진다.
- 상품별 (성공+실패+미입력+시장미수집) == 전체 행 수.
"""

import unittest
from datetime import date, timedelta

from macau_fare_monitor import load_fares, summarize
from macau_fare_monitor.models import Product


def _expected_dates():
    d, end = date(2026, 6, 20), date(2026, 10, 31)
    while d <= end:
        yield d
        d += timedelta(days=1)


class TestDataIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_fares()

    def test_air_macau_dates_are_contiguous_134_days(self):
        expected = list(_expected_dates())
        self.assertEqual(len(expected), 134)
        for product in (Product.AIRMACAU_2N3D, Product.AIRMACAU_3N4D):
            dates = sorted(r.depart_date for r in self.rows if r.product is product)
            self.assertEqual(dates, expected, f"{product.korean} 날짜 불연속/누락")

    def test_every_row_has_some_price(self):
        for r in self.rows:
            self.assertFalse(
                r.our_price_2p is None and r.market_low_2p is None,
                f"{r.product.value} {r.depart_date} 양쪽 모두 비어 있음",
            )

    def test_air_busan_has_our_price_but_no_market(self):
        busan = [r for r in self.rows
                 if r.product in (Product.AIRBUSAN_2N3D, Product.AIRBUSAN_3N4D)]
        self.assertTrue(busan)
        for r in busan:
            self.assertIsNotNone(r.our_price_2p)
            self.assertIsNone(r.market_low_2p)

    def test_summary_counts_add_up(self):
        summaries = summarize(self.rows)
        per_product_total = {}
        for r in self.rows:
            per_product_total[r.product] = per_product_total.get(r.product, 0) + 1
        for product, s in summaries.items():
            self.assertEqual(
                s.ok + s.fail + s.no_our_price + s.no_market,
                per_product_total[product],
                f"{product.korean} 합계 불일치",
            )


if __name__ == "__main__":
    unittest.main()
