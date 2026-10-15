"""树形功能点 → 功能测试提示词 v3.0 用例（多级目录适配）。"""
from __future__ import annotations

import uuid

from ..models import ExtraRequirement, TestCase

STOP = "功能验证完成或出现阻断缺陷即终止"


def _chain(node_id: str, tree: list[dict]) -> list[dict]:
    by = {n["id"]: n for n in tree}
    out = []
    cur = by.get(node_id)
    g = 0
    while cur and g < 30:
        out.append(cur)
        cur = by.get(cur.get("parent_id"))
        g += 1
    out.reverse()
    return out


def _fields_for(node: dict, tree: list[dict], sys_name: str) -> dict:
    """
    映射：系统名字 / 模块分类 / 一级标题 / 二级标题
    更深目录并入「二级标题」路径（或设计需求），满足 v3 两列上限。
    """
    chain = _chain(node["id"], tree)
    by_type = {}
    dirs = []  # 目录节点（title*）
    point_name = node.get("name") or "功能点"
    for n in chain:
        nt = n.get("node_type")
        nm = (n.get("name") or "").strip()
        if nt == "module":
            by_type["module"] = nm or "模块"
        elif nt.startswith("title"):
            dirs.append(nm or "/")
        elif nt in ("point", "case"):
            point_name = nm or point_name

    module_cat = by_type.get("module") or sys_name or "模块"
    l1 = dirs[0] if dirs else "/"
    if len(dirs) >= 2:
        l2 = dirs[1]
    else:
        l2 = "/"
    # 更深目录：写入二级标题扩展，用 - 串联
    if len(dirs) > 2:
        l2 = "-".join(dirs[1:]) if dirs[1] else "/"

    track = f"{module_cat}-{l1}" if l1 != "/" else f"{module_cat}-{point_name}"
    return {
        "sys_name": sys_name,
        "module_cat": module_cat,
        "title_l1": l1 or "/",
        "title_l2": l2 or "/",
        "point_name": point_name,
        "design_req": f"支持通过界面操作对「{point_name}」进行查询/展示验证",
        "test_track": track,
        "deep_path": " / ".join([x for x in (module_cat, l1, l2, point_name) if x]),
    }


def _mk(
    *,
    no: str,
    f: dict,
    title: str,
    pre: str,
    steps: str,
    expect: str,
    category: str,
    priority: str,
    remark: str = "-",
    point_id: str = "",
    url: str = "",
) -> TestCase:
    return TestCase(
        id=uuid.uuid4().hex[:12],
        point_id=point_id,
        title=title,
        module=f["module_cat"],
        priority=priority,
        preconditions=pre,
        steps=steps,
        expected=expect,
        data="-",
        method="GET",
        url=url,
        auth_notes="已登录系统",
        category=category,
        ai_rationale=f["test_track"],
        approved=True,
        case_no=no,
        sys_name=f["sys_name"],
        module_cat=f["module_cat"],
        title_l1=f["title_l1"],
        title_l2=f["title_l2"],
        design_req=f["design_req"],
        test_track=f["test_track"],
        stop_cond=STOP,
        remark=remark,
    )


def build_cases_from_tree(
    tree: list[dict],
    marked_elements: list[dict],
    extra: ExtraRequirement,
    sys_name: str = "",
    start_no: int = 1,
) -> list[TestCase]:
    """按功能测试提示词 v3.0 生成；支持多级目录，更深层级并入二级标题。"""
    cases: list[TestCase] = []
    el_by_id = {e.get("id"): e for e in marked_elements}
    seq = start_no
    sys_name = sys_name or "被测系统"

    def next_no() -> str:
        nonlocal seq
        n = f"GN-{seq:04d}"
        seq += 1
        return n

    for node in tree:
        if node.get("node_type") not in ("point", "case"):
            continue
        if node.get("status") == "ignored":
            continue

        f = _fields_for(node, tree, sys_name)
        point_name = f["point_name"]
        url = node.get("url") or ""
        els = [el_by_id[i] for i in (node.get("element_ids") or []) if i in el_by_id]
        el_desc = "、".join((e.get("name") or e.get("text") or e.get("selector") or "") for e in els[:5])
        if not el_desc:
            el_desc = point_name

        # 正向：页面类 / 查询类
        cases.append(
            _mk(
                no=next_no(),
                f=f,
                title=f"{point_name}页面加载与元素展示验证",
                pre=f"1.已使用测试账号登录{sys_name}；2.存在与「{point_name}」相关的基础数据；3.已进入{f['deep_path']}",
                steps=f"1.进入「{f['deep_path']}」；2.定位元素：{el_desc}；3.观察页面元素是否完整展示（只读）",
                expect="1.页面加载完成，元素可见可操作；2.展示数据与条件一致，无报错弹窗；3.页面无JS异常",
                category="positive",
                priority="P0" if node.get("status") != "fail" else "P1",
                remark=f"P0；只读校验，不做增删改",
                point_id=node.get("id", ""),
                url=url,
            )
        )

        # 查询类（若有输入框）
        has_input = any((e.get("kind") == "input") for e in els) or node.get("node_type") == "point"
        if has_input and extra.include_negative:
            cases.append(
                _mk(
                    no=next_no(),
                    f=f,
                    title=f"{point_name}条件查询功能验证",
                    pre=f"1.已登录{sys_name}；2.存在至少一条可查询的「{point_name}」数据",
                    steps=f"1.进入「{f['deep_path']}」；2.在检索条件输入合法关键字；3.点击「查询」按钮；4.核对列表结果；5.点击「重置」按钮后再查询",
                    expect="1.查询后列表按条件过滤，数据正确；2.重置后条件清空并恢复默认列表；3.无报错弹窗",
                    category="positive",
                    priority="P1",
                    remark="P1",
                    point_id=node.get("id", ""),
                    url=url,
                )
            )
            cases.append(
                _mk(
                    no=next_no(),
                    f=f,
                    title=f"{point_name}格式异常校验验证",
                    pre=f"1.已登录{sys_name}；2.已进入「{f['deep_path']}」",
                    steps="1.在相关输入框输入特殊字符或超长内容；2.点击「查询」按钮；3.观察提示与列表",
                    expect="1.给出明确校验或空结果提示；2.不产生脏数据；3.无JS报错",
                    category="negative",
                    priority="P2",
                    remark="P2；未标注具体长度时不写死位数",
                    point_id=node.get("id", ""),
                    url=url,
                )
            )

        if extra.include_auth_cases:
            cases.append(
                _mk(
                    no=next_no(),
                    f=f,
                    title=f"{point_name}未登录访问权限控制验证",
                    pre="1.清除会话或使用无痕窗口；2.保留原访问链接",
                    steps=f"1.未登录直接访问「{f['deep_path']}」或刷新页面；2.观察跳转与提示",
                    expect="1.跳转登录页或提示无权限；2.不展示业务数据；3.不改变服务端数据",
                    category="auth",
                    priority="P0",
                    remark="P0",
                    point_id=node.get("id", ""),
                    url=url,
                )
            )

        if node.get("annotation"):
            st = node.get("status", "pending")
            cases.append(
                _mk(
                    no=next_no(),
                    f=f,
                    title=f"{point_name}问题标注复核验证",
                    pre=f"1.已登录{sys_name}；2.标注内容：{node.get('annotation')[:80]}",
                    steps=f"1.按标注路径进入「{f['deep_path']}」；2.复现标注问题；3.确认是否仍存在（只读）",
                    expect="1.问题已修复或不再复现；2.若仍存在则在备注登记缺陷；3.无新增报错",
                    category="negative" if st == "fail" else "positive",
                    priority="P0" if st == "fail" else "P2",
                    remark=f"人工标注复核；状态={st}",
                    point_id=node.get("id", ""),
                    url=url,
                )
            )

    return cases
