from pathlib import Path
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
start = t.find("async function loadProject()")
assert start > 0
end = t.find("function ", start + 10)
# include until next top-level function after loadProject's closing
# find "\nfunction " or "\nasync function " after start
import re
m = re.search(r"\n(function |async function |/\* )", t[start + 20:])
end = start + 20 + m.start() + 1 if m else start + 800
new = '''function rebindCasesToTree() {
  const treeIds = new Set(state.tree.map((n) => n.id));
  const points = state.tree.filter((n) => n.node_type === "point" || n.node_type === "case");
  const orphans = [];
  for (const c of state.committedCases || []) {
    if (c.point_id && treeIds.has(c.point_id)) continue;
    let hit = points.find((p) => p.name && (c.title || "").includes(p.name));
    if (!hit && c.module_cat) {
      hit = state.tree.find((n) => n.node_type === "module" && n.name === c.module_cat);
    }
    if (hit) c.point_id = hit.id;
    else orphans.push(c);
  }
  if (orphans.length && state.tree.length) {
    const root = state.tree.find((n) => n.node_type === "point") || state.tree[0];
    for (const c of orphans) c.point_id = root.id;
  }
}

async function loadProject() {
  if (!state.projectId) return toast("未选项目", "err");
  try {
    const r = await api(`/api/projects/${state.projectId}/load`, {
      method: "POST",
      body: { restore_login: true },
    });
    state.tree = r.project.tree || [];
    state.marked = r.project.marked_elements || [];
    state.shots = r.project.shots || [];
    state.projectCases = r.project.cases || [];
    state.committedCases = r.project.cases || [];
    window._lastCases = [];
    rebindCasesToTree();
    renderTree();
    await loadMarked();
    $("#case-preview").innerHTML =
      `<div class="muted">项目已加载：已入库 ${state.committedCases.length} 条（见功能点树）。</div>`;
    await loadShotList();
    toast(`已加载 ${r.project.name}（用例 ${state.committedCases.length}）`, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
}

'''
t = t[:start] + new + t[end:]
p.write_text(t, encoding="utf-8")
print("loadProject replaced", "rebindCasesToTree" in t)
