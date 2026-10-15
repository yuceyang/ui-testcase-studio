from pathlib import Path
import re
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
# after API success mutations that call loadTree/save already
# hook scheduleAutoSave into loadTree callers used for mutations by wrapping loadTree
if "async function loadTree()" in t and "scheduleAutoSave" not in t[t.find("async function loadTree()"):t.find("async function loadTree()")+300]:
    t = t.replace(
        """async function loadTree() {
  try {
    const r = await api("/api/browser/tree");
    state.tree = r.tree || [];
    renderTree();
  } catch {
    /* ignore */
  }
}""",
        """async function loadTree(opts = {}) {
  try {
    const r = await api("/api/browser/tree");
    state.tree = r.tree || [];
    renderTree();
    if (opts.save) scheduleAutoSave();
  } catch {
    /* ignore */
  }
}""",
    )
# mutate paths: append scheduleAutoSave after loadTree() in handlers
# easier: in loadTree default save true for this app
t = t.replace("if (opts.save) scheduleAutoSave();", "scheduleAutoSave();")
p.write_text(t, encoding="utf-8")
print("loadTree autosave", "scheduleAutoSave();" in t)
