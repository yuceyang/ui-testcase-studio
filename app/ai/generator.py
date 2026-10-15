"""测试用例生成编排。"""
from __future__ import annotations

import re
import uuid

from ..config import Settings
from ..models import ExtraRequirement, FunctionalPoint, TestCase
from .client import LLMClient, LLMError
from .demo import demo_enabled, generate_demo_cases
from .prompts import SYSTEM_PROMPT, build_generation_prompt, parse_cases_json


MUTATION_WORDS = re.compile(
    r"(删除|移除|清空|修改|编辑|新增|创建|保存|提交|上传|下架|上架|禁用|启用|重置密码|"
    r"delete|remove|create|update|insert|put|patch|drop|truncate|upload)",
    re.I,
)


def _sanitize_case(raw: dict, point: FunctionalPoint | None) -> TestCase | None:
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    steps = (raw.get("steps") or "").strip()
    # 步骤里若混入写操作词，在 rationale 注明风险，但仍保留用例供人工审（预期是查询）
    risky = bool(MUTATION_WORDS.search(steps + " " + title))
    category = raw.get("category") or "positive"
    if category not in ("positive", "negative", "boundary", "auth", "performance"):
        category = "positive"
    priority = raw.get("priority") or "P1"
    if priority not in ("P0", "P1", "P2", "P3"):
        priority = "P1"

    method = (raw.get("method") or point.method or "GET").upper()
    if method not in ("GET", "HEAD", "OPTIONS"):
        method = "GET"

    url = raw.get("url") or (point.url if point else "")
    note = (raw.get("ai_rationale") or "").strip()
    if risky:
        note = (note + " | [人工注意] 步骤措辞含疑似写操作词，请核对是否为只读校验。").strip(" |")

    return TestCase(
        id=uuid.uuid4().hex[:12],
        point_id=raw.get("point_id") or (point.id if point else ""),
        title=title[:120],
        module=raw.get("module") or (point.tags[0] if point and point.tags else "查询功能"),
        priority=priority,
        preconditions=(raw.get("preconditions") or "").strip(),
        steps=steps,
        expected=(raw.get("expected") or "").strip(),
        data=(raw.get("data") or "").strip(),
        method=method,
        url=str(url)[:500],
        auth_notes=(raw.get("auth_notes") or "").strip(),
        category=category,
        ai_rationale=note,
        human_modified=False,
        approved=True,
    )


def generate_test_cases(
    points: list[FunctionalPoint],
    extra: ExtraRequirement,
    settings: Settings,
    *,
    image_paths: list[str] | None = None,
) -> tuple[list[TestCase], str, list[str]]:
    """调用 AI 生成用例，返回 (cases, raw_summary, warnings)。"""
    warnings: list[str] = []
    if not points:
        return [], "", ["未选择任何功能点。"]

    # 无密钥 / 强制演示时走本地示例，保证流程可试用
    api_key = (settings.ai.api_key or "").strip()
    if demo_enabled(extra) or (not api_key or api_key.startswith("sk-demo") or api_key.startswith("your-")):
        cases, summary, warns = generate_demo_cases(points, extra)
        return cases, summary, warns

    # 分批，避免超长
    batch_size = 12
    all_cases: list[TestCase] = []
    summaries: list[str] = []

    client = LLMClient(settings.ai)
    use_vision = bool(image_paths)

    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        prompt = build_generation_prompt(batch, extra, use_vision=use_vision)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            client.build_user_message(prompt, image_paths if use_vision else None),
        ]
        try:
            raw = client.chat(messages, vision=use_vision)
        except LLMError as e:
            warnings.append(f"批次 {i // batch_size + 1} 生成失败: {e}")
            if not all_cases and i == 0:
                cases, summary, _ = generate_demo_cases(points, extra)
                warnings.append("AI 不可用，已自动切换演示用例，便于继续体验流程。")
                return cases, summary, warnings
            continue

        try:
            data = parse_cases_json(raw)
        except ValueError as e:
            warnings.append(str(e))
            continue

        summaries.append(str(data.get("summary") or ""))
        by_id = {p.id: p for p in batch}
        for item in data.get("cases") or []:
            if not isinstance(item, dict):
                continue
            pid = item.get("point_id") or ""
            case = _sanitize_case(item, by_id.get(pid))
            if case:
                all_cases.append(case)

        # 多模态：第一张图用一次即可，避免重复传图
        image_paths = None
        use_vision = False

    if not all_cases and not warnings:
        warnings.append("AI 未返回有效用例，请检查模型配置或收窄功能点范围后重试。")

    return all_cases, " / ".join(s for s in summaries if s), warnings
