from pathlib import Path

p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
t = t.replace(
    """function applyZoom() {
  const img = $("#live-img");
  if (!img) return;
  img.style.width = 100 * liveZoom + "%";""",
    """function applyZoom() {
  const img = $("#live-img");
  if (!img) return;
  const frame = $("#live-frame");
  // zoom 不改布局流，配合 overflow 避免黑框
  if (frame) {
    frame.style.zoom = String(liveZoom);
  }
  img.style.width = "100%";
  img.style.zoom = String(liveZoom);""",
)
t = t.replace(
    "liveZoom = Math.min(Math.max(z, 0.5), 3);",
    "liveZoom = Math.min(Math.max(z, 0.5), 2);",
)
t = t.replace(
    'toast("缩放请输入 50–300");',
    'toast("缩放请输入 50–200");',
)
t = t.replace(
    "if (!isNaN(v) && v >= 50 && v <= 300) setZoom(v / 100);",
    "if (!isNaN(v) && v >= 50 && v <= 200) setZoom(v / 100);",
)
# ensure initZoom runs after applyZoom on load
if "applyZoom();" not in t.split("function initZoom")[-1][:200]:
    t = t.replace(
        '$("#btn-zoom-reset") && $("#btn-zoom-reset").addEventListener("click", () => setZoom(1));',
        '$("#btn-zoom-reset") && $("#btn-zoom-reset").addEventListener("click", () => setZoom(1));\n  applyZoom();',
    )
p.write_text(t, encoding="utf-8")

p = Path("static/css/browser.css")
c = p.read_text(encoding="utf-8")
c += """
/* 缩放：允许镜像按 zoom 缩放，但不撑破容器黑框 */
#live-frame {
  transform-origin: 0 0;
}
#live-frame img {
  width: 100% !important;
  height: auto !important;
}
.live-stage {
  overflow: auto !important;
}
"""
p.write_text(c, encoding="utf-8")
print("zoom patched")
