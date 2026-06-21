"""리포트 생성.

리포트는 **1차 목적(컴플레인 가드레일)** 을 맨 위에 둔다:
  1) 🔴 경보 / 🟠 주의 헤드라인  — 우리가 고객 분노 임계만큼 더 비싼 출발일
  2) 수동확인 큐               — 시장최저 미수집(예: 에어부산) → '안전' 아님
  3) 상품별 요약              — 경보/주의/안전/비교불가/미수집 분포
  4) (보조) 가격 인상 검토 후보 — 우리가 과하게 싼 구간(마진)
  5) 데이터 건전성            — STALE/SPIKE 등 신뢰도
  6) v1 시트 재현            — 원본 스프레드시트 '방어' 열과 일치(역사적 기준)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, List

from .alert import AlertLevel
from .analysis import alert_for_row
from .config import DEFAULT_CONFIG, DefenseConfig
from .defense import DefenseStatus, evaluate_row
from .models import FareRow, Product
from .validate import Severity, validate_dataset


# ─────────────────────────── v1 (시트 재현) ───────────────────────────

@dataclass
class ProductSummary:
    product: Product
    ok: int = 0
    fail: int = 0
    no_our_price: int = 0
    no_market: int = 0
    total_shortfall: int = 0
    worst_shortfall: int = 0

    @property
    def evaluated(self) -> int:
        return self.ok + self.fail

    @property
    def defense_rate(self) -> float:
        return 100.0 * self.ok / self.evaluated if self.evaluated else 0.0


def summarize(rows: Iterable[FareRow]) -> Dict[Product, ProductSummary]:
    summaries: Dict[Product, ProductSummary] = {}
    for row in rows:
        s = summaries.setdefault(row.product, ProductSummary(row.product))
        result = evaluate_row(row)
        if result.status is DefenseStatus.OK:
            s.ok += 1
        elif result.status is DefenseStatus.FAIL:
            s.fail += 1
            s.total_shortfall += result.shortfall
            s.worst_shortfall = max(s.worst_shortfall, result.shortfall)
        elif result.status is DefenseStatus.NO_OUR_PRICE:
            s.no_our_price += 1
        else:
            s.no_market += 1
    return summaries


# ─────────────────────── 가드레일 경보(1차 목적) ───────────────────────

@dataclass
class AlertSummary:
    product: Product
    alarm: int = 0
    watch: int = 0
    safe: int = 0
    non_comparable: int = 0
    no_market: int = 0
    no_our_price: int = 0
    margin_review: int = 0          # 인상 검토 후보(우리가 과하게 쌈)
    worst_surcharge_pp: int = 0     # 가장 비싼 초과액(인당, 양수)

    @property
    def judged(self) -> int:
        return self.alarm + self.watch + self.safe


def summarize_alerts(rows: Iterable[FareRow],
                     config: DefenseConfig = DEFAULT_CONFIG) -> Dict[Product, AlertSummary]:
    out: Dict[Product, AlertSummary] = {}
    for row in rows:
        s = out.setdefault(row.product, AlertSummary(row.product))
        a = alert_for_row(row, config)
        if a.level is AlertLevel.ALARM:
            s.alarm += 1
        elif a.level is AlertLevel.WATCH:
            s.watch += 1
        elif a.level is AlertLevel.SAFE:
            s.safe += 1
        elif a.level is AlertLevel.NON_COMPARABLE:
            s.non_comparable += 1
        elif a.level is AlertLevel.NO_MARKET:
            s.no_market += 1
        else:
            s.no_our_price += 1
        if a.margin_review:
            s.margin_review += 1
        if a.surcharge_pp is not None and a.level in (AlertLevel.WATCH, AlertLevel.ALARM):
            s.worst_surcharge_pp = max(s.worst_surcharge_pp, a.surcharge_pp)
    return out


def _rows_at(rows: List[FareRow], config: DefenseConfig, *levels) -> List[tuple]:
    """(row, alert) 중 지정 레벨만, 초과액 큰 순."""
    picked = []
    for r in rows:
        a = alert_for_row(r, config)
        if a.level in levels:
            picked.append((r, a))
    picked.sort(key=lambda ra: -(ra[1].surcharge_pp or 0))
    return picked


def alert_headline_md(rows: List[FareRow], config: DefenseConfig = DEFAULT_CONFIG) -> str:
    alarms = _rows_at(rows, config, AlertLevel.ALARM)
    watches = _rows_at(rows, config, AlertLevel.WATCH)
    lines = [
        "## 🚨 컴플레인 가드레일",
        "",
        f"기준: 🔴경보 ≥ 인당 {config.alarm_min_surcharge_pp:,} · "
        f"🟠주의 인당 {config.watch_min_surcharge_pp:,}~{config.alarm_min_surcharge_pp:,} "
        f"(우리가 시장보다 더 비싼 초과액)",
        "",
    ]
    if alarms:
        lines.append(f"### 🔴 경보 {len(alarms)}건 — 즉시 대응(가격 재산정/판매 보류)")
        lines.append("| 출발일 | 상품 | 우리(2인) | 시장(2인) | 초과액(인당) | 비고 |")
        lines.append("| :-: | :-- | --: | --: | --: | :-- |")
        for r, a in alarms:
            tag = " ⚠덤핑의심" if a.dumping_suspect else ""
            lines.append(
                f"| {r.depart_date:%m/%d}({r.weekday_kr}) | {r.product.korean} | "
                f"{r.our_price_2p:,} | {r.market_low_2p:,} | **+{a.surcharge_pp:,}**{tag} | {r.note} |"
            )
    else:
        lines.append("### 🔴 경보 0건 — 현재 스냅샷에 컴플레인 임계 초과 없음")
        lines.append("")
        lines.append("> 이 도구의 진짜 값은 **판매 기간 중 OTA 덤핑**이 터질 때다. 단일 사전 스냅샷엔 "
                     "보통 경보가 없다(아래 주의 구간만 사람이 점검).")
    lines.append("")
    if watches:
        worst = watches[0][1].surcharge_pp
        lines.append(f"### 🟠 주의 {len(watches)}건 — 침묵 경보(사람이 점검, 판매결정 보류)")
        lines.append(f"가장 큰 초과액: 인당 +{worst:,} "
                     f"({watches[0][0].product.korean} {watches[0][0].depart_date:%m/%d})")
    return "\n".join(lines)


def manual_check_md(rows: List[FareRow], config: DefenseConfig = DEFAULT_CONFIG) -> str:
    by_product: Dict[Product, int] = {}
    for r in rows:
        if alert_for_row(r, config).level is AlertLevel.NO_MARKET:
            by_product[r.product] = by_product.get(r.product, 0) + 1
    lines = ["## 🔍 수동확인 큐 (시장최저 미수집 — '안전' 아님)", ""]
    if not by_product:
        lines.append("- 없음")
        return "\n".join(lines)
    for product, cnt in by_product.items():
        lines.append(f"- **{product.korean}**: {cnt}건 — 시장최저 미수집. 수집 공백을 안전으로 "
                     "오해 금지(에어부산 BX는 과거 덤핑 사고 레그, Amadeus 미커버).")
    return "\n".join(lines)


def alert_summary_md(summaries: Dict[Product, AlertSummary]) -> str:
    lines = [
        "## 상품별 경보 요약",
        "",
        "| 상품 | 🔴경보 | 🟠주의 | 🟢안전 | 비교불가 | 시장미수집 | 미입력 | 최대초과(인당) | 인상검토 |",
        "| :-- | --: | --: | --: | --: | --: | --: | --: | --: |",
    ]
    for product in Product:
        s = summaries.get(product)
        if s is None:
            continue
        lines.append(
            f"| {product.korean} | {s.alarm} | {s.watch} | {s.safe} | {s.non_comparable} | "
            f"{s.no_market} | {s.no_our_price} | {s.worst_surcharge_pp:,} | {s.margin_review} |"
        )
    return "\n".join(lines)


# ─────────────────────────── 데이터 건전성 ───────────────────────────

def health_md(rows: List[FareRow], as_of: date,
              config: DefenseConfig = DEFAULT_CONFIG) -> str:
    issues = validate_dataset(rows, as_of, config)
    order = {Severity.ERROR: 0, Severity.WARN: 1, Severity.INFO: 2}
    icon = {Severity.ERROR: "⛔", Severity.WARN: "⚠️", Severity.INFO: "ℹ️"}
    lines = ["## 데이터 건전성", "", f"기준일(as-of): {as_of} · 점검 {len(issues)}건", ""]
    for issue in sorted(issues, key=lambda i: order[i.severity]):
        where = f" [{issue.depart_date:%m/%d}]" if issue.depart_date else ""
        lines.append(f"- {icon[issue.severity]} `{issue.code}`{where} {issue.message}")
    return "\n".join(lines)


# ─────────────────────────── 상세 표 ───────────────────────────

def _fmt(value) -> str:
    return f"{value:,}" if isinstance(value, int) else ""


def product_table_md(product: Product, rows: List[FareRow],
                     config: DefenseConfig = DEFAULT_CONFIG) -> str:
    target = sorted((r for r in rows if r.product is product), key=lambda r: r.depart_date)
    lines = [
        f"### {product.korean}",
        "",
        "| 날짜 | 요일 | 우리(2인) | 시장(2인) | 초과액(인당) | 경보 | 비고 |",
        "| :-: | :-: | --: | --: | --: | :-- | :-- |",
    ]
    for r in target:
        a = alert_for_row(r, config)
        sp = f"{a.surcharge_pp:+,}" if a.surcharge_pp is not None else ""
        lines.append(
            f"| {r.depart_date:%m/%d} | {r.weekday_kr} | {_fmt(r.our_price_2p)} | "
            f"{_fmt(r.market_low_2p)} | {sp} | {a.label} | {r.note} |"
        )
    return "\n".join(lines)


def summary_md(summaries: Dict[Product, ProductSummary]) -> str:
    lines = [
        "### 방어 현황(v1 · 스프레드시트 재현)",
        "",
        "| 상품 | 방어성공 | 방어실패 | 우리요금 미입력 | 시장최저 미수집 | 방어율 |",
        "| :-- | --: | --: | --: | --: | --: |",
    ]
    for product in Product:
        s = summaries.get(product)
        if s is None:
            continue
        lines.append(
            f"| {product.korean} | {s.ok} | {s.fail} | {s.no_our_price} | "
            f"{s.no_market} | {s.defense_rate:.0f}% |"
        )
    return "\n".join(lines)


# ─────────────────────────── 종합 ───────────────────────────

def full_report_md(rows: List[FareRow], as_of: date,
                   config: DefenseConfig = DEFAULT_CONFIG) -> str:
    parts = [
        "# 마카오 항공 요금 — 컴플레인 가드레일 리포트",
        "",
        alert_headline_md(rows, config),
        "",
        manual_check_md(rows, config),
        "",
        alert_summary_md(summarize_alerts(rows, config)),
        "",
        health_md(rows, as_of, config),
        "",
        "## 부록 — v1 시트 재현",
        "",
        summary_md(summarize(rows)),
        "",
        "## 상품별 상세",
        "",
    ]
    for product in Product:
        if any(r.product is product for r in rows):
            parts.append(product_table_md(product, rows, config))
            parts.append("")
    return "\n".join(parts)
