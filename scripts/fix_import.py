from pathlib import Path

p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
start = t.find('$("#btn-build-cases").addEventListener')
end = t.find('$("#btn-export")', start)
if end < 0:
    end = t.find('$("#btn-go-cases")', start)
assert start > 0 and end > start

new = '''$("#btn-build-cases").addEventListener("click", async () => {
  // 只入库「用例生成台（未入库）」中的用例，禁止全树覆盖
  const pending = window._lastCases || [];
  if (!pending.length) {
    return toast("生成台没有未入库用例，请先「生成用例」", "err");
  }
  const scope = new Set(generateScopeIds());
  const toImport = pending.filter(
    (c) => !scope.size || scope.has(c.point_id) || inScope(c.point_id, generateScopeIds())
  );
  if (!toImport.length) return toast("当前范围无待入库用例", "err");

  const mode = (state.committedCases || []).length
    ? (await new Promise((res) => res(window.__importMode || "merge")))
    : "merge";
  // 默认合并入库，不覆盖其它功能点
  const key = (c) => c.point_id + "|" + (c.case_no || c.title);
  const map = new Map((state.committedCases || []).map((c) => [key(c), c]));
  for (const c of toImport) map.set(key(c), c);
  state.committedCases = Array.from(map.values());
  state.projectCases = state.committedCases;
  state.casesReady = true;
  window._lastCases = [];
  if (state.projectId) {
    await api(`/api/projects/${state.projectId}/save-from-engine`, {
      method: "POST",
      body: { cases: state.committedCases },
    }).catch((e) => toast("保存项目失败: " + e.message, "err"));
  }
  renderTree();
  $("#case-preview").innerHTML =
    `<div class="muted">已入库 ${toImport.length} 条（合并到树，未动其它功能点）。树上可查看/编辑。</div>`;
  toast(`已入库 ${toImport.length} 条`, "ok");
});

'''
t = t[:start] + new + t[end:]
p.write_text(t, encoding="utf-8")
print("build-cases rewritten")
