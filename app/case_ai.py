"""用例 AI 修改：按提示词改写选定字段。"""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, HTTPException

from .config import load_settings
from .models import TestCase

router = APIRouter(prefix="/api/case", tags=["case-ai"])

FIELD_MAP = {
    "title": "用例标题",
    "design_req": "设计需求",
    "test_track": "测试追踪",
    "preconditions": "前提与约束",
    "steps": "输入及操作说明",
    "expected": "期望测试结果",
    "params": "携带参数",
    "remark": "备注",
}

# 前端字段名 → 模型字段
ALIAS = {
    "designRequirement": "design_req",
    "expectedResult": "expected",
    "operationSteps": "steps",
    "precondition": "preconditions",
    "caseTitle": "title",
}


def _demo_edit(fields: dict[str, str], prompt: str) -> dict[str, str]:
    out = {}
    for k, v in fields.items():
        s = (v or "").strip()
        if k in ("expected", "expectedResult"):
            out[k] = (
                (s + "；" if s else "")
                + "1.边界值最小/最大仍正常展示；2.异常输入有校验提示；3.页面无JS错误"
            )
        elif k in ("steps", "operationSteps"):
            out[k] = (s + "；" if s else "") + "N.按提示词补充更细步骤（人工确认）"
        elif k in ("preconditions", "precondition"):
            out[k] = (s + "；" if s else "") + "N.已准备提示词要求的测试数据"
        else:
            out[k] = s + ("（已按提示词润色）" if s else "（按提示词生成，请人工确认）")
        if prompt:
            out[k] = out[k] + f"｜提示: {prompt[:40]}"
    return out


@router.post("/ai-edit")
def ai_edit(payload: dict[str, Any]):
    """
    body: { caseId, currentContent: {field: value}, prompt, fields?: [names] }
    return: { ok, data: {field: new}, mode: "ai"|"demo" }
    """
    current: dict[str, str] = payload.get("currentContent") or {}
    prompt = (payload.get("prompt") or "").strip()
    fields = payload.get("fields") or list(current.keys())
    if not fields:
        raise HTTPException(400, "未选择要修改的字段")
    if not prompt:
        raise HTTPException(400, "请填写 AI 提示词")

    # 仅处理选中字段
    src = {}
    for f in fields:
        key = ALIAS.get(f, f)
        if f in current:
            src[f] = current.get(f) or ""
        elif key in current:
            src[f] = current.get(key) or ""

    settings = load_settings()
    api_key = (settings.ai.api_key or "").strip()
    if api_key:
        try:
            from .ai.client import LLMClient

            names = "、".join(FIELD_MAP.get(ALIAS.get(f, f), f) for f in fields)
            sys_p = (
                "你是资深测试工程师。根据用户提示词改写测试用例字段。"
                "只输出 JSON 对象，键与输入 currentContent 的键一致，不要解释。"
            )
            user_p = (
                f"需要修改的字段: {names}\n提示词: {prompt}\n"
                f"现有内容 JSON:\n{json.dumps(src, ensure_ascii=False)}"
            )
            client = LLMClient(settings.ai)
            raw = client.chat(
                [
                    {"role": "system", "content": sys_p},
                    {"role": "user", "content": user_p},
                ]
            )
            m = re.search(r"\{.*\}", raw, re.S)
            data = json.loads(m.group(0)) if m else {}
            out = {}
            for k in fields:
                if k in data:
                    out[k] = str(data.get(k) or "")
                elif ALIAS.get(k) in data:
                    out[k] = str(data.get(ALIAS[k]) or "")
                else:
                    out[k] = src.get(k, "")
            return {"ok": True, "data": out, "mode": "ai"}
        except Exception as e:  # noqa: BLE001
            return {"ok": True, "data": _demo_edit(src, prompt), "mode": "demo", "error": str(e)}

    return {"ok": True, "data": _demo_edit(src, prompt), "mode": "demo"}
