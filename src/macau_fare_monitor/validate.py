"""데이터 건전성 검증.

부정확한 입력을 '사실'인 양 신뢰하지 않도록, 비교 전에 데이터 문제를 자동 탐지한다.
탐지 항목:
  - STALE         : 수집일이 기준일 대비 오래됨(수집 파이프 점검 필요)
  - NO_MARKET     : 시장최저 미수집(에어마카오는 경고, 에어부산은 예정 → 정보)
  - REFERENCE_ONLY: 참고가/미운항 → 비교 불가 benchmark
  - SPIKE         : 전후 이웃 대비 비정상 급등/급락(글리치/입력오류 의심)
  - APPROX_2PAX   : 2인가가 1인최저×2 근사라는 방법론적 한계(정보)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict, List, Optional

from .config import DEFAULT_CONFIG, DefenseConfig
from .models import FareRow, Product
from .staleness import check as check_staleness

_AIR_MACAU = (Product.AIRMACAU_2N3D, Product.AIRMACAU_3N4D)


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    message: str
    product: Optional[Product] = None
    depart_date: Optional[date] = None


def _by_product(rows: List[FareRow]) -> Dict[Product, List[FareRow]]:
    out: Dict[Product, List[FareRow]] = {}
    for r in rows:
        out.setdefault(r.product, []).append(r)
    for prows in out.values():
        prows.sort(key=lambda r: r.depart_date)
    return out


def _detect_spikes(prows: List[FareRow], config: DefenseConfig) -> List[Issue]:
    """고립된 이상치(글리치/입력오류)만 탐지.

    성수기처럼 며칠 연속 비싼 '평탄 구간'을 오탐하지 않도록, 바로 옆 두 날과
    **양쪽 모두** 같은 방향으로 크게 벌어진 경우(= 하루만 튄 값)만 SPIKE 로 본다.
    """
    issues: List[Issue] = []
    priced = [r for r in prows if r.market_low_2p is not None]  # 날짜순(prows 정렬됨)
    for i in range(1, len(priced) - 1):
        prev, cur, nxt = priced[i - 1], priced[i], priced[i + 1]
        # 바로 앞/뒤 날이 탐지창 안에 있어야(데이터 공백 건너뛰지 않도록)
        if abs((cur.depart_date - prev.depart_date).days) > config.spike_window_days:
            continue
        if abs((nxt.depart_date - cur.depart_date).days) > config.spike_window_days:
            continue
        pv, cv, nv = prev.market_low_2p, cur.market_low_2p, nxt.market_low_2p
        if not (pv and nv):
            continue
        dev_prev = abs(cv - pv) / pv
        dev_next = abs(cv - nv) / nv
        up = cv > pv and cv > nv
        down = cv < pv and cv < nv
        if (up or down) and dev_prev >= config.spike_ratio and dev_next >= config.spike_ratio:
            direction = "급등" if up else "급락"
            issues.append(Issue(
                Severity.WARN, "SPIKE",
                f"시장최저 {cv:,} 이 인접일({pv:,} / {nv:,}) 대비 {direction} — 글리치/입력오류 의심",
                cur.product, cur.depart_date,
            ))
    return issues


def validate_dataset(rows: List[FareRow],
                     as_of: date,
                     config: DefenseConfig = DEFAULT_CONFIG) -> List[Issue]:
    issues: List[Issue] = []

    # 방법론적 한계 1건(전체) — 2인가는 1인최저×2 근사
    issues.append(Issue(
        Severity.INFO, "APPROX_2PAX",
        "시장최저(2인)는 1인 최저가 × 2 로 산출된 근사치 — 실제 2석 동시 발권가와 차이날 수 있음.",
    ))

    # 신선도: 수집일별로 1건씩 집계(행마다 반복하지 않음)
    stale_counts: Dict[date, int] = {}
    for r in rows:
        if r.collected_on is None:
            continue
        st = check_staleness(r.collected_on, as_of, config.max_age_days)
        if st.is_stale:
            stale_counts[r.collected_on] = stale_counts.get(r.collected_on, 0) + 1
    for collected_on, cnt in sorted(stale_counts.items()):
        age = (as_of - collected_on).days
        issues.append(Issue(
            Severity.WARN, "STALE",
            f"{collected_on} 수집 데이터 {cnt}행이 {age}일 경과(stale) — 재수집 필요.",
        ))

    # 상품별 집계
    for product, prows in _by_product(rows).items():
        ref_dates = [r.depart_date for r in prows if r.reference_only]
        if ref_dates:
            issues.append(Issue(
                Severity.INFO, "REFERENCE_ONLY",
                f"{product.korean}: 참고가/비교불가 {len(ref_dates)}건"
                f"({min(ref_dates):%m/%d}~{max(ref_dates):%m/%d}) — 승패 판정에서 제외.",
                product,
            ))

        missing = [r for r in prows if r.market_low_2p is None and not r.reference_only]
        if missing:
            if product in _AIR_MACAU:
                issues.append(Issue(
                    Severity.WARN, "NO_MARKET",
                    f"{product.korean}: 시장최저 미수집 {len(missing)}건 — 방어 판정 불가.",
                    product,
                ))
            else:
                issues.append(Issue(
                    Severity.INFO, "NO_MARKET",
                    f"{product.korean}: 시장최저 미수집 {len(missing)}건(수집 예정).",
                    product,
                ))

        issues.extend(_detect_spikes(prows, config))

    return issues


def summarize_issues(issues: List[Issue]) -> Dict[Severity, int]:
    out = {s: 0 for s in Severity}
    for i in issues:
        out[i.severity] += 1
    return out
