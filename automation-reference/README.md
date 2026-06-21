# automation-reference — GitHub Actions (비활성 / 돌리지 않음)

이 폴더의 `*.yml`은 GitHub Actions 워크플로지만 **실행하지 않는다.**
`.github/workflows/`에 있으면 GitHub가 자동 실행하므로, **여기로 옮겨 비활성화**했다
(GitHub는 `.github/workflows/` 안의 워크플로만 실행함). + repo 설정에서도 Actions를 껐다.

남겨둔 이유: **검수(CPO)용 참고 코드.** 자동화 로직이 어떻게 생겼는지 보여준다.

실제 운영(확정):
- **로컬**(맥 launchd) + 가드레일 코드. 시트 데이터는 사용자 네이버 수집기가 채움.
- **에어부산**은 Claude가 구글 항공에서 날짜별 수동 확인 → 시트 입력(검수코드: `tripwire/airbusan_lookup.py`).
- ci.yml/monitor.yml/tripwire.yml는 과거 시도(Amadeus/Travelpayouts)라 현재 미사용.
