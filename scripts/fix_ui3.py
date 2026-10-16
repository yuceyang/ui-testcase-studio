from pathlib import Path

# HTML zoom input
p = Path("static/index.html")
t = p.read_text(encoding="utf-8")
t = t.replace(
    '<span id="zoom-label">100%</span>',
    '<input id="zoom-label" class="zoom-input" value="100" style="width:52px;text-align:center" />',
)
p.write_text(t, encoding="utf-8")
print("html", "zoom-input" in t or "id=\"zoom-label\"" in t)

# CSS
p = Path("static/css/browser.css")
ct = p.read_text(encoding="utf-8")
if ".zoom-input" not in ct:
    ct += "\n.zoom-input{width:52px;text-align:center;border-radius:6px;border:1px solid #475569;background:#1b2433;color:#fff;height:28px}\n.right-stack .elements-panel,.right-stack .cases-panel{max-height:none !important;}\n.right-stack .browser-col{flex:var(--browser-flex,55) 1 0% !important;min-height:180px !important;}\n.splitter{touch-action:none;user-select:none;}\n"
    p.write_text(ct, encoding="utf-8")
print("css ok")

# routes filter
p = Path("app/routes_browser.py")
t = p.read_text(encoding="utf-8")
i = t.find('pids = set(payload.get("point_ids")')
print("routes snippet:\n", t[i : i + 500])
