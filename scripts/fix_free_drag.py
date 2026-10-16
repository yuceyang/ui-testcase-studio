from pathlib import Path

p = Path("static/css/browser.css")
t = p.read_text(encoding="utf-8")
t += """
/* 自由拖拽：页面整体撑高 + 全局滚动 */
html, body {
  min-height: 100vh !important;
  height: auto !important;
  overflow-y: visible !important;
  overflow-x: hidden !important;
}
.workspace, .layout-2 {
  height: auto !important;
  min-height: calc(100vh - 96px) !important;
  overflow: visible !important;
}
.right-stack {
  overflow: visible !important;
}
#browser-col {
  max-height: none !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
}
.live-wrap {
  flex: 1 1 auto;
  min-height: 0;
  max-height: none !important;
  overflow: hidden;
}
.live-stage {
  height: 100% !important;
  min-height: 240px !important;
  max-height: none !important;
  overflow: auto !important;
}
#live-img {
  width: 100% !important;
  height: auto !important;
  max-height: none !important;
  object-fit: contain;
  background: #0b1220;
}
#elements-panel, #cases-panel {
  max-height: none !important;
  overflow: visible !important;
}
#el-body, .el-table-wrap, #case-preview, #cases-body {
  overflow: visible !important;
  max-height: none !important;
  height: auto !important;
}
"""
p.write_text(t, encoding="utf-8")

p = Path("static/js/browser.js")
j = p.read_text(encoding="utf-8")
# right-v: allow browser grow to 220vh; elements auto
j = j.replace(
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
    """          if (kind === "right-v") {
            // 浏览器预览：可拉到约 2.2 屏（近全屏/更长）
            const maxB = window.innerHeight * 2.2;
            const minB = 220;
            brow.style.flex = "none";
            brow.style.height = Math.min(Math.max(minB, hb + dy), maxB) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.height = "auto";
            cap.style.flex = "0 0 auto";
            cap.style.height = "auto";
          } else {
            // 元素 / 用例：绝对像素，无上限
            cap.style.flex = "none";
            cap.style.height = Math.max(120, hc - dy) + "px";
            elp.style.flex = "0 0 auto";
            elp.style.height = "auto";
          }""",
)
p.write_text(j, encoding="utf-8")
print("ok")
