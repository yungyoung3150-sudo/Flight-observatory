# tripwire — 소비자가 OTA 덤핑 감시 (하루 2회, 로컬)

목적: **우리 공구가가 OTA의 '모든 결제 수단' 소비자 최저가보다 인당 분노임계(10만) 이상 비싸지면**
잡아내는 트립와이어. (카드사 할인 무관 — 표준 소비자가 자체가 인당 ~30만 빠진 다온맘형 덤핑이 표적.)

봇은 가격을 **자동 수집(합법 API)** 하거나, **사람을 정확한 네이버 화면으로 데려다 놓는다.**
판정은 기존 가드레일([../src/macau_fare_monitor/alert.py](../src/macau_fare_monitor/alert.py))을 재사용.

## 두 트랙 (둘 다 코드, 공유 싱크 `consumer_prices.csv`)

| | 트랙 A — 풀 자동 | 트랙 B — 네이버 사람판독 |
|:--|:--|:--|
| 소스 | 메타서치 소비자가 API(Travelpayouts) | 네이버 항공권 '모든 결제 수단' |
| 커버 | 글로벌 OTA 덤핑(Trip.com=다온맘 범인) | + 국내채널(모두투어·하나투어) |
| 사람 | 0 (완전 자동) | 링크 탭→숫자 1개 읽기 |
| 파일 | `meta_source.py` | `naver_deeplink.py`→`checklist_notifier.py`→`submit_price.py` |
| 컴플라이언스 | legit (라이선스 API) | legit (봇은 URL만 조립, 네이버 접속 0; 사람이 읽음) |

> 왜 네이버는 사람이 읽나: 네이버를 봇으로 긁는 건 사용자 폐기결정 + AUP(안티봇 우회 금지)라 불가.
> 봇은 '언제·어디'를 100% 자동화하고, '얼마'는 사람이 본다. (확정 human-in-the-loop)

## 흐름

```
[A] meta_source.py ─┐
                    ├─→ consumer_prices.csv ─→ evaluate_tripwire.py ─→ 🟢/🟡/🔴 (+경보 시 사람확인)
[B] checklist_notifier→사람→submit_price.py ─┘
```

## 실행 (설치 불필요, Python 3.9+)

```bash
# 판정만 (데모 데이터로 즉시 확인 — 30만 덤핑 → 🔴 경보 재현)
python3 tripwire/evaluate_tripwire.py

# 트랙 A 쿼리 계획(토큰 없이)            python3 tripwire/meta_source.py --demo
# 트랙 B 푸시 메시지(발송 없이)          python3 tripwire/checklist_notifier.py --dry-run
# 사람판독 제출                          python3 tripwire/submit_price.py --sku nx_icn_mfm_2n3d --depart 2026-07-25 --price 300000

# 전체 1회(래퍼)                         bash tripwire/run_tripwire.sh
```

## 운영 배치 (하루 2회 자동 — 맥 launchd)

```bash
cp tripwire/launchd/com.yestravel.tripwire.plist ~/Library/LaunchAgents/
# plist 안의 경로/자격증명 채운 뒤
launchctl load ~/Library/LaunchAgents/com.yestravel.tripwire.plist
```
→ 매일 09:00 / 18:00 에 `run_tripwire.sh` 실행. (서버/GHA 아님 — 로컬 맥. 네이버 헤드리스 차단+ToS 때문)

## 가동에 필요한 것 (3가지)

1. **`TRAVELPAYOUTS_TOKEN`** — 트랙 A 자동수집. 무료: https://www.travelpayouts.com → 발급 후 plist/셸에 export.
   (※ 발급 주시면 실제로 네이버급 '모든 결제 수단' 가격을 주는지 제가 바로 테스트해 검증.)
2. **`PUSHOVER_TOKEN` / `PUSHOVER_USER`** — 트랙 B 체크리스트·경보 푸시.
3. **실제 SKU** — `sku_catalog.json` 의 `our_price_pp`(우리 공구가 인당)·`depart_dates` 를 실 공구로 교체, BX 박수 오프셋 검증.

## 폰 UX 옵션 (트랙 B 회수)

`submit_price.py`(로컬 CLI) 대신 폰에서 제출하려면: 구글폼(출발일 프리필 + 숫자 1필드) → Apps Script
`onFormSubmit` 로 시트 append → 로컬 `pull_intake`(Sheets API)로 `consumer_prices.csv` 동기화.
(Apps Script 스니펫·Sheets 동기화는 후속 작업.)

## 정직한 한계

- **트랙 A(메타서치)는 캐시·글로벌**이라 국내채널 전용 덤핑은 늦/미탐 가능 → 트랙 B(네이버 사람)로 보완.
- **트랙 B는 사람이 하루 2회 회수**해야 함(빠뜨리면 미탐). 미회수는 신선도 워치독으로 완화(후속).
- 임계 2만/10만은 시작 기본값 — 실데이터로 보정.
- `our_price_pp`·BX 박수 등 카탈로그 값은 **placeholder**(실 공구로 교체 전까지 데모용).
