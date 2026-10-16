from pathlib import Path

p = Path("static/css/browser.css")
t = p.read_text(encoding="utf-8")
t += """
/* 无限下拉：页面随拖拽变高，body 全局滚动 */
html, body {
  height: auto !important;
  min-height: 100vh !important;
  overflow-x: hidden !important;
  overflow-y: visible !important;
}
.workspace, .layout-2 {
  height: auto !important;
  min-height: calc(100vh - 96px) !important;
  max-height: none !important;
  overflow: visible !important;
}
.left-stack {
  height: auto !important;
  max-height: none !important;
  overflow: visible !important;
}
#tree-panel {
  max-height: none !important;
}
#side-panel {
  max-height: none !important;
  min-height: 160px !important;
  overflow: visible !important;
}
#marked-body, #marked-list {
  max-height: none !important;
  overflow: visible !important;
  height: auto !important;
}
#cases-panel {
  max-height: none !important;
  min-height: 120px !important;
  overflow: visible !important;
}
#case-preview {
  max-height: none !important;
  overflow: visible !important;
  height: auto !important;
}
#elements-panel {
  max-height: none !important;
}
#el-body, .el-table-wrap {
  overflow: visible !important;
  max-height: none !important;
}
/* 浏览器仍限制，避免深色区无限拉高 */
#browser-col {
  max-height: 85vh !important;
}
.live-wrap, .live-stage {
  max-height: calc(85vh - 50px) !important;
}
"""
p.write_text(t, encoding="utf-8")

p = Path("static/js/browser.js")
j = p.read_text(encoding="utf-8")
j = j.replace(
    """        const move = (e) => {
          // 固定 delta，避免累加误差；限制树/已标最大高度
          const maxTree = window.innerHeight * 0.75;
          const h = Math.min(Math.max(120, h0 + (e.clientY - startY)), maxTree);
          tEl.style.flex = "none";
          tEl.style.height = h + "px";
          sEl.style.flex = "0 0 auto";
          sEl.style.height = "auto";
          sEl.style.minHeight = "160px";
          sEl.style.maxHeight = "55vh";
        };""",
    """        const move = (e) => {
          // 像素绝对高度，可超出视口；页面 body 滚
          const h = Math.max(120, h0 + (e.clientY - startY));
          tEl.style.flex = "none";
          tEl.style.height = h + "px";
          sEl.style.flex = "0 0 auto";
          sEl.style.height = "auto";
          sEl.style.minHeight = "160px";
          sEl.style.maxHeight = "none";
        };""",
)
j = j.replace(
    """          if (kind === "right-v") {
            const maxB = window.innerHeight * 0.85;
            brow.style.flex = "none";
            brow.style.height = Math.min(Math.max(160, hb + dy), maxB) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.height = "auto";
            elp.style.maxHeight = "45vh";
            cap.style.flex = "0 0 auto";
            cap.style.height = "auto";
            cap.style.maxHeight = "40vh";
          } else {
            const maxC = window.innerHeight * 0.5;
            cap.style.flex = "none";
            cap.style.height = Math.min(Math.max(100, hc - dy), maxC) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.height = "auto";
            elp.style.maxHeight = "45vh";
          }""",
    """          if (kind === "right-v") {
            const maxB = window.innerHeight * 0.85;
            brow.style.flex = "none";
            brow.style.height = Math.min(Math.max(160, hb + dy), maxB) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.height = "auto";
            elp.style.maxHeight = "none";
            cap.style.flex = "0 0 auto";
            cap.style.height = "auto";
            cap.style.maxHeight = "none";
          } else {
            // 用例台：可无限向下
            cap.style.flex = "none";
            cap.style.height = Math.max(120, hc - dy) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.height = "auto";
            elp.style.maxHeight = "none";
          }""",
)
p.write_text(j, encoding="utf-8")
print("ok")
