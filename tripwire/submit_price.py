#!/usr/bin/env python3
"""[트랙 B 회수] 사람이 네이버에서 읽은 '모든 결제 수단' 최저가를 consumer_prices.csv 에 기록.

로컬 CLI(폰 UX는 README의 구글폼+Apps Script 옵션). (sku_id, depart, source) upsert.
예) python3 tripwire/submit_price.py --sku nx_icn_mfm_2n3d --depart 2026-07-25 --price 300000
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent
PRICES = ROOT / "consumer_prices.csv"
FIELDS = ["sku_id", "depart_date", "source", "consumer_pp", "observed_at", "note"]


def upsert(path: Path, row: dict) -> None:
    rows: List[dict] = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    k = (row["sku_id"], row["depart_date"], row["source"])
    rows = [r for r in rows if (r["sku_id"], r["depart_date"], r["source"]) != k]
    rows.append(row)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in FIELDS})


def main() -> int:
    p = argparse.ArgumentParser(description="네이버 사람판독 가격 제출")
    p.add_argument("--sku", required=True)
    p.add_argument("--depart", required=True, help="YYYY-MM-DD")
    p.add_argument("--price", required=True, type=int, help="모든 결제 수단 최저가(인당, 원)")
    p.add_argument("--source", default="naver_human")
    p.add_argument("--out", type=Path, default=PRICES)
    args = p.parse_args()

    row = {
        "sku_id": args.sku, "depart_date": args.depart, "source": args.source,
        "consumer_pp": str(args.price),
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "human",
    }
    upsert(args.out, row)
    print(f"기록: {args.sku} {args.depart} 인당 {args.price:,} ({args.source}) → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
