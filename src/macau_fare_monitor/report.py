"""리포트 생성.

스프레드시트의 '방어' 시트를 코드로 재생성하고(상품별 마크다운 표),
방어 실패 현황 요약을 만든다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from .defense import DefenseStatus, evaluate_row
from .models import FareRow, Product


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
        "| 날짜 | 요일 | 우리요금(2인) | 시장최저(2인) | 방어 | 비고 |",
        "| :-: | :-: | --: | --: | :-- | :-- |",
    ]
    for r in target:
        result = evaluate_row(r)
        lines.append(
            f"| {r.depart_date:%m/%d} | {r.weekday_kr} | {_fmt(r.our_price_2p)} | "
            f"{_fmt(r.market_low_2p)} | {result.label} | {r.note} |"
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


def full_report_md(rows: List[FareRow]) -> str:
    summaries = summarize(rows)
    parts = [
        "# 마카오 항공 요금 방어 리포트",
        "",
        summary_md(summaries),
        "",
        "## 상품별 방어 상세",
        "",
    ]
    for product in Product:
        if any(r.product is product for r in rows):
            parts.append(product_table_md(product, rows))
            parts.append("")
    return "\n".join(parts)
