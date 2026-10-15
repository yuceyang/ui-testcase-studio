# UI Testcase Studio

Interactive **read-only** functional test-case workbench: open a live embedded browser, navigate and **log in manually**, harvest UI controls (buttons / inputs / selects, including iframes), organize them as a module tree, then generate query-only test cases and export to Excel / Markdown / CSV.

> 仅用于**授权测试环境**的查询/展示类功能验证。默认约束：不设计、不执行增删改写操作。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- **Live browser view** — address bar, click, type (manual login, no cookie paste required)
- **Element discovery** — buttons, inputs, selects, links; recursive iframe walk
- **Module tree** — `Module → Title1 → Title2 → Title3 → Point → XX test/verify`
- **Human review** — mark points, annotate issues, pass / fail / ignore
- **Case generation** — query-only cases (optional LLM / multimodal assist)
- **Export** — `.xlsx` / `.md` / `.csv`

## Requirements

- Windows / macOS / Linux
- Python 3.10+
- Microsoft Edge or Google Chrome (Playwright `channel=msedge` / `chrome`; no separate Chromium download required)

## Install

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configure (optional LLM)

```bash
cp config.example.yaml config.yaml
# edit ai.base_url / ai.model / ai.vision_model
# or: export QTS_API_KEY=sk-...
```

## Run

```bash
python run.py
# open http://127.0.0.1:8787
```

Typical flow in the UI:

1. Click **启动浏览器**
2. Type the target URL in the address bar → **前往**
3. Click the live view to focus login fields, type account/password in the top input bar, press **Enter**
4. **自动发现元素** → **自动建功能点树** (or add nodes manually)
5. Mark functional points, annotate pass/fail
6. **生成测试用例** → **导出Excel**

## Project layout

```
├── LICENSE                 # MIT
├── README.md
├── requirements.txt
├── config.example.yaml
├── run.py                  # entry: python run.py
├── app/
│   ├── main.py             # FastAPI
│   ├── browser/            # Playwright live view + element extract
│   ├── discovery/          # optional HTTP discovery
│   ├── ai/                 # optional LLM case generation
│   └── export/             # xlsx / md / csv
├── static/                 # web UI
└── docs/compose/spec/      # design notes
```

## Security & ethics

- Use only on systems you are authorized to test.
- The tool does **not** execute create/update/delete operations by design.
- Do not commit `config.yaml` or session cookies/tokens; they are gitignored.

## License

[MIT](LICENSE)

## Chinese quick start / 中文速览

| 步骤 | 操作 |
|------|------|
| 启动 | `python run.py` 后打开 `http://127.0.0.1:8787` |
| 登录 | 地址栏输入网址，在页面视图里点选输入框并手动登录（无需粘贴 Cookie） |
| 发现 | 「自动发现元素」抓按钮/输入框（含 iframe） |
| 树 | 「自动建功能点树」或手动：模块 → 一/二/三级标题 → 功能点 |
| 判定 | 标注问题后点通过 / 不通过 |
| 用例 | 生成测试用例 → 导出 Excel，命名「模块-标题-功能点-XX功能点测试/验证」 |
