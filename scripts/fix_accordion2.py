from pathlib import Path

# HTML: maximize button on chrome
p = Path("static/index.html")
t = p.read_text(encoding="utf-8")
if "btn-max-browser" not in t:
    t = t.replace(
        '<button id="btn-popout" class="chrome-btn" title="弹出">⧉</button>',
        '<button id="btn-popout" class="chrome-btn" title="弹出">⧉</button>\n          <button id="btn-max-browser" class="chrome-btn" title="最大化浏览器">⛶</button>',
    )
p.write_text(t, encoding="utf-8")

# CSS accordion
p = Path("static/css/browser.css")
c = p.read_text(encoding="utf-8")
c += """
/* 手风琴：浏览器吃满剩余高度 */
#browser-col {
  flex: 1 1 auto !important;
  min-height: 200px !important;
  max-height: none !important;
  overflow: hidden !important;
}
#elements-panel {
  flex: 0 0 auto !important;
  min-height: 100px !important;
  max-height: 50vh !important;
  overflow: hidden !important;
}
#cases-panel {
  flex: 0 0 auto !important;
  min-height: 80px !important;
  max-height: 40vh !important;
  overflow: hidden !important;
}
#elements-panel.is-min, #cases-panel.is-min {
  height: 36px !important;
  min-height: 36px !important;
  max-height: 36px !important;
}
#elements-panel.is-min #el-body,
#cases-panel.is-min #cases-body { display: none !important; }
#el-body, .el-table-wrap, #cases-body, #case-preview {
  min-height: 0 !important;
  overflow-y: auto !important;
  padding-top: 0 !important;
}
.el-table-wrap { max-height: none !important; }
.col-head { padding: 6px 10px !important; }
.status-box, .shot-list, .marked-list { padding: 6px !important; }
"""
p.write_text(c, encoding="utf-8")

# JS maximize
p = Path("static/js/browser.js")
j = p.read_text(encoding="utf-8")
if "btn-max-browser" not in j:
    j += """
$("#btn-max-browser") &&
  $("#btn-max-browser").addEventListener("click", () => {
    const el = $("#elements-panel");
    const cap = $("#cases-panel");
    const brow = $("#browser-col");
    const minned = el.classList.contains("is-min");
    if (!minned) {
      el.classList.add("is-min");
      cap.classList.add("is-min");
      brow.style.flex = "1 1 auto";
      brow.style.minHeight = "calc(100vh - 160px)";
      toast("浏览器已最大化");
    } else {
      el.classList.remove("is-min");
      cap.classList.remove("is-min");
      brow.style.minHeight = "200px";
      toast("已恢复下方面板");
    }
    window.dispatchEvent(new Event("resize"));
  });
"""
p.write_text(j, encoding="utf-8")
print("done")
