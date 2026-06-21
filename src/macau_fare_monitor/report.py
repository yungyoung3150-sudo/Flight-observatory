"""리포트 생성.

스프레드시트의 '방어' 시트를 코드로 재생성하고(상품별 마크다운 표),
방어 실패 현황 요약을 만든다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, List

from .analysis import verdict_for_row
from .config import DEFAULT_CONFIG, DefenseConfig
from .defense import DefenseStatus, evaluate_row
from .models import FareRow, Product
from .validate import Severity, validate_dataset
from .verdict import Verdict


@dataclass
class ProductSummary:
    product: Product
    ok: int = 0
    fail: int = 0
    no_our_price: int = 0
    no_market: int = 0
    total_shortfall: int = 0   # 방어 실패분 합계(양수)
    worst_shortfall: int = 0   # 단일 최대 실패분

    @property
    def evaluated(self) -> int:
        return self.ok + self.fail

    @property
    def defense_rate(self) -> float:
        """판정 가능한 행 중 방어 성공 비율(%)."""
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


def _fmt(value) -> str:
    return f"{value:,}" if isinstance(value, int) else ""


def product_table_md(product: Product, rows: List[FareRow]) -> str:
    """한 상품의 방어 표를 마크다운으로 (스프레드시트 '방어' 시트 재현)."""
    target = sorted(
        (r for r in rows if r.product is product),
        key=lambda r: r.depart_date,
    )
    lines = [
        f"### {product.korean}",
        "",
        "| 날짜 | 요일 | 우리요금(2인) | 시장최저(2인) | 방어(v1) | 판정(v2) | 비고 |",
        "| :-: | :-: | --: | --: | :-- | :-- | :-- |",
    ]
    for r in target:
        v1 = evaluate_row(r)
        v2 = verdict_for_row(r)
        lines.append(
            f"| {r.depart_date:%m/%d} | {r.weekday_kr} | {_fmt(r.our_price_2p)} | "
            f"{_fmt(r.market_low_2p)} | {v1.label} | {v2.label} | {r.note} |"
        )
    return "\n".join(lines)


def summary_md(summaries: Dict[Product, ProductSummary]) -> str:
    lines = [
        "## 방어 현황 요약",
        "",
        "| 상품 | 방어성공 | 방어실패 | 우리요금 미입력 | 시장최저 미수집 | 방어율 | 실패분 합계 | 최대 실패분 |",
        "| :-- | --: | --: | --: | --: | --: | --: | --: |",
    ]
    for product in Product:
        s = summaries.get(product)
        if s is None:
            continue
        lines.append(
            f"| {product.korean} | {s.ok} | {s.fail} | {s.no_our_price} | "
            f"{s.no_market} | {s.defense_rate:.0f}% | {s.total_shortfall:,} | "
            f"{s.worst_shortfall:,} |"
        )
    return "\n".join(lines)


@dataclass
class VerdictSummary:
    product: Product
    over_defended: int = 0
    win: int = 0
    tie: int = 0
    lose: int = 0
    non_comparable: int = 0
    no_our_price: int = 0
    no_market: int = 0
    total_loss: int = 0          # 열위 부족분 합계(양수)
    recoverable_margin: int = 0  # 과방어로 남긴 여유분 합계(가격 인상 여지)

    @property
    def judged(self) -> int:
        return self.over_defended + self.win + self.tie + self.lose


def summarize_verdicts(rows: Iterable[FareRow],
                       config: DefenseConfig = DEFAULT_CONFIG) -> Dict[Product, VerdictSummary]:
    out: Dict[Product, VerdictSummary] = {}
    for row in rows:
        s = out.setdefault(row.product, VerdictSummary(row.product))
        v = verdict_for_row(row, config)
        if v.verdict is Verdict.OVER_DEFENDED:
            s.over_defended += 1
            s.recoverable_margin += v.gap or 0
        elif v.verdict is Verdict.WIN:
            s.win += 1
        elif v.verdict is Verdict.TIE:
            s.tie += 1
        elif v.verdict is Verdict.LOSE:
            s.lose += 1
            s.total_loss += -(v.gap or 0)
        elif v.verdict is Verdict.NON_COMPARABLE:
            s.non_comparable += 1
        elif v.verdict is Verdict.NO_OUR_PRICE:
            s.no_our_price += 1
        else:
            s.no_market += 1
    return out


def verdict_summary_md(summaries: Dict[Product, VerdictSummary],
                       config: DefenseConfig = DEFAULT_CONFIG) -> str:
    lines = [
        "## 정밀 판정(v2) 요약",
        "",
        f"기준: 동률밴드 ±{config.tie_band_krw:,} / 과방어 ≥ {config.over_defended_krw:,} (2인 합산, KRW)",
        "",
        "| 상품 | 🟦 과방어 | ✅ 우위 | 🟨 동률 | 🔴 열위 | 판정수 | 열위 부족분 | 과방어 여유분 |",
        "| :-- | --: | --: | --: | --: | --: | --: | --: |",
    ]
    for product in Product:
        s = summaries.get(product)
        if s is None:
            continue
        lines.append(
            f"| {product.korean} | {s.over_defended} | {s.win} | {s.tie} | {s.lose} | "
            f"{s.judged} | {s.total_loss:,} | {s.recoverable_margin:,} |"
        )
    return "\n".join(lines)


def health_md(rows: List[FareRow], as_of: date,
              config: DefenseConfig = DEFAULT_CONFIG) -> str:
    issues = validate_dataset(rows, as_of, config)
    order = {Severity.ERROR: 0, Severity.WARN: 1, Severity.INFO: 2}
    icon = {Severity.ERROR: "⛔", Severity.WARN: "⚠️", Severity.INFO: "ℹ️"}
    lines = [
        "## 데이터 건전성",
        "",
        f"기준일(as-of): {as_of} · 점검 {len(issues)}건",
        "",
    ]
    for issue in sorted(issues, key=lambda i: order[i.severity]):
        where = f" [{issue.depart_date:%m/%d}]" if issue.depart_date else ""
        lines.append(f"- {icon[issue.severity]} `{issue.code}`{where} {issue.message}")
    return "\n".join(lines)


def full_report_md(rows: List[FareRow], as_of: date,
                   config: DefenseConfig = DEFAULT_CONFIG) -> str:
    parts = [
        "# 마카오 항공 요금 방어 리포트",
        "",
        verdict_summary_md(summarize_verdicts(rows, config), config),
        "",
        health_md(rows, as_of, config),
        "",
        "## 방어 현황(v1 · 스프레드시트 재현)",
        "",
        summary_md(summarize(rows)),
        "",
        "## 상품별 상세",
        "",
    ]
    for product in Product:
        if any(r.product is product for r in rows):
            parts.append(product_table_md(product, rows))
            parts.append("")
    return "\n".join(parts)
