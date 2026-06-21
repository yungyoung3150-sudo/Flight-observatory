#!/usr/bin/env python3
"""트립와이어 판정 — consumer_prices.csv(소비자 '모든 결제 수단' 최저가) × 우리 공구가 → 경보.

두 소스(메타서치 API / 네이버 사람판독)가 consumer_prices.csv 에 쓴 값을 읽어, 기존 가드레일
(macau_fare_monitor.alert)의 비대칭·인당 판정으로 🟢안전/🟡주의/🔴경보를 매긴다.

초과액(인당) = 우리공구가(인당) − 소비자최저(인당). 양수 = 우리가 더 비쌈.
  ≤ +2만 → 🟢안전 · +2만~10만 → 🟡주의 · ≥ +10만 → 🔴경보(덤핑 의심, 사람 확인)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "src"))

from macau_fare_monitor.alert import AlertLevel, classify  # noqa: E402
from macau_fare_monitor.config import DefenseConfig  # noqa: E402

CATALOG = ROOT / "sku_catalog.json"
PRICES = ROOT / "consumer_prices.csv"


def load_catalog(path: Path = CATALOG) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def our_price_map(catalog: dict) -> Dict[str, dict]:
    return {s["id"]: s for s in catalog["skus"]}


def read_prices(path: Path = PRICES) -> List[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if (r.get("consumer_pp") or "").strip()]


def evaluate(catalog: dict, prices: List[dict], config: DefenseConfig):
    skus = our_price_map(catalog)
    results = []
    for row in prices:
        sku = skus.get(row["sku_id"])
        if sku is None:
            continue
        our_pp = sku.get("our_price_pp")
        consumer_pp = int(row["consumer_pp"])
        # alert.classify 는 2인 합산 입력을 받아 인당으로 환산 → ×2 로 넘긴다.
        a = classify(
            our_pp * 2 if our_pp is not None else None,
            consumer_pp * 2,
            config,
        )
        results.append({
            "sku_id": row["sku_id"],
            "carrier": sku["carrier_name"],
            "stay": sku["stay"],
            "depart": row["depart_date"],
            "source": row.get("source", ""),
            "our_pp": our_pp,
            "consumer_pp": consumer_pp,
            "surcharge_pp": a.surcharge_pp,
            "level": a.level,
            "label": a.label,
        })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="소비자가 트립와이어 판정")
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--prices", type=Path, default=PRICES)
    args = parser.parse_args()

    catalog = load_catalog(args.catalog)
    config = DefenseConfig(
        safe_max_surcharge_pp=catalog.get("tolerance_pp", 20000),
        alarm_min_surcharge_pp=catalog.get("anger_threshold_pp", 100000),
    )
    results = evaluate(catalog, read_prices(args.prices), config)

    order = {AlertLevel.ALARM: 0, AlertLevel.WATCH: 1, AlertLevel.SAFE: 2}
    results.sort(key=lambda r: (order.get(r["level"], 9), -(r["surcharge_pp"] or 0)))

    alarms = [r for r in results if r["level"] is AlertLevel.ALARM]
    print(f"=== 트립와이어 판정: {len(results)}건 · 🔴경보 {len(alarms)}건 ===\n")
    for r in results:
        our = f'{r["our_pp"]:,}' if r["our_pp"] else "(공구가 미설정)"
        con = f'{r["consumer_pp"]:,}'
        print(f"{r['label']:<22} {r['carrier']} {r['stay']} {r['depart']} "
              f"[{r['source']}]  우리 {our} vs 소비자 {con} (인당)")
    if alarms:
        print("\n🔴 경보 — 사람이 네이버에서 확인 후 그 출발일 판매 보류/가격조정:")
        for r in alarms:
            print(f"  · {r['carrier']} {r['stay']} {r['depart']}: "
                  f"소비자가 우리보다 인당 {r['surcharge_pp']:,} 더 쌈 ({r['source']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
