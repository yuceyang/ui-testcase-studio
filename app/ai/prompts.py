"""提示词模板：强制只读查询、结构化 JSON 输出。"""
from __future__ import annotations

import json

from ..models import ExtraRequirement, FunctionalPoint


SYSTEM_PROMPT = """你是资深软件测试专家，专注「查询/只读」类功能测试用例设计。

硬性约束（不可违反）：
1. 只设计查询/展示/检索/详情/列表/统计类用例，禁止任何增删改、提交、导出写库、上传、删除等操作步骤。
2. 步骤中不得出现 POST/PUT/PATCH/DELETE 写操作；接口调用一律按 GET/HEAD 描述。
3. 若某功能点疑似写操作，标记为 risk，并建议「仅校验页面展示与查询参数」，不给出写操作步骤。
4. 用例要可执行：前置条件、步骤、预期结果清晰；数据要具体（参数名+示例值）。
5. 仅输出 JSON，不要 Markdown 围栏，不要额外解释。

输出 JSON 结构：
{
  "cases": [
    {
      "point_id": "功能点ID",
      "title": "用例标题",
      "module": "模块名",
      "priority": "P0|P1|P2|P3",
      "category": "positive|negative|boundary|auth|performance",
      "preconditions": "前置条件",
      "steps": "操作步骤（只读）",
      "expected": "预期结果",
      "data": "测试数据/参数",
      "method": "GET",
      "url": "相对或完整URL",
      "auth_notes": "鉴权说明",
      "ai_rationale": "设计理由，一句话"
    }
  ],
  "summary": "总体设计说明"
}
"""


def build_generation_prompt(
    points: list[FunctionalPoint],
    extra: ExtraRequirement,
    *,
    use_vision: bool = False,
) -> str:
    policy_scope = "仅查询/只读，禁止增删改"
    focus = "、".join(extra.focus_modules) if extra.focus_modules else "无特别限定"
    user_req = extra.text.strip() or "无额外要求，按通用查询场景设计。"

    compact_points = []
    for p in points:
        compact_points.append(
            {
                "id": p.id,
                "name": p.name,
                "method": p.method,
                "url": p.url,
                "path": p.path,
                "source": p.source,
                "summary": p.summary,
                "params": p.params[:12],
                "tags": p.tags,
                "notes": p.notes,
            }
        )

    vision_note = ""
    if use_vision:
        vision_note = (
            "\n\n【多模态】若附带页面截图，请结合界面元素完善步骤与预期（字段名、按钮、列表列）；"
            "截图仅用于理解界面，不得设计写操作。"
        )

    return f"""请为以下功能点设计软件测试用例。

【测试范围】{policy_scope}
【禁止】增、删、改、提交表单写库、上传、批量修改、状态流转写操作
【需要包含】{"异常/边界" if extra.include_negative else "主要正向"}
【鉴权用例】{"需要（Token失效/Cookie过期/未登录跳转等，但仅验证访问与提示，不改数据）" if extra.include_auth_cases else "不需要"}
【每个功能点最多】{extra.max_cases_per_point} 条
【重点模块】{focus}
【语言】中文
【额外人工要求】
{user_req}
{vision_note}

【功能点列表】
{json.dumps(compact_points, ensure_ascii=False, indent=2)}

请输出严格 JSON。
"""


def parse_cases_json(text: str) -> dict:
    """容错解析：去掉可能的 markdown 围栏 / 前后杂讯。"""
    t = text.strip()
    if t.startswith("```"):
        # 去掉 ```json ... ```
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:].strip()
        t = t.strip()
        if t.endswith("```"):
            t = t[:-3].strip()
    # 找第一个 { 到最后一个 }
    start = t.find("{")
    end = t.rfind("}")
    if start >= 0 and end > start:
        t = t[start : end + 1]
    try:
        return json.loads(t)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI 输出 JSON 解析失败: {e}\n原始片段: {text[:400]}") from e
