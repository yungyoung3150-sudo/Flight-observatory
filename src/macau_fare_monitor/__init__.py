"""macau_fare_monitor

예스트래블 마카오 공동구매 항공권 '요금 방어' 모니터링 코어 로직.
구글 스프레드시트(마카오 항공 최저가 모니터링)의 계산 로직을 코드로 옮긴 패키지.
"""

from .defense import DefenseResult, DefenseStatus, evaluate, evaluate_row
from .loader import load_fares
from .models import Carrier, FareRow, Product
from .report import ProductSummary, full_report_md, summarize
from .staleness import StalenessResult, check as check_staleness

__all__ = [
    "Carrier",
    "Product",
    "FareRow",
    "DefenseStatus",
    "DefenseResult",
    "evaluate",
    "evaluate_row",
    "load_fares",
    "ProductSummary",
    "summarize",
    "full_report_md",
    "StalenessResult",
    "check_staleness",
]
