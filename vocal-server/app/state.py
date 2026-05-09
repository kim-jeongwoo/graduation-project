"""앱 런타임 상태 (메모리 변수). startup에서 .env로 초기화 + admin에서 토글."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppState:
    signup_enabled: bool = True


app_state = AppState()
