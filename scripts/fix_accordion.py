from pathlib import Path

p = Path("static/css/browser.css")
t = p.read_text(encoding="utf-8")
if "is-collapsed" not in t:
    t += """
/* 折叠手风琴：只留标题栏，空间让给浏览器 */
#elements-panel.is-collapsed,
#cases-panel.is-collapsed,
#side-panel.is-collapsed {
  flex: 0 0 auto !important;
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  overflow: visible !important;
}
#elements-panel.is-collapsed .el-table-wrap,
#elements-panel.is-collapsed #el-body,
#cases-panel.is-collapsed .case-preview,
#cases-panel.is-collapsed #cases-body,
#side-panel.is-collapsed .collapse-body,
#side-panel.is-collapsed .hint-line {
  display: none !important;
}
#browser-col {
  flex: 1 1 auto !important;
  min-height: 280px !important;
}
.right-stack .browser-col { flex: 1 1 auto !important; }
.splitter.h.hidden-split { display: none !important; }
"""
    p.write_text(t, encoding="utf-8")
    print("css ok")

p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
old = """function toggleCollapse(id) {
  const body = document.getElementById(id);
  if (!body) return;
  const on = body.classList.toggle("collapsed");"""
new = """function toggleCollapse(id) {
  const body = document.getElementById(id);
  if (!body) return;
  const on = body.classList.toggle("collapsed");
  const panel = body.closest(".col");
  if (panel) {
    panel.classList.toggle("is-collapsed", on);
    const sp = panel.previousElementSibling;
    if (sp && sp.classList && sp.classList.contains("splitter")) {
      sp.classList.toggle("hidden-split", on);
    }
  }
  window.dispatchEvent(new Event("resize"));"""
if old in t and "is-collapsed" not in t[t.find("function toggleCollapse") : t.find("function toggleCollapse") + 600]:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("js ok")
else:
    print("js skip", old in t)
