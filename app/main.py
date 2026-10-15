"""FastAPI 主入口：鉴权 → 功能点发现 → AI 生成用例 → 人工审阅 → 导出。"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .auth import AuthConfig, build_headers
from .config import Settings, ensure_dirs, load_settings
from .ai.client import LLMClient, LLMError
from .ai.generator import generate_test_cases
from .discovery import discover_functional_points
from .export import export_cases
from .routes_browser import router as browser_router
from .routes_browser import projects_router
from .models import (
    CaseUpdate,
    DiscoverRequest,
    DiscoverResult,
    ExportRequest,
    ExtraRequirement,
    FunctionalPoint,
    GenerateRequest,
    GenerateResult,
    SessionState,
    TestCase,
)
from .storage import store

ensure_dirs()

app = FastAPI(
    title="软件功能测试系统",
    description="内置浏览器：鉴权跳转 → 界面功能点（按钮/输入框）→ 树形管理 → 只读测试用例",
    version="2.0.0",
)

app.include_router(browser_router)
app.include_router(projects_router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

settings: Settings = load_settings()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# ---------------- 配置 ----------------
@app.get("/api/config")
def get_config() -> dict:
    s = settings.model_dump()
    # 不回传 api_key 明文
    if s.get("ai"):
        key = s["ai"].get("api_key") or ""
        s["ai"]["api_key"] = (key[:4] + "…" + "*" * 8) if key else ""
    return s


@app.put("/api/config")
def update_config(payload: dict) -> dict:
    """更新 AI / discovery / test_policy 配置（不强制保存到磁盘）。"""
    global settings
    try:
        data = settings.model_dump()
        for section in ("ai", "discovery", "test_policy", "server"):
            if section in payload and isinstance(payload[section], dict):
                data[section].update(payload[section])
        # 若前端传来完整 key（非掩码），写入；否则保留原 key
        new_key = (payload.get("ai") or {}).get("api_key") or ""
        if new_key and "…" not in new_key and "*" not in new_key:
            data["ai"]["api_key"] = new_key
        else:
            data["ai"]["api_key"] = settings.ai.api_key
        settings = Settings.model_validate(data)
        return {"ok": True, "message": "配置已更新（内存生效）"}
    except Exception as e:
        raise HTTPException(400, f"配置无效: {e}") from e


@app.post("/api/config/save")
def save_config_to_disk() -> dict:
    from .config import save_settings

    path = save_settings(settings)
    return {"ok": True, "path": str(path)}


@app.post("/api/ai/test")
def test_ai() -> dict:
    try:
        client = LLMClient(settings.ai)
        reply = client.ping()
        return {"ok": True, "model": settings.ai.model, "reply": reply[:200]}
    except LLMError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------- 发现 ----------------
@app.post("/api/discover", response_model=DiscoverResult)
def api_discover(req: DiscoverRequest) -> DiscoverResult:
    sid = uuid.uuid4().hex[:12]
    try:
        points, warnings, stats = discover_functional_points(
            base_url=req.base_url,
            auth=req.auth,
            settings=settings.discovery,
            seed_urls=req.seed_urls,
        )
    except Exception as e:
        raise HTTPException(500, f"发现失败: {e}") from e

    result = DiscoverResult(
        session_id=sid,
        base_url=req.base_url.strip(),
        functional_points=points,
        warnings=warnings,
        stats=stats,
        total=len(points),
    )
    store.create(sid, base_url=result.base_url, auth_redacted=req.auth.redacted())
    store.update_discover(sid, result)
    return result


# ---------------- 功能点人工干预 ----------------
@app.get("/api/session/{sid}")
def get_session(sid: str) -> SessionState:
    st = store.get(sid)
    if not st:
        raise HTTPException(404, "会话不存在")
    return st


@app.get("/api/session/{sid}/points")
def list_points(sid: str) -> list[FunctionalPoint]:
    st = store.get(sid)
    if not st or not st.discover:
        raise HTTPException(404, "无功能点数据")
    return st.discover.functional_points


@app.put("/api/session/{sid}/points/{pid}")
def update_point(sid: str, pid: str, payload: dict) -> FunctionalPoint:
    st = store.get(sid)
    if not st or not st.discover:
        raise HTTPException(404, "无功能点数据")
    for i, p in enumerate(st.discover.functional_points):
        if p.id == pid:
            updated = p.model_copy(update={k: v for k, v in payload.items() if k in FunctionalPoint.model_fields})
            st.discover.functional_points[i] = updated
            st.updated_at = updated.updated_at if hasattr(updated, "updated_at") else st.updated_at
            return updated
    raise HTTPException(404, "功能点不存在")


@app.post("/api/session/{sid}/points/{pid}/toggle")
def toggle_point(sid: str, pid: str) -> FunctionalPoint:
    st = store.get(sid)
    if not st or not st.discover:
        raise HTTPException(404, "无功能点数据")
    for p in st.discover.functional_points:
        if p.id == pid:
            p.selected = not p.selected
            return p
    raise HTTPException(404, "功能点不存在")


@app.post("/api/session/{sid}/points/batch")
def batch_points(sid: str, payload: dict) -> dict:
    st = store.get(sid)
    if not st or not st.discover:
        raise HTTPException(404, "无功能点数据")
    action = payload.get("action")
    ids = set(payload.get("ids") or [])
    n = 0
    for p in st.discover.functional_points:
        if not ids or p.id in ids:
            if action == "select":
                p.selected = True
            elif action == "deselect":
                p.selected = False
            elif action == "delete":
                pass  # 后面过滤
            n += 1
    if action == "delete" and ids:
        st.discover.functional_points = [p for p in st.discover.functional_points if p.id not in ids]
        n = len(ids)
    return {"ok": True, "affected": n}


# ---------------- 生成 ----------------
@app.post("/api/generate", response_model=GenerateResult)
def api_generate(req: GenerateRequest) -> GenerateResult:
    st = store.get(req.session_id)
    if not st or not st.discover:
        raise HTTPException(404, "请先执行功能点发现")

    points = st.discover.functional_points
    if req.point_ids:
        idset = set(req.point_ids)
        selected = [p for p in points if p.id in idset]
    else:
        selected = [p for p in points if p.selected]

    if not selected:
        raise HTTPException(400, "未选择任何功能点")

    # 额外要求
    extra = req.extra
    images = [p for p in (req.screenshot_paths or []) if Path(p).exists()]

    try:
        cases, summary, warnings = generate_test_cases(
            points=selected,
            extra=extra,
            settings=settings,
            image_paths=images if req.use_vision else None,
        )
    except Exception as e:
        raise HTTPException(500, f"生成失败: {e}") from e

    result = GenerateResult(
        session_id=req.session_id,
        model=settings.ai.vision_model if req.use_vision else settings.ai.model,
        cases=cases,
        warnings=warnings,
        raw_summary=summary,
    )
    store.update_generate(req.session_id, result)
    return result


# ---------------- 用例人工干预 ----------------
@app.get("/api/session/{sid}/cases")
def list_cases(sid: str) -> list[TestCase]:
    st = store.get(sid)
    if not st or not st.generate:
        raise HTTPException(404, "无用例数据")
    return st.generate.cases


@app.put("/api/session/{sid}/cases/{cid}")
def update_case(sid: str, cid: str, payload: dict) -> TestCase:
    st = store.get(sid)
    if not st or not st.generate:
        raise HTTPException(404, "无用例数据")
    for i, c in enumerate(st.generate.cases):
        if c.id == cid:
            updated = c.model_copy(update={k: v for k, v in payload.items() if k in TestCase.model_fields})
            updated.human_modified = True
            st.generate.cases[i] = updated
            return updated
    raise HTTPException(404, "用例不存在")


@app.delete("/api/session/{sid}/cases/{cid}")
def delete_case(sid: str, cid: str) -> dict:
    st = store.get(sid)
    if not st or not st.generate:
        raise HTTPException(404, "无用例数据")
    before = len(st.generate.cases)
    st.generate.cases = [c for c in st.generate.cases if c.id != cid]
    return {"ok": True, "deleted": before - len(st.generate.cases)}


@app.post("/api/session/{sid}/cases/{cid}/approve")
def approve_case(sid: str, cid: str, payload: Optional[dict] = None) -> TestCase:
    st = store.get(sid)
    if not st or not st.generate:
        raise HTTPException(404, "无用例数据")
    approved = True if not payload else bool(payload.get("approved", True))
    for c in st.generate.cases:
        if c.id == cid:
            c.approved = approved
            return c
    raise HTTPException(404, "用例不存在")


@app.post("/api/session/{sid}/cases/regenerate")
def regenerate_selected(sid: str, payload: dict) -> GenerateResult:
    """对勾选用例的功能点重新生成（仍走 AI）。"""
    st = store.get(sid)
    if not st or not st.discover:
        raise HTTPException(404, "请先发现功能点")

    case_ids = set(payload.get("case_ids") or [])
    point_ids = set(payload.get("point_ids") or [])
    extra = ExtraRequirement(**(payload.get("extra") or {}))

    if not point_ids and st.generate:
        for c in st.generate.cases:
            if not case_ids or c.id in case_ids:
                point_ids.add(c.point_id)

    selected = [p for p in st.discover.functional_points if p.id in point_ids and p.selected or p.id in point_ids]
    if not selected:
        raise HTTPException(400, "没有对应功能点")

    cases, summary, warnings = generate_test_cases(selected, extra, settings)
    # 追加到已有用例（人工可再删）
    if st.generate:
        existing_ids = {c.id for c in st.generate.cases}
        keep = [c for c in st.generate.cases if not case_ids or c.id not in case_ids]
        st.generate.cases = keep + cases
        st.generate.warnings.extend(warnings)
        st.generate.raw_summary = summary
    else:
        st.generate = GenerateResult(
            session_id=sid, model=settings.ai.model, cases=cases,
            warnings=warnings, raw_summary=summary,
        )
    return st.generate


# ---------------- 导出 ----------------
@app.post("/api/export")
def api_export(req: ExportRequest) -> dict:
    st = store.get(req.session_id)
    if not st or not st.generate:
        raise HTTPException(404, "无用例可导出")
    cases = st.generate.cases
    if req.case_ids:
        idset = set(req.case_ids)
        cases = [c for c in cases if c.id in idset]
    if req.point_ids:
        pids = set(req.point_ids)
        cases = [c for c in cases if c.point_id in pids]
    cases = [c for c in cases if c.approved]
    if not cases:
        raise HTTPException(400, "没有已通过审阅的用例")

    try:
        path = export_cases(cases, req.format)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"导出失败: {e}") from e
    return {"ok": True, "path": str(path), "count": len(cases)}


@app.get("/api/export/download/{filename}")
def download(filename: str) -> FileResponse:
    safe = Path(filename).name
    path = (Path(__file__).resolve().parent.parent / "data" / "output" / safe)
    if not path.exists():
        raise HTTPException(404, "文件不存在")
    return FileResponse(path, filename=safe)


@app.get("/api/sessions")
def list_all_sessions() -> list[dict]:
    return store.list_sessions()


# ---------------- 健康 ----------------
@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "ai_provider": settings.ai.provider,
        "ai_model": settings.ai.model,
        "vision_model": settings.ai.vision_model,
        "policy": settings.test_policy.scope,
    }
