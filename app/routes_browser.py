"""内置浏览器 API：启动、鉴权、跳转、元素、截图、树、标注。"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from .auth import AuthConfig
from .browser.elements import classify_kind_label
from .browser.engine import BrowserError, get_engine
from .browser.tree import (
    auto_tree_from_nav,
    build_cases_from_tree,
    case_title_for,
    full_path_name,
    new_node,
    path_of,
)
from .models import ExtraRequirement, TestCase

router = APIRouter(prefix="/api/browser", tags=["browser"])


def _ok(**kw):
    return {"ok": True, **kw}


def _run(fn, *args, **kwargs):
    eng = get_engine()
    try:
        return fn(eng, *args, **kwargs)
    except BrowserError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e


# ---------- 启停 ----------
@router.post("/start")
def start_browser(payload: dict | None = None):
    payload = payload or {}
    # 未显式指定时保留引擎默认（可由 QTS_HEADED 控制）
    headless = payload["headless"] if "headless" in payload else None

    def fn(eng, headless):
        return eng.start(headless=headless)

    return _run(fn, headless)


@router.post("/close")
def close_browser():
    def fn(eng):
        eng.close()
        return _ok(message="浏览器已关闭")

    return _run(fn)


@router.get("/current")
def current():
    return get_engine().current()


@router.get("/state")
def state():
    return get_engine().snapshot_state()


# ---------- 鉴权 + 导航 ----------
@router.post("/auth")
def apply_auth(payload: dict):
    auth = AuthConfig(**(payload.get("auth") or {}))
    base_url = payload.get("base_url") or payload.get("url") or ""

    def fn(eng, auth, base_url):
        return _ok(**eng.apply_auth(auth, base_url))

    return _run(fn, auth, base_url)


@router.post("/goto")
def goto(payload: dict):
    url = payload.get("url") or ""
    if not url:
        raise HTTPException(400, "缺少 url")

    def fn(eng, url):
        return _ok(**eng.goto(url))

    return _run(fn, url)


@router.post("/reload")
def reload_page():
    def fn(eng):
        return _ok(**eng.reload())

    return _run(fn)


@router.post("/back")
def go_back():
    def fn(eng):
        return _ok(**eng.go_back())

    return _run(fn)


# ---------- 实时镜像 ----------
@router.get("/live/frame")
def live_frame():
    from fastapi.responses import Response

    data = _run(lambda eng: eng.live_frame())
    return Response(content=data, media_type="image/jpeg")


@router.get("/live/meta")
def live_meta():
    return _run(lambda eng: eng.live_viewport())


@router.post("/live/navigate")
def live_navigate(payload: dict):
    url = (payload or {}).get("url") or ""
    return _run(lambda eng: _ok(**eng.live_navigate(url)))


@router.post("/live/click")
def live_click(payload: dict):
    x = (payload or {}).get("x")
    y = (payload or {}).get("y")
    if x is None or y is None:
        raise HTTPException(400, "缺少 x/y")
    return _run(lambda eng: _ok(**eng.live_click(x, y)))


@router.post("/live/type")
def live_type(payload: dict):
    text = (payload or {}).get("text") or ""
    return _run(lambda eng: _ok(**eng.live_type(text)))


@router.post("/live/key")
def live_key(payload: dict):
    key = (payload or {}).get("key") or "Enter"
    return _run(lambda eng: _ok(**eng.live_key(key)))


@router.post("/live/clear")
def live_clear():
    return _run(lambda eng: _ok(**eng.live_clear_focus()))


@router.post("/click")
def click(payload: dict):
    selector = payload.get("selector") or ""
    frame_path = payload.get("frame_path") or "main"
    if not selector:
        raise HTTPException(400, "缺少 selector")

    def fn(eng, selector, frame_path):
        return _ok(**eng.click_selector(selector, frame_path))

    return _run(fn, selector, frame_path)


# ---------- 元素发现 ----------
@router.post("/extract")
def extract():
    def fn(eng):
        data = eng.extract_elements()
        for e in data.get("elements") or []:
            e["kind_label"] = classify_kind_label(e.get("kind", ""))
        return _ok(**data)

    return _run(fn)


@router.post("/discover-tree")
def discover_tree(payload: dict | None = None):
    """自动：导航 → 树 + 当前页元素挂到功能点。"""
    payload = payload or {}
    module_name = payload.get("module_name") or "默认模块"

    def fn(eng, module_name):
        data = eng.extract_elements()
        tree = auto_tree_from_nav(data.get("nav_hints") or [], module_name, data.get("url") or "")
        # 把按钮/输入框挂到第一个功能点下，方便人工挪动
        points = [n for n in tree if n["node_type"] == "point"]
        els = data.get("elements") or []
        if points and els:
            pts = points[0]
            pts["element_ids"] = [e["id"] for e in els[:20]]
            pts["elements"] = els[:20]
            pts["url"] = data.get("url") or ""
        eng.set_tree(tree)
        return _ok(
            tree=tree,
            elements=els,
            counts=data.get("counts") or {},
            frame_tree=data.get("frame_tree") or [],
            nav_hints=data.get("nav_hints") or [],
            url=data.get("url"),
            title=data.get("title"),
        )

    return _run(fn, module_name)


# ---------- 树 CRUD ----------
@router.get("/tree")
def get_tree():
    return {"ok": True, "tree": get_engine().get_tree()}


@router.post("/tree/node")
def add_node(payload: dict):
    node = new_node(
        name=payload.get("name") or "新节点",
        node_type=payload.get("node_type") or "point",
        parent_id=payload.get("parent_id"),
        url=payload.get("url") or "",
        note=payload.get("note") or "",
    )
    for k in ("element_ids", "elements", "annotation", "status", "screenshot_id"):
        if k in payload:
            node[k] = payload[k]
    return _ok(node=get_engine().add_tree_node(node))


@router.put("/tree/node/{node_id}")
def update_node(node_id: str, payload: dict):
    n = get_engine().update_tree_node(node_id, payload)
    if not n:
        raise HTTPException(404, "节点不存在")
    return _ok(node=n)


@router.delete("/tree/node/{node_id}")
def delete_node(node_id: str):
    ok = get_engine().delete_tree_node(node_id)
    return _ok(deleted=ok)


@router.post("/tree/node/{node_id}/status")
def set_status(node_id: str, payload: dict):
    status = payload.get("status") or "pending"
    if status not in ("pending", "pass", "fail", "ignored"):
        raise HTTPException(400, "状态必须是 pending/pass/fail/ignored")
    ann = payload.get("annotation")
    upd = {"status": status}
    if ann is not None:
        upd["annotation"] = ann
    n = get_engine().update_tree_node(node_id, upd)
    if not n:
        raise HTTPException(404, "节点不存在")
    return _ok(node=n)


@router.api_route("/tree/preview-cases", methods=["GET", "POST"])
def preview_cases(payload: dict | None = None):
    eng = get_engine()
    tree = eng.get_tree()
    if not tree:
        raise HTTPException(400, "功能点树为空")
    e = ExtraRequirement(**(payload or {}))
    cases = build_cases_from_tree(tree, eng.list_marked(), e)
    return {
        "ok": True,
        "count": len(cases),
        "titles": [
            {"title": c.title, "module": c.module, "priority": c.priority, "status": "—"}
            for c in cases[:50]
        ],
        "cases": [c.model_dump() for c in cases],
    }


# ---------- 标记元素为功能点 ----------
@router.post("/mark")
def mark_element(payload: dict):
    el = payload.get("element") or payload
    if not el.get("selector") and not el.get("name"):
        raise HTTPException(400, "元素缺少 selector/name")

    def fn(eng, el):
        return _ok(element=eng.mark_element(el))

    return _run(fn, el)


@router.post("/unmark/{el_id}")
def unmark(el_id: str):
    return _ok(unmarked=get_engine().unmark_element(el_id))


@router.get("/marked")
def marked():
    return {"ok": True, "elements": get_engine().list_marked()}


@router.put("/marked/{el_id}")
def update_marked(el_id: str, payload: dict):
    e = get_engine().update_element(el_id, payload)
    if not e:
        raise HTTPException(404, "元素不存在")
    return _ok(element=e)


# ---------- 截图 ----------
@router.post("/screenshot")
def screenshot(payload: dict | None = None):
    payload = payload or {}
    tag = payload.get("tag") or "manual"

    def fn(eng, tag):
        return _ok(**eng.screenshot(tag))

    return _run(fn, tag)


@router.post("/screenshot/auto")
def set_auto(payload: dict):
    enabled = bool(payload.get("enabled", True))
    return _ok(**get_engine().set_auto_screenshot(enabled))


@router.get("/shots")
def shots():
    return {"ok": True, "shots": get_engine().list_shots()}


@router.delete("/shots/{sid}")
def delete_shot(sid: str):
    return _ok(deleted=get_engine().delete_shot(sid))


@router.get("/shot-file/{filename}")
def shot_file(filename: str):
    from fastapi.responses import FileResponse

    p = get_engine().resolve_shot_path(filename)
    if not p:
        raise HTTPException(404, f"截图不存在: {Path(filename).name}")
    return FileResponse(p, filename=p.name)


# ---------- 标注 ----------
@router.post("/notes")
def add_note(payload: dict):
    return _ok(note=get_engine().add_note(payload))


@router.get("/notes")
def notes():
    return {"ok": True, "notes": get_engine().list_notes()}


@router.post("/notes/clear")
def clear_notes():
    get_engine().clear_notes()
    return _ok()


# ---------- 从树生成用例入库（供主流程导出） ----------
@router.post("/cases/from-tree")
def cases_from_tree(payload: dict):
    """把树生成的用例写入测试用例会话，供审阅/导出。"""
    from .storage import store
    from .models import GenerateResult
    from datetime import datetime

    eng = get_engine()
    tree = eng.get_tree()
    if not tree:
        raise HTTPException(400, "功能点树为空")
    extra = ExtraRequirement(**(payload.get("extra") or {}))
    sid = payload.get("session_id") or ("ui_" + datetime.now().strftime("%H%M%S"))
    cases = build_cases_from_tree(tree, eng.list_marked(), extra)

    if not store.get(sid):
        store.create(sid, base_url=eng.current().get("url", ""))
    store.update_generate(
        sid,
        GenerateResult(
            session_id=sid,
            model="ui-tree",
            cases=cases,
            raw_summary=f"由界面功能点树生成 {len(cases)} 条（模块-标题-功能点-测试/验证）",
        ),
    )
    return {
        "ok": True,
        "session_id": sid,
        "count": len(cases),
        "cases": [c.model_dump() for c in cases],
    }
