#!/usr/bin/env python3
"""data/fares.csv 를 읽어 방어 리포트를 생성하는 CLI.

사용:
    python scripts/build_report.py                  # 콘솔 요약(v1+v2+건전성)
    python scripts/build_report.py --out reports     # reports/ 에 마크다운/CSV 저장
    python scripts/build_report.py --as-of 2026-06-21

설치 없이 실행되도록 src/ 를 import 경로에 추가한다.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from macau_fare_monitor import (  # noqa: E402
    DEFAULT_CONFIG,
    Severity,
    evaluate_row,
    full_report_md,
    load_fares,
    summarize,
    summarize_issues,
    summarize_verdicts,
    validate_dataset,
    verdict_for_row,
)
from macau_fare_monitor.models import Product  # noqa: E402


def write_defense_csv(rows, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["product", "depart_date", "weekday", "our_price_2p", "market_low_2p",
             "defense_v1", "verdict_v2", "gap", "comparable", "note"]
        )
        for r in sorted(rows, key=lambda r: (r.product.value, r.depart_date)):
            v1 = evaluate_row(r)
            v2 = verdict_for_row(r)
            writer.writerow([
                r.product.value,
                r.depart_date.isoformat(),
                r.weekday_kr,
                r.our_price_2p if r.our_price_2p is not None else "",
                r.market_low_2p if r.market_low_2p is not None else "",
                v1.label,
                v2.verdict.value,
                v2.gap if v2.gap is not None else "",
                r.comparable,
                r.note,
            ])


def main() -> int:
    parser = argparse.ArgumentParser(description="마카오 항공 요금 방어 리포트 생성")
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "fares.csv")
    parser.add_argument("--out", type=Path, default=None,
                        help="지정 시 해당 폴더에 report.md / defense.csv 저장")
    parser.add_argument("--as-of", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
                        default=date.today(), help="신선도 기준일(기본: 오늘)")
    args = parser.parse_args()

    rows = load_fares(args.data)
    config = DEFAULT_CONFIG

    print(f"로드: {len(rows)}행  (데이터: {args.data})  기준일: {args.as_of}\n")

    print("[정밀 판정 v2]  🟦과방어 / ✅우위 / 🟨동률 / 🔴열위")
    for product, s in summarize_verdicts(rows, config).items():
        print(
            f"- {product.korean:<14} 🟦{s.over_defended:>3} ✅{s.win:>3} 🟨{s.tie:>3} "
            f"🔴{s.lose:>3} | 열위부족분 {s.total_loss:>10,} | 과방어여유분 {s.recoverable_margin:>10,}"
        )

    print("\n[방어 v1 · 시트 재현]")
    for product, s in summarize(rows).items():
        print(
            f"- {product.korean:<14} 성공 {s.ok:>3} / 실패 {s.fail:>3} "
            f"| 방어율 {s.defense_rate:5.1f}% | 실패분합계 {s.total_shortfall:>10,}"
        )

    issues = validate_dataset(rows, args.as_of, config)
    counts = summarize_issues(issues)
    print(f"\n[데이터 건전성]  ⛔{counts[Severity.ERROR]} ⚠️{counts[Severity.WARN]} ℹ️{counts[Severity.INFO]}")
    for issue in issues:
        if issue.severity is Severity.WARN:
            print(f"  ⚠️ {issue.code}: {issue.message}")

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "report.md").write_text(
            full_report_md(rows, args.as_of, config), encoding="utf-8")
        write_defense_csv(rows, args.out / "defense.csv")
        print(f"\n저장 완료 → {args.out}/report.md, {args.out}/defense.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
