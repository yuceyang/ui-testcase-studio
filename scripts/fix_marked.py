from pathlib import Path
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
start = t.find("async function loadMarked()")
end = t.find("function ", start + 20)
import re
m = re.search(r"\n(async function |function |/\* )", t[start + 20:])
end = start + 20 + m.start() + 1 if m else start + 900
new = '''async function loadMarked() {
  try {
    const r = await api("/api/browser/marked");
    const all = r.elements || [];
    state.marked = all;
    // 与选中节点联动
    const n = state.tree.find((x) => x.id === state.selectedNodeId);
    let list = all;
    if (n && (n.element_ids || []).length) {
      const ids = new Set(n.element_ids);
      list = all.filter((e) => ids.has(e.id));
    } else if (n) {
      list = [];
    }
    $("#marked-count").textContent = String(list.length);
    $("#marked-list").innerHTML =
      list
        .map(
          (e) => `
      <div class="marked-item" data-id="${e.id}">
        <div><b>${esc(e.name || e.text || e.kind)}</b> <span class="k">${esc(e.kind)}</span></div>
        <div class="k">${esc(e.selector || "")}</div>
        <div class="row">
          <button class="mini" data-act="un" data-id="${e.id}">取消</button>
        </div>
      </div>`
        )
        .join("") || `<div class="muted">当前节点无关联标记</div>`;
    $("#marked-list").querySelectorAll("button[data-act=un]").forEach((b) => {
      b.addEventListener("click", () => unmarkElement(b.dataset.id));
    });
    drawGhost();
  } catch {
    /* ignore */
  }
}

'''
t = t[:start] + new + t[end:]
# selectNode also loadMarked
t = t.replace(
    """  document.querySelectorAll(".shot-rect").forEach((r) => {
    r.classList.toggle("strong", ids.has(r.dataset.elId));
    r.classList.toggle("hover", ids.has(r.dataset.elId));
  });
  if (n.screenshot_id) {""",
    """  document.querySelectorAll(".shot-rect").forEach((r) => {
    r.classList.toggle("strong", ids.has(r.dataset.elId));
    r.classList.toggle("hover", ids.has(r.dataset.elId));
  });
  loadMarked();
  if (n.screenshot_id) {""",
)
p.write_text(t, encoding="utf-8")
print("loadMarked patched", "当前节点无关联标记" in t, "loadMarked();" in t[t.find("function selectNode"):t.find("function selectNode")+800])
