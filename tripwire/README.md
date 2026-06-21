# tripwire — 소비자가 OTA 덤핑 감시 (하루 2회)

목적: **우리 공구가가 OTA의 '모든 결제 수단' 소비자 최저가보다 인당 일정 이상 비싸지면** 잡아내는
트립와이어. (카드사 할인 무관 — 표준 소비자가 자체가 인당 ~30만 빠진 다온맘형 덤핑이 표적.)

**경보 단계(초과액=우리 − 소비자, 인당):**
- `< 5만` → 🟢 **안전** (고객이 거의 신경 안 씀)
- `5만 ~ 10만` → 🟠 **주의** (고객 이슈 가능) — 아이폰 일반 알림
- `≥ 10만` → 🔴 **경보** (컴플레인) — **아이폰 긴급 알림(Pushover priority 1)**

봇은 가격을 **자동 수집(합법 API)** 하거나, **사람을 정확한 네이버 화면으로 데려다 놓는다.**
판정은 기존 가드레일([../src/macau_fare_monitor/alert.py](../src/macau_fare_monitor/alert.py))을 재사용.

## ★ 실제 데이터 소스 = 당신의 기존 시트 (확정)

당신(팀)은 이미 **네이버 수집기**가 구글 시트에 시장최저를 매일 채우고 있다(수집일 갱신 확인).
그러므로 봇이 네이버를 새로 긁을 필요가 없다 — **이미 수집된 시트만 읽어** 판정한다.

```
당신 네이버 수집기 ─→ 구글 시트(시장최저 vs 우리요금) ─→ 가드레일 ─→ 🟠/🔴 아이폰
```

두 가지 실행 방법:

- **(권장) 시트 안 Apps Script** — [guardrail.gs](guardrail.gs). 시트에 붙여 하루 2회 자동 실행 →
  외부 서버 0. 설정 3단계(붙여넣기 / 스크립트 속성에 PUSHOVER_TOKEN·USER / installTriggers 1회).
- **Python** — [sheet_guardrail.py](sheet_guardrail.py). 시트에서 추출한 CSV(또는 시트 API)를 읽어 판정.
  데모: `python3 tripwire/sheet_guardrail.py`(오늘자 [sheet_today.csv](sheet_today.csv) → 🟢/🟠/🔴).

> 효과(오늘자 실데이터): 시트가 '방어실패(빨강)'로 칠한 구간도 **고객 기준(인당 5만/10만)으론
> 대부분 🟢안전·🟠주의, 🔴 컴플레인급 0건.** 아이폰은 진짜 🔴일 때만 울린다.

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
                    ├─→ consumer_prices.csv ─→ evaluate_tripwire.py ─→ 🟢/🟠/🔴 (+경보 시 사람확인)
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

## 운영 배치

### 1순위 — GitHub Actions (클라우드 백그라운드, 맥 안 켜도 됨)

트랙 A는 API 호출이라 **스크래핑이 없어 클라우드에서 합법적으로 자동 실행** 가능.
[.github/workflows/tripwire.yml](../.github/workflows/tripwire.yml) 가 하루 2회(09:00/18:00 KST) 수집→판정→아이폰 경보.

```
Repo → Settings → Secrets and variables → Actions 에 3개 등록:
  TRAVELPAYOUTS_TOKEN,  PUSHOVER_TOKEN,  PUSHOVER_USER
```
→ 등록하면 끝. 🔴/🟠 발생 시 아이폰으로 Pushover 알림. (트랙 B 네이버 사람판독은 폰/로컬 보완)

### 2순위 — 로컬 맥 launchd (대안/보완)

```bash
cp tripwire/launchd/com.yestravel.tripwire.plist ~/Library/LaunchAgents/
# plist 안의 경로/자격증명 채운 뒤
launchctl load ~/Library/LaunchAgents/com.yestravel.tripwire.plist
```
→ 매일 09:00 / 18:00 `run_tripwire.sh`. 트랙 B(네이버 사람판독)까지 포함하려면 로컬이 편함.

## 가동에 필요한 것 (3가지)

1. **`TRAVELPAYOUTS_TOKEN`** — 트랙 A 자동수집. 무료: https://www.travelpayouts.com
   (※ 발급 주시면 실제로 네이버급 '모든 결제 수단' 가격을 주는지 제가 바로 테스트해 검증.)
2. **`PUSHOVER_TOKEN` / `PUSHOVER_USER`** — 아이폰 경보·체크리스트 푸시.
3. **실제 SKU** — `sku_catalog.json` 의 `our_price_pp`(우리 공구가 인당)·`depart_dates` 를 실 공구로 교체, BX 박수 오프셋 검증.

## 폰 UX 옵션 (트랙 B 회수)

`submit_price.py`(로컬 CLI) 대신 폰에서 제출하려면: 구글폼(출발일 프리필 + 숫자 1필드) → Apps Script
`onFormSubmit` 로 시트 append → 로컬 `pull_intake`(Sheets API)로 `consumer_prices.csv` 동기화.
(Apps Script 스니펫·Sheets 동기화는 후속 작업.)

## 정직한 한계

- **트랙 A(메타서치)는 캐시·글로벌**이라 국내채널 전용 덤핑은 늦/미탐 가능 → 트랙 B(네이버 사람)로 보완.
- **트랙 B는 사람이 하루 2회 회수**해야 함(빠뜨리면 미탐). 미회수는 신선도 워치독으로 완화(후속).
- 임계 5만/10만은 시작 기본값 — 실데이터로 보정.
- `our_price_pp`·BX 박수 등 카탈로그 값은 **placeholder**(실 공구로 교체 전까지 데모용).
