"""판정·검증에 쓰는 설정값(임계치).

이 프로그램의 1차 목적 = **고객 컴플레인 가드레일**.
"우리 공구가가 시장 최저가보다 고객이 화낼 만큼 더 비싸지는 것"을 막는다.
→ 임계는 대칭(싸다/비싸다)이 아니라 **비대칭**: '우리가 더 비싼 쪽'에만, 단계적으로.
→ 단위는 **인당(per person)**. 고객 분노 임계가 인당으로 진술됨(인당 1~2만 용인, 인당 10만+ 분노).

모든 임계는 운영자가 조정 가능. 시트 데이터가 2인 합산이므로 인당 = 2인합산 ÷ 2.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DefenseConfig:
    # --- 가드레일: 우리가 시장보다 '인당' 얼마나 더 비싼가(초과액, KRW/인) ---
    # 5만원 미만 = 안전(SAFE, 🟢): 고객이 거의 신경 안 씀.
    # 5만원 이상 = 주의(WATCH, 🟠): 고객에게 이슈가 될 수 있는 구간.
    watch_min_surcharge_pp: int = 50_000
    # 10만원 이상 = 경보(ALARM, 🔴): 컴플레인까지 들어오는 구간.
    alarm_min_surcharge_pp: int = 100_000

    # 우리가 시장보다 '인당' 이만큼 이상 더 싸면 → 마진 손실 가능(가격 인상 검토 후보).
    # 경보가 아니라 정보(INFO). 가드레일과 마진 최적화는 별개 우선순위.
    margin_review_pp: int = 100_000

    # 2인 합산가 → 인당 환산에 쓰는 인원수.
    pax_basis: int = 2

    # --- 데이터 건전성 ---
    # 수집일이 기준일보다 이만큼(일) 이상 지나면 stale.
    max_age_days: int = 1
    # 이상 급등/급락 탐지: 바로 앞/뒤 날과 양쪽 모두 이 비율 이상 벌어진 '고립' 값만.
    spike_window_days: int = 3
    spike_ratio: float = 0.35

    # --- 견고한 benchmark ---
    # 견적이 2개 이상일 때, 2번째로 싼 값 대비 최저값이 이 비율 이상 더 싸면
    # 글리치/덤핑 의심 → 최저값 대신 2번째 값을 benchmark 로 채택(이상치 가드).
    outlier_guard_ratio: float = 0.25


DEFAULT_CONFIG = DefenseConfig()
