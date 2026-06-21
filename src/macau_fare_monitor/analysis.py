"""행(FareRow) → benchmark → 마진 인지 판정(v2) 글루.

시트의 단일 시장최저값을 견적 1개로 감싸 benchmark 모듈에 통과시킨 뒤 classify 한다.
정식 API로 (date, product) 당 견적이 여러 개 들어오면 quotes 를 그대로 넘기면 된다.
"""

from __future__ import annotations

from typing import List, Optional

from .benchmark import Benchmark, MarketQuote, compute_benchmark
from .config import DEFAULT_CONFIG, DefenseConfig
from .models import FareRow
from .verdict import VerdictResult, classify


def quote_from_row(row: FareRow) -> Optional[MarketQuote]:
    """시트 행의 시장최저값(2인)을 견적 1개로 변환. 시장값 없으면 None."""
    if row.market_low_2p is None:
        return None
    return MarketQuote(
        product=row.product,
        depart_date=row.depart_date,
        price=row.market_low_2p,
        pax=2,
        comparable=row.comparable,
        two_pax_is_approx=True,   # 시트의 2인가 = 1인최저 × 2
        source="sheet",
    )


def benchmark_for_row(row: FareRow,
                      config: DefenseConfig = DEFAULT_CONFIG,
                      extra_quotes: Optional[List[MarketQuote]] = None) -> Optional[Benchmark]:
    quotes: List[MarketQuote] = list(extra_quotes or [])
    q = quote_from_row(row)
    if q is not None:
        quotes.append(q)
    return compute_benchmark(quotes, config) if quotes else None


def verdict_for_row(row: FareRow,
                    config: DefenseConfig = DEFAULT_CONFIG,
                    extra_quotes: Optional[List[MarketQuote]] = None) -> VerdictResult:
    bench = benchmark_for_row(row, config, extra_quotes)
    used = bench.used_2p if bench else None
    comparable = bench.comparable if bench else True
    return classify(row.our_price_2p, used, config, comparable=comparable)
