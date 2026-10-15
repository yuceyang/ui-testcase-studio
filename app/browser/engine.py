"""Playwright 内置浏览器引擎。

所有 Playwright 调用固定在单一线程执行，避免 FastAPI 线程池触发
「Cannot switch to a different thread」greenlet 错误。
"""
from __future__ import annotations

import os
import queue
import threading
import time
import uuid
from concurrent.futures import Future
from pathlib import Path
from typing import Any, Callable, Optional

from ..auth import AuthConfig
from ..config import OUTPUT_DIR
from .elements import EXTRACT_JS, extract_nav_tree, parse_extract


SHOT_DIR = OUTPUT_DIR / "shots"
TEMP_SHOT_DIR = OUTPUT_DIR / "shots_tmp"
SHOT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_SHOT_DIR.mkdir(parents=True, exist_ok=True)

PREFERRED_CHANNELS = ("msedge", "chrome", None)


class BrowserError(RuntimeError):
    pass


class BrowserEngine:
    """单会话浏览器封装；Playwright 亲和到专用线程。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
        self.session_id: str = ""
        self.headless: bool = os.environ.get("QTS_HEADED", "").lower() not in ("1", "true")
        self.auto_screenshot: bool = True
        self.last_shot_id: str = ""
        self.shots: list[dict] = []
        self.marked_elements: list[dict] = []
        self.tree: list[dict] = []
        self.notes: list[dict] = []
        self._pending_storage_tokens: list[str] = []

        # 专用 Playwright 线程（先建 thread.local，再启动线程）
        self._local = threading.local()
        self._ready = threading.Event()
        self._work: queue.Queue = queue.Queue()
        self._pw_thread = threading.Thread(
            target=self._thread_main, name="qts-playwright", daemon=True
        )
        self._pw_thread.start()
        self._ready.wait(timeout=5)

    # ---------- 线程泵 ----------
    def _thread_main(self) -> None:
        self._local.is_pw = True
        self._ready.set()
        while True:
            item = self._work.get()
            if item is None:
                break
            fn, fut = item
            try:
                fut.set_result(fn())
            except Exception as e:  # noqa: BLE001
                fut.set_exception(e)

    def _call(self, fn: Callable[[], Any], timeout: float = 90.0) -> Any:
        """在 Playwright 线程执行 fn；若已在该线程则直接调用。"""
        if getattr(self._local, "is_pw", False):
            return fn()
        if not self._pw_thread.is_alive():
            raise BrowserError("浏览器工作线程已退出，请调用 start 重启")
        fut: Future = Future()
        self._work.put((fn, fut))
        try:
            return fut.result(timeout=timeout)
        except BrowserError:
            raise
        except Exception as e:  # noqa: BLE001
            raise BrowserError(str(e)) from e

    # ---------- 生命周期 ----------
    def is_running(self) -> bool:
        return self._page is not None

    def start(self, *, headless: bool | None = None) -> dict:
        def _inner() -> dict:
            self._close_inner()
            if headless is not None:
                self.headless = headless
            try:
                from playwright.sync_api import sync_playwright
            except ImportError as e:
                raise BrowserError("未安装 playwright，请执行: pip install playwright") from e

            self._playwright = sync_playwright().start()
            self._browser = None
            last_err = None
            for ch in PREFERRED_CHANNELS:
                try:
                    kwargs: dict[str, Any] = {"headless": self.headless}
                    if ch:
                        kwargs["channel"] = ch
                    self._browser = self._playwright.chromium.launch(**kwargs)
                    break
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    self._browser = None
            if not self._browser:
                raise BrowserError(f"浏览器启动失败: {last_err}")

            self._context = self._browser.new_context(
                viewport={"width": 1680, "height": 1050},
                ignore_https_errors=True,
                locale="zh-CN",
            )
            self._context.set_default_timeout(20000)
            self._page = self._context.new_page()
            self.session_id = uuid.uuid4().hex[:12]
            self.shots = []
            self.marked_elements = []
            self.tree = []
            self.notes = []
            self._pending_storage_tokens = []
            return {"session_id": self.session_id, "headless": self.headless}

        return self._call(_inner)

    def close(self) -> dict:
        self._call(self._close_inner)
        return {"ok": True}

    def _close_inner(self) -> None:
        for obj in (self._page, self._context, self._browser):
            try:
                if obj:
                    obj.close()
            except Exception:
                pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._page = self._context = self._browser = self._playwright = None

    def _require_page(self):
        if not self._page:
            raise BrowserError("浏览器未启动，请先启动内置浏览器")
        return self._page

    # ---------- 鉴权 ----------
    def apply_auth(self, auth: AuthConfig, base_url: str) -> dict:
        def _inner() -> dict:
            ctx = self._context
            if not ctx:
                raise BrowserError("浏览器未启动")

            from urllib.parse import urlparse

            from ..auth import build_headers

            raw_headers = build_headers(auth)
            cookie_header = raw_headers.pop("Cookie", None)
            headers = {
                k: v
                for k, v in raw_headers.items()
                if k.lower() not in ("user-agent", "accept")
            }
            applied: dict[str, Any] = {"cookies": 0, "headers": list(headers.keys()), "storage": []}

            if cookie_header:
                parsed = urlparse(base_url if "://" in base_url else "https://" + base_url)
                domain = parsed.hostname or "localhost"
                cookies = []
                for part in cookie_header.split(";"):
                    if "=" not in part:
                        continue
                    name, value = part.split("=", 1)
                    name, value = name.strip(), value.strip()
                    if not name:
                        continue
                    cookies.append({"name": name, "value": value, "domain": domain, "path": "/"})
                if cookies:
                    try:
                        ctx.add_cookies(cookies)
                        applied["cookies"] = len(cookies)
                    except Exception as e:  # noqa: BLE001
                        applied["cookie_error"] = str(e)

            if headers:
                try:
                    ctx.set_extra_http_headers(headers)
                except Exception as e:  # noqa: BLE001
                    applied["header_error"] = str(e)

            token_vals = []
            if auth.token:
                token_vals.append(auth.token)
            if auth.api_key_value:
                token_vals.append(auth.api_key_value)
            if token_vals:
                self._pending_storage_tokens = token_vals
                applied["storage"] = ["pending_token"]
            return applied

        return self._call(_inner)

    def _flush_storage_tokens(self) -> None:
        tokens = self._pending_storage_tokens or []
        if not tokens or not self._page:
            return
        js = """
        (tokens) => {
          try {
            for (const t of tokens) {
              localStorage.setItem('token', t);
              localStorage.setItem('access_token', t);
              localStorage.setItem('Authorization', 'Bearer ' + t);
              sessionStorage.setItem('token', t);
            }
          } catch (e) {}
          return true;
        }
        """
        try:
            self._page.evaluate(js, tokens)
        except Exception:
            pass

    # ---------- 导航 ----------
    def goto(self, url: str, *, wait_until: str = "domcontentloaded") -> dict:
        target = url.strip()
        if not target.startswith("http"):
            target = "https://" + target

        def _inner() -> dict:
            page = self._require_page()
            page.goto(target, wait_until=wait_until, timeout=45000)
            self._flush_storage_tokens()
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            info = {"url": page.url, "title": page.title()}
            if self.auto_screenshot:
                info["screenshot"] = self._screenshot_inner(tag="auto")
            return info

        return self._call(_inner, timeout=120)

    def reload(self) -> dict:
        def _inner() -> dict:
            page = self._require_page()
            page.reload(wait_until="domcontentloaded")
            self._flush_storage_tokens()
            return {"url": page.url, "title": page.title()}

        return self._call(_inner)

    def go_back(self) -> dict:
        def _inner() -> dict:
            page = self._require_page()
            page.go_back()
            return {"url": page.url, "title": page.title()}

        return self._call(_inner)

    # ---------- 实时镜像 ----------
    def live_frame(self) -> bytes:
        """返回当前页 JPEG 帧（视口截图），供前端镜像展示。"""

        def _inner() -> bytes:
            page = self._require_page()
            return page.screenshot(type="jpeg", quality=72, full_page=False)

        return self._call(_inner, timeout=20)

    def live_viewport(self) -> dict:
        def _inner() -> dict:
            page = self._require_page()
            size = page.viewport_size or {"width": 1680, "height": 1050}
            return {"url": page.url, "title": page.title(), "viewport": size}

        return self._call(_inner)

    def live_navigate(self, url: str) -> dict:
        from urllib.parse import urljoin

        target = (url or "").strip()
        if not target:
            raise BrowserError("URL 为空")
        if not target.startswith("http"):
            if target.startswith("/"):
                def _rel() -> dict:
                    page = self._require_page()
                    page.goto(urljoin(page.url, target), wait_until="domcontentloaded")
                    return {"url": page.url, "title": page.title()}
                return self._call(_rel, timeout=60)
            target = "https://" + target
        return self.goto(target)

    def live_click(self, x: float, y: float) -> dict:
        """按视口坐标点击（前端已换算）。"""

        def _inner() -> dict:
            page = self._require_page()
            page.mouse.click(float(x), float(y))
            try:
                page.wait_for_load_state("networkidle", timeout=2500)
            except Exception:
                pass
            return {"url": page.url, "title": page.title()}

        return self._call(_inner, timeout=20)

    def live_type(self, text: str) -> dict:
        """向当前焦点键入文本（登录表单）。"""

        def _inner() -> dict:
            page = self._require_page()
            if text:
                page.keyboard.type(text, delay=25)
            return {"url": page.url, "title": page.title()}

        return self._call(_inner, timeout=30)

    def live_key(self, key: str) -> dict:
        """按下按键：Enter / Tab / Backspace 等。"""

        def _inner() -> dict:
            page = self._require_page()
            page.keyboard.press(key)
            try:
                page.wait_for_load_state("networkidle", timeout=2000)
            except Exception:
                pass
            return {"url": page.url, "title": page.title()}

        return self._call(_inner, timeout=15)

    def live_insert_text(self, text: str) -> dict:
        """向焦点输入文本（镜像内直接打字）。"""

        def _inner() -> dict:
            page = self._require_page()
            if text:
                page.keyboard.insert_text(text)
            return {"url": page.url}

        return self._call(_inner, timeout=15)

    def live_copy(self) -> dict:
        """读取页面当前选区文本。"""

        def _inner() -> dict:
            page = self._require_page()
            text = page.evaluate(
                "() => { try { return String(window.getSelection() || ''); } catch(e) { return ''; } }"
            )
            return {"text": text or ""}

        return self._call(_inner, timeout=10)

    def live_press(self, key: str) -> dict:
        def _inner() -> dict:
            page = self._require_page()
            page.keyboard.press(key)
            return {"url": page.url}

        return self._call(_inner, timeout=10)

    def live_wheel(self, dx: float, dy: float) -> dict:
        def _inner() -> dict:
            page = self._require_page()
            page.mouse.wheel(float(dx), float(dy))
            return {"url": page.url}

        return self._call(_inner, timeout=10)

    def live_clear_focus(self) -> dict:
        def _inner() -> dict:
            page = self._require_page()
            # 全选后删除，清空当前输入框
            page.keyboard.press("Control+a")
            page.keyboard.press("Delete")
            return {"url": page.url, "title": page.title()}

        return self._call(_inner, timeout=15)

    def current(self) -> dict:
        def _inner() -> dict:
            if not self._page:
                return {"running": False, "auto_screenshot": self.auto_screenshot}
            try:
                title = self._page.title()
                url = self._page.url
            except Exception:
                title, url = "", ""
            return {
                "running": True,
                "url": url,
                "title": title,
                "session_id": self.session_id,
                "auto_screenshot": self.auto_screenshot,
                "headless": self.headless,
                "shots": len(self.shots),
                "marked": len(self.marked_elements),
            }

        return self._call(_inner)

    # ---------- 截图 ----------
    def screenshot(self, tag: str = "manual") -> dict:
        return self._call(lambda: self._screenshot_inner(tag))

    def _screenshot_inner(self, tag: str = "manual") -> dict:
        page = self._require_page()
        sid = "shot_" + uuid.uuid4().hex[:10]
        filename = f"{sid}.png"
        # 未入库前写临时目录，不进截图库
        path = TEMP_SHOT_DIR / filename
        try:
            page.screenshot(path=str(path), full_page=False, type="png")
        except Exception as e:  # noqa: BLE001
            raise BrowserError(f"截图失败: {e}") from e
        rec = {
            "id": sid,
            "tag": tag,
            "url": page.url,
            "title": page.title(),
            "path": str(path),
            "file": filename,
            "time": time.time(),
            "committed": False,
        }
        self.shots.append(rec)
        self.last_shot_id = sid
        return rec

    def commit_shots(self, dest_dir) -> list[dict]:
        """把临时截图移入项目截图库，返回提交后的记录。"""
        import shutil

        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        out = []
        for s in self.shots:
            if s.get("committed"):
                out.append(s)
                continue
            src = Path(s.get("path") or "")
            if src.exists():
                dst = dest_dir / src.name
                try:
                    shutil.copy2(src, dst)
                except OSError:
                    dst = src
                s = dict(s)
                s["path"] = str(dst)
                s["committed"] = True
                out.append(s)
            else:
                out.append(s)
        self.shots = out
        return out

    def set_auto_screenshot(self, enabled: bool) -> dict:
        self.auto_screenshot = bool(enabled)
        return {"auto_screenshot": self.auto_screenshot}

    def list_shots(self) -> list[dict]:
        return list(self.shots)

    def delete_shot(self, sid: str) -> bool:
        with self._lock:
            target = next((s for s in self.shots if s["id"] == sid), None)
            self.shots = [s for s in self.shots if s["id"] != sid]
        if target:
            try:
                p = Path(target.get("path") or "")
                if p.is_file():
                    p.unlink()
            except OSError:
                pass
            return True
        return False

    # ---------- 元素提取（含 iframe） ----------
    def extract_elements(self) -> dict:
        def _inner() -> dict:
            page = self._require_page()
            main_raw: dict[str, Any] = {"navHints": []}
            all_elements: list[dict] = []
            frame_tree: list[dict] = []

            def walk(frame, path: str, ox: int = 0, oy: int = 0):
                nonlocal main_raw
                try:
                    raw = frame.evaluate(EXTRACT_JS)
                except Exception:
                    raw = {}
                if path == "main" and raw:
                    main_raw = raw
                els = parse_extract(raw, frame_path=path, page_url=frame.url or "")
                # 子 frame 元素换算到顶层视口，保证镜像/截图叠框对齐
                if ox or oy:
                    for e in els:
                        b = e.get("bbox") or {}
                        if b:
                            b["x"] = b.get("x", 0) + ox
                            b["y"] = b.get("y", 0) + oy
                            e["bbox"] = b
                all_elements.extend(els)
                node = {
                    "path": path,
                    "url": getattr(frame, "url", ""),
                    "name": getattr(frame, "name", "") or "",
                    "count": len(els),
                    "children": [],
                }
                for i, child in enumerate(frame.child_frames):
                    cname = child.name or f"iframe[{i}]"
                    cx, cy = ox, oy
                    try:
                        handle = child.frame_element()
                        pos = handle.evaluate(
                            "el => { const r = el.getBoundingClientRect(); return {x:r.x, y:r.y}; }"
                        )
                        cx = ox + int(pos.get("x") or 0)
                        cy = oy + int(pos.get("y") or 0)
                    except Exception:
                        pass
                    node["children"].append(walk(child, f"{path}>{cname}", cx, cy))
                return node

            frame_tree.append(walk(page.main_frame, "main"))
            nav = extract_nav_tree(main_raw.get("navHints") or [])

            if self.auto_screenshot:
                try:
                    self._screenshot_inner(tag="auto")
                except Exception:
                    pass

            return {
                "url": page.url,
                "title": page.title(),
                "elements": all_elements,
                "frame_tree": frame_tree,
                "nav_hints": nav,
                "counts": {
                    "total": len(all_elements),
                    "button": sum(1 for e in all_elements if e["kind"] == "button"),
                    "input": sum(1 for e in all_elements if e["kind"] == "input"),
                    "select": sum(1 for e in all_elements if e["kind"] == "select"),
                    "link": sum(1 for e in all_elements if e["kind"] == "link"),
                    "frames": self._count_frames(page.main_frame),
                },
            }

        return self._call(_inner, timeout=60)

    def _count_frames(self, frame) -> int:
        n = 1
        for c in frame.child_frames:
            n += self._count_frames(c)
        return n

    # ---------- 点击 ----------
    def click_selector(self, selector: str, frame_path: str = "main") -> dict:
        def _inner() -> dict:
            page = self._require_page()
            frame = self._resolve_frame(page, frame_path)
            try:
                frame.locator(selector).first.click(timeout=5000)
            except Exception as e:  # noqa: BLE001
                raise BrowserError(f"点击失败: {e}") from e
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            info = {"url": page.url, "title": page.title()}
            if self.auto_screenshot:
                info["screenshot"] = self._screenshot_inner(tag="auto")
            return info

        return self._call(_inner)

    def _resolve_frame(self, page, frame_path: str):
        if frame_path in ("", "main"):
            return page.main_frame
        parts = frame_path.split(">")
        frame = page.main_frame
        for name in parts[1:]:
            found = None
            for c in frame.child_frames:
                if (c.name or "") == name or name in (c.name or "") or name in (c.url or ""):
                    found = c
                    break
            if not found and frame.child_frames:
                m = name.replace("iframe[", "").replace("]", "")
                if m.isdigit() and int(m) < len(frame.child_frames):
                    found = frame.child_frames[int(m)]
            if not found:
                raise BrowserError(f"找不到 frame: {frame_path}")
            frame = found
        return frame

    # ---------- 标记元素 ----------
    def mark_element(self, element: dict) -> dict:
        el = dict(element)
        if not el.get("id"):
            el["id"] = "el_" + uuid.uuid4().hex[:10]
        el["marked"] = True
        el["marked_at"] = time.time()
        with self._lock:
            self.marked_elements = [
                e
                for e in self.marked_elements
                if not (
                    e.get("frame_path") == el.get("frame_path")
                    and e.get("selector") == el.get("selector")
                )
            ]
            self.marked_elements.append(el)
        return el

    def unmark_element(self, el_id: str) -> bool:
        with self._lock:
            before = len(self.marked_elements)
            self.marked_elements = [e for e in self.marked_elements if e.get("id") != el_id]
            return len(self.marked_elements) < before

    def update_element(self, el_id: str, payload: dict) -> dict | None:
        with self._lock:
            for i, e in enumerate(self.marked_elements):
                if e.get("id") == el_id:
                    e.update(
                        {
                            k: v
                            for k, v in payload.items()
                            if k in e or k in ("note", "name", "text", "kind", "selector")
                        }
                    )
                    self.marked_elements[i] = e
                    return e
        return None

    def list_marked(self) -> list[dict]:
        return list(self.marked_elements)

    # ---------- 树 ----------
    def set_tree(self, tree: list[dict]) -> None:
        self.tree = tree

    def get_tree(self) -> list[dict]:
        return self.tree

    def add_tree_node(self, node: dict) -> dict:
        if not node.get("id"):
            node["id"] = "nd_" + uuid.uuid4().hex[:10]
        self.tree.append(node)
        return node

    def update_tree_node(self, node_id: str, payload: dict) -> dict | None:
        for i, n in enumerate(self.tree):
            if n.get("id") == node_id:
                n.update(payload)
                self.tree[i] = n
                return n
        return None

    def delete_tree_node(self, node_id: str) -> bool:
        ids = {node_id}
        changed = True
        while changed:
            changed = False
            for n in self.tree:
                if n.get("parent_id") in ids and n.get("id") not in ids:
                    ids.add(n["id"])
                    changed = True
        before = len(self.tree)
        self.tree = [n for n in self.tree if n.get("id") not in ids]
        return len(self.tree) < before

    # ---------- 标注 ----------
    def add_note(self, note: dict) -> dict:
        if not note.get("id"):
            note["id"] = "nt_" + uuid.uuid4().hex[:10]
        note["time"] = time.time()
        self.notes.append(note)
        return note

    def list_notes(self) -> list[dict]:
        return self.notes

    def clear_notes(self) -> None:
        self.notes = []

    def snapshot_state(self) -> dict:
        def _inner() -> dict:
            return {
                "current": (
                    {
                        "running": False,
                        "auto_screenshot": self.auto_screenshot,
                    }
                    if not self._page
                    else {
                        "running": True,
                        "url": self._page.url,
                        "title": self._page.title(),
                        "session_id": self.session_id,
                        "auto_screenshot": self.auto_screenshot,
                        "headless": self.headless,
                        "shots": len(self.shots),
                        "marked": len(self.marked_elements),
                    }
                ),
                "shots": self.shots,
                "marked_elements": self.marked_elements,
                "tree": self.tree,
                "notes": self.notes,
            }

        return self._call(_inner)

    def resolve_shot_path(self, filename: str) -> Path | None:
        """按文件名解析截图绝对路径（临时目录或已入库目录）。"""
        safe = Path(filename).name
        if not safe or safe in (".", ".."):
            return None
        roots = [TEMP_SHOT_DIR.resolve(), SHOT_DIR.resolve()]
        # 项目目录
        try:
            proj = (OUTPUT_DIR.parent / "projects")
            if proj.exists():
                for d in proj.iterdir():
                    if d.is_dir():
                        roots.append((d / "shots").resolve())
        except OSError:
            pass
        for root in roots:
            for candidate in (root / safe, root / f"{safe}.png"):
                try:
                    resolved = candidate.resolve()
                except OSError:
                    continue
                if resolved.is_file() and (resolved.parent == root or root in resolved.parents):
                    return resolved
        return None


_engine: Optional[BrowserEngine] = None
_engine_lock = threading.Lock()


def get_engine() -> BrowserEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = BrowserEngine()
        return _engine
