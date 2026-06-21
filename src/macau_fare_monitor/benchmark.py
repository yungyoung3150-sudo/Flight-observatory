"""시장 견적(quote) → 견고한 benchmark 산출.

스프레드시트는 (date, product) 마다 시장최저값 하나만 갖는다. 그 단일 값은
글리치/유령요금 하나에 취약하고, 비교 불가능한 다른 항공편일 수도 있다.

이 모듈은 **여러 견적**을 받아 benchmark 를 견고하게 만든다:
  - 비교 가능(comparable) 견적이 있으면 그 안에서만 최저 선택(사과 vs 사과)
  - 2인가 = 1인가 × 2 근사 여부를 추적해 결과에 명시
  - 최저값이 2번째 값보다 비정상적으로 더 싸면(설정 비율 이상) 이상치로 보고
    2번째 값을 benchmark 로 채택(이상치 가드)

현재 시트 데이터는 (date, product) 당 견적 1개로 들어오므로 가드/필터는 자연히 무동작,
정식 API(Amadeus/Duffel)로 견적이 여러 개 들어오면 그대로 효과를 낸다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import List, Optional

from .config import DEFAULT_CONFIG, DefenseConfig
from .models import Product


@dataclass(frozen=True)
class MarketQuote:
    product: Product
    depart_date: date
    price: int                       # 관측 가격(KRW)
    pax: int = 2                     # 가격 기준 인원(1 또는 2)
    comparable: bool = True          # 우리 상품과 동급 비교 가능 여부
    two_pax_is_approx: bool = False  # pax=2 가격이 1인×2 로 산출된 근사치인지
    carrier: Optional[str] = None
    source: str = ""

    def to_2p(self) -> "tuple[int, bool]":
        """(2인 합산가, 근사여부) 반환."""
        if self.pax == 2:
            return self.price, self.two_pax_is_approx
        return self.price * 2, True  # 1인가 × 2 는 근사


@dataclass(frozen=True)
class Benchmark:
    product: Product
    depart_date: date
    used_2p: Optional[int]        # 채택된 benchmark(2인). 견적 없으면 None
    min_2p: Optional[int]
    second_min_2p: Optional[int]
    median_2p: Optional[int]
    n: int                        # 전체 견적 수
    comparable_n: int             # 비교가능 견적 수
    approx_2p: bool               # 채택값이 ×2 근사 기반인지
    outlier_suspected: bool       # 최저값 글리치 의심 여부
    basis: str                    # 채택 근거

    @property
    def comparable(self) -> bool:
        return self.comparable_n > 0


def compute_benchmark(quotes: List[MarketQuote],
                      config: DefenseConfig = DEFAULT_CONFIG) -> Optional[Benchmark]:
    """견적 리스트에서 benchmark 산출. 견적이 없으면 None."""
    if not quotes:
        return None

    product = quotes[0].product
    depart_date = quotes[0].depart_date
    comparable_quotes = [q for q in quotes if q.comparable]

    # 비교 가능한 견적이 있으면 그 안에서만, 없으면 전체에서.
    pool = comparable_quotes if comparable_quotes else quotes
    pool_is_comparable = bool(comparable_quotes)

    pairs = sorted((q.to_2p() for q in pool), key=lambda p: p[0])  # [(price_2p, approx), ...]
    prices = [p for p, _ in pairs]
    min_2p = prices[0]
    second_min_2p = prices[1] if len(prices) >= 2 else None
    median_2p = int(median(prices))

    # 이상치 가드: 최저가 2번째보다 너무 싸면 글리치 의심 → 2번째 채택.
    outlier_suspected = False
    chosen_idx = 0
    if second_min_2p is not None and second_min_2p > 0:
        drop = (second_min_2p - min_2p) / second_min_2p
        if drop >= config.outlier_guard_ratio:
            outlier_suspected = True
            chosen_idx = 1

    used_2p, used_approx = pairs[chosen_idx]
    if outlier_suspected:
        basis = "second_min(outlier_guard)"
    elif pool_is_comparable:
        basis = "comparable_min"
    else:
        basis = "absolute_min(no_comparable)"

    return Benchmark(
        product=product,
        depart_date=depart_date,
        used_2p=used_2p,
        min_2p=min_2p,
        second_min_2p=second_min_2p,
        median_2p=median_2p,
        n=len(quotes),
        comparable_n=len(comparable_quotes),
        approx_2p=used_approx,
        outlier_suspected=outlier_suspected,
        basis=basis,
    )
