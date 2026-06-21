"""고객 컴플레인 가드레일 — 비대칭·인당 임계 경보.

이 프로그램의 1차 목적: 우리 공구가가 시장 최저가보다 **고객이 화낼 만큼** 더 비싸지는
상황을 잡아낸다. 항공요금은 시시각각 변하므로 '완벽한 매칭'이 목표가 아니다. 고객은
인당 1~2만원 차이는 용인하지만, 인당 10만원 이상 벌어지면 컴플레인한다(특히 OTA가
마케팅비를 태워 덤핑할 때).

따라서 경보는 **우리가 더 비싼 쪽에만** 세운다(비대칭). '우리가 더 쌈'은 위험이 아니라
마진 사안(가격 인상 검토 정보)일 뿐이다.

    초과액(인당) = (우리요금_2인 - 시장최저_2인) / pax   (양수 = 우리가 더 비쌈)

    초과액 ≤ safe_max_surcharge_pp           → 🟢 SAFE   (안전, 무알림)
    safe_max < 초과액 < alarm_min            → 🟡 WATCH  (주의, 사람이 점검)
    초과액 ≥ alarm_min_surcharge_pp          → 🔴 ALARM  (경보, 컴플레인 위험 → 즉시 대응)

판정 전 **건전성 게이트**가 우선한다:
    우리요금 없음 → NO_OUR_PRICE (아직 미가격)
    시장최저 없음 → NO_MARKET    (수집 공백 → '안전' 아님, 수동확인 큐. 예: 에어부산 BX)
    비교 불가     → NON_COMPARABLE (참고가/미운항 — 사과 vs 오렌지 방지)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .config import DEFAULT_CONFIG, DefenseConfig


class AlertLevel(str, Enum):
    SAFE = "SAFE"
    WATCH = "WATCH"
    ALARM = "ALARM"
    NON_COMPARABLE = "NON_COMPARABLE"
    NO_MARKET = "NO_MARKET"        # 시장최저 미수집 → 수동확인(안전 아님)
    NO_OUR_PRICE = "NO_OUR_PRICE"


@dataclass(frozen=True)
class AlertResult:
    level: AlertLevel
    surcharge_pp: Optional[int]    # 우리 - 시장(인당). 양수 = 우리가 더 비쌈
    surcharge_2p: Optional[int]
    benchmark_2p: Optional[int]
    approx_2p: bool = False        # 시장가가 1인×2 근사인지(인당 환산은 이를 되돌림)
    margin_review: bool = False    # 우리가 인당 margin_review_pp 이상 더 쌈 → 가격인상 검토(정보)
    dumping_suspect: bool = False  # 정적 약신호(벤치마크 이상치). 진짜 덤핑탐지는 실시간 필요

    @property
    def is_alarm(self) -> bool:
        return self.level is AlertLevel.ALARM

    @property
    def is_watch(self) -> bool:
        return self.level is AlertLevel.WATCH

    @property
    def needs_manual_check(self) -> bool:
        return self.level is AlertLevel.NO_MARKET

    @property
    def label(self) -> str:
        if self.level is AlertLevel.NO_OUR_PRICE:
            return ""
        if self.level is AlertLevel.NO_MARKET:
            return "⚪ 시장미수집(수동확인)"
        if self.level is AlertLevel.NON_COMPARABLE:
            return "◻ 비교불가(참고가)"
        icon = {AlertLevel.SAFE: "🟢 안전",
                AlertLevel.WATCH: "🟡 주의",
                AlertLevel.ALARM: "🔴 경보"}[self.level]
        text = f"{icon} (인당 {self.surcharge_pp:+,})"
        if self.dumping_suspect:
            text += " ⚠덤핑의심"
        if self.margin_review:
            text += " · 인상검토"
        return text


def classify(our_2p: Optional[int],
             market_2p: Optional[int],
             config: DefenseConfig = DEFAULT_CONFIG,
             *,
             comparable: bool = True,
             approx_2p: bool = False,
             outlier_suspected: bool = False) -> AlertResult:
    """우리요금·시장최저(2인 합산)로 컴플레인 경보 단계를 판정."""
    if our_2p is None:
        return AlertResult(AlertLevel.NO_OUR_PRICE, None, None, market_2p)
    if market_2p is None:
        # 수집 공백은 '안전'이 아니라 수동확인 대상(BX 덤핑 사각 방지).
        return AlertResult(AlertLevel.NO_MARKET, None, None, None)

    surcharge_2p = our_2p - market_2p
    surcharge_pp = round(surcharge_2p / config.pax_basis)

    if not comparable:
        return AlertResult(AlertLevel.NON_COMPARABLE, surcharge_pp, surcharge_2p,
                           market_2p, approx_2p=approx_2p)

    margin_review = surcharge_pp <= -config.margin_review_pp
    if surcharge_pp >= config.alarm_min_surcharge_pp:
        level = AlertLevel.ALARM
    elif surcharge_pp > config.safe_max_surcharge_pp:
        level = AlertLevel.WATCH
    else:
        level = AlertLevel.SAFE
    dumping_suspect = level is AlertLevel.ALARM and outlier_suspected
    return AlertResult(level, surcharge_pp, surcharge_2p, market_2p,
                       approx_2p=approx_2p, margin_review=margin_review,
                       dumping_suspect=dumping_suspect)
