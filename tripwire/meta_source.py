#!/usr/bin/env python3
"""[트랙 A — 풀 자동] 메타서치 소비자가 수집기 (Travelpayouts/Aviasales Data API).

OTA가 실제로 파는 '모든 결제 수단' 표준 소비자가를 합법 API로 수집한다(네이버 스크래핑 아님).
Amadeus(항공사 공급가)와 달리 OTA 소비자가라 글로벌 OTA(예: Trip.com=다온맘 범인) 덤핑이 보인다.
수집값은 consumer_prices.csv 에 source=travelpayouts 로 적재 → evaluate_tripwire 가 판정.

자격증명: 환경변수 TRAVELPAYOUTS_TOKEN (https://www.travelpayouts.com 무료 가입 후 발급).
한계: 캐시성·글로벌 메타라 국내 채널 전용 덤핑(모두투어·하나투어)은 못 볼 수 있음 → 네이버(트랙 B)로 보완.

표준 라이브러리만 사용(urllib). --demo 는 네트워크 없이 호출 계획만 출력.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "sku_catalog.json"
PRICES = ROOT / "consumer_prices.csv"
FIELDS = ["sku_id", "depart_date", "source", "consumer_pp", "observed_at", "note"]
API = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
SOURCE = "travelpayouts"


def load_catalog(path: Path = CATALOG) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _plan(catalog: dict) -> List[Tuple[dict, str, str]]:
    """(sku, depart, return) 쿼리 계획."""
    plan = []
    for sku in catalog["skus"]:
        for ds in sku["depart_dates"]:
            dep = datetime.strptime(ds, "%Y-%m-%d").date()
            ret = dep + timedelta(days=sku["return_offset_days"])
            plan.append((sku, ds, ret.isoformat()))
    return plan


def fetch_cheapest_pp(origin: str, dest: str, depart: str, return_at: str,
                      token: str, currency: str = "krw") -> Optional[int]:
    """왕복 1인 최저가(소비자가) 조회. 실패/무결과면 None."""
    params = {
        "origin": origin, "destination": dest,
        "departure_at": depart, "return_at": return_at,
        "currency": currency, "sorting": "price", "direct": "false",
        "one_way": "false", "limit": "1", "page": "1",
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"X-Access-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # 네트워크/파싱 실패 → 스킵(미탐<오탐이라 조용히 넘기고 로그)
        print(f"  ! {origin}-{dest} {depart} 조회 실패: {exc}", file=sys.stderr)
        return None
    data = payload.get("data") or []
    if not data:
        return None
    price = data[0].get("price")
    return int(price) if price is not None else None


def _upsert(path: Path, new_rows: List[dict]) -> None:
    """(sku_id, depart_date, source) 기준 upsert."""
    existing: List[dict] = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            existing = list(csv.DictReader(fh))
    key = lambda r: (r["sku_id"], r["depart_date"], r["source"])
    keys = {key(r) for r in new_rows}
    merged = [r for r in existing if key(r) not in keys] + new_rows
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in merged:
            writer.writerow({k: r.get(k, "") for k in FIELDS})


def main() -> int:
    parser = argparse.ArgumentParser(description="메타서치 소비자가 수집(Travelpayouts)")
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--out", type=Path, default=PRICES)
    parser.add_argument("--demo", action="store_true", help="네트워크 없이 쿼리 계획만 출력")
    args = parser.parse_args()

    catalog = load_catalog(args.catalog)
    plan = _plan(catalog)

    if args.demo:
        print(f"[meta:demo] 쿼리 계획 {len(plan)}건 (토큰 발급 시 실제 수집):")
        for sku, dep, ret in plan:
            print(f"  {sku['origin']}-{sku['dest']} {dep}→{ret}  ({sku['carrier_name']} {sku['stay']})")
        print("\n토큰 설정 후: TRAVELPAYOUTS_TOKEN=... python3 tripwire/meta_source.py")
        return 0

    token = os.environ.get("TRAVELPAYOUTS_TOKEN")
    if not token:
        print("✗ TRAVELPAYOUTS_TOKEN 환경변수 필요. (무료: https://www.travelpayouts.com)\n"
              "  계획만 보려면 --demo", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: List[dict] = []
    for sku, dep, ret in plan:
        pp = fetch_cheapest_pp(sku["origin"], sku["dest"], dep, ret, token)
        if pp is None:
            continue
        rows.append({"sku_id": sku["id"], "depart_date": dep, "source": SOURCE,
                     "consumer_pp": pp, "observed_at": now, "note": "auto"})
        print(f"  {sku['carrier_name']} {sku['stay']} {dep}: 인당 {pp:,}")

    if rows:
        _upsert(args.out, rows)
        print(f"\n[meta] {len(rows)}건 적재 → {args.out}")
    else:
        print("[meta] 수집 0건(무결과/실패).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
