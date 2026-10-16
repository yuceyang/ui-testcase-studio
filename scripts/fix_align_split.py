from pathlib import Path

# 1) twist 无字占位 + 对齐
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
# empty twist 不要输出“·”
t = t.replace(
    """          hasKids ? (collapsed ? "▸" : "▾") : "·"
        }</span>""",
    """          hasKids ? (collapsed ? "▸" : "▾") : ""
        }</span>""",
)
# 若写法不同
t = t.replace('hasKids ? (collapsed ? "▸" : "▾") : "·"', 'hasKids ? (collapsed ? "▸" : "▾") : ""')
p.write_text(t, encoding="utf-8")

# 2) CSS 对齐 + 左栏可拖
p = Path("static/css/browser.css")
c = p.read_text(encoding="utf-8")
c += """
/* 同级严格对齐 */
#tree .tree-root > .tree-children > .tree-node,
#tree .tree-children > .tree-node {
  margin-left: 0 !important;
  padding-left: 2px !important;
}
#tree .twist,
#tree .twist.empty {
  width: 16px !important;
  min-width: 16px !important;
  max-width: 16px !important;
  height: 16px !important;
  line-height: 16px !important;
  display: inline-block !important;
  text-align: center !important;
}
#tree .twist.empty { visibility: hidden; }

/* 左栏上下分栏：禁止写死高度，交给 flex + 拖拽 */
.left-stack {
  height: 100%;
  min-height: 0;
}
.left-stack .tree-panel,
.left-stack .side-panel {
  min-height: 80px;
  overflow: hidden;
}
.left-stack .tree {
  min-height: 0 !important;
  max-height: none !important;
  flex: 1;
  overflow: auto;
}
.splitter.h {
  height: 10px !important;
  margin: -5px 0 !important;
  background: transparent;
  z-index: 20;
  flex: 0 0 10px !important;
  cursor: row-resize;
  touch-action: none;
}
.splitter.h::after {
  width: 48px;
  height: 6px;
  background: #94a3b8;
}
.splitter.h:hover::after { background: var(--accent); }
"""
p.write_text(c, encoding="utf-8")
print("css/js aligned")
