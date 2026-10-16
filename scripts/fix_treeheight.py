from pathlib import Path

p = Path("static/index.html")
t = p.read_text(encoding="utf-8")
t = t.replace('href="/static/css/app.css"', 'href="/static/css/app.css?v=20261016c"')
t = t.replace('href="/static/css/browser.css"', 'href="/static/css/browser.css?v=20261016c"')
t = t.replace('src="/static/js/browser.js"', 'src="/static/js/browser.js?v=20261016c"')
p.write_text(t, encoding="utf-8")

p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
STYLE = ' style="height:24px;min-height:24px;max-height:24px;line-height:24px;margin:0;padding:0 4px"'
repls = [
    (
        '<div class="tree-node ${state.selectedNodeId === n.id ? "active" : ""}" data-id="${n.id}">',
        '<div class="tree-node ${state.selectedNodeId === n.id ? "active" : ""}" data-id="${n.id}"' + STYLE + ">",
    ),
    (
        '<div class="tree-node tree-case" data-id="${c.id}" data-point="${c.point_id || ""}">',
        '<div class="tree-node tree-case" data-id="${c.id}" data-point="${c.point_id || ""}"' + STYLE + ">",
    ),
    (
        '<div class="tree-node unbound-root" data-id="__unbound__">',
        '<div class="tree-node unbound-root" data-id="__unbound__"' + STYLE + ">",
    ),
]
for a, b in repls:
    if a in t and 'height:24px' not in t[t.find(a) : t.find(a) + 200]:
        t = t.replace(a, b)
p.write_text(t, encoding="utf-8")
print("patched", t.count("height:24px"))

p = Path("static/css/browser.css")
c = p.read_text(encoding="utf-8")
c += """
/* 空节点行距统一（覆盖旧规则） */
#tree, #tree * {
  box-sizing: border-box;
}
#tree .tree-node {
  height: 24px !important;
  min-height: 24px !important;
  max-height: 24px !important;
  margin: 0 !important;
  padding: 0 4px !important;
  gap: 4px !important;
}
#tree .tree-children {
  margin: 0 0 0 8px !important;
  padding: 0 !important;
  border-left: 1px solid var(--line);
}
#tree .tree-children > .tree-node {
  margin-left: 4px !important;
}
"""
p.write_text(c, encoding="utf-8")
print("css ok")
