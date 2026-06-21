#!/usr/bin/env python3
"""Pushover 발송 — 아이폰 푸시 알림.

자격증명(환경변수): PUSHOVER_TOKEN(앱 토큰), PUSHOVER_USER(유저 키).
priority: 🔴경보=1(긴급 — 소리·방해금지 무시), 🟠주의=0(일반), 2=긴급반복(ack까지, retry/expire 필요).
표준 라이브러리만 사용(urllib).
"""

from __future__ import annotations

import os
import urllib.parse
import urllib.request

API = "https://api.pushover.net/1/messages.json"


def configured() -> bool:
    return bool(os.environ.get("PUSHOVER_TOKEN") and os.environ.get("PUSHOVER_USER"))


def send(message: str, title: str, priority: int = 0) -> bool:
    """Pushover로 발송. 자격증명 없으면 False(미발송)."""
    token = os.environ.get("PUSHOVER_TOKEN")
    user = os.environ.get("PUSHOVER_USER")
    if not (token and user):
        return False
    params = {
        "token": token, "user": user,
        "title": title[:250], "message": message[:1024],
        "priority": str(priority),
    }
    if priority == 2:               # 긴급반복은 retry/expire 필수
        params["retry"] = "60"
        params["expire"] = "3600"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(API, data=data)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status == 200
