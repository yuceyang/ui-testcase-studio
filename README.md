# 软件功能测试系统（UI Testcase Studio）

面向 Web 系统的 **只读查询类** 功能测试工作台：内置浏览器手动登录、采集界面控件、按「模块 → 目录 → 功能点」建树、生成可编辑测试用例并导出 Excel/CSV/HTML/JSON/Markdown。

> 仅用于**授权测试环境**的查询与展示类功能验证；默认**不设计、不执行**增删改写操作。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 功能特性

| 模块 | 能力 |
|------|------|
| 内置浏览器 | 地址栏导航、镜像内点击/中文输入/粘贴、缩放（±1%、可手输 50–200%）、弹出窗 |
| 登录 | 镜像内手动登录；项目可保存 `storageState`，加载时恢复会话（无需粘贴 Cookie） |
| 交互元素 | 按钮/输入框/下拉/链接；iframe 递归；右键标记/取消；批量标记为模块/目录/功能点 |
| 功能点树 | 模块 → 一/二/三级 → 功能点 → 用例（缺级用 `/` 占位）；折叠、级联勾选、批量移动/删除、未绑定分组 |
| 测试用例 | 仅查询类模板（正向/查询/异常/鉴权）；详情可编辑；**AI 修改**选定字段 |
| 截图 | 自动截图默认开启；未入库临时缓存；入库写入项目截图库；Excel 内嵌缩略图 |
| 导出 | Excel（v3.0 19 列 + 请求字段 + 截图列）、CSV、HTML、JSON、Markdown |
| AI | 可选大模型/多模态辅助；无 API Key 时演示用例可跑通流程 |
| 项目 | 按被测系统建项目，操作自动保存 |

## 环境要求

- Windows / macOS / Linux
- Python 3.10+
- Microsoft Edge 或 Google Chrome（Playwright `channel=msedge` / `chrome`）
- 可选：Pillow（Excel 插入截图）

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## 配置（可选）

```bash
cp config.example.yaml config.yaml
```

密钥请用环境变量，**不要提交到仓库**：

```bash
export QTS_API_KEY=sk-...
# 或 export OPENAI_API_KEY=sk-...
```

| 配置项 | 含义 |
|--------|------|
| `ai.provider` | `openai` \| `anthropic` \| `custom` |
| `ai.base_url` | 兼容网关地址（可留空） |
| `ai.model` / `ai.vision_model` | 文本 / 多模态模型名 |
| `QTS_API_KEY` | API Key（推荐环境变量） |

## 启动

```bash
python run.py
# 打开 http://127.0.0.1:8787
```

## 推荐流程

1. **新建项目**（按被测系统）
2. 地址栏输入网址 → **前往**（自动启动内置浏览器）
3. 点击镜像，输入账号密码（支持中文输入法）完成登录
4. **发现元素** → **自动建树**（或 +新增 / 批量标记为…）
5. 树上勾选功能点 → **生成用例** → 用例生成台（未入库）核对
6. 点 **生成入库** → 用例挂在功能点下 → **批量导出**

## 目录结构

```
├── LICENSE
├── README.md
├── requirements.txt
├── config.example.yaml     # 复制为 config.yaml（已 gitignore）
├── run.py
├── app/
│   ├── main.py             # FastAPI
│   ├── browser/            # Playwright 实时镜像与元素
│   ├── discovery/          # 可选 HTTP 发现
│   ├── ai/                 # 可选大模型用例
│   ├── export/             # xlsx/csv/html/json/md
│   └── projects.py         # 项目持久化
├── static/                 # Web 界面
└── docs/                   # 设计说明
```

## 导出格式

Excel 列遵循 **《功能测试提示词 v3.0》**（用例编号、系统、模块、一级/二级、设计需求、测试追踪、终止条件、用例标题、前提、步骤、期望、执行字段、备注），并附加：

- 请求方式、URL、携带参数  
- 执行状态  
- 截图路径  
- **截图缩略图**（安装 Pillow 后嵌入）  

## 安全与伦理

- 仅对**已授权**系统做测试  
- 用例设计限定只读查询，不包含增删改流程  
- 密钥仅存环境变量或本地 `config.yaml`（已忽略提交）  
- 项目登录态只保存在本地 `data/projects/`  

## 中文速览

内置浏览器手动登录 → 采集控件 → 功能点树 → 生成/入库用例 → 导出。无 API Key 时可用演示用例体验全流程。

## 许可证

[MIT](LICENSE)
