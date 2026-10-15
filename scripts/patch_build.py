from pathlib import Path
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
start = t.find('$("#btn-build-cases").addEventListener')
end = t.find('$("#btn-go-cases")', start)
assert start > 0 and end > start
new = '''$("#btn-build-cases").addEventListener("click", async () => {
  const has = (state.committedCases || []).length > 0;
  if (has && !confirm("已存在入库用例，重新生成将覆盖，是否继续？")) return;
  try {
    const r = await api("/api/browser/cases/from-tree", {
      method: "POST",
      body: {
        extra: { include_negative: true, include_auth_cases: true },
        sys_name: "",
        replace: true,
      },
    });
    state.sessionId = r.session_id;
    state.committedCases = r.cases || [];
    state.projectCases = state.committedCases;
    window._lastCases = [];
    if (state.projectId) {
      api(`/api/projects/${state.projectId}`, {
        method: "PUT",
        body: { cases: state.committedCases },
      }).catch(() => {});
      api(`/api/projects/${state.projectId}/save-from-engine`, {
        method: "POST",
        body: {},
      }).catch(() => {});
    }
    renderTree();
    $("#case-preview").innerHTML =
      `<div class="muted">已入库 ${state.committedCases.length} 条（覆盖旧数据），挂在功能点树下。</div>`;
    toast(`已入库 ${r.count} 条`, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("patched build-cases")
