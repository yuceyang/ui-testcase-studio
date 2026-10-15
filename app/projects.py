"""项目持久化：每个被测系统一个项目，保存树/已标/截图索引/登录态。"""
from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from .config import DATA_DIR


PROJECTS_DIR = DATA_DIR / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def _safe_id(pid: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", pid or "")[:64]


def project_dir(pid: str) -> Path:
    return PROJECTS_DIR / _safe_id(pid)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


class ProjectStore:
    def create(self, name: str, base_url: str = "", **meta: Any) -> dict:
        pid = "prj_" + uuid.uuid4().hex[:10]
        now = time.time()
        data = {
            "id": pid,
            "name": name or "未命名项目",
            "base_url": base_url or "",
            "created_at": now,
            "updated_at": now,
            "tree": [],
            "marked_elements": [],
            "notes": [],
            "shots": [],
            "cases": [],
            "meta": meta,
        }
        self.save(pid, data)
        return data

    def path_of(self, pid: str, filename: str) -> Path:
        return project_dir(pid) / filename

    def shots_dir(self, pid: str) -> Path:
        d = project_dir(pid) / "shots"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def load(self, pid: str) -> Optional[dict]:
        return _read_json(project_dir(pid) / "project.json")

    def save(self, pid: str, data: dict) -> dict:
        data = dict(data)
        data["id"] = _safe_id(pid)
        data["updated_at"] = time.time()
        _write_json(project_dir(pid) / "project.json", data)
        return data

    def save_storage_state(self, pid: str, state: dict) -> Path:
        path = project_dir(pid) / "storage_state.json"
        _write_json(path, state)
        return path

    def load_storage_state(self, pid: str) -> Optional[dict]:
        return _read_json(project_dir(pid) / "storage_state.json")

    def list_projects(self) -> list[dict]:
        items = []
        for p in PROJECTS_DIR.iterdir():
            if not p.is_dir():
                continue
            meta = _read_json(p / "project.json")
            if not meta:
                continue
            items.append(
                {
                    "id": meta.get("id") or p.name,
                    "name": meta.get("name"),
                    "base_url": meta.get("base_url"),
                    "updated_at": meta.get("updated_at"),
                    "created_at": meta.get("created_at"),
                    "tree_count": len(meta.get("tree") or []),
                    "marked_count": len(meta.get("marked_elements") or []),
                    "shots_count": len(meta.get("shots") or []),
                    "cases_count": len(meta.get("cases") or []),
                }
            )
        items.sort(key=lambda x: x.get("updated_at") or 0, reverse=True)
        return items

    def delete(self, pid: str) -> bool:
        import shutil

        d = project_dir(pid)
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            return True
        return False

    def update_from_engine(self, pid: str, engine, cases: list | None = None) -> dict:
        """把引擎里当前树/已标/截图/备注刷进项目；cases 不为空则写入。"""
        data = self.load(pid) or {
            "id": _safe_id(pid),
            "name": pid,
            "base_url": "",
            "tree": [],
            "marked_elements": [],
            "notes": [],
            "shots": [],
            "cases": [],
        }
        data["tree"] = engine.get_tree()
        data["marked_elements"] = engine.list_marked()
        data["notes"] = engine.list_notes()
        data["shots"] = engine.list_shots()
        if cases is not None:
            data["cases"] = cases
        # 兜底：始终保留已有 cases 字段（不在此处清空）
        data.setdefault("cases", [])
        if cases is None:
            # 保留磁盘上已有的用例
            pass
        cur = engine.current()
        if cur.get("url"):
            data.setdefault("meta", {})
            data["base_url"] = data.get("base_url") or cur.get("url") or ""
            data["last_url"] = cur.get("url")
        return self.save(pid, data)


store = ProjectStore()
