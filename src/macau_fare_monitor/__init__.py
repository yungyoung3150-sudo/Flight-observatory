"""macau_fare_monitor

예스트래블 마카오 공동구매 항공권 모니터링 코어 로직.

1차 목적 = **고객 컴플레인 가드레일**: 우리 공구가가 시장 최저가보다 고객이 화낼 만큼
(인당 10만원+) 더 비싸지는 것을 잡는다. 완벽한 가격 매칭이 아니라 '큰 격차 노출' 방지.

- alert.py     — ★ 비대칭·인당 임계 경보(안전/주의/경보) = 1차 목적
- benchmark.py — 다중 견적 → 견고한 benchmark(이상치 가드, comparable 필터)
- validate.py  — 데이터 건전성(STALE/SPIKE/NO_MARKET/REFERENCE_ONLY)
- defense.py   — v1: 스프레드시트 '방어' 열 재현(역사적 기준, 보조)
"""

from .alert import AlertLevel, AlertResult, classify
from .analysis import alert_for_row, benchmark_for_row, quote_from_row
from .benchmark import Benchmark, MarketQuote, compute_benchmark
from .config import DEFAULT_CONFIG, DefenseConfig
from .defense import DefenseResult, DefenseStatus, evaluate, evaluate_row
from .loader import load_fares
from .models import Carrier, FareRow, Product
from .report import (
    AlertSummary,
    ProductSummary,
    full_report_md,
    summarize,
    summarize_alerts,
)
from .staleness import StalenessResult, check as check_staleness
from .validate import Issue, Severity, summarize_issues, validate_dataset

__all__ = [
    # 모델/로더
    "Carrier",
    "Product",
    "FareRow",
    "load_fares",
    # 가드레일 경보(1차 목적)
    "DefenseConfig",
    "DEFAULT_CONFIG",
    "AlertLevel",
    "AlertResult",
    "classify",
    "alert_for_row",
    "AlertSummary",
    "summarize_alerts",
    # 견고한 benchmark
    "MarketQuote",
    "Benchmark",
    "compute_benchmark",
    "quote_from_row",
    "benchmark_for_row",
    # 데이터 건전성
    "Issue",
    "Severity",
    "validate_dataset",
    "summarize_issues",
    # v1 (시트 재현, 보조)
    "DefenseStatus",
    "DefenseResult",
    "evaluate",
    "evaluate_row",
    "ProductSummary",
    "summarize",
    # 리포트/신선도
    "full_report_md",
    "StalenessResult",
    "check_staleness",
]
