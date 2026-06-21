#!/usr/bin/env python3
"""[트랙 B — 사람판독] 네이버 딥링크 체크리스트를 Pushover로 발송.

봇은 네이버에 접속하지 않는다. 그날 확인할 SKU×출발일의 네이버 딥링크 + 우리 공구가를 묶어
Pushover로 푸시할 뿐. 사람이 폰에서 링크를 탭→'모든 결제 수단' 최저가를 눈으로 읽고
submit_price.py(또는 회수 폼)로 숫자 1개 제출 → consumer_prices.csv → evaluate_tripwire 판정.

자격증명: 환경변수 PUSHOVER_TOKEN(앱), PUSHOVER_USER(유저 키). 없으면 --dry-run 으로 출력만.
표준 라이브러리만 사용(urllib).
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from naver_deeplink import build_checklist, load_catalog  # noqa: E402

PUSHOVER_API = "https://api.pushover.net/1/messages.json"


def format_message(items) -> str:
    lines = ["[네이버 '모든 결제 수단' 최저가 확인] 링크 탭→최저가 읽고 제출", ""]
    for it in items:
        price = f'{it["our_price_pp"]:,}' if it["our_price_pp"] else "(미설정)"
        lines.append(f"• {it['carrier']} {it['stay']} {it['depart']} | 우리 인당 {price}")
        lines.append(f"  {it['flight_hint']}")
        lines.append(f"  {it['naver_url']}")
    lines.append("")
    lines.append("→ 읽은 숫자: submit_price.py --sku <id> --depart <YYYY-MM-DD> --price <원>")
    return "\n".join(lines)


def send_pushover(message: str, token: str, user: str, title: str) -> None:
    data = urllib.parse.urlencode({
        "token": token, "user": user, "title": title,
        "message": message, "priority": "0",
    }).encode()
    req = urllib.request.Request(PUSHOVER_API, data=data)
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Pushover {resp.status}")


def main() -> int:
    parser = argparse.ArgumentParser(description="네이버 딥링크 체크리스트 푸시")
    parser.add_argument("--catalog", type=Path, default=ROOT / "sku_catalog.json")
    parser.add_argument("--dry-run", action="store_true", help="발송 없이 메시지 출력")
    parser.add_argument("--title", default="마카오 항공 가격 확인(하루 2회)")
    args = parser.parse_args()

    items = build_checklist(load_catalog(args.catalog))
    message = format_message(items)

    token = os.environ.get("PUSHOVER_TOKEN")
    user = os.environ.get("PUSHOVER_USER")
    if args.dry_run or not (token and user):
        if not args.dry_run:
            print("(PUSHOVER_TOKEN/PUSHOVER_USER 없음 → dry-run 출력)\n", file=sys.stderr)
        print(message)
        return 0

    send_pushover(message, token, user, args.title)
    print(f"[notify] Pushover 발송 완료 — SKU×출발일 {len(items)}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
