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


def _default_sys_name() -> str:
    try:
        from .projects import store as project_store

        lst = project_store.list_projects()
        return (lst[0]["name"] if lst else "") or "被测系统"
    except Exception:
        return "被测系统"


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


@router.post("/live/insert")
def live_insert(payload: dict):
    text = (payload or {}).get("text") or ""
    return _run(lambda eng: _ok(**eng.live_insert_text(text)))


@router.post("/live/copy")
def live_copy():
    return _run(lambda eng: eng.live_copy())


@router.post("/live/key")
def live_key(payload: dict):
    key = (payload or {}).get("key") or "Enter"
    return _run(lambda eng: _ok(**eng.live_key(key)))


@router.post("/live/press")
def live_press(payload: dict):
    key = (payload or {}).get("key") or "Enter"
    return _run(lambda eng: _ok(**eng.live_press(key)))


@router.post("/live/wheel")
def live_wheel(payload: dict):
    dx = float((payload or {}).get("dx") or 0)
    dy = float((payload or {}).get("dy") or 0)
    return _run(lambda eng: _ok(**eng.live_wheel(dx, dy)))


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
    payload = payload or {}
    e = ExtraRequirement(**payload)
    sys_name = payload.get("sys_name") or _default_sys_name()
    cases = build_cases_from_tree(tree, eng.list_marked(), e, sys_name=sys_name)
    return {
        "ok": True,
        "count": len(cases),
        "titles": [
            {
                "title": c.case_no + " " + c.title,
                "module": f"{c.module_cat}/{c.title_l1}/{c.title_l2}",
                "priority": c.priority,
                "status": "—",
            }
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
    sys_name = payload.get("sys_name") or _default_sys_name()
    cases = build_cases_from_tree(tree, eng.list_marked(), extra, sys_name=sys_name)

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


# ---------- 项目管理 ----------
from .projects import store as project_store  # noqa: E402

projects_router = APIRouter(prefix="/api/projects", tags=["projects"])


@projects_router.get("")
def list_projects():
    return {"ok": True, "projects": project_store.list_projects()}


@projects_router.post("")
def create_project(payload: dict):
    name = (payload or {}).get("name") or "未命名项目"
    base_url = (payload or {}).get("base_url") or ""
    data = project_store.create(name, base_url)
    return {"ok": True, "project": data}


@projects_router.get("/{pid}")
def get_project(pid: str):
    data = project_store.load(pid)
    if not data:
        raise HTTPException(404, "项目不存在")
    data = dict(data)
    data["storage_path"] = str(project_store.path_of(pid, "storage_state.json"))
    data["shots_dir"] = str(project_store.shots_dir(pid))
    return {"ok": True, "project": data}


@projects_router.put("/{pid}")
def update_project(pid: str, payload: dict):
    data = project_store.load(pid) or {"id": pid, "name": pid}
    for k in ("name", "base_url", "tree", "marked_elements", "notes", "shots", "cases", "meta"):
        if k in payload:
            data[k] = payload[k]
    saved = project_store.save(pid, data)
    return {"ok": True, "project": saved}


@projects_router.delete("/{pid}")
def delete_project(pid: str):
    return {"ok": True, "deleted": project_store.delete(pid)}


@projects_router.post("/{pid}/save-from-engine")
def save_from_engine(pid: str):
    eng = get_engine()
    saved = project_store.update_from_engine(pid, eng)
    # 顺带保存登录态（必须在 Playwright 线程）
    try:
        if eng.is_running():
            state = eng._call(lambda: eng._context.storage_state())
            project_store.save_storage_state(pid, state)
            saved["storage_saved"] = True
    except Exception as e:  # noqa: BLE001
        saved["storage_error"] = str(e)
    return {"ok": True, "project": saved}


@projects_router.post("/{pid}/load")
def load_project(pid: str, payload: dict | None = None):
    payload = payload or {}
    data = project_store.load(pid)
    if not data:
        raise HTTPException(404, "项目不存在")
    eng = get_engine()
    eng.set_tree(data.get("tree") or [])
    eng.marked_elements = data.get("marked_elements") or []
    eng.notes = data.get("notes") or []
    eng.shots = data.get("shots") or []

    restored = False
    if payload.get("restore_login", True):
        state = project_store.load_storage_state(pid)
        if state:
            try:
                if not eng.is_running():
                    eng.start(headless=True)
                cookies = state.get("cookies") or []

                def _restore():
                    if cookies:
                        eng._context.add_cookies(cookies)
                    page = eng._require_page()
                    for origin in state.get("origins") or []:
                        items = origin.get("localStorage") or []
                        if not items:
                            continue
                        its = [{"name": i.get("name"), "value": i.get("value")} for i in items]
                        page.evaluate(
                            """(its) => {
                                try {
                                  for (const it of its) localStorage.setItem(it.name, it.value);
                                } catch (e) {}
                                return true;
                            }""",
                            its,
                        )
                    return True

                eng._call(_restore)
                restored = True
            except Exception as e:  # noqa: BLE001
                data["restore_error"] = str(e)
    return {
        "ok": True,
        "project": data,
        "restored_login": restored,
        "tree_count": len(eng.get_tree()),
        "marked_count": len(eng.list_marked()),
    }
