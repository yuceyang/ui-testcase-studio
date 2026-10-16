from pathlib import Path

p = Path("static/css/browser.css")
t = p.read_text(encoding="utf-8")
t += """
/* flex 内滚动：min-height:0 + overflow */
.left-stack,
.right-stack,
.col {
  min-height: 0;
}
#tree-panel, #side-panel, #elements-panel, #cases-panel, #browser-col {
  min-height: 0 !important;
}
#tree {
  overflow: auto !important;
  height: 100% !important;
  min-height: 0 !important;
  max-height: none !important;
  flex: 1 1 auto !important;
}
#marked-body, #case-preview, .el-table-wrap, .shot-list, .marked-list {
  overflow: auto !important;
  min-height: 0 !important;
}
#case-preview {
  height: 100%;
  max-height: none;
}
.side-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.side-panel .collapse-body {
  min-height: 0;
}
.side-panel .collapse-body.grow,
#marked-body {
  overflow: auto;
}
.elements-panel, .cases-panel {
  display: flex !important;
  flex-direction: column !important;
  overflow: hidden !important;
}
.elements-panel .el-table-wrap {
  flex: 1 1 auto !important;
  max-height: none !important;
}
.cases-panel .case-preview {
  flex: 1 1 auto !important;
  max-height: none !important;
}

/* 统一水平拖条 */
.splitter.h {
  flex: 0 0 12px !important;
  height: 12px !important;
  margin: -6px 0 !important;
  cursor: row-resize !important;
  z-index: 30 !important;
  touch-action: none !important;
  background: transparent;
}
.splitter.h::after {
  content: "" !important;
  display: block;
  width: 56px;
  height: 6px;
  margin: 3px auto 0;
  border-radius: 4px;
  background: #94a3b8;
}
.splitter.h:hover::after,
.splitter.h.active::after { background: var(--accent); }

/* 树层级缩进：模块0 / 目录+20 / 功能点+20 / 用例+20 */
#tree .tree-children {
  margin-left: 18px !important;
  padding-left: 4px !important;
  border-left: 1px solid #e5e7eb;
}
#tree .tree-node {
  height: 26px !important;
  min-height: 26px !important;
  max-height: 26px !important;
  line-height: 26px !important;
  font-size: 12.5px;
}
#tree .tree-node .badge-sm {
  width: 36px;
  text-align: center;
  flex: 0 0 36px;
}
#tree .tree-node .nm {
  font-size: 12.5px;
}
#tree .tree-case .nm { color: #475569; font-size: 12px; }
#tree .twist {
  width: 14px !important;
  min-width: 14px !important;
}
"""
p.write_text(t, encoding="utf-8")
print("css ok")
