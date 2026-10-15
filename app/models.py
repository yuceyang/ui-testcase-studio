"""领域模型与 API Schema。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from .auth import AuthConfig


class DiscoverRequest(BaseModel):
    base_url: str = Field(..., description="目标系统入口 URL")
    auth: AuthConfig = Field(default_factory=AuthConfig)
    seed_urls: list[str] = Field(default_factory=list, description="额外入口/接口线索")
    include_screenshots: bool = False
    extra_notes: str = ""


class FunctionalPoint(BaseModel):
    id: str
    name: str
    method: str = "GET"
    url: str
    path: str = ""
    source: Literal["page", "api", "swagger", "manual"] = "page"
    summary: str = ""
    params: list[dict[str, Any]] = Field(default_factory=list)
    request_headers: list[dict[str, str]] = Field(default_factory=list)
    response_hints: str = ""
    tags: list[str] = Field(default_factory=list)
    risk: Literal["safe", "caution"] = "safe"
    selected: bool = True
    notes: str = ""
    page_title: str = ""
    content_type: str = ""


class DiscoverResult(BaseModel):
    session_id: str
    base_url: str
    discovered_at: datetime = Field(default_factory=datetime.now)
    total: int = 0
    functional_points: list[FunctionalPoint] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


class ExtraRequirement(BaseModel):
    text: str = ""
    focus_modules: list[str] = Field(default_factory=list)
    include_negative: bool = True
    include_auth_cases: bool = True
    max_cases_per_point: int = 8


class GenerateRequest(BaseModel):
    session_id: str
    point_ids: list[str] = Field(default_factory=list, description="为空则用全部 selected")
    extra: ExtraRequirement = Field(default_factory=ExtraRequirement)
    use_vision: bool = False
    screenshot_paths: list[str] = Field(default_factory=list)


class TestCase(BaseModel):
    id: str
    point_id: str
    title: str
    module: str = ""
    priority: Literal["P0", "P1", "P2", "P3"] = "P1"
    preconditions: str = ""
    steps: str = ""
    expected: str = ""
    data: str = ""
    method: str = "GET"
    url: str = ""
    auth_notes: str = ""
    category: Literal["positive", "negative", "boundary", "auth", "performance"] = "positive"
    ai_rationale: str = ""
    human_modified: bool = False
    approved: bool = True
    # 功能测试提示词 v3.0 列
    case_no: str = ""
    sys_name: str = ""
    module_cat: str = ""
    title_l1: str = "/"
    title_l2: str = "/"
    design_req: str = ""
    test_track: str = ""
    stop_cond: str = "功能验证完成或出现阻断缺陷即终止"
    remark: str = "-"
    params: str = "-"
    screenshot_path: str = ""
    screenshot_file: str = ""
    case_status: str = "未执行"


class GenerateResult(BaseModel):
    session_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    model: str = ""
    cases: list[TestCase] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    raw_summary: str = ""


class CaseUpdate(BaseModel):
    case: TestCase


class ExportRequest(BaseModel):
    session_id: str
    format: Literal["xlsx", "md", "csv"] = "xlsx"
    case_ids: list[str] = Field(default_factory=list)


class SessionState(BaseModel):
    session_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    discover: Optional[DiscoverResult] = None
    generate: Optional[GenerateResult] = None
    auth_redacted: dict[str, Any] = Field(default_factory=dict)
    base_url: str = ""
