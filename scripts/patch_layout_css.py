from pathlib import Path

p = Path("static/css/browser.css")
t = p.read_text(encoding="utf-8")
start = t.find(".workspace {")
end = t.find("/* 浏览器壳 */")
assert start > 0 and end > start
new = """
.workspace {
  padding: 8px 10px 12px;
  max-width: 100%;
  margin: 0;
}
/* 两列布局：左=树+侧栏，右=浏览器+交互元素 */
.layout-2 {
  display: grid;
  grid-template-columns: var(--left-w, 320px) 8px minmax(0, 1fr);
  gap: 0;
  height: calc(100vh - 92px);
  min-height: 0;
}
.col-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}
.left-stack .tree-panel {
  flex: var(--tree-flex, 52) 1 0%;
  min-height: 140px;
  overflow: hidden;
}
.left-stack .side-panel {
  flex: var(--side-flex, 48) 1 0%;
  min-height: 180px;
  overflow: auto;
}
.right-stack .browser-col {
  flex: var(--browser-flex, 62) 1 0%;
  min-height: 240px;
}
.right-stack .elements-panel {
  flex: var(--elem-flex, 38) 1 0%;
  min-height: 140px;
  display: flex;
  flex-direction: column;
}
.right-stack .el-table-wrap {
  flex: 1;
  max-height: none;
  min-height: 0;
  overflow: auto;
}

/* 拖动条 */
.splitter {
  background: transparent;
  position: relative;
  z-index: 5;
  flex: 0 0 8px;
}
.splitter.h {
  cursor: row-resize;
  height: 8px;
  margin: -4px 0;
}
.splitter.v {
  cursor: col-resize;
  height: 100%;
}
.splitter::after {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  background: #cbd5e1;
  border-radius: 2px;
}
.splitter.h::after { width: 36px; height: 4px; }
.splitter.v::after { width: 4px; height: 36px; }
.splitter:hover::after,
.splitter.active::after { background: var(--accent); }

.browser-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--muted);
  background: #f8fafc;
}
.browser-placeholder.hidden { display: none; }

.popout-browser {
  position: fixed;
  right: 24px;
  top: 100px;
  width: min(960px, 92vw);
  height: min(720px, 82vh);
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, .28);
  display: flex;
  flex-direction: column;
  z-index: 40;
  overflow: hidden;
}
.popout-browser.hidden { display: none; }
.popout-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #f1f5f9;
  border-bottom: 1px solid var(--line);
  cursor: move;
  user-select: none;
}
.popout-bar b { margin-right: auto; }
.popout-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.popout-body .browser-col {
  flex: 1;
  min-height: 0;
  border: none;
}
.popout-resize {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 18px;
  height: 18px;
  cursor: nwse-resize;
  background: linear-gradient(135deg, transparent 50%, #94a3b8 50%);
  border-bottom-right-radius: 12px;
}

.zoom-box {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: #e5e7eb;
  font-size: 12px;
}
#zoom-label { min-width: 42px; text-align: center; opacity: .9; }

"""
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("css patched", p.stat().st_size)
