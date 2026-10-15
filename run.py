"""启动入口：python run.py"""
from __future__ import annotations

import uvicorn

from app.config import ensure_dirs, load_settings


def main() -> None:
    ensure_dirs()
    s = load_settings()
    print(f"◆ 软件功能测试系统  http://{s.server.host}:{s.server.port}")
    print(f"◆ AI 模型: {s.ai.provider} / {s.ai.model}  (多模态: {s.ai.vision_model})")
    print("◆ 约束: 仅查询/只读，不执行增删改")
    uvicorn.run(
        "app.main:app",
        host=s.server.host,
        port=s.server.port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
