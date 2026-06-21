#!/usr/bin/env python3
"""시세 수집기 — data/fares.csv 의 시장최저값을 갱신하고 수집 로그를 남긴다.

하루 2회(오전/오후) 자동 실행되는 파이프라인의 '수집' 단계. 소스는 교체 가능하다:

    --source demo      기존 데이터 그대로(파이프라인 검증용 — 실제 시세는 안 바뀜)
    --source amadeus   (TODO) Amadeus self-service Flight Offers Search.
                       AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET 환경변수 필요.

⚠️ 정직한 한계: Amadeus 같은 published 운임 API는 OTA의 '카드·페이 즉시할인 덤핑'을
   보지 못한다. 그게 이 가드레일의 핵심 표적이라(README §3), 진짜로 막으려면 소비자 OTA
   채널 최종결제가(네이버 등)를 별도 소스로 더해야 한다. 이 수집기는 그 소스를 끼우는 자리다.

설치 없이 실행되도록 src/ 를 import 경로에 추가한다.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "src"))

from macau_fare_monitor.models import Product  # noqa: E402

FARES = DATA / "fares.csv"
LOG = DATA / "collection_log.csv"
FIELDS = ["product", "depart_date", "our_price_2p", "market_low_2p", "collected_on", "note"]


# ─────────────────────────── 소스(교체 가능) ───────────────────────────

class FareSource:
    """시장최저값을 갱신하는 소스 인터페이스.

    collect() 는 (갱신된 rows, 실제로 바뀌었는지) 를 돌려준다.
    rows 는 fares.csv 의 dict 행 리스트. market_low_2p / collected_on 만 갱신하면 된다
    (우리요금 our_price_2p 는 우리 내부 가격이라 소스가 건드리지 않는다).
    """

    name = "base"

    def collect(self, rows: List[dict], today: date) -> "tuple[List[dict], bool]":
        raise NotImplementedError


class DemoSource(FareSource):
    """아무것도 수집하지 않는다 — 파이프라인이 도는지 확인용. 데이터/신선도 불변."""

    name = "demo"

    def collect(self, rows, today):
        return rows, False


class AmadeusSource(FareSource):
    """Amadeus self-service Flight Offers Search 어댑터(미구현).

    구현 시: OAuth2 토큰 발급(client_credentials) → GET /v2/shopping/flight-offers
    (ICN→MFM 등, 날짜별 최저 total price) → market_low_2p = 1인 최저 × 2, collected_on = today.
    """

    name = "amadeus"

    def collect(self, rows, today):
        raise NotImplementedError(
            "Amadeus 어댑터 미구현. AMADEUS_CLIENT_ID/SECRET 발급 후 연결 필요(README §7)."
        )


SOURCES = {s.name: s for s in (DemoSource, AmadeusSource)}


# ─────────────────────────── 입출력 ───────────────────────────

def read_fares(path: Path) -> List[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def write_fares(path: Path, rows: List[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in FIELDS})


def _min_1p(rows: List[dict], product: Product) -> str:
    vals = [int(r["market_low_2p"]) for r in rows
            if r["product"] == product.value and r.get("market_low_2p")]
    return str(min(vals) // 2) if vals else ""


def append_log(path: Path, run_at: str, data_date: str, rows: List[dict], source: str) -> None:
    priced = [r for r in rows if r.get("market_low_2p")]
    row = [run_at, data_date, str(len(priced)),
           _min_1p(rows, Product.AIRMACAU_2N3D), _min_1p(rows, Product.AIRMACAU_3N4D), source]
    new_file = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if new_file:
            writer.writerow(["run_at", "data_collected_on", "row_count",
                             "min_2n3d_1p", "min_3n4d_1p", "source"])
        writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="시세 수집 → fares.csv 갱신")
    parser.add_argument("--source", choices=list(SOURCES), default="demo")
    parser.add_argument("--data", type=Path, default=FARES)
    args = parser.parse_args()

    rows = read_fares(args.data)
    today = date.today()
    src = SOURCES[args.source]()

    updated, changed = src.collect(rows, today)
    run_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if changed:
        write_fares(args.data, updated)
        data_date = today.isoformat()
        print(f"[collect:{src.name}] 시세 갱신 완료 → {args.data} (수집일 {data_date})")
    else:
        existing = next((r.get("collected_on") for r in rows if r.get("collected_on")), "")
        data_date = existing or "(기존)"
        print(f"[collect:{src.name}] 실제 수집 없음 — fares.csv 불변(데이터 여전히 {data_date}). "
              f"실데이터는 source 어댑터 구현 필요(README §7).")

    append_log(LOG, run_at, data_date, updated, src.name)
    print(f"[collect:{src.name}] 로그 기록 → {LOG} (run_at={run_at})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
