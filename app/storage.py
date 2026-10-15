"""会话状态内存存储（供人工干预，不持久化鉴权明文）。"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional

from .models import GenerateResult, DiscoverResult, SessionState


class SessionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, SessionState] = {}

    def create(self, session_id: str, base_url: str = "", auth_redacted: dict | None = None) -> SessionState:
        with self._lock:
            st = SessionState(
                session_id=session_id,
                base_url=base_url,
                auth_redacted=auth_redacted or {},
            )
            self._data[session_id] = st
            return st

    def get(self, session_id: str) -> Optional[SessionState]:
        return self._data.get(session_id)

    def update_discover(self, session_id: str, result: DiscoverResult) -> None:
        with self._lock:
            st = self._data.get(session_id)
            if not st:
                st = SessionState(session_id=session_id)
                self._data[session_id] = st
            st.discover = result
            st.base_url = result.base_url
            st.updated_at = datetime.now()

    def update_generate(self, session_id: str, result: GenerateResult) -> None:
        with self._lock:
            st = self._data.get(session_id)
            if not st:
                st = SessionState(session_id=session_id)
                self._data[session_id] = st
            st.generate = result
            st.updated_at = datetime.now()

    def list_sessions(self) -> list[dict]:
        return [
            {
                "session_id": s.session_id,
                "base_url": s.base_url,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "points": len(s.discover.functional_points) if s.discover else 0,
                "cases": len(s.generate.cases) if s.generate else 0,
            }
            for s in sorted(self._data.values(), key=lambda x: x.updated_at, reverse=True)
        ]


store = SessionStore()
