"""用例导出：xlsx / md / csv。"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from ..config import OUTPUT_DIR
from ..models import TestCase


HEADERS = [
    "用例编号", "功能点ID", "模块", "标题", "优先级", "类型",
    "前置条件", "操作步骤", "预期结果", "测试数据",
    "方法", "URL", "鉴权说明", "设计理由", "人工修改",
]


def _row(c: TestCase) -> list[str]:
    return [
        c.id,
        c.point_id,
        c.module,
        c.title,
        c.priority,
        c.category,
        c.preconditions,
        c.steps,
        c.expected,
        c.data,
        c.method,
        c.url,
        c.auth_notes,
        c.ai_rationale,
        "是" if c.human_modified else "否",
    ]


def export_cases(cases: list[TestCase], fmt: str, base_name: str | None = None) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = base_name or f"查询测试用例_{stamp}"

    if fmt == "xlsx":
        path = OUTPUT_DIR / f"{name}.xlsx"
        _to_xlsx(cases, path)
    elif fmt == "md":
        path = OUTPUT_DIR / f"{name}.md"
        _to_md(cases, path)
    else:
        path = OUTPUT_DIR / f"{name}.csv"
        _to_csv(cases, path)
    return path


def _to_xlsx(cases: list[TestCase], path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "查询测试用例"

    header_fill = PatternFill("solid", fgColor="D9D9D9")
    thin = Border(
        left=Side(style="thin", color="000000"),
        right=Side(style="thin", color="000000"),
        top=Side(style="thin", color="000000"),
        bottom=Side(style="thin", color="000000"),
    )
    header_font = Font(name="宋体", size=11, bold=True, color="000000")
    body_font = Font(name="宋体", size=11, color="000000")

    ws.append(HEADERS)
    for col, _ in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin

    for c in cases:
        ws.append(_row(c))

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=len(HEADERS)):
        for cell in row:
            cell.font = body_font
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            cell.border = thin

    from openpyxl.utils import get_column_letter

    widths = [12, 12, 12, 28, 8, 10, 22, 36, 28, 22, 8, 32, 18, 22, 10]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = "A2"
    wb.save(path)


def _to_md(cases: list[TestCase], path: Path) -> None:
    lines = [
        "# 查询功能测试用例",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"> 用例数量：{len(cases)}  ",
        "> 约束：仅查询/只读，不含增删改操作。",
        "",
    ]
    for i, c in enumerate(cases, 1):
        lines.extend(
            [
                f"## {i}. {c.title}",
                "",
                f"- **编号**：{c.id}",
                f"- **模块**：{c.module}",
                f"- **优先级**：{c.priority}",
                f"- **类型**：{c.category}",
                f"- **方法**：{c.method}",
                f"- **URL**：`{c.url}`",
                f"- **前置条件**：{c.preconditions or '—'}",
                f"- **操作步骤**：{c.steps or '—'}",
                f"- **预期结果**：{c.expected or '—'}",
                f"- **测试数据**：{c.data or '—'}",
                f"- **鉴权说明**：{c.auth_notes or '—'}",
                f"- **设计理由**：{c.ai_rationale or '—'}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _to_csv(cases: list[TestCase], path: Path) -> None:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(HEADERS)
    for c in cases:
        w.writerow(_row(c))
    # utf-8-sig 方便 Excel 打开
    path.write_text(buf.getvalue(), encoding="utf-8-sig")
