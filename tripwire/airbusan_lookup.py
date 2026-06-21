#!/usr/bin/env python3
"""에어부산(PUS-MFM) 수동 가격 수집 보조 + 가드레일 — 검수용 코드.

에어부산은 네이버 수집기 미커버라, Claude가 구글 항공에서 날짜별로 직접 확인(BX381/382)한다.
이 스크립트는 그 '수동 작업'을 결정적·검수 가능하게 만든다:

  1) plan : 박수 규칙으로 각 출발일의 (출발→귀국) 일정을 산출 → 구글에서 무엇을 검색할지 안내.
  2) eval : 수집한 가격(airbusan_manual.csv)을 읽어 시장최저(2인)=직항1인×2 계산 → 기존 가드레일 판정.

박수 규칙(출처: 옵시디언 '마카오 패키지 핵심 정보'):
  금·일 출발 = 2박4일 (귀국 = 출발+3)  /  화 출발 = 3박5일 (귀국 = 출발+4)
  [출국] BX381 부산 21:55 → 마카오 00:55(+1)  /  [귀국] BX382 마카오 01:55 → 부산 06:20
  그 외 요일 = 에어부산 미운항.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(ROOT))

from macau_fare_monitor.alert import AlertLevel, classify  # noqa: E402

MANUAL = ROOT / "airbusan_manual.csv"
# 요일: 월0 화1 수2 목3 금4 토5 일6
WD_KR = ["월", "화", "수", "목", "금", "토", "일"]


def itinerary(dep: date):
    """출발일 → (박수, 귀국일). 미운항 요일이면 (None, None)."""
    wd = dep.weekday()
    if wd in (4, 6):           # 금·일 출발
        return "2박4일", dep + timedelta(days=3)
    if wd == 1:                # 화 출발
        return "3박5일", dep + timedelta(days=4)
    return None, None


def cmd_plan(depart_dates):
    print("=== 에어부산 구글 검색 일정(BX381/382) — 부산(PUS)→마카오(MFM) ===\n")
    for ds in depart_dates:
        dep = datetime.strptime(ds, "%Y-%m-%d").date()
        stay, ret = itinerary(dep)
        if stay is None:
            print(f"  {ds}({WD_KR[dep.weekday()]}): 에어부산 미운항 요일 — 건너뜀")
            continue
        print(f"  {ds}({WD_KR[dep.weekday()]}) {stay}: 출발 {ds} → 귀국 {ret.isoformat()}"
              f"({WD_KR[ret.weekday()]})  [구글: PUS→MFM 왕복, 에어부산 직항가 읽기]")


def cmd_eval(path: Path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not (r.get("bx_direct_pp") or "").strip():
                continue
            dep = datetime.strptime(r["depart_date"], "%Y-%m-%d").date()
            stay, ret = itinerary(dep)
            our_2p = int(r["our_2p"]) if r.get("our_2p") else None
            bx_pp = int(r["bx_direct_pp"])
            market_2p = bx_pp * 2                 # 시장최저(2인) = 직항 1인 × 2
            a = classify(our_2p, market_2p)
            rows.append((dep, stay, ret, our_2p, bx_pp, market_2p, a))

    order = {AlertLevel.ALARM: 0, AlertLevel.WATCH: 1, AlertLevel.SAFE: 2}
    rows.sort(key=lambda t: (order.get(t[6].level, 9), -(t[6].surcharge_pp or 0)))
    n = {lv: sum(1 for t in rows if t[6].level is lv)
         for lv in (AlertLevel.ALARM, AlertLevel.WATCH, AlertLevel.SAFE)}
    print(f"=== 에어부산 가드레일: {len(rows)}건 · "
          f"🔴{n[AlertLevel.ALARM]} 🟠{n[AlertLevel.WATCH]} 🟢{n[AlertLevel.SAFE]} ===\n")
    for dep, stay, ret, our, bx, mkt, a in rows:
        print(f"{a.label:<22} {dep}({WD_KR[dep.weekday()]}) {stay}  "
              f"우리 {our:,} vs 시장 {mkt:,}(직항 {bx:,}×2)  →시트입력값 {mkt}")


def main() -> int:
    p = argparse.ArgumentParser(description="에어부산 수동수집 보조+가드레일")
    sub = p.add_subparsers(dest="cmd")
    pe = sub.add_parser("eval", help="수집값으로 가드레일 판정")
    pe.add_argument("--csv", type=Path, default=MANUAL)
    pp = sub.add_parser("plan", help="출발일들의 구글 검색 일정 산출")
    pp.add_argument("dates", nargs="+", help="출발일 YYYY-MM-DD ...")
    args = p.parse_args()

    if args.cmd == "plan":
        cmd_plan(args.dates)
    else:
        cmd_eval(getattr(args, "csv", MANUAL))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
