---
feature: live-browser-ui
status: delivered
updated: 2026-10-15
branch: main
commits: 
---

# 实时镜像内置浏览器与开源项目骨架

## Report

**What was built** — 页面视图改为大尺寸实时镜像（JPEG 轮询约 320ms），顶部地址栏可直接导航；点击画面映射到 Playwright 视口坐标，配套「键入 / Enter / Tab / 清空」完成手动登录，主流程不再依赖 Cookie 粘贴。项目按 GitHub 形态整理：MIT LICENSE、.gitignore（排除 config.yaml 与 data/output）、英文主 README（含中文速览）、`docs/compose/spec` 设计说明。

**Verification** — `engine.live_*` 单元调用（navigate/frame/click/type/key）PASS；HTTP `/api/browser/live/frame` 返回 image/jpeg PASS；`index.html` 无「鉴权并跳转」且含 addr-url/live-img PASS；`.gitignore` 覆盖敏感运行文件 PASS。外部 review 代理超时取消，改为本地验收清单核对（ACCEPTANCE_CHECKS_PASS）。

**Journey log** — Playwright sync 必须绑单线程（greenlet）；截图坐标用视口系并按显示比例缩放叠加层；`Path.name` 不能当路径牢笼要配合 `is_file()`；实时镜像用轮询 JPEG 比 CDP screencast 在 sync API 下更稳。

## [S1] Problem
页面视图区过小，无法看清目标系统并完成操作；鉴权仍依赖粘贴 Cookie，与「在浏览器里输地址、手动登录」的预期不符；项目尚未按 GitHub / MIT 开源形态组织，无法直接发布。

## [S2] Design

### 2.1 实时镜像视图
- 在「页面视图」中提供**地址栏**（URL 输入 + 前往）与**实时画面**。
- 画面由 Playwright 页视口截图以 JPEG 轮询下发（约 250–400ms/帧），前端 `<img>` 展示，形成可点选的镜像。
- 坐标约定：前端点击 `(dx, dy)` 以 `img` 显示尺寸为准，换算 `sx = dx * (viewport_w / display_w)` 后发给后端；后端 `page.mouse.click(sx, sy)`。
- 登录：用户在镜像中点击输入框，通过「输入栏」向页面焦点键入账号/密码，或点击页面上的登录按钮；**不再提供 Cookie/Token 注入为必选路径**。
- 地址栏导航、后退、刷新直接驱动同一 Playwright 页。
- 登录完成后仍执行「自动发现元素 / 建树 / 截图标注」，截图与元素 bbox 保持视口坐标对齐。

### 2.2 页面布局
- 中栏以实时画面为主，高度 `clamp(480px, 68vh, 920px)`，宽度自适应中栏全宽。
- 交互元素表与截图标注区可折叠或置于画面下方，不挤压主视图。
- ≤1280px / ≤900px 时维持可用：右栏沉底或单栏，地址栏与画面仍完整。

### 2.3 GitHub / MIT 开源形态
- 仓库根目录：`LICENSE`（MIT）、`README.md`、`.gitignore`、`requirements.txt`、`run.py`、`config.example.yaml`、`app/`、`static/`、`docs/`。
- 不提交密钥、`config.yaml`、`data/output` 运行产物。
- README 使用 GitHub 可渲染的 Markdown，含简介、安装、启动、免责声明（仅授权测试）。

## [S3] Out of Scope
- 不实现录屏回放、脚本录制导出。
- 不实现多账号并行浏览器会话。
- 不改 AI 用例生成策略本身（仍为只读查询约束）。
- 不创建远程 GitHub 仓库（本地 git 仓库形态交付，由用户推送）。

## Tasks
- [x] T1: Git 根骨架 + MIT LICENSE + .gitignore — acceptance: 仓库根含 LICENSE/.gitignore，gitignore 排除 config.yaml 与 data/output (covers: S2.3)
- [x] T2: 实时帧接口与输入接口 — acceptance: GET live/frame 返回 JPEG；POST navigate/click/input 可驱动页面 (covers: S2.1)
- [x] T3: 前端大视图 + 地址栏 + 输入栏，移除 Cookie 主入口 — acceptance: 主流程为地址栏导航与镜像内手动登录；视图高度 ≥480px (covers: S2.1; S2.2)
- [x] T4: 回归：登录后元素发现/截图对位仍可用 — acceptance: 跳转后 extract 坐标与镜像/截图框对齐 (covers: S2.1)
- [x] T5: README 按 GitHub 文档规范更新 — acceptance: 含安装启动、MIT 声明、授权测试提示 (covers: S2.3)
