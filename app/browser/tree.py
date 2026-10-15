"""树形功能点结构：模块 → 一级/二级/三级标题 → 功能点 → XX功能点测试/验证。"""
from __future__ import annotations

import uuid
from typing import Any

from ..models import ExtraRequirement, TestCase


LEVEL_TYPES = ("module", "title1", "title2", "title3", "point", "case")
LEVEL_LABEL = {
    "module": "模块",
    "title1": "一级标题",
    "title2": "二级标题",
    "title3": "三级标题",
    "point": "功能点",
    "case": "测试/验证",
}


def new_node(
    name: str,
    node_type: str = "point",
    parent_id: str | None = None,
    **extra: Any,
) -> dict:
    return {
        "id": "nd_" + uuid.uuid4().hex[:10],
        "name": name,
        "node_type": node_type if node_type in LEVEL_TYPES else "point",
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
    """从根到该节点的路径。"""
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


def case_title_for(node: dict, tree: list[dict], suffix: str = "测试/验证") -> str:
    """生成「模块-一级-…-功能点-XX测试/验证」，避免功能点名重复拼接。"""
    chain = path_of(node.get("id"), tree)
    names = [n.get("name") or "" for n in chain if n.get("name")]
    if not names:
        return suffix
    if node.get("node_type") == "case":
        # 已是验证节点，原样输出路径
        return "-".join(names)
    # 功能点：路径 + 「XX功能点测试/验证」
    point_name = names[-1]
    return "-".join(names[:-1] + [f"{point_name}功能点{suffix}"] if len(names) > 1 else [f"{point_name}功能点{suffix}"])


def iter_points(tree: list[dict]) -> list[dict]:
    return [n for n in tree if n.get("node_type") in ("point", "case")]


def build_cases_from_tree(
    tree: list[dict],
    marked_elements: list[dict],
    extra: ExtraRequirement,
) -> list[TestCase]:
    """按树节点生成只读测试用例，命名对齐「模块-…-功能点-测试/验证」。"""
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

        path = full_path_name(node.get("id"), tree)
        module = path_of(node.get("id"), tree)
        module_name = module[0]["name"] if module else "未分类"

        # 关联元素
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

        # 主验证
        cases.append(
            TestCase(
                id=uuid.uuid4().hex[:12],
                point_id=node.get("id", ""),
                title=title,
                module=path,
                priority="P0" if node.get("status") == "pass" else "P1",
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
                auth_notes="已带有效 Cookie/Token",
                category="positive",
                ai_rationale=f"结构: {path}；状态: {node.get('status','pending')}",
                approved=node.get("status") != "fail",
            )
        )

        # 异常
        if extra.include_negative:
            cases.append(
                TestCase(
                    id=uuid.uuid4().hex[:12],
                    point_id=node.get("id", ""),
                    title=title + "（异常输入）",
                    module=path,
                    priority="P1",
                    preconditions="已鉴权登录；位于该功能页面",
                    steps=(
                        f"1. 在相关输入框输入非法/超长/特殊字符\n"
                        f"2. 点「查询」或触发搜索（不点提交/删除）\n"
                        f"3. 观察提示"
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

        # 鉴权
        if extra.include_auth_cases:
            cases.append(
                TestCase(
                    id=uuid.uuid4().hex[:12],
                    point_id=node.get("id", ""),
                    title=title + "（未登录/Token失效）",
                    module=path,
                    priority="P0",
                    preconditions="清除 Cookie 或使用过期 Token",
                    steps="1. 无有效鉴权访问该功能\n2. 观察跳转/提示",
                    expected="401 或跳转登录；不展示业务数据；不改服务端状态",
                    data="无",
                    method=method,
                    url=url,
                    auth_notes="无/过期鉴权",
                    category="auth",
                    ai_rationale="鉴权边界",
                    approved=True,
                )
            )

        if node.get("annotation"):
            # 标注问题时生成一条复核用例
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
    """把导航菜单粗建成：模块 / 一级标题 / （叶子作功能点）。"""
    tree: list[dict] = []
    root = new_node(module_name, "module", None, url=page_url)
    tree.append(root)

    # 简单启发式：前几个作一级，其余作二级；或全作一级
    titles: list[dict] = []
    for i, h in enumerate(nav_hints[:30]):
        name = (h.get("name") or "").strip()
        if not name:
            continue
        t = new_node(name, "title1", root["id"], url=h.get("href") or page_url)
        tree.append(t)
        titles.append(t)
        # 每个一级下挂一个功能点占位
        p = new_node(name, "point", t["id"], url=h.get("href") or page_url)
        tree.append(p)
    return tree
