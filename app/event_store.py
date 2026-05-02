"""인메모리 이벤트 저장소 – 회원가입/로그인 이벤트를 기록하고 SSE로 푸시합니다."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import Any

MAX_EVENTS = 50

# 최근 이벤트를 저장하는 deque (FIFO, 최대 50개)
_events: deque[dict[str, Any]] = deque(maxlen=MAX_EVENTS)

# SSE 구독자 큐 목록
_subscribers: list[asyncio.Queue] = []


def add_event(event_type: str, nickname: str, email: str) -> dict[str, Any]:
    """이벤트를 기록하고 SSE 구독자에게 푸시합니다."""
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,  # "signup" | "login"
        "nickname": nickname,
        "email": email,
    }
    _events.appendleft(event)  # 최신이 앞에

    # 모든 SSE 구독자에게 비동기로 전달
    for queue in _subscribers:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass  # 느린 구독자는 건너뜀

    return event


def get_events() -> list[dict[str, Any]]:
    """현재 저장된 이벤트 리스트를 반환합니다 (최신순)."""
    return list(_events)


def subscribe() -> asyncio.Queue:
    """SSE 구독 큐를 생성하고 등록합니다."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(queue)
    return queue


def unsubscribe(queue: asyncio.Queue) -> None:
    """SSE 구독을 해제합니다."""
    try:
        _subscribers.remove(queue)
    except ValueError:
        pass
