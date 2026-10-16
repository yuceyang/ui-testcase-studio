from pathlib import Path

# JS: 空 twist 保证占位
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
t = t.replace(
    """        <span class="twist ${hasKids ? "" : "empty"}" data-twist="${n.id}" title="折叠/展开">${
          hasKids ? (collapsed ? "▸" : "▾") : ""
        }</span>""",
    """        <span class="twist ${hasKids ? "" : "empty"}" data-twist="${n.id}" title="折叠/展开">${
          hasKids ? (collapsed ? "▸" : "▾") : "&nbsp;"
        }</span>""",
)
p.write_text(t, encoding="utf-8")

# CSS
p = Path("static/css/browser.css")
c = p.read_text(encoding="utf-8")
c += """
/* 1) 同级对齐：空箭头固定占位 */
#tree .tree-node > .twist {
  flex: 0 0 16px !important;
  width: 16px !important;
  min-width: 16px !important;
  display: inline-block !important;
  overflow: hidden !important;
}
#tree .tree-node > .twist.empty {
  visibility: hidden !important;
}
#tree .tree-node > input.tree-check {
  flex: 0 0 14px !important;
  margin: 0 2px 0 0 !important;
}

/* 2) 标签禁止换行 */
#tree .badge-sm {
  white-space: nowrap !important;
  width: auto !important;
  min-width: 36px !important;
  flex: 0 0 auto !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

/* 3) 浏览器区不被挤走；元素表内滚 */
.right-stack {
  min-height: 0 !important;
}
#browser-col {
  flex: 1 1 55% !important;
  min-height: 220px !important;
  max-height: none;
  overflow: hidden !important;
}
#elements-panel {
  flex: 1 1 35% !important;
  min-height: 160px !important;
  max-height: 45vh !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
}
#elements-panel .col-head {
  flex: 0 0 auto;
}
#el-body {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
}
#el-body .el-table-wrap {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  overflow-y: auto !important;
  overflow-x: auto !important;
}
#live-stage {
  min-height: 200px !important;
}
"""
p.write_text(c, encoding="utf-8")
print("ok")
