from pathlib import Path

# --- CSS: twist 固定宽，同级对齐 ---
p = Path("static/css/browser.css")
t = p.read_text(encoding="utf-8")
t += """
/* 同级对齐：箭头槽位固定宽，空/有子一致 */
#tree .twist {
  width: 14px !important;
  min-width: 14px !important;
  max-width: 14px !important;
  display: inline-block;
  text-align: center;
  visibility: visible;
}
#tree .twist.empty {
  visibility: hidden;
}
#tree .tree-node {
  padding-left: 2px !important;
  gap: 2px !important;
}
#tree .tree-root > .tree-node {
  background: #eef2ff;
  font-weight: 600;
}
"""
p.write_text(t, encoding="utf-8")

# --- JS renderTree: virtual root + count on root ---
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")

old_start = t.find("  const rootNodes = state.tree.filter((n) => !n.parent_id);")
# may be after unbound html - find and replace segment from rootNodes to innerHTML assignment
idx = t.find("const rootNodes = state.tree.filter((n) => !n.parent_id);")
if idx < 0:
    print("rootNodes not found")
else:
    # find end of unboundHtml / innerHTML block
    end = t.find("const total = (state.committedCases || []).length;", idx)
    if end < 0:
        end = t.find("const el = $(\"#tree-case-total\");", idx)
    new = r'''const rootNodes = state.tree.filter((n) => !n.parent_id);
  // 未绑定用例虚拟分组
  const unbound = casesByPoint["__unbound__"] || [];
  const unboundHtml = unbound.length
    ? `
      <div class="tree-node unbound-root" data-id="__unbound__" style="height:24px;min-height:24px;max-height:24px;line-height:24px;margin:0;padding:0 4px">
        <span class="twist" data-twist="__unbound__">${
          state.collapsedIds.has("__unbound__") ? "▸" : "▾"
        }</span>
        <input type="checkbox" class="tree-check" data-id="__unbound__" ${
          state.checkedIds.has("__unbound__") ? "checked" : ""
        } />
        <span class="badge-sm unbound">未绑定</span>
        <span class="nm">未绑定用例</span>
        <span class="case-cnt">${unbound.length}</span>
      </div>
      ${
        state.collapsedIds.has("__unbound__")
          ? ""
          : `<div class="tree-children">${unbound
              .map(
                (c) => `
        <div class="tree-node tree-case" data-id="${c.id}" data-point="__unbound__" style="height:24px;min-height:24px;max-height:24px;line-height:24px;margin:0;padding:0 4px">
          <input type="checkbox" class="tree-check" data-id="${c.id}" ${
                  state.checkedIds.has(c.id) ? "checked" : ""
                } />
          <span class="badge-sm case">用例</span>
          <span class="nm">${esc(c.case_no || "")} ${esc((c.title || "").slice(0, 24))}</span>
        </div>`
              )
              .join("")}</div>`
      }`
    : "";

  const total = (state.committedCases || []).length;
  const allChecked =
    state.tree.length > 0 &&
    state.tree.every((n) => state.checkedIds.has(n.id));
  const rootCollapsed = state.collapsedIds.has("__root__");
  const bodyHtml = rootCollapsed
    ? ""
    : `<div class="tree-children">${
        rootNodes.map(nodeHtml).join("") + unboundHtml
      }</div>`;
  const htmlTree = `
    <div class="tree-root">
      <div class="tree-node" data-id="__root__" style="height:24px;min-height:24px;max-height:24px;line-height:24px;margin:0;padding:0 4px">
        <span class="twist" data-twist="__root__">${rootCollapsed ? "▸" : "▾"}</span>
        <input type="checkbox" class="tree-check" data-id="__root__" ${
          allChecked ? "checked" : ""
        } title="全选/全不选" />
        <span class="badge-sm module">根</span>
        <span class="nm">项目全部用例</span>
        <span class="case-cnt">${total} 用例</span>
      </div>
      ${bodyHtml}
    </div>`;
  if (!rootNodes.length && !unbound.length) {
    $("#tree").innerHTML = `
      <div class="tree-empty">
        <div class="tree-empty-title">尚未建立功能点树</div>
        <div class="muted">1. 在镜像中登录并「发现元素」</div>
        <div class="muted">2. 「自动建树」或使用 ＋新增 / 批量标记为…</div>
        <div class="muted">3. 结构：模块 → 一/二/三级 → 功能点（缺级用 /）</div>
      </div>`;
  } else {
    $("#tree").innerHTML = htmlTree;
  }
  const el = $("#tree-case-total");
  if (el) {
    el.textContent = total + " 用例";
    el.style.display = "none"; // 总数已挪到根节点
  }
'''
    t = t[:idx] + new + t[end:]

# bind root checkbox: check all
t = t.replace(
    """  $("#tree").querySelectorAll(".tree-check").forEach((cb) => {
    const id = cb.dataset.id;
    const owner = cb.closest(".tree-node");
    const ownerPoint = owner && owner.dataset.point;""",
    """  $("#tree").querySelectorAll(".tree-check").forEach((cb) => {
    const id = cb.dataset.id;
    const owner = cb.closest(".tree-node");
    const ownerPoint = owner && owner.dataset.point;
    if (id === "__root__") {
      cb.addEventListener("click", (ev) => ev.stopPropagation());
      cb.addEventListener("change", (ev) => {
        ev.stopPropagation();
        if (cb.checked) {
          state.tree.forEach((n) => state.checkedIds.add(n.id));
          (state.committedCases || []).forEach((c) => state.checkedIds.add(c.id));
          state.checkedIds.add("__unbound__");
        } else {
          state.checkedIds.clear();
        }
        renderTree();
      });
      return;
    }""",
)

# selectedTreeIds: if root checked, expand to all
t = t.replace(
    """function selectedTreeIds() {
  return Array.from(state.checkedIds || []);
}""",
    """function selectedTreeIds() {
  const ids = state.checkedIds || new Set();
  if (ids.has("__root__")) {
    return state.tree.map((n) => n.id);
  }
  return Array.from(ids).filter((x) => x !== "__unbound__");
}""",
)

p.write_text(t, encoding="utf-8")
print("js ok", "项目全部用例" in t, "__root__" in t)
