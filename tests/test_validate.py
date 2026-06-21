"""데이터 건전성 검증 테스트."""

import unittest
from datetime import date, timedelta

from macau_fare_monitor import load_fares, validate_dataset
from macau_fare_monitor.models import FareRow, Product
from macau_fare_monitor.validate import Severity

AS_OF = date(2026, 6, 21)


def _codes(issues):
    return {i.code for i in issues}


class TestValidateRealData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.issues = validate_dataset(load_fares(), AS_OF)

    def test_flags_stale_data(self):
        # 06-19 수집 → 06-21 기준 2일 경과 → STALE 경고
        stale = [i for i in self.issues if i.code == "STALE"]
        self.assertTrue(stale)
        self.assertIs(stale[0].severity, Severity.WARN)

    def test_notes_2pax_approximation(self):
        self.assertIn("APPROX_2PAX", _codes(self.issues))

    def test_marks_reference_only(self):
        ref = [i for i in self.issues if i.code == "REFERENCE_ONLY"]
        self.assertTrue(ref)  # 에어마카오 2박3일 NX825 미운항 구간

    def test_air_busan_market_pending(self):
        nomk = [i for i in self.issues if i.code == "NO_MARKET"]
        self.assertTrue(nomk)


class TestSpikeDetection(unittest.TestCase):
    def test_isolated_spike_flagged(self):
        base = date(2026, 7, 1)
        rows = []
        for i in range(7):
            price = 2000000 if i == 3 else 1000000  # 가운데 하루만 2배
            rows.append(FareRow(
                product=Product.AIRMACAU_2N3D,
                depart_date=base + timedelta(days=i),
                our_price_2p=None,
                market_low_2p=price,
                collected_on=AS_OF,
            ))
        issues = validate_dataset(rows, AS_OF)
        spikes = [i for i in issues if i.code == "SPIKE"]
        self.assertEqual(len(spikes), 1)
        self.assertEqual(spikes[0].depart_date, base + timedelta(days=3))

    def test_sustained_high_not_flagged(self):
        # 연휴처럼 여러 날 연속 높으면 이상치가 아님
        base = date(2026, 9, 23)
        rows = [FareRow(
            product=Product.AIRMACAU_2N3D,
            depart_date=base + timedelta(days=i),
            our_price_2p=None,
            market_low_2p=2200000,
            collected_on=AS_OF,
        ) for i in range(7)]
        issues = validate_dataset(rows, AS_OF)
        self.assertFalse([i for i in issues if i.code == "SPIKE"])


if __name__ == "__main__":
    unittest.main()
