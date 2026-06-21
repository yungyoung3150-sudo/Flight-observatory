"""CSV → 도메인 객체 로더.

data/fares.csv 를 읽어 FareRow 리스트로 만든다. 표준 라이브러리(csv)만 사용.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from .models import FareRow, Product

DEFAULT_FARES_CSV = Path(__file__).resolve().parents[2] / "data" / "fares.csv"
# 시트 1차 수집일. fares.csv 에 collected_on 컬럼이 없을 때 기본값으로 사용.
DEFAULT_COLLECTED_ON = date(2026, 6, 19)


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    value = value.strip().replace(",", "").replace("₩", "")
    return int(value) if value else None


def _parse_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()


# 시장최저가 '참고가/비교불가'임을 나타내는 비고 표식.
_REFERENCE_MARKERS = ("참고가", "미운항")


def _is_reference_only(note: str) -> bool:
    return any(m in note for m in _REFERENCE_MARKERS)


def load_fares(path: Path = DEFAULT_FARES_CSV,
               collected_on: date = DEFAULT_COLLECTED_ON) -> List[FareRow]:
    """fares.csv 를 FareRow 리스트로 로드한다."""
    rows: List[FareRow] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for raw in csv.DictReader(fh):
            note = (raw.get("note") or "").strip()
            # collected_on 컬럼이 있으면 행별 수집일 사용(수집기가 채움), 없으면 기본값.
            raw_collected = (raw.get("collected_on") or "").strip()
            row_collected = _parse_date(raw_collected) if raw_collected else collected_on
            rows.append(
                FareRow(
                    product=Product(raw["product"].strip()),
                    depart_date=_parse_date(raw["depart_date"]),
                    our_price_2p=_parse_int(raw.get("our_price_2p")),
                    market_low_2p=_parse_int(raw.get("market_low_2p")),
                    collected_on=row_collected,
                    note=note,
                    reference_only=_is_reference_only(note),
                )
            )
    return rows
