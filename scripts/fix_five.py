from pathlib import Path

# --- HTML: primary button + empty tree hint already in js ---
p = Path("static/index.html")
t = p.read_text(encoding="utf-8")
t = t.replace(
    '<button class="mini" id="btn-bulk-mark-as">批量标记为…</button>',
    '<button class="mini primary" id="btn-bulk-mark-as">批量标记为…</button>',
)
# 说明文案
t = t.replace(
    "将按类型为每个元素建立树节点；名称用元素文本（可自动）",
    "将按类型为每个元素建立树节点；名称用元素文本；默认类型=功能点",
)
p.write_text(t, encoding="utf-8")

# --- JS ---
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")

# 4) openMarkAs default type = point
t = t.replace(
    "$(\"#mka-type\").value = cur && cur.node_type !== \"module\" ? \"point\" : \"module\";",
    "$(\"#mka-type\").value = \"point\";",
)

# 5) fillParentOptions hierarchical indent
old_fill = t[t.find("function fillParentOptions") : t.find("function openMarkAs")]
new_fill = '''function fillParentOptions(sel, excludeId, selectedParent) {
  const skip = excludeId ? descendantsOf(excludeId) : new Set();
  const rows = state.tree.filter((n) => !skip.has(n.id));
  // 按层级缩进，父子关系一目了然
  const byParent = {};
  for (const n of rows) {
    const p = n.parent_id || "";
    (byParent[p] = byParent[p] || []).push(n);
  }
  const typeShort = {
    module: "模块",
    title1: "一级",
    title2: "二级",
    title3: "三级",
    point: "功能点",
    case: "用例",
  };
  const ordered = [];
  const walk = (pid, depth) => {
    for (const n of byParent[pid] || []) {
      ordered.push({ n, depth });
      walk(n.id, depth + 1);
    }
  };
  walk("", 0);
  // 父不在列表里的孤儿也收进来
  for (const n of rows) {
    if (!ordered.some((x) => x.n.id === n.id)) ordered.push({ n, depth: 0 });
  }
  sel.innerHTML =
    `<option value="">（顶层）</option>` +
    ordered
      .map(({ n, depth }) => {
        const indent = "　".repeat(Math.min(depth, 6));
        const label = `${indent}${n.name} (${typeShort[n.node_type] || n.node_type})`;
        const selAttr = n.id === selectedParent ? " selected" : "";
        return `<option value="${n.id}"${selAttr}>${esc(label)}</option>`;
      })
      .join("");
}

'''
if "function fillParentOptions" in t:
    start = t.find("function fillParentOptions")
    end = t.find("function openMarkAs")
    t = t[:start] + new_fill + t[end:]

# 2) 新入库默认勾选
t = t.replace(
    """    state.committedCases = Array.from(map.values());
    state.projectCases = state.committedCases;
    state.casesReady = true;""",
    """    state.committedCases = Array.from(map.values());
    state.projectCases = state.committedCases;
    state.casesReady = true;
    // 新入库节点/用例默认选中
    for (const c of toImport) {
      if (c.id) state.checkedIds.add(c.id);
      if (c.point_id) state.checkedIds.add(c.point_id);
    }""",
)

# 1) 空树骨架
t = t.replace(
    """  $("#tree").innerHTML =
    (rootNodes.map(nodeHtml).join("") + unboundHtml) ||
    `<div class="muted" style="padding:12px">空树。「自动建树」或右键镜像添加。</div>`;""",
    """  const htmlTree = rootNodes.map(nodeHtml).join("") + unboundHtml;
  if (!htmlTree.trim()) {
    $("#tree").innerHTML = `
      <div class="tree-empty">
        <div class="tree-empty-title">尚未建立功能点树</div>
        <div class="muted">1. 在镜像中登录并「发现元素」</div>
        <div class="muted">2. 「自动建树」或使用 ＋新增 / 批量标记为…</div>
        <div class="muted">3. 结构：模块 → 一/二/三级 → 功能点（缺级用 /）</div>
      </div>`;
  } else {
    $("#tree").innerHTML = htmlTree;
  }""",
)

p.write_text(t, encoding="utf-8")

# CSS
p = Path("static/css/browser.css")
c = p.read_text(encoding="utf-8")
if ".tree-empty" not in c:
    c += """
.tree-empty {
  padding: 18px 12px;
  border: 1px dashed var(--line);
  border-radius: 8px;
  margin: 8px;
}
.tree-empty-title { font-weight: 600; margin-bottom: 8px; }
.mini.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.mini.primary:hover { background: var(--accent-hover); }
"""
    p.write_text(c, encoding="utf-8")

print("done")
