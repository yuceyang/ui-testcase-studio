from pathlib import Path

p = Path("static/css/browser.css")
t = p.read_text(encoding="utf-8")
t += """
/* 页面可被拖高，全局滚动条接管 */
html, body {
  height: auto !important;
  min-height: 100vh !important;
  overflow: visible !important;
}
.workspace, .layout-2 {
  height: auto !important;
  min-height: calc(100vh - 96px) !important;
  max-height: none !important;
  overflow: visible !important;
}
.left-stack {
  max-height: none !important;
  overflow: visible !important;
  height: auto !important;
}
#side-panel {
  max-height: none !important;
  min-height: 160px !important;
  overflow: hidden !important;
}
#tree-panel {
  max-height: none !important;
  min-height: 120px !important;
}
#cases-panel, #elements-panel {
  max-height: none !important;
}
#browser-col {
  min-height: 240px !important;
}
/* 拖高后内容区内部仍可滚 */
#tree, #marked-list, .el-table-wrap, #case-preview {
  overflow-y: auto !important;
}
"""
p.write_text(t, encoding="utf-8")

# JS: 拖拽取消 stackH 上限，允许超出视口
p = Path("static/js/browser.js")
j = p.read_text(encoding="utf-8")
old = """        const move = (e) => {
          const minSide = 160;
          const h = Math.min(Math.max(120, h0 + (e.clientY - startY)), stackH - minSide);
          tEl.style.flex = "none";
          tEl.style.height = h + "px";
          sEl.style.flex = "0 0 auto";
          sEl.style.height = Math.max(minSide, stackH - h) + "px";
        };"""
new = """        const move = (e) => {
          // 允许超出视口：整页出滚动条，不设 max
          const h = Math.max(120, h0 + (e.clientY - startY));
          tEl.style.flex = "none";
          tEl.style.height = h + "px";
          sEl.style.flex = "0 0 auto";
          sEl.style.height = "auto";
          sEl.style.minHeight = "160px";
        };"""
if old in j:
    j = j.replace(old, new)
    print("js clamp removed")
else:
    print("js pattern miss")
# right/cases also allow grow beyond viewport
j = j.replace(
    """          if (kind === "right-v") {
            brow.style.flex = "none";
            brow.style.height = Math.max(160, hb + dy) + "px";
            elp.style.flex = "1 1 auto";
            elp.style.height = "auto";
          } else {
            cap.style.flex = "none";
            cap.style.height = Math.max(100, hc - dy) + "px";
            elp.style.flex = "1 1 auto";
            elp.style.height = "auto";
          }""",
    """          if (kind === "right-v") {
            brow.style.flex = "none";
            brow.style.height = Math.max(160, hb + dy) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.height = "auto";
            cap.style.flex = "0 0 auto";
            cap.style.height = "auto";
          } else {
            cap.style.flex = "none";
            cap.style.height = Math.max(120, hc - dy) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.height = "auto";
          }""",
)
p.write_text(j, encoding="utf-8")
print("js done")
