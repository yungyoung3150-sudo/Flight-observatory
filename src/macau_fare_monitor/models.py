"""도메인 모델.

마카오 공동구매 항공권 '요금 방어(defense)' 모니터링의 핵심 데이터 구조.
스프레드시트의 각 행(날짜 × 상품)을 FareRow 로, 상품 구분을 Product 로 표현한다.

가격 단위 규칙(스프레드시트와 동일):
  - our_price_2p   : 우리(예스트래블) 공동구매가, **2인 합산** 금액(KRW)
  - market_low_2p  : 시장 최저가, **2인 합산** 금액(KRW)
  스프레드시트의 시장최저(2인) = 항공 최저가 시트의 1인가 × 2 로 산출된 값이다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

# 한국어 요일 (월=0 ... 일=6 은 date.weekday() 기준)
_WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


class Carrier(str, Enum):
    """항공사."""

    AIR_MACAU = "에어마카오"
    AIR_BUSAN = "에어부산"


class Product(str, Enum):
    """모니터링 대상 상품(항공사 × 일정)."""

    AIRMACAU_2N3D = "airmacau_2n3d"
    AIRMACAU_3N4D = "airmacau_3n4d"
    AIRBUSAN_2N3D = "airbusan_2n3d"
    AIRBUSAN_3N4D = "airbusan_3n4d"

    @property
    def carrier(self) -> Carrier:
        return (
            Carrier.AIR_MACAU
            if self in (Product.AIRMACAU_2N3D, Product.AIRMACAU_3N4D)
            else Carrier.AIR_BUSAN
        )

    @property
    def nights_label(self) -> str:
        return "2박3일" if self in (Product.AIRMACAU_2N3D, Product.AIRBUSAN_2N3D) else "3박4일"

    @property
    def korean(self) -> str:
        """'에어마카오 2박3일' 같은 사람이 읽는 이름."""
        return f"{self.carrier.value} {self.nights_label}"


@dataclass(frozen=True)
class FareRow:
    """특정 출발일·상품의 요금 한 행.

    our_price_2p / market_low_2p 는 수집 전이면 None 이 될 수 있다.
    (예: 에어부산은 우리요금만 있고 시장최저는 수집 예정 → market_low_2p=None)
    """

    product: Product
    depart_date: date
    our_price_2p: Optional[int] = None
    market_low_2p: Optional[int] = None
    collected_on: Optional[date] = None
    note: str = ""

    @property
    def weekday_kr(self) -> str:
        return _WEEKDAY_KR[self.depart_date.weekday()]
