---
feature: projects-live-ux
status: designed
updated: 2026-10-15
branch: main
commits: 
---

# 项目管理 · 截图库 · 浏览器化实时镜像

## Report

## [S1] Problem
刷新页面后树、已标、用例与登录态全部丢失；截图无库可查、无大图详情；实时镜像初始化是破图黑框，且仍依赖「键入/Enter」侧栏，不像真浏览器；重启后识别框残留；品牌栏挤占高度，视图仍偏小。

## [S2] Design

### 2.1 项目（按系统持久化）
- 每个项目目录：`data/projects/<project_id>/`
  - `project.json`：名称、base_url、功能点树、已标元素、备注、用例索引
  - `storage_state.json`：Playwright storageState（Cookie/localStorage），登录一次后保存
  - `shots/`：该项目截图
- API：`GET/POST /api/projects`，`GET/PUT/DELETE /api/projects/{id}`，`POST /api/projects/{id}/load`（恢复树/已标/截图索引并可选注入 storageState）。
- UI：顶栏「项目」选择/新建/保存；切换项目即换上下文；刷新后默认加载最近项目。

### 2.2 截图库
- 右栏「截图库」：列表含 `id / tag / 时间 / 存储路径`；点击缩略或「详情」开大图。
- 功能点节点绑定 `screenshot_id`；点该节点 →「截图详情」显示关联大图与路径。

### 2.3 实时镜像空态与布局
- 未启动：深色占位「等待启动浏览器」，禁止 `<img>` 裂图。
- 去掉页头 logo/产品名；URL/后退/刷新放进镜像区顶部浏览器壳（类 Chrome）。
- 镜像高度 `calc(100vh - 左右工具)` 级别，主操作区尽量大。

### 2.4 镜像内直接操作（对齐真浏览器）
- 移除「键入/Enter/Tab/清空」侧栏按钮。
- 点击镜像聚焦后直接键入：keydown/keyup/keypress → Playwright keyboard；滚轮 → mouse.wheel。
- 保留地址栏前往；登录、点菜单、填表单均在镜像内完成。

### 2.5 叠框管理
- `start`/重启时清空页面上 `state.elements` 叠框与临时 overlay。
- 识别框右键：取消该框（并可选 unmark）；空白处右键：菜单「添加功能点到当前节点」等。

## [S3] Out of Scope
- 多用户/权限；远程同步；录屏。
- 自动持久化每一次点击操作脚本。

## Tasks
- [ ] T1: 项目存储与 API（project.json + storage_state） — acceptance: 新建/保存/加载后树与已标仍在；reload 项目可恢复 (covers: S2.1)
- [ ] T2: 截图库列表+路径+功能点详情 — acceptance: 列表可见路径；节点详情能开大图 (covers: S2.2)
- [ ] T3: 镜像空态+浏览器壳+放大布局、去 logo — acceptance: 无裂图；URL 在镜像壳内；高度显著增大 (covers: S2.3)
- [ ] T4: 镜像键盘/滚轮直操，移除键入栏 — acceptance: 聚焦后可打字登录，无多余按钮 (covers: S2.4)
- [ ] T5: 启动清空叠框，右键取消/添加 — acceptance: 重启无残留框；右键可取消 (covers: S2.5)
