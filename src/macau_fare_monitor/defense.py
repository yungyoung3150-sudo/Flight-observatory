"""요금 '방어(defense)' 판정 로직.

스프레드시트의 '방어' 열을 그대로 코드로 옮긴 것.

판정 규칙(2인 합산가 기준):
    gap = market_low_2p - our_price_2p
      - our / market 중 하나라도 없으면 → 판정 불가(빈 칸)
      - gap >= 0  : 우리가 시장최저 이하 → ✅ OK (방어 성공)
      - gap < 0   : 우리가 시장최저보다 비쌈 → 🔴 방어실패, 부족분 = -gap

스프레드시트 표기 예:
    "✅ OK"
    "🔴 방어실패 -29,332"   (gap 이 음수, 그대로 천단위 콤마 표기)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .models import FareRow


class DefenseStatus(str, Enum):
    OK = "OK"                    # 방어 성공
    FAIL = "FAIL"                # 방어 실패(우리가 더 비쌈)
    NO_OUR_PRICE = "NO_OUR_PRICE"  # 우리요금 미입력
    NO_MARKET = "NO_MARKET"        # 시장최저 미수집


@dataclass(frozen=True)
class DefenseResult:
    status: DefenseStatus
    # gap = market - our. OK 면 >=0(여유분), FAIL 이면 음수(부족분). 판정불가면 None.
    gap: Optional[int]

    @property
    def is_failure(self) -> bool:
        return self.status is DefenseStatus.FAIL

    @property
    def shortfall(self) -> int:
        """방어 실패 시 우리가 더 비싼 금액(양수). 그 외 0."""
        return -self.gap if (self.status is DefenseStatus.FAIL and self.gap is not None) else 0

    @property
    def label(self) -> str:
        """스프레드시트 '방어' 열과 동일한 문자열."""
        if self.status is DefenseStatus.OK:
            return "✅ OK"
        if self.status is DefenseStatus.FAIL:
            return f"🔴 방어실패 {self.gap:,}"  # gap 음수 → "-29,332"
        return ""  # 판정 불가(빈 칸)


def evaluate(our_price_2p: Optional[int], market_low_2p: Optional[int]) -> DefenseResult:
    """우리요금·시장최저(2인 합산)로 방어 결과를 계산한다."""
    if our_price_2p is None:
        return DefenseResult(DefenseStatus.NO_OUR_PRICE, None)
    if market_low_2p is None:
        return DefenseResult(DefenseStatus.NO_MARKET, None)
    gap = market_low_2p - our_price_2p
    status = DefenseStatus.OK if gap >= 0 else DefenseStatus.FAIL
    return DefenseResult(status, gap)


def evaluate_row(row: FareRow) -> DefenseResult:
    return evaluate(row.our_price_2p, row.market_low_2p)
