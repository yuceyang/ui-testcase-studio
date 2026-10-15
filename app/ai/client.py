"""多模态大模型客户端：OpenAI 兼容 / Anthropic。"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from ..config import AISettings


class LLMError(RuntimeError):
    pass


def _image_to_data_url(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise LLMError(f"截图不存在: {p}")
    mime, _ = mimetypes.guess_type(p.name)
    mime = mime or "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


class LLMClient:
    """统一接口：chat(messages) -> str；messages 支持 content 数组（多模态）。"""

    def __init__(self, settings: AISettings):
        self.s = settings

    def chat(self, messages: list[dict[str, Any]], *, vision: bool = False) -> str:
        provider = (self.s.provider or "openai").lower()
        if provider == "anthropic":
            return self._chat_anthropic(messages, vision=vision)
        return self._chat_openai(messages, vision=vision)

    # ---------- OpenAI 兼容 ----------
    def _chat_openai(self, messages: list[dict[str, Any]], vision: bool = False) -> str:
        model = self.s.vision_model if vision else self.s.model
        base = (self.s.base_url or "").strip() or "https://api.openai.com/v1"
        url = base.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.s.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "temperature": self.s.temperature,
            "max_tokens": self.s.max_tokens,
            "messages": messages,
        }
        try:
            with httpx.Client(timeout=self.s.timeout) as client:
                r = client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as e:
            raise LLMError(f"请求 AI 失败: {e}") from e

        if r.status_code >= 400:
            raise LLMError(f"AI 接口错误 {r.status_code}: {r.text[:500]}")
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"AI 响应结构异常: {data}") from e

    # ---------- Anthropic ----------
    def _chat_anthropic(self, messages: list[dict[str, Any]], vision: bool = False) -> str:
        model = self.s.vision_model if vision else self.s.model
        base = (self.s.base_url or "").strip() or "https://api.anthropic.com"
        url = base.rstrip("/") + "/v1/messages"
        headers = {
            "x-api-key": self.s.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        # system 单独拆出
        system = ""
        api_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system = content if isinstance(content, str) else str(content)
                continue
            api_messages.append({"role": role, "content": content})

        payload = {
            "model": model,
            "max_tokens": self.s.max_tokens,
            "temperature": self.s.temperature,
            "messages": api_messages,
        }
        if system:
            payload["system"] = system

        try:
            with httpx.Client(timeout=self.s.timeout) as client:
                r = client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as e:
            raise LLMError(f"请求 AI 失败: {e}") from e

        if r.status_code >= 400:
            raise LLMError(f"AI 接口错误 {r.status_code}: {r.text[:500]}")
        data = r.json()
        try:
            parts = data.get("content") or []
            return "".join(p.get("text", "") for p in parts if p.get("type") == "text")
        except Exception as e:
            raise LLMError(f"AI 响应结构异常: {data}") from e

    # ---------- 工具：拼多模态 user 消息 ----------
    @staticmethod
    def build_user_message(text: str, image_paths: list[str] | None = None) -> dict[str, Any]:
        if not image_paths:
            return {"role": "user", "content": text}
        content: list[dict[str, Any]] = [{"type": "text", "text": text}]
        for p in image_paths:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": _image_to_data_url(p)},
                }
            )
        return {"role": "user", "content": content}

    def ping(self) -> str:
        """连通性探测。"""
        msg = self.build_user_message("请回复 OK，两个字母即可。")
        return self.chat([msg], vision=False)
