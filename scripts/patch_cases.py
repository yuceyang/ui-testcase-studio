from pathlib import Path
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
needle = "toast(`已生成 ${r.count} 条`, \"ok\");"
if "body: { cases: state.projectCases }" in t:
    print("already patched")
else:
    t = t.replace(
        "renderTree();\n    toast(`已生成 ${r.count} 条`, \"ok\");",
        "renderTree();\n    if (state.projectId) {\n"
        "      api(`/api/projects/${state.projectId}`, {\n"
        "        method: \"PUT\",\n"
        "        body: { cases: state.projectCases },\n"
        "      }).catch(() => {});\n"
        "    }\n"
        "    toast(`已生成 ${r.count} 条`, \"ok\");",
    )
    p.write_text(t, encoding="utf-8")
    print("patched", "body: { cases: state.projectCases }" in t)
