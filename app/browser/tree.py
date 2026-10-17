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


def auto_tree_from_nav(
    nav_hints: list[dict],
    module_name: str = "默认模块",
    page_url: str = "",
) -> list[dict]:
    """从递归导航线索生成目录树（父先子后的扁平列表，只含目录不含功能点）。

    深度映射：0→module, 1→title1, 2→title2, 3→title3；
    每个导航条目都按深度映射为目录节点，不生成 "/" 占位、不生成功能点。
    """
    LEVEL_TYPE = {0: "module", 1: "title1", 2: "title2", 3: "title3"}

    items: list[dict] = []
    seen = set()
    for idx, hint in enumerate(nav_hints or []):
        name = (hint.get("name") or hint.get("text") or "").strip()
        if not name:
            continue
        hid = hint.get("id") or f"nav_{idx}"
        key = (hint.get("level", 0), name.casefold(), hint.get("parent") or "")
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "name": name,
                "href": (hint.get("href") or hint.get("url") or "").strip(),
                "level": int(hint.get("level") or 0),
                "parent": hint.get("parent") or "",
                "id": hid,
                "is_sub": bool(hint.get("is_sub") or hint.get("isSub")),
            }
        )

    if not items:
        return [new_node(module_name, "module", None, url=page_url)]

    by_nav_id = {it["id"]: it for it in items}
    children: dict[str, list[dict]] = {}
    for it in items:
        parent = it["parent"] if it["parent"] in by_nav_id else ""
        children.setdefault(parent, []).append(it)

    tree: list[dict] = []

    def emit(nav_id: str, app_parent_id: str | None, level: int) -> None:
        for it in children.get(nav_id, []):
            node_type = LEVEL_TYPE.get(level, "title3")
            node = new_node(it["name"], node_type, app_parent_id, url=it["href"] or page_url)
            tree.append(node)
            emit(it["id"], node["id"], level + 1)

    emit("", None, 0)
    return tree


def diff_auto_tree(existing_tree: list[dict], generated_tree: list[dict]) -> list[dict]:
    """比对现有树与自动生成树，返回带 existing_id 标记的发现清单（只读，不写引擎）。

    generated_tree 需为父先子后的扁平列表；每个生成节点保留其临时 id 与临时 parent_id，
    命中的节点额外带 existing_id（现有树节点 id），未命中为 None。
    父节点为新增节点时用哨兵标记，避免误匹配到现有根节点。
    已存在且没有新增子孙的节点会被剪掉（功能树已有的目录不必再显示）。
    """
    def node_key(parent_id, node: dict) -> tuple:
        return (parent_id, node.get("node_type"), (node.get("name") or "").strip().casefold())

    existing_by_key = {
        node_key(node.get("parent_id"), node): node.get("id")
        for node in (existing_tree or [])
    }
    resolved = {}  # temp_id -> existing 字符串 id，或 False（新增节点）
    result: list[dict] = []
    for node in generated_tree or []:
        parent_temp = node.get("parent_id")
        if parent_temp:
            parent_resolved = resolved.get(parent_temp, False)
        else:
            parent_resolved = None
        existing_id = None
        if parent_resolved is not False:
            existing_id = existing_by_key.get(node_key(parent_resolved, node))
        resolved[node["id"]] = existing_id if existing_id else False
        result.append({**dict(node), "existing_id": existing_id})

    children: dict = {}
    by_id = {n["id"]: n for n in result}
    for node in result:
        children.setdefault(node.get("parent_id"), []).append(node)

    def subtree_has_new(node_id) -> bool:
        node = by_id.get(node_id)
        if node is None:
            return False
        if node.get("existing_id") is None:
            return True
        return any(subtree_has_new(child["id"]) for child in children.get(node_id, []))

    return [node for node in result if subtree_has_new(node["id"])]


def descendants_of_ids(ids: set, tree: list[dict]) -> set:
    """返回 ids 的全部子孙节点 id（不含自身，调用方自行并集）。"""
    idset = set(ids)
    changed = True
    while changed:
        changed = False
        for n in tree:
            if n.get("parent_id") in idset and n.get("id") not in idset:
                idset.add(n["id"])
                changed = True
    return idset - set(ids)
