from pathlib import Path
t = Path("static/index.html").read_text(encoding="utf-8")
i = t.find('id="marked-body"')
print(t[i : i + 350])

p = Path("static/css/browser.css")
p.write_text(
    p.read_text(encoding="utf-8")
    + """
/* ===== 全局滚动条统一 ===== */
.scroll-y {
  overflow-y: auto !important;
  overflow-x: hidden !important;
  min-height: 0 !important;
}
#marked-body {
  display: block !important;
  flex: 1 1 auto !important;
  min-height: 0 !important;
  max-height: none !important;
  height: auto !important;
  overflow: hidden !important;
}
#marked-list {
  display: block !important;
  width: 100% !important;
  height: 100% !important;
  max-height: none !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  min-height: 0 !important;
  box-sizing: border-box;
}
#side-panel {
  overflow: hidden !important;
}
#side-panel .collapse-body:not(.collapsed) {
  min-height: 0 !important;
}
#side-panel .collapse-body.collapsed {
  display: none !important;
}
/* 拖拽后保证子项重新计算高度 */
.splitter.h.active ~ * {
  will-change: height;
}
::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
::-webkit-scrollbar-thumb {
  background: #c1c7d0;
  border-radius: 6px;
  border: 2px solid transparent;
  background-clip: content-box;
}
::-webkit-scrollbar-thumb:hover { background: #94a3b8; background-clip: content-box; }
::-webkit-scrollbar-track { background: transparent; }
""",
    encoding="utf-8",
)
print("css patched")
