"""加载并管理 config.yaml。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get("QTS_CONFIG", ROOT / "config.yaml"))
DATA_DIR = ROOT / "data"
OUTPUT_DIR = DATA_DIR / "output"
SESSION_DIR = DATA_DIR / "sessions"


class AISettings(BaseModel):
    provider: str = "openai"
    base_url: str = ""
    api_key: str = ""
    model: str = "gpt-4o"
    vision_model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 8000
    timeout: int = 120


class DiscoverySettings(BaseModel):
    max_pages: int = 30
    max_depth: int = 3
    timeout: int = 15
    same_origin_only: bool = True
    respect_robots: bool = False
    allow_methods: list[str] = Field(default_factory=lambda: ["GET", "HEAD", "OPTIONS"])
    deny_path_keywords: list[str] = Field(
        default_factory=lambda: [
            "delete", "remove", "destroy", "create", "update",
            "edit", "insert", "modify", "drop", "upload",
        ]
    )
    include_api_hints: list[str] = Field(
        default_factory=lambda: [
            "/api/", "/v1/", "/v2/", "/rest/", "/query",
            "/list", "/search", "/detail", "/get", "/find", "/info",
        ]
    )


class TestPolicy(BaseModel):
    scope: str = "query_only"
    forbid_mutations: bool = True
    language: str = "zh-CN"
    max_cases_per_point: int = 8
    include_negative: bool = True
    include_auth_cases: bool = True


class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8787


class Settings(BaseModel):
    server: ServerSettings = Field(default_factory=ServerSettings)
    ai: AISettings = Field(default_factory=AISettings)
    discovery: DiscoverySettings = Field(default_factory=DiscoverySettings)
    test_policy: TestPolicy = Field(default_factory=TestPolicy)


def _load_yaml() -> dict[str, Any]:
    for candidate in (CONFIG_PATH, ROOT / "config.example.yaml"):
        if candidate.exists():
            with candidate.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            # 环境变量覆盖 API Key，避免密钥落盘
            env_key = os.environ.get("QTS_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if env_key:
                data.setdefault("ai", {})["api_key"] = env_key
            return data
    return {}


def load_settings() -> Settings:
    return Settings.model_validate(_load_yaml())


def save_settings(settings: Settings) -> Path:
    payload = settings.model_dump()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    return CONFIG_PATH


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
