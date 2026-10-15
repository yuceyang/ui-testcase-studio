"""树形功能点结构：模块 → 一级/二级/三级目录 → 功能点 → 测试/验证。

缺级目录用 "/" 占位，保证用例命名链完整：
  模块-一级-二级-三级-功能点-XX功能点测试/验证
用例正文由 case_builder 按《功能测试提示词 v3.0》生成。
"""
from __future__ import annotations

import uuid
from typing import Any

from ..models import ExtraRequirement, TestCase
from .case_builder import build_cases_from_tree  # noqa: F401  — 对外统一入口


LEVEL_TYPES = ("module", "title1", "title2", "title3", "point", "case")
LEVEL_LABEL = {
    "module": "模块",
    "title1": "一级",
    "title2": "二级",
    "title3": "三级",
    "point": "功能点",
    "case": "验证",
}
LEVEL_ORDER = ["module", "title1", "title2", "title3", "point"]
PLACEHOLDER = "/"


def new_node(
    name: str,
    node_type: str = "point",
    parent_id: str | None = None,
    **extra: Any,
) -> dict:
    nt = node_type if node_type in LEVEL_TYPES else "point"
    if nt.startswith("title") and not (name or "").strip():
        name = PLACEHOLDER
    return {
        "id": "nd_" + uuid.uuid4().hex[:10],
        "name": name,
        "node_type": nt,
        "parent_id": parent_id,
        "status": extra.pop("status", "pending"),  # pending | pass | fail | ignored
        "annotation": extra.pop("annotation", ""),
        "element_ids": extra.pop("element_ids", []),
        "elements": extra.pop("elements", []),
        "url": extra.pop("url", ""),
        "screenshot_id": extra.pop("screenshot_id", ""),
        "note": extra.pop("note", ""),
        **extra,
    }


def path_of(node_id: str, tree: list[dict]) -> list[dict]:
    by_id = {n["id"]: n for n in tree}
    chain: list[dict] = []
    cur = by_id.get(node_id)
    guard = 0
    while cur and guard < 20:
        chain.append(cur)
        cur = by_id.get(cur.get("parent_id"))
        guard += 1
    chain.reverse()
    return chain


def full_path_name(node_id: str, tree: list[dict], sep: str = " / ") -> str:
    chain = path_of(node_id, tree)
    return sep.join(n.get("name") or LEVEL_LABEL.get(n.get("node_type"), "") for n in chain)


def padded_path_names(node_id: str, tree: list[dict]) -> list[str]:
    """返回 5 段：模块/一级/二级/三级/功能点；缺失层级用 / 占位。"""
    chain = path_of(node_id, tree)
    by_type = {n.get("node_type"): n.get("name") or PLACEHOLDER for n in chain}
    # 最后一个非 title 节点视为功能点
    point_name = None
    for n in reversed(chain):
        if n.get("node_type") in ("point", "case"):
            point_name = n.get("name") or PLACEHOLDER
            break
    if point_name is None and chain:
        point_name = chain[-1].get("name") or PLACEHOLDER

    return [
        by_type.get("module") or PLACEHOLDER,
        by_type.get("title1") or PLACEHOLDER,
        by_type.get("title2") or PLACEHOLDER,
        by_type.get("title3") or PLACEHOLDER,
        point_name or PLACEHOLDER,
    ]


def case_title_for(node: dict, tree: list[dict], suffix: str = "测试/验证") -> str:
    """模块-一级-二级-三级-功能点-XX功能点测试/验证（缺级以 / 占位）。"""
    parts = padded_path_names(node.get("id"), tree)
    point_name = parts[-1] if parts[-1] != PLACEHOLDER else "功能点"
    return "-".join(parts[:-1] + [f"{point_name}功能点{suffix}"])


def iter_points(tree: list[dict]) -> list[dict]:
    return [n for n in tree if n.get("node_type") in ("point", "case")]


def ensure_child_levels(parent: dict, tree: list[dict]) -> dict:
    """
    在 parent 下补齐 title2/title3 占位（若 parent 是 title1），
    返回应挂功能点的目标节点。
    """
    nt = parent.get("node_type")
    if nt == "title1":
        t2 = next((n for n in tree if n.get("parent_id") == parent["id"] and n.get("node_type") == "title2"), None)
        if not t2:
            t2 = new_node(PLACEHOLDER, "title2", parent["id"])
            tree.append(t2)
        t3 = next((n for n in tree if n.get("parent_id") == t2["id"] and n.get("node_type") == "title3"), None)
        if not t3:
            t3 = new_node(PLACEHOLDER, "title3", t2["id"])
            tree.append(t3)
        return t3
    if nt == "title2":
        t3 = next((n for n in tree if n.get("parent_id") == parent["id"] and n.get("node_type") == "title3"), None)
        if not t3:
            t3 = new_node(PLACEHOLDER, "title3", parent["id"])
            tree.append(t3)
        return t3
    return parent


def auto_tree_from_nav(
    nav_hints: list[dict],
    module_name: str = "默认模块",
    page_url: str = "",
) -> list[dict]:
    """
    从导航菜单粗建层级。
      模块 → 一级目录 → 二级(/) → 三级(/) → 功能点
    nav_hints 条目：{id, name, href, level, parent, ...}
    """
    tree: list[dict] = []

    def url_of(h: dict) -> str:
        return (h.get("href") or h.get("url") or page_url or "").strip()

    modules = [h for h in nav_hints if h.get("level") == 0]
    if not modules:
        root = new_node(module_name, "module", None, url=page_url)
        tree.append(root)
        for h in nav_hints[:20]:
            name = (h.get("name") or "").strip()
            if not name:
                continue
            t1 = new_node(name, "title1", root["id"], url=url_of(h))
            tree.append(t1)
            target = ensure_child_levels(t1, tree)
            tree.append(new_node(f"{name}查询", "point", target["id"], url=url_of(h)))
        return tree

    for m in modules:
        mname = (m.get("name") or "模块").strip() or "模块"
        mod = new_node(mname, "module", None, url=url_of(m))
        tree.append(mod)
        mid = m.get("id") or ""
        children = [
            h for h in nav_hints
            if h.get("level") == 1 and (h.get("parent") == mid or h.get("module_ref") == mid)
        ]
        if not children:
            t1 = new_node(PLACEHOLDER, "title1", mod["id"], url=url_of(m))
            tree.append(t1)
            target = ensure_child_levels(t1, tree)
            tree.append(new_node(f"{mname}功能", "point", target["id"], url=url_of(m)))
            continue
        for c in children:
            cname = (c.get("name") or "").strip() or PLACEHOLDER
            t1 = new_node(cname, "title1", mod["id"], url=url_of(c))
            tree.append(t1)
            target = ensure_child_levels(t1, tree)
            pt = f"{cname}查询" if cname != PLACEHOLDER else f"{mname}查询"
            tree.append(new_node(pt, "point", target["id"], url=url_of(c)))
    return tree
