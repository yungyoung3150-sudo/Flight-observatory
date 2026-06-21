"""마진 인지 판정(v2).

v1(defense.py)은 '우리 ≤ 시장 → OK / 아니면 실패' 이진 판정으로 스프레드시트를 재현한다.
v2는 같은 격차(gap)를 **운영 의사결정에 쓰도록** 4단계로 세분한다.

    gap = benchmark_2p - our_2p   (양수 = 우리가 더 쌈)

    gap >= over_defended_krw         → 🟦 과방어   (너무 싸서 마진 손실 가능 → 가격 인상 검토)
    tie_band < gap < over_defended   → ✅ 우위     (여유 있게 방어)
    |gap| <= tie_band                → 🟨 동률     (근소차 — 사실상 같은 값)
    gap < -tie_band                  → 🔴 열위     (실질적으로 더 비쌈 → 즉시 조정)

benchmark 가 '참고가/비교불가'(예: 우리 항공편 미운항으로 다른 편 가격)면 승패를 매기지 않고
NON_COMPARABLE 로 분리한다 — 사과 vs 오렌지 비교를 막기 위함.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .config import DEFAULT_CONFIG, DefenseConfig


class Verdict(str, Enum):
    OVER_DEFENDED = "OVER_DEFENDED"
    WIN = "WIN"
    TIE = "TIE"
    LOSE = "LOSE"
    NON_COMPARABLE = "NON_COMPARABLE"
    NO_OUR_PRICE = "NO_OUR_PRICE"
    NO_MARKET = "NO_MARKET"


_LABELS = {
    Verdict.OVER_DEFENDED: "🟦 과방어",
    Verdict.WIN: "✅ 우위",
    Verdict.TIE: "🟨 동률",
    Verdict.LOSE: "🔴 열위",
    Verdict.NON_COMPARABLE: "⚪ 비교불가(참고가)",
    Verdict.NO_OUR_PRICE: "",
    Verdict.NO_MARKET: "",
}


@dataclass(frozen=True)
class VerdictResult:
    verdict: Verdict
    gap: Optional[int]            # benchmark_2p - our_2p (양수=우리가 쌈)
    benchmark_2p: Optional[int]

    @property
    def is_loss(self) -> bool:
        return self.verdict is Verdict.LOSE

    @property
    def is_over_defended(self) -> bool:
        return self.verdict is Verdict.OVER_DEFENDED

    @property
    def label(self) -> str:
        base = _LABELS[self.verdict]
        if self.gap is None or self.verdict in (Verdict.NO_OUR_PRICE, Verdict.NO_MARKET):
            return base
        if self.verdict is Verdict.NON_COMPARABLE:
            return f"{base} ({self.gap:+,})"
        return f"{base} {self.gap:+,}"


def classify(our_2p: Optional[int],
             benchmark_2p: Optional[int],
             config: DefenseConfig = DEFAULT_CONFIG,
             *,
             comparable: bool = True) -> VerdictResult:
    """우리요금·benchmark(2인 합산)를 마진 인지 4단계로 판정."""
    if our_2p is None:
        return VerdictResult(Verdict.NO_OUR_PRICE, None, benchmark_2p)
    if benchmark_2p is None:
        return VerdictResult(Verdict.NO_MARKET, None, None)

    gap = benchmark_2p - our_2p
    if not comparable:
        return VerdictResult(Verdict.NON_COMPARABLE, gap, benchmark_2p)

    if gap >= config.over_defended_krw:
        verdict = Verdict.OVER_DEFENDED
    elif gap > config.tie_band_krw:
        verdict = Verdict.WIN
    elif gap >= -config.tie_band_krw:
        verdict = Verdict.TIE
    else:
        verdict = Verdict.LOSE
    return VerdictResult(verdict, gap, benchmark_2p)
