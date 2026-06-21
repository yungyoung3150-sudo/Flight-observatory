#!/usr/bin/env python3
"""data/fares.csv 를 읽어 컴플레인 가드레일 리포트를 생성하는 CLI.

사용:
    python scripts/build_report.py                  # 콘솔 요약(경보/수동확인/건전성)
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
    alert_for_row,
    full_report_md,
    load_fares,
    summarize_alerts,
    summarize_issues,
    validate_dataset,
)
from macau_fare_monitor.alert import AlertLevel  # noqa: E402
from macau_fare_monitor.models import Product  # noqa: E402


def write_alert_csv(rows, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["product", "depart_date", "weekday", "our_price_2p", "market_low_2p",
             "surcharge_pp", "alert", "comparable", "approx_2p", "note"]
        )
        for r in sorted(rows, key=lambda r: (r.product.value, r.depart_date)):
            a = alert_for_row(r)
            writer.writerow([
                r.product.value, r.depart_date.isoformat(), r.weekday_kr,
                r.our_price_2p if r.our_price_2p is not None else "",
                r.market_low_2p if r.market_low_2p is not None else "",
                a.surcharge_pp if a.surcharge_pp is not None else "",
                a.level.value, r.comparable, a.approx_2p, r.note,
            ])


def main() -> int:
    parser = argparse.ArgumentParser(description="마카오 항공 컴플레인 가드레일 리포트")
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "fares.csv")
    parser.add_argument("--out", type=Path, default=None,
                        help="지정 시 해당 폴더에 report.md / alerts.csv 저장")
    parser.add_argument("--as-of", type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
                        default=date.today(), help="신선도 기준일(기본: 오늘)")
    args = parser.parse_args()

    rows = load_fares(args.data)
    config = DEFAULT_CONFIG
    print(f"로드: {len(rows)}행  (데이터: {args.data})  기준일: {args.as_of}")
    print(f"임계: 🔴경보 ≥ 인당 {config.alarm_min_surcharge_pp:,} · "
          f"🟠주의 인당 {config.watch_min_surcharge_pp:,}~{config.alarm_min_surcharge_pp:,}\n")

    print("[컴플레인 가드레일]  🔴경보 / 🟠주의 / 🟢안전")
    for product, s in summarize_alerts(rows, config).items():
        flags = []
        if s.no_market:
            flags.append(f"🔍수동확인 {s.no_market}")
        if s.non_comparable:
            flags.append(f"◻비교불가 {s.non_comparable}")
        extra = ("  | " + " ".join(flags)) if flags else ""
        print(
            f"- {product.korean:<14} 🔴{s.alarm:>2} 🟠{s.watch:>2} 🟢{s.safe:>2} "
            f"| 최대초과 인당 {s.worst_surcharge_pp:>8,}{extra}"
        )

    # 경보(있으면) 상세
    alarms = [(r, alert_for_row(r, config)) for r in rows
              if alert_for_row(r, config).level is AlertLevel.ALARM]
    if alarms:
        print("\n  🔴 경보 상세:")
        for r, a in sorted(alarms, key=lambda ra: -(ra[1].surcharge_pp or 0)):
            print(f"    {r.depart_date} {r.product.korean}: 인당 +{a.surcharge_pp:,}")
    else:
        print("\n  🔴 경보 0건 (현재 스냅샷) — 가드레일의 진짜 값은 판매 중 OTA 덤핑 때.")

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
        write_alert_csv(rows, args.out / "alerts.csv")
        print(f"\n저장 완료 → {args.out}/report.md, {args.out}/alerts.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
