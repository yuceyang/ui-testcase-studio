from pathlib import Path

p = Path("static/css/browser.css")
t = p.read_text(encoding="utf-8")
t += """
/* 防拖拽撑出巨型黑区 */
.live-wrap, .live-stage, #browser-col {
  background: #0b1220;
}
#browser-col {
  max-height: 85vh !important;
  overflow: hidden !important;
}
.live-wrap {
  max-height: calc(85vh - 48px) !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
}
.live-stage {
  flex: 1 1 auto !important;
  min-height: 0 !important;
  max-height: 100% !important;
  height: auto !important;
  overflow: auto !important;
}
#elements-panel {
  max-height: 45vh !important;
  overflow: hidden !important;
}
#cases-panel {
  max-height: 40vh !important;
  overflow: hidden !important;
}
#side-panel {
  max-height: 55vh !important;
}
#tree-panel {
  max-height: calc(100vh - 200px) !important;
}
.workspace, .layout-2 {
  overflow: visible;
  min-height: calc(100vh - 96px);
  height: auto;
}
"""
p.write_text(t, encoding="utf-8")

# JS drag: use absolute height not repeated add; cap sizes
p = Path("static/js/browser.js")
j = p.read_text(encoding="utf-8")
j = j.replace(
    """        const move = (e) => {
          // 允许超出视口：整页出滚动条，不设 max
          const h = Math.max(120, h0 + (e.clientY - startY));
          tEl.style.flex = "none";
          tEl.style.height = h + "px";
          sEl.style.flex = "0 0 auto";
          sEl.style.height = "auto";
          sEl.style.minHeight = "160px";
        };""",
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
            cap.style.height = Math.max(120, hc - dy) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.height = "auto";
          }""",
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
)
p.write_text(j, encoding="utf-8")
print("patched")
