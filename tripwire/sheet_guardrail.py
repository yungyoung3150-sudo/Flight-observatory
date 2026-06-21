#!/usr/bin/env python3
"""시트 → 가드레일 연결.

당신의 네이버 수집기가 채우는 구글 시트(시장최저 vs 우리요금)를 읽어, 기존 가드레일
(macau_fare_monitor.alert)의 인당·비대칭 임계(5만/10만)로 🟢/🟠/🔴 판정한다.
봇이 네이버를 긁지 않는다 — '이미 수집된 시트'만 읽는다.

데이터 입력:
  - 지금: tripwire/sheet_today.csv (시트에서 추출한 product,depart,our_2p,market_2p)
  - 운영(무인): 시트 API로 같은 컬럼을 읽으면 됨(아래 read_sheet_via_api 자리). 또는
    더 간단히는 시트에 붙는 Apps Script(tripwire/guardrail.gs)로 시트 안에서 돌린다.

옵션: PUSHOVER_TOKEN/PUSHOVER_USER 있으면 🔴/🟠 아이폰 발송.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(ROOT))

from macau_fare_monitor.alert import AlertLevel, classify  # noqa: E402
import pushover  # noqa: E402

DEFAULT_CSV = ROOT / "sheet_today.csv"


def evaluate_rows(path: Path):
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            our = int(r["our_2p"]) if r.get("our_2p") else None
            mkt = int(r["market_2p"]) if r.get("market_2p") else None
            a = classify(our, mkt)  # 인당 환산·임계는 alert.classify 가 처리
            out.append({"product": r["product"], "depart": r["depart"],
                        "our": our, "market": mkt, "level": a.level,
                        "surcharge_pp": a.surcharge_pp, "label": a.label})
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="시트 데이터로 가드레일 판정")
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    p.add_argument("--no-push", action="store_true")
    args = p.parse_args()

    rows = evaluate_rows(args.csv)
    order = {AlertLevel.ALARM: 0, AlertLevel.WATCH: 1, AlertLevel.SAFE: 2}
    rows.sort(key=lambda r: (order.get(r["level"], 9), -(r["surcharge_pp"] or 0)))

    n = {lv: sum(1 for r in rows if r["level"] is lv) for lv in
         (AlertLevel.ALARM, AlertLevel.WATCH, AlertLevel.SAFE)}
    print(f"=== 시트 가드레일: {len(rows)}행 · "
          f"🔴{n[AlertLevel.ALARM]} 🟠{n[AlertLevel.WATCH]} 🟢{n[AlertLevel.SAFE]} ===\n")
    for r in rows:
        if r["level"] in (AlertLevel.ALARM, AlertLevel.WATCH):
            print(f"{r['label']:<20} {r['product']} {r['depart']}  "
                  f"우리 {r['our']:,} vs 시장 {r['market']:,}")

    alarms = [r for r in rows if r["level"] is AlertLevel.ALARM]
    watches = [r for r in rows if r["level"] is AlertLevel.WATCH]
    if (alarms or watches) and not args.no_push:
        if pushover.configured():
            lines = [f"{r['label']} {r['product']} {r['depart']} (시장 {r['market']:,})"
                     for r in (alarms + watches)]
            pushover.send("\n".join(lines),
                          "🔴 마카오 항공 경보" if alarms else "🟠 마카오 항공 주의",
                          priority=1 if alarms else 0)
            print(f"\n아이폰 발송: 🔴{len(alarms)} 🟠{len(watches)}")
        else:
            print("\n(Pushover 미설정 → 아이폰 발송 생략)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
