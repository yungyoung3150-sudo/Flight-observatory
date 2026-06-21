"""macau_fare_monitor

예스트래블 마카오 공동구매 항공권 '요금 방어' 모니터링 코어 로직.
구글 스프레드시트(마카오 항공 최저가 모니터링)의 계산 로직을 코드로 옮긴 패키지.

- v1: defense.py — 시트의 '방어' 열을 그대로 재현(이진 OK/실패).
- v2: verdict.py + benchmark.py + validate.py — 마진 인지 판정, 견고한 benchmark,
      데이터 건전성 검증으로 비교 정확도를 높인 계층.
"""

from .analysis import benchmark_for_row, quote_from_row, verdict_for_row
from .benchmark import Benchmark, MarketQuote, compute_benchmark
from .config import DEFAULT_CONFIG, DefenseConfig
from .defense import DefenseResult, DefenseStatus, evaluate, evaluate_row
from .loader import load_fares
from .models import Carrier, FareRow, Product
from .report import (
    ProductSummary,
    VerdictSummary,
    full_report_md,
    summarize,
    summarize_verdicts,
)
from .staleness import StalenessResult, check as check_staleness
from .validate import Issue, Severity, summarize_issues, validate_dataset
from .verdict import Verdict, VerdictResult, classify

__all__ = [
    # 모델/로더
    "Carrier",
    "Product",
    "FareRow",
    "load_fares",
    # v1 (시트 재현)
    "DefenseStatus",
    "DefenseResult",
    "evaluate",
    "evaluate_row",
    "ProductSummary",
    "summarize",
    # v2 (정밀 판정)
    "DefenseConfig",
    "DEFAULT_CONFIG",
    "Verdict",
    "VerdictResult",
    "classify",
    "MarketQuote",
    "Benchmark",
    "compute_benchmark",
    "quote_from_row",
    "benchmark_for_row",
    "verdict_for_row",
    "VerdictSummary",
    "summarize_verdicts",
    # 검증/리포트/신선도
    "Issue",
    "Severity",
    "validate_dataset",
    "summarize_issues",
    "full_report_md",
    "StalenessResult",
    "check_staleness",
]
