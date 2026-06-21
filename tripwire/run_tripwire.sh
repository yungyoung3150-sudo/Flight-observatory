#!/bin/bash
# 하루 2회(launchd) 실행되는 트립와이어 파이프라인.
#   1) 트랙 A: 메타서치 소비자가 자동수집(토큰 있으면)
#   2) 트랙 B: 네이버 딥링크 체크리스트 Pushover 발송(사람 확인용)
#   3) 판정: 소비자가 vs 우리 공구가 → 🔴경보 출력/기록
# 자격증명은 환경변수로(launchd plist 의 EnvironmentVariables 또는 ~/.zprofile):
#   TRAVELPAYOUTS_TOKEN, PUSHOVER_TOKEN, PUSHOVER_USER
set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1

echo "===== tripwire run: $(date '+%Y-%m-%d %H:%M:%S') ====="
python3 tripwire/meta_source.py        || echo "(meta_source 스킵/실패 — 토큰 미설정 가능)"
python3 tripwire/checklist_notifier.py || echo "(notifier 스킵/실패 — Pushover 미설정 가능)"
python3 tripwire/evaluate_tripwire.py
