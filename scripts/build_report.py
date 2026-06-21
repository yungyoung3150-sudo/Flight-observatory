#!/usr/bin/env python3
"""data/fares.csv 를 읽어 방어 리포트를 생성하는 CLI.

사용:
    python scripts/build_report.py                 # 요약을 콘솔에 출력
    python scripts/build_report.py --out reports    # reports/ 에 마크다운/CSV 저장

설치 없이 실행되도록 src/ 를 import 경로에 추가한다.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from macau_fare_monitor import (  # noqa: E402
    evaluate_row,
    full_report_md,
    load_fares,
    summarize,
)
from macau_fare_monitor.models import Product  # noqa: E402


def write_defense_csv(rows, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["product", "depart_date", "weekday", "our_price_2p",
             "market_low_2p", "defense", "gap", "note"]
        )
        for r in sorted(rows, key=lambda r: (r.product.value, r.depart_date)):
            result = evaluate_row(r)
            writer.writerow([
                r.product.value,
                r.depart_date.isoformat(),
                r.weekday_kr,
                r.our_price_2p if r.our_price_2p is not None else "",
                r.market_low_2p if r.market_low_2p is not None else "",
                result.label,
                result.gap if result.gap is not None else "",
                r.note,
            ])


def main() -> int:
    parser = argparse.ArgumentParser(description="마카오 항공 요금 방어 리포트 생성")
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "fares.csv")
    parser.add_argument("--out", type=Path, default=None,
                        help="지정 시 해당 폴더에 report.md / defense.csv 저장")
    args = parser.parse_args()

    rows = load_fares(args.data)
    summaries = summarize(rows)

    # 콘솔 요약
    print(f"로드: {len(rows)}행  (데이터: {args.data})")
    print(f"기준일(as-of): {date(2026, 6, 21)}\n")
    for product in Product:
        s = summaries.get(product)
        if s is None:
            continue
        print(
            f"- {product.korean:<14} 성공 {s.ok:>3} / 실패 {s.fail:>3} / "
            f"미입력 {s.no_our_price:>3} / 시장미수집 {s.no_market:>3} "
            f"| 방어율 {s.defense_rate:5.1f}% | 실패분합계 {s.total_shortfall:>10,}"
        )

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "report.md").write_text(full_report_md(rows), encoding="utf-8")
        write_defense_csv(rows, args.out / "defense.csv")
        print(f"\n저장 완료 → {args.out}/report.md, {args.out}/defense.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
