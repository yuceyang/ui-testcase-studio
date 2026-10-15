"""鉴权信息组装：Cookie / Token / Authorization / 自定义 Header。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


AUTH_MODES = ("cookie", "bearer", "basic", "api_key", "custom_headers", "none")


class AuthConfig(BaseModel):
    """前端提交的鉴权配置。敏感字段仅在会话内存中使用，不落盘明文日志。"""

    mode: str = "cookie"
    cookie: str = ""
    token: str = ""
    username: str = ""
    password: str = ""
    api_key_header: str = "Authorization"
    api_key_value: str = ""
    custom_headers: dict[str, str] = Field(default_factory=dict)

    def redacted(self) -> dict[str, Any]:
        """用于日志/回显的脱敏视图。"""
        def mask(v: str) -> str:
            if not v:
                return ""
            if len(v) <= 8:
                return "*" * len(v)
            return v[:4] + "…" + "*" * min(12, len(v) - 4)

        return {
            "mode": self.mode,
            "cookie": mask(self.cookie),
            "token": mask(self.token),
            "username": self.username,
            "password": mask(self.password),
            "api_key_header": self.api_key_header,
            "api_key_value": mask(self.api_key_value),
            "custom_headers": {k: mask(v) for k, v in self.custom_headers.items()},
        }


def build_headers(auth: AuthConfig) -> dict[str, str]:
    """按模式生成请求头。合并 custom_headers（可覆盖）。"""
    headers: dict[str, str] = {
        "User-Agent": "QueryTestSystem/1.0 (+functional-discovery)",
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    }

    mode = (auth.mode or "cookie").lower()
    if mode == "cookie" and auth.cookie.strip():
        headers["Cookie"] = auth.cookie.strip()
    elif mode == "bearer" and auth.token.strip():
        headers["Authorization"] = f"Bearer {auth.token.strip()}"
    elif mode == "basic" and auth.username:
        import base64

        raw = f"{auth.username}:{auth.password}".encode("utf-8")
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
    elif mode == "api_key" and auth.api_key_value:
        headers[auth.api_key_header or "Authorization"] = auth.api_key_value.strip()

    # 自定义头始终叠加
    for k, v in (auth.custom_headers or {}).items():
        if k and v:
            headers[k.strip()] = v.strip()

    return headers


def is_safe_method(method: str, allow: list[str]) -> bool:
    return (method or "GET").upper() in {m.upper() for m in allow}


def path_is_denied(path: str, deny_keywords: list[str]) -> bool:
    low = (path or "").lower()
    return any(k.lower() in low for k in deny_keywords)
