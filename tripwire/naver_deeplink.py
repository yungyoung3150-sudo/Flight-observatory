#!/usr/bin/env python3
"""네이버 항공권 딥링크 빌더 — SKU × 출발일 → 왕복 검색 URL.

★중요(컴플라이언스): 이 스크립트는 **네이버에 접속하지 않는다.** 문자열로 URL을 조립할 뿐이다.
안티봇 우회·헤드리스·스크래핑이 전혀 없다. 만든 URL은 '체크리스트 알림'에 실려 사람에게 가고,
사람이 자기 정상 브라우저로 열어 **'모든 결제 수단' 최저가**를 직접 눈으로 읽는다.

타깃 = 네이버 '모든 결제 수단' 최저가(카드사 할인 무관). OTA 덤핑은 이 표준 소비자가가
인당 ~30만원 빠지는 형태로 나타난다 — 카드 할인 문제가 아니다.
왜 봇이 네이버를 직접 안 읽나: ① 네이버 봇 자동읽기는 사용자가 이미 폐기 결정한 '스크래핑/우회'
경로이고 ② 자동화 탐지를 뚫으려면 우회가 구조적으로 필요(=AUP 위반, 제작 불가). ∴ 네이버 그 숫자
판독은 사람(딥링크로 정확한 화면에 데려다 놓음). '풀 자동'은 합법 메타서치 소비자가 API가 별도 길
(네이버를 안 긁어도 같은 모든-결제-수단 표준가를 줌).
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "sku_catalog.json"

# 검증된 네이버 항공권 국제선 왕복 URL 패턴(메모리: 엔드포인트 구조 파악됨).
# {O}-{D}-{YYYYMMDD} 가출 / {D}-{O}-{YYYYMMDD} 귀국, adult=1, fareType=Y(일반석).
NAVER_BASE = ("https://flight.naver.com/flights/international/"
              "{o}-{d}-{dep}/{d}-{o}-{ret}?adult=1&fareType=Y")


def build_url(origin: str, dest: str, depart: date, return_offset_days: int) -> str:
    ret = depart + timedelta(days=return_offset_days)
    return NAVER_BASE.format(o=origin, d=dest,
                             dep=depart.strftime("%Y%m%d"),
                             ret=ret.strftime("%Y%m%d"))


def build_checklist(catalog: dict) -> List[dict]:
    """카탈로그 → 그날 사람이 확인할 (SKU×출발일) 딥링크 목록."""
    items: List[dict] = []
    for sku in catalog["skus"]:
        for ds in sku["depart_dates"]:
            depart = datetime.strptime(ds, "%Y-%m-%d").date()
            items.append({
                "sku_id": sku["id"],
                "carrier": sku["carrier_name"],
                "route": f'{sku["origin"]}-{sku["dest"]}',
                "stay": sku["stay"],
                "depart": ds,
                "our_price_pp": sku.get("our_price_pp"),
                "flight_hint": sku.get("flight_hint", ""),
                "naver_url": build_url(sku["origin"], sku["dest"], depart,
                                       sku["return_offset_days"]),
            })
    return items


def load_catalog(path: Path = CATALOG) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    parser = argparse.ArgumentParser(description="네이버 항공권 딥링크 생성(스크래핑 아님)")
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--json", action="store_true", help="JSON으로 출력")
    args = parser.parse_args()

    items = build_checklist(load_catalog(args.catalog))
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0

    print(f"=== 오늘 확인할 SKU×출발일: {len(items)}건 (사람이 링크 열어 '모든 결제 수단' 최저가 읽기) ===\n")
    for it in items:
        price = f'{it["our_price_pp"]:,}' if it["our_price_pp"] else "(공구가 미설정)"
        print(f"[{it['carrier']} {it['stay']}] {it['route']} {it['depart']}  우리 인당 {price}")
        print(f"  힌트: {it['flight_hint']}")
        print(f"  {it['naver_url']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
