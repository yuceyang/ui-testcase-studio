"""无 API Key 时的演示用例生成（便于本地试用全流程）。"""
from __future__ import annotations

import uuid

from ..models import ExtraRequirement, FunctionalPoint, TestCase


def demo_enabled(extra: ExtraRequirement | None = None) -> bool:
    import os

    flag = os.environ.get("QTS_DEMO", "").strip().lower()
    return flag in ("1", "true", "yes", "on")


def _demo_for_point(
    p: FunctionalPoint,
    extra: ExtraRequirement,
    used: set[str],
) -> list[TestCase]:
    name = p.name or p.path or "功能"
    url = p.url
    cases: list[TestCase] = []
    max_n = max(1, min(extra.max_cases_per_point or 8, 6))

    def add(title, category, steps, expected, data, priority="P1", auth="已登录带 Cookie/Token"):
        if len(cases) >= max_n:
            return
        if title in used:
            return
        used.add(title)
        cases.append(
            TestCase(
                id=uuid.uuid4().hex[:12],
                point_id=p.id,
                title=title,
                module=name[:20] or "查询功能",
                priority=priority,
                preconditions="已使用有效 Cookie/Token 登录；网络可达目标环境",
                steps=steps,
                expected=expected,
                data=data,
                method="GET",
                url=url,
                auth_notes=auth,
                category=category,
                ai_rationale="[演示模式] 未配置 API Key，生成示例用例供流程体验",
                human_modified=False,
                approved=True,
            )
        )

    add(
        f"【正向】{name} — 默认条件查询返回列表",
        "positive",
        f"1. 带鉴权请求 GET {url}\n2. 不传或传默认分页参数\n3. 查看响应状态与数据体",
        "HTTP 200；返回 JSON/页面内容；字段完整、无敏感异常堆栈",
        "page=1, pageSize=20",
        "P0",
    )
    add(
        f"【边界】{name} — 分页参数边界值",
        "boundary",
        f"1. 请求 GET {url}\n2. page=1 且 pageSize=1；再试 pageSize=100\n3. 观察响应条数与耗时",
        "返回条数与 pageSize 一致或按上限截断；响应时间可接受；不报 500",
        "page=1, pageSize=1 / 100",
        "P1",
    )
    if extra.include_negative:
        add(
            f"【异常】{name} — 非法/空参数",
            "negative",
            f"1. 请求 GET {url}\n2. 传入非法值（空串、特殊字符、超长字符串）\n3. 检查是否优雅报错",
            "返回 4xx 或业务错误码与明确提示；不泄露 SQL/堆栈；不写入任何数据",
            'page=-1 或 q=<script>',
            "P1",
        )
        add(
            f"【异常】{name} — 不存在的资源 ID",
            "negative",
            f"1. 请求 GET {url}（带不存在的 id）\n2. 观察响应",
            "返回 404 或空结果；提示友好；不触发删除/兜底写库",
            "id=999999999",
            "P1",
        )
    if extra.include_auth_cases:
        add(
            f"【鉴权】{name} — 未携带 Token/Cookie",
            "auth",
            f"1. 清除 Cookie/Authorization 后请求 GET {url}\n2. 观察响应与跳转",
            "返回 401 或跳转登录页；不返回业务数据；不修改服务端状态",
            "无鉴权头",
            "P0",
        )
        add(
            f"【鉴权】{name} — 过期/伪造 Token",
            "auth",
            f"1. 使用过期或随机伪造 Token 请求 GET {url}\n2. 观察响应",
            "拒绝访问并给出明确鉴权失败提示；不产生写操作副作用",
            "Authorization: Bearer invalid.xx",
            "P1",
        )
    if extra.include_negative and extra.max_cases_per_point >= 5:
        add(
            f"【边界】{name} — 时间/范围过滤边界",
            "boundary",
            f"1. 请求 GET {url}\n2. 传入开始=结束时间、跨月范围、远古日期\n3. 校验过滤结果",
            "按参数正确过滤或提示范围非法；结果为空时返回空列表而非错误",
            "startDate=2020-01-01&endDate=2020-01-01",
            "P2",
        )

    return cases


def generate_demo_cases(
    points: list[FunctionalPoint],
    extra: ExtraRequirement,
) -> tuple[list[TestCase], str, list[str]]:
    used: set[str] = set()
    cases: list[TestCase] = []
    for p in points:
        cases.extend(_demo_for_point(p, extra, used))

    note = (
        f"[演示模式] 已为 {len(points)} 个功能点生成 {len(cases)} 条只读查询示例用例。"
        "配置真实 API Key 后可重新生成贴合业务的用例。"
    )
    return cases, note, ["当前为演示模式（未配置可用 API Key），用例为示例模板。"]
