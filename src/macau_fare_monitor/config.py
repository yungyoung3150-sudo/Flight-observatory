"""판정·검증에 쓰는 설정값(임계치).

모든 임계치는 운영자가 조정 가능하도록 한곳에 모은다. 기본값은 2인 합산가(KRW) 기준.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DefenseConfig:
    # --- 마진 인지 판정(verdict) ---
    # |시장최저 - 우리요금| 이 이 값 이하이면 사실상 '동률(TIE)' 로 본다.
    tie_band_krw: int = 10_000
    # 시장최저보다 이 값 이상 싸면 '과방어(OVER_DEFENDED)' — 마진을 남겨둔 것일 수 있어 점검 대상.
    over_defended_krw: int = 150_000

    # --- 데이터 건전성 ---
    # 수집일이 기준일보다 이만큼(일) 이상 지나면 stale.
    max_age_days: int = 1
    # 이상 급등 탐지: 전후 spike_window 일 이웃들의 중앙값 대비
    # spike_ratio 이상 벗어난 시장최저값을 '이상치 의심'으로 표시.
    spike_window_days: int = 3
    spike_ratio: float = 0.35

    # --- 견고한 benchmark ---
    # 견적이 2개 이상일 때, 2번째로 싼 값 대비 최저값이 이 비율 이상 더 싸면
    # 글리치/유령요금 의심 → 최저값 대신 2번째 값을 benchmark 로 채택(이상치 가드).
    outlier_guard_ratio: float = 0.25


DEFAULT_CONFIG = DefenseConfig()
