from pathlib import Path
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
start = t.find("  function nodeHtml(n) {")
# end at closing of nodeHtml: find "  }\n\n  const rootNodes"
end = t.find("  const rootNodes", start)
assert start > 0 and end > start
new = r'''  function nodeHtml(n) {
    const kids = byParent[n.id] || [];
    const cs = casesByPoint[n.id] || [];
    const st = n.status || "pending";
    const stCls = st === "pass" ? "st-pass" : st === "fail" ? "st-fail" : "";
    const cnt = caseCountForNode(n.id);
    const hasKids = kids.length > 0 || cs.length > 0;
    const collapsed = state.collapsedIds.has(n.id);
    const caseHtml = collapsed
      ? ""
      : cs
          .map(
            (c) => `
      <div class="tree-node tree-case" data-id="${c.id}" data-point="${c.point_id || ""}">
        <input type="checkbox" class="tree-check" data-id="${c.id}" ${
              state.checkedIds.has(c.id) ? "checked" : ""
            } />
        <span class="badge-sm case">用例</span>
        <span class="nm">${esc(c.case_no || "")} ${esc((c.title || "").slice(0, 24))}</span>
      </div>`
          )
          .join("");
    const childHtml = collapsed ? "" : kids.map(nodeHtml).join("");
    return `
      <div class="tree-node ${state.selectedNodeId === n.id ? "active" : ""}" data-id="${n.id}">
        <span class="twist ${hasKids ? "" : "empty"}" data-twist="${n.id}" title="折叠/展开">${
          hasKids ? (collapsed ? "▸" : "▾") : "·"
        }</span>
        <input type="checkbox" class="tree-check" data-id="${n.id}" ${
          state.checkedIds.has(n.id) ? "checked" : ""
        } />
        <span class="badge-sm ${n.node_type}">${typeLabel[n.node_type] || n.node_type}</span>
        <span class="nm">${esc(n.name)}</span>
        ${cnt ? `<span class="case-cnt" title="测试用例数">${cnt}</span>` : ""}
        <span class="${stCls}">${st === "pass" ? "✓" : st === "fail" ? "✗" : ""}</span>
      </div>
      ${
        caseHtml || childHtml
          ? `<div class="tree-children">${caseHtml}${childHtml}</div>`
          : ""
      }`;
  }

'''
t = t[:start] + new + t[end:]
# add collapsedIds to state if missing
if "collapsedIds" not in t:
    t = t.replace("checkedIds: new Set(),", "checkedIds: new Set(),\n  collapsedIds: new Set(),")
else:
    t = t.replace("checkedIds: new Set(),", "checkedIds: new Set(),\n  collapsedIds: new Set(),", 1) if "collapsedIds: new Set()" not in t else t
# bind twist clicks after tree render - append to tree check binder
old = '''  $("#tree").querySelectorAll(".tree-check").forEach((cb) => {'''
new_bind = '''  $("#tree").querySelectorAll("[data-twist]").forEach((tw) => {
    tw.addEventListener("click", (ev) => {
      ev.stopPropagation();
      const id = tw.dataset.twist;
      if (state.collapsedIds.has(id)) state.collapsedIds.delete(id);
      else state.collapsedIds.add(id);
      renderTree();
    });
  });
  $("#tree").querySelectorAll(".tree-check").forEach((cb) => {'''
if "[data-twist]" not in t:
    t = t.replace(old, new_bind, 1)
p.write_text(t, encoding="utf-8")
print("nodeHtml patched", t.count("data-twist"), "collapsedIds", "collapsedIds" in t)
