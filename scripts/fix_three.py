from pathlib import Path

# --- 1) backend: strict scope filter ---
p = Path("app/routes_browser.py")
t = p.read_text(encoding="utf-8")
old = '''    pids = set(payload.get("point_ids") or [])
    if pids:
        from .browser.tree import path_of

        def _hit(c):
            if c.point_id in pids:
                return True
            return any(n.get("id") in pids for n in path_of(c.point_id, tree))

        cases = [c for c in cases if _hit(c)]
'''
new = '''    pids = set(payload.get("point_ids") or [])
    if pids:
        from .browser.tree import path_of, descendants_of_ids

        scope = descendants_of_ids(pids, tree) | pids
        cases = [c for c in cases if c.point_id in scope]
'''
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t, encoding="utf-8")
    print("routes filter ok")
else:
    print("routes filter skip")

# --- 2) tree helper descendants_of_ids ---
p = Path("app/browser/tree.py")
t = p.read_text(encoding="utf-8")
if "def descendants_of_ids" not in t:
    t += '''

def descendants_of_ids(ids: set, tree: list[dict]) -> set:
    """返回 ids 的全部子孙节点 id（不含自身，调用方自行并集）。"""
    idset = set(ids)
    changed = True
    while changed:
        changed = False
        for n in tree:
            if n.get("parent_id") in idset and n.get("id") not in idset:
                idset.add(n["id"])
                changed = True
    return idset - set(ids)
'''
    p.write_text(t, encoding="utf-8")
    print("tree helper ok")
else:
    print("tree helper exists")

# --- 3) frontend generate strict filter + zoom input + free splitters ---
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")

# zoom input: replace zoom-label span usage
t = t.replace(
    '<span id="zoom-label">100%</span>',
    '<input id="zoom-label" class="zoom-input" value="100" style="width:52px;text-align:center" title="缩放百分比，可输入" />',
)
# if html only, patch index separately

t = t.replace(
    '''function applyZoom() {
  const img = $("#live-img");
  if (!img) return;
  img.style.width = 100 * liveZoom + "%";
  $("#zoom-label").textContent = Math.round(liveZoom * 100) + "%";
  drawGhost();
}''',
    '''function applyZoom() {
  const img = $("#live-img");
  if (!img) return;
  img.style.width = 100 * liveZoom + "%";
  const box = $("#zoom-label");
  if (box) {
    if (document.activeElement !== box) {
      box.value = String(Math.round(liveZoom * 100));
    }
  }
  drawGhost();
}''',
)

if "zoom-label" in t and "change" not in t[t.find("function initZoom"):t.find("function initZoom") + 900]:
    t = t.replace(
        '''function initZoom() {
  $("#btn-zoom-in") && $("#btn-zoom-in").addEventListener("click", () => setZoom(liveZoom + 0.1));
  $("#btn-zoom-out") && $("#btn-zoom-out").addEventListener("click", () => setZoom(liveZoom - 0.1));
  $("#btn-zoom-reset") && $("#btn-zoom-reset").addEventListener("click", () => setZoom(1));''',
        '''function initZoom() {
  $("#btn-zoom-in") && $("#btn-zoom-in").addEventListener("click", () => setZoom(liveZoom + 0.01));
  $("#btn-zoom-out") && $("#btn-zoom-out").addEventListener("click", () => setZoom(liveZoom - 0.01));
  $("#btn-zoom-reset") && $("#btn-zoom-reset").addEventListener("click", () => setZoom(1));
  const zbox = $("#zoom-label");
  if (zbox) {
    zbox.addEventListener("change", () => {
      const v = parseFloat(String(zbox.value).replace("%", ""));
      if (!isNaN(v) && v >= 50 && v <= 300) setZoom(v / 100);
      else {
        toast("缩放请输入 50–300");
        zbox.value = String(Math.round(liveZoom * 100));
      }
    });
    zbox.addEventListener("keydown", (e) => {
      if (e.key === "Enter") zbox.blur();
    });
  }''',
    )

# strict client filter after preview
t = t.replace(
    '''    window._lastCases = r.cases || [];
    renderPreview({ cases: window._lastCases, mode: "preview" });
    toast(`已生成 ${r.count} 条未入库用例，请确认后点「生成入库」`, "ok");''',
    '''    const scope = new Set(ids);
    const all = r.cases || [];
    // 双保险：仅保留 scope（含子树）内用例
    window._lastCases = all.filter((c) => scope.has(c.point_id) || inScope(c.point_id, ids));
    renderPreview({ cases: window._lastCases, mode: "preview" });
    toast(`已生成 ${window._lastCases.length} 条未入库用例，请确认后点「生成入库」`, "ok");''',
)

# helper inScope after generateScopeIds
if "function inScope" not in t:
    t = t.replace(
        "function generateScopeIds() {",
        '''function inScope(pointId, rootIds) {
  if (!pointId) return false;
  const roots = new Set(rootIds);
  const ids = new Set([pointId]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const n of state.tree) {
      if (ids.has(n.parent_id) && !ids.has(n.id)) {
        ids.add(n.id);
        changed = true;
      }
    }
  }
  // pointId 在某个勾选子树内
  for (const root of roots) {
    const sub = new Set([root]);
    let ch = true;
    while (ch) {
      ch = false;
      for (const n of state.tree) {
        if (sub.has(n.parent_id) && !sub.has(n.id)) {
          sub.add(n.id);
          ch = true;
        }
      }
    }
    if (sub.has(pointId)) return true;
  }
  return false;
}

function generateScopeIds() {''',
        1,
    )

p.write_text(t, encoding="utf-8")
print("js ok")
