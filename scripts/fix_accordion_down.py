from pathlib import Path

p = Path("static/css/browser.css")
t = p.read_text(encoding="utf-8")
t += """
/* ===== 手风琴向下扩展（防黑框铁律） ===== */
html, body {
  height: auto !important;
  min-height: 100vh !important;
  max-height: none !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
}
.workspace, .layout-2 {
  height: auto !important;
  min-height: 100vh !important;
  max-height: none !important;
  overflow: visible !important;
}

/* 浏览器区：绝不被压缩，也不参与无限拉伸 */
#browser-col {
  flex: 0 0 auto !important;
  flex-shrink: 0 !important;
  min-height: 600px !important;
  max-height: 800px !important;
  height: 600px !important;
  overflow: hidden !important;
  background: #fff !important;
}
.live-wrap, .live-stage {
  height: 100% !important;
  min-height: 0 !important;
  max-height: 100% !important;
  overflow: auto !important;
  background: #fff !important;
}
#live-frame, #live-frame img, .live-stage img {
  display: block !important;
  width: 100% !important;
  height: auto !important;
  max-height: 100% !important;
  max-width: 100% !important;
  border: none !important;
}

/* 下方面板：高度由拖拽/内容决定，页面被撑长 */
#elements-panel, #cases-panel {
  flex: 0 0 auto !important;
  flex-shrink: 0 !important;
  height: auto !important;
  min-height: 80px !important;
  max-height: none !important;
  overflow: hidden !important;
}
#el-body .el-table-wrap, #cases-body, #case-preview {
  overflow-y: auto !important;
  min-height: 0 !important;
  max-height: none !important;
}
"""
p.write_text(t, encoding="utf-8")

# JS: drag only changes bottom panel px height; never browser height
p = Path("static/js/browser.js")
j = p.read_text(encoding="utf-8")
import re
# replace right-v move to only grow elements/cases downward (page taller)
j = re.sub(
    r'if \(kind === "right-v"\) \{[\s\S]*?\n          \} else \{[\s\S]*?\n          \}',
    '''if (kind === "right-v") {
            // 只增加元素/用例像素高度，页面变长；浏览器不动
            const maxE = window.innerHeight * 1.5;
            const hE = Math.min(Math.max(120, he + dy), maxE);
            elp.style.flex = "0 0 auto";
            elp.style.height = hE + "px";
            brow.style.height = "";
            brow.style.flex = "0 0 auto";
            brow.style.minHeight = "600px";
            brow.style.maxHeight = "800px";
            cap.style.flex = "0 0 auto";
            cap.style.height = cap.style.height || "auto";
          } else {
            // cases-v：只改用例台高度
            const maxC = window.innerHeight * 1.2;
            cap.style.flex = "0 0 auto";
            cap.style.height = Math.min(Math.max(100, hc - dy), maxC) + "px";
          }''',
    j,
    count=1,
)
p.write_text(j, encoding="utf-8")
print("ok")
