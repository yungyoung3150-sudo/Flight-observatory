"""수집 데이터 신선도(staleness) 점검.

스프레드시트 수집 로그 탭의 '1일 전(stale)' / '⚠ 데이터 미갱신 — 수집 파이프 점검 필요'
경고를 코드로 재현한다. 수집일이 기준일보다 max_age_days 이상 오래되면 stale 로 본다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

STALE_WARNING = "⚠ 데이터 미갱신 — 수집 파이프 점검 필요"


@dataclass(frozen=True)
class StalenessResult:
    collected_on: date
    as_of: date
    age_days: int
    is_stale: bool

    @property
    def freshness_label(self) -> str:
        if self.age_days <= 0:
            return "최신"
        suffix = "(stale)" if self.is_stale else ""
        return f"{self.age_days}일 전{suffix}"

    @property
    def message(self) -> str:
        return STALE_WARNING if self.is_stale else ""


def check(collected_on: date, as_of: date, max_age_days: int = 1) -> StalenessResult:
    """collected_on 데이터가 as_of 기준으로 신선한지 판정.

    age_days >= max_age_days 이면 stale.
    """
    age_days = (as_of - collected_on).days
    is_stale = age_days >= max_age_days
    return StalenessResult(collected_on, as_of, age_days, is_stale)
