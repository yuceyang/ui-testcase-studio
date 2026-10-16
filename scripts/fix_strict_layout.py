from pathlib import Path

# --- CSS 布局回归稳健版 ---
p = Path("static/css/browser.css")
t = p.read_text(encoding="utf-8")
t += """
/* ===== 稳健视口布局：禁止整页撑爆 / 黑框 ===== */
html, body {
  height: 100% !important;
  min-height: 0 !important;
  max-height: 100vh !important;
  overflow: hidden !important;
}
.workspace, .layout-2 {
  height: calc(100vh - 96px) !important;
  min-height: 0 !important;
  max-height: calc(100vh - 96px) !important;
  overflow: hidden !important;
}
.left-stack, .right-stack {
  height: 100% !important;
  min-height: 0 !important;
  overflow: hidden !important;
}
#browser-col {
  flex: 1 1 0% !important;
  min-height: 180px !important;
  max-height: none !important;
  overflow: hidden !important;
  background: #fff !important;
}
.live-wrap {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  max-height: 100% !important;
  overflow: hidden !important;
  background: #fff !important;
}
.live-stage {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  height: auto !important;
  max-height: 100% !important;
  overflow: auto !important;
  background: #fff !important;
}
.live-stage img, #live-frame, #live-frame img {
  max-width: 100% !important;
  max-height: 100% !important;
  width: auto !important;
  height: auto !important;
}
#elements-panel, #cases-panel, #tree-panel, #side-panel {
  min-height: 0 !important;
  overflow: hidden !important;
}
#el-body .el-table-wrap, #case-preview, #tree, #marked-list {
  overflow-y: auto !important;
  min-height: 0 !important;
  max-height: 100% !important;
}
#elements-panel { flex: 1 1 0% !important; max-height: 45vh !important; }
#cases-panel { flex: 1 1 0% !important; max-height: 35vh !important; }
#side-panel { flex: 0 0 auto !important; max-height: 55% !important; min-height: 160px !important; }
#tree-panel { flex: 1 1 0% !important; min-height: 120px !important; max-height: calc(100% - 160px) !important; }
"""
p.write_text(t, encoding="utf-8")
print("css ok")

# --- JS：拖拽用相对起点，夹紧到视口内 ---
p = Path("static/js/browser.js")
j = p.read_text(encoding="utf-8")
# 简化 initSplitters 关键：right-v / cases-v / left-v 夹紧
import re
j = re.sub(
    r"const move = \(e\) => \{\n          // 允许超出视口[\s\S]*?\n        \};",
    """const move = (e) => {
          const maxH = window.innerHeight * 0.75;
          const h = Math.min(Math.max(120, h0 + (e.clientY - startY)), maxH);
          tEl.style.flex = "none";
          tEl.style.height = h + "px";
          sEl.style.flex = "0 0 auto";
          sEl.style.minHeight = "160px";
          sEl.style.maxHeight = "55%";
          sEl.style.height = "auto";
        };""",
    j,
    count=1,
)
j = j.replace(
    """          if (kind === "right-v") {
            brow.style.flex = "none";
            brow.style.height = Math.max(160, hb + dy) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.height = "auto";
            cap.style.flex = "0 0 auto";
            cap.style.height = "auto";
          } else {
            cap.style.flex = "none";
            cap.style.height = Math.max(100, hc - dy) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.height = "auto";
          }""",
    """          if (kind === "right-v") {
            const maxB = window.innerHeight - 120;
            brow.style.flex = "none";
            brow.style.height = Math.min(Math.max(180, hb + dy), maxB) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.maxHeight = "45vh";
            elp.style.height = "auto";
            cap.style.flex = "0 0 auto";
            cap.style.maxHeight = "35vh";
            cap.style.height = "auto";
          } else {
            const maxC = window.innerHeight * 0.4;
            cap.style.flex = "none";
            cap.style.height = Math.min(Math.max(100, hc - dy), maxC) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.maxHeight = "45vh";
            elp.style.height = "auto";
          }""",
)
p.write_text(j, encoding="utf-8")
print("js ok")
