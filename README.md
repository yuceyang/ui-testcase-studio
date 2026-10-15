# UI Testcase Studio

Interactive **read-only** functional test-case workbench for web systems.

Open a live embedded browser, log in manually, harvest UI controls (buttons, inputs, including iframes), organize them as a module tree, generate query-only test cases aligned with **《功能测试提示词 v3.0》**, and export to Excel / CSV / HTML / JSON / Markdown.

> Use only on systems you are authorized to test. The tool is designed for **query/read-only** verification and does not execute create/update/delete operations.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

| Area | What you get |
|------|----------------|
| Live browser | Address bar, click, type (Chinese IME), paste, zoom (Ctrl+wheel), pop-out window |
| Auth | Manual login in the mirror (no cookie paste required); optional project `storageState` restore |
| Elements | Buttons / inputs / selects / links; recursive iframe walk; right-click mark / cancel |
| Tree | `Module → L1/L2/L3 → Point → Cases`; collapse; batch move/delete; case counts |
| Cases | Query-only templates (positive / query / negative / auth); editable detail; auto-save projects |
| Screenshots | Auto (default on) temp cache → persist into project on import; embed images in Excel |
| Export | Excel (19+ columns per v3 + request fields + screenshot column), CSV, HTML, JSON, Markdown |
| AI | Optional LLM / multimodal (vision) assist; demo fallback without API key |

## Requirements

- Windows / macOS / Linux
- Python 3.10+
- Microsoft Edge or Google Chrome (Playwright `channel=msedge` / `chrome`)
- Optional: Pillow (Excel image embed)

## Install

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Configure

```bash
cp config.example.yaml config.yaml
```

Put model settings in `config.yaml` if needed. **Do not commit API keys.**

```bash
export QTS_API_KEY=sk-...
# or: export OPENAI_API_KEY=sk-...
```

| Key | Meaning |
|-----|---------|
| `ai.provider` | `openai` \| `anthropic` \| `custom` |
| `ai.base_url` | Compatible gateway base URL (optional) |
| `ai.model` / `ai.vision_model` | Text / multimodal model names |
| `QTS_API_KEY` | API key via environment (preferred) |

## Run

```bash
python run.py
# open http://127.0.0.1:8787
```

Typical workflow:

1. **New project** (per system under test)
2. Type target URL in the browser chrome → **前往** (auto-starts the built-in browser)
3. Click the live view, type username/password (IME supported), log in
4. **发现元素** → **自动建树** (or add Module / Dir / Point manually)
5. Mark controls (batch *标记为…*), adjust tree, pass/fail on case detail
6. **生成入库** → cases appear under tree nodes
7. **批量导出** → Excel / CSV / HTML / JSON / Markdown

## Project layout

```
├── LICENSE
├── README.md
├── requirements.txt
├── config.example.yaml     # copy to config.yaml (gitignored)
├── run.py
├── app/
│   ├── main.py             # FastAPI
│   ├── browser/            # Playwright live view + elements + case builder
│   ├── discovery/          # optional HTTP discovery
│   ├── ai/                 # optional LLM case generation
│   ├── export/             # xlsx / csv / html / json / md
│   └── projects.py         # per-project persistence
├── static/                 # web UI
└── docs/
```

## Case export format

Excel columns follow **功能测试提示词 v3.0** (case no, system, module, L1/L2, design, trace, stop condition, title, preconditions, steps, expected, exec fields, remark) plus:

- Request method, URL, params
- Execution status
- Screenshot path
- **Screenshot image** (embedded thumbnail when Pillow is installed)

## Security & ethics

- Authorized testing only
- No create/update/delete workflows in case design
- Secrets stay in env vars / local `config.yaml` (gitignored)
- Project login state is stored under `data/projects/` locally only

## 中文说明

面向 Web 系统的**只读查询类**功能测试辅助：内置浏览器手动登录，采集按钮/输入框等控件，按「模块-一/二/三级-功能点」建树，生成可编辑用例并导出。

- 默认开启自动截图（入库后写入项目截图库）
- 操作自动保存项目
- 无 API Key 时可用演示用例跑通流程

## License

[MIT](LICENSE)
