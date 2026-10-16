from pathlib import Path
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")

# 1) add generateScopeIds after selectedTreeIds
if "function generateScopeIds" not in t:
    t = t.replace(
        "function selectedTreeIds() {\n  return Array.from(state.checkedIds || []);\n}",
        """function selectedTreeIds() {
  return Array.from(state.checkedIds || []);
}

/** 生成用例范围：勾选优先，否则当前单击选中的节点 */
function generateScopeIds() {
  const checked = selectedTreeIds();
  if (checked.length) return checked;
  if (state.selectedNodeId) return [state.selectedNodeId];
  return [];
}""",
        1,
    )

# 2) rewrite btn-go-cases handler
start = t.find('$("#btn-go-cases").addEventListener')
end = t.find('$("#btn-clear-cases")', start)
if start > 0 and end > start:
    t = t[: start] + '''$("#btn-go-cases").addEventListener("click", async () => {
  // 生成用例：只写入「用例生成台（未入库）」，禁止入库/保存
  const ids = generateScopeIds();
  if (!ids.length) return toast("请先选中或勾选功能点树节点", "err");
  try {
    const r = await api("/api/browser/tree/preview-cases", {
      method: "POST",
      body: {
        include_negative: true,
        include_auth_cases: true,
        point_ids: ids,
        sys_name: "",
      },
    });
    window._lastCases = r.cases || [];
    renderPreview({ cases: window._lastCases, mode: "preview" });
    toast(`已生成 ${r.count} 条未入库用例，请确认后点「生成入库」`, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

''' + t[end:]

p.write_text(t, encoding="utf-8")
print("scope", "generateScopeIds" in t)
print("go-cases preview", t[t.find("btn-go-cases"):t.find("btn-go-cases") + 200].count("preview-cases") or "see block")
