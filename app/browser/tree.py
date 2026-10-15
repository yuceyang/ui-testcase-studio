"""树形功能点结构：模块 → 一级/二级/三级目录 → 功能点 → 测试/验证。

缺级目录用 "/" 占位，保证用例命名链完整：
  模块-一级-二级-三级-功能点-XX功能点测试/验证
"""
from __future__ import annotations

import uuid
from typing import Any

from ..models import ExtraRequirement, TestCase


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


def build_cases_from_tree(
    tree: list[dict],
    marked_elements: list[dict],
    extra: ExtraRequirement,
) -> list[TestCase]:
    """按树节点生成只读测试用例，命名：模块-一-二-三-功能点-XX功能点测试/验证。"""
    cases: list[TestCase] = []
    el_by_id = {e.get("id"): e for e in marked_elements}
    used_titles: set[str] = set()

    for node in tree:
        if node.get("node_type") not in ("point", "case"):
            continue
        if node.get("status") == "ignored":
            continue

        title = case_title_for(node, tree)
        if not title or title in used_titles:
            title = f"{title or '功能点'}-{uuid.uuid4().hex[:4]}"
        used_titles.add(title)

        path = " / ".join(padded_path_names(node.get("id"), tree))
        module = path_of(node.get("id"), tree)
        module_name = module[0]["name"] if module else "未分类"

        els = [el_by_id[eid] for eid in (node.get("element_ids") or []) if eid in el_by_id]
        if not els and node.get("elements"):
            els = node.get("elements") or []
        el_desc = "；".join(
            f"{e.get('kind','')}:{e.get('name') or e.get('text') or e.get('selector','')}"
            for e in els[:6]
        ) or "页面既有展示"

        url = node.get("url") or (els[0].get("page_url") if els else "")
        sel = els[0].get("selector", "") if els else ""
        method = "GET"

        cases.append(
            TestCase(
                id=uuid.uuid4().hex[:12],
                point_id=node.get("id", ""),
                title=title,
                module=path,
                priority="P0" if node.get("status") == "fail" else "P1",
                preconditions=f"已鉴权登录系统；打开页面：{url or '目标页面'}",
                steps=(
                    f"1. 进入「{path}」\n"
                    f"2. 定位元素：{el_desc}\n"
                    f"3. 观察展示/查询结果（只读，不做提交写库）"
                ),
                expected="元素可见可操作；查询/展示结果正确；无报错弹窗",
                data=f"selector={sel}" if sel else "—",
                method=method,
                url=url,
                auth_notes="已带有效会话（镜像内手动登录）",
                category="positive",
                ai_rationale=f"结构: {path}；状态: {node.get('status','pending')}",
                approved=node.get("status") != "fail",
            )
        )

        if extra.include_negative:
            cases.append(
                TestCase(
                    id=uuid.uuid4().hex[:12],
                    point_id=node.get("id", ""),
                    title=title + "（异常输入）",
                    module=path,
                    priority="P1",
                    preconditions="已登录；位于该功能页面",
                    steps=(
                        "1. 在相关输入框输入非法/超长/特殊字符\n"
                        "2. 点「查询」或触发搜索（不点提交/删除）\n"
                        "3. 观察提示"
                    ),
                    expected="给出明确校验提示；不产生脏数据；不触发写操作",
                    data="含 <script>、空格、超长字符串",
                    method=method,
                    url=url,
                    auth_notes="同正向",
                    category="negative",
                    ai_rationale="只读异常边界",
                    approved=True,
                )
            )

        if extra.include_auth_cases:
            cases.append(
                TestCase(
                    id=uuid.uuid4().hex[:12],
                    point_id=node.get("id", ""),
                    title=title + "（未登录/会话失效）",
                    module=path,
                    priority="P0",
                    preconditions="清除会话或重新打开无痕",
                    steps="1. 无有效会话访问该功能\n2. 观察跳转/提示",
                    expected="401 或跳转登录；不展示业务数据；不改服务端状态",
                    data="无",
                    method=method,
                    url=url,
                    auth_notes="无/过期会话",
                    category="auth",
                    ai_rationale="鉴权边界",
                    approved=True,
                )
            )

        if node.get("annotation"):
            cases.append(
                TestCase(
                    id=uuid.uuid4().hex[:12],
                    point_id=node.get("id", ""),
                    title=title + "（人工标注复核）",
                    module=path,
                    priority="P0" if node.get("status") == "fail" else "P2",
                    preconditions="按标注步骤复现",
                    steps=f"1. 核查标注内容：{node.get('annotation')}\n2. 确认是否仍复现（只读）",
                    expected="问题已修复或不再复现；如仍存在则记录缺陷单",
                    data="—",
                    method=method,
                    url=url,
                    auth_notes="—",
                    category="negative" if node.get("status") == "fail" else "positive",
                    ai_rationale="人工标注复核",
                    approved=True,
                )
            )

    return cases


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
