from pathlib import Path

# HTML: buttons
p = Path("static/index.html")
t = p.read_text(encoding="utf-8")
t = t.replace(
    '<button class="mini primary" id="btn-bulk-mark-as">批量标记为…</button>',
    '<button class="mini primary" id="btn-bulk-mark-as">批量标记为…</button>\n            <button class="mini danger" id="btn-clear-elements">清空</button>',
)
t = t.replace(
    '''          <b>已标功能点</b>
          <span class="muted" id="marked-count">0</span>
          <button class="mini collapse-toggle" data-collapse="marked-body">折叠</button>''',
    '''          <b>已标功能点</b>
          <span class="muted" id="marked-count">0</span>
          <button class="mini danger" id="btn-clear-marks2">清空</button>
          <button class="mini collapse-toggle" data-collapse="marked-body">折叠</button>''',
)
p.write_text(t, encoding="utf-8")
print("html", "btn-clear-elements" in t, "btn-clear-marks2" in t)

# CSS: left stack flexible
p = Path("static/css/browser.css")
c = p.read_text(encoding="utf-8")
c += """
/* 左栏不锁死，仅限最高 */
.workspace, .layout-2 {
  height: auto !important;
  min-height: calc(100vh - 96px) !important;
  overflow: visible !important;
}
.left-stack {
  height: auto !important;
  max-height: calc(100vh - 120px) !important;
  overflow: hidden !important;
}
.collapse-toggle { pointer-events: auto; }
.col-head.collapsible { cursor: default; }
"""
p.write_text(c, encoding="utf-8")

# JS
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")

# fix collapse: only toggle when clicking toggle button or head but not inputs; stopPropagation
t = t.replace(
    """function initCollapsible() {
  $$(".collapse-toggle, .col-head.collapsible").forEach((el) => {
    el.addEventListener("click", (ev) => {
      if (ev.target.closest("button") && !ev.target.classList.contains("collapse-toggle")) {
        // 标题栏内其它按钮不折叠
        if (!ev.target.classList.contains("collapse-toggle")) return;
      }
      const id = el.dataset.collapse;
      if (!id) return;
      const body = document.getElementById(id);
      if (!body) return;
      const on = body.classList.toggle("collapsed");
      $$(`[data-collapse="${id}"]`).forEach((b) => {
        if (b.classList.contains("collapse-toggle")) b.textContent = on ? "展开" : "折叠";
      });
    });
  });
}""",
    """function toggleCollapse(id) {
  const body = document.getElementById(id);
  if (!body) return;
  const on = body.classList.toggle("collapsed");
  $$(`[data-collapse="${id}"]`).forEach((b) => {
    if (b.classList.contains("collapse-toggle")) b.textContent = on ? "展开" : "折叠";
  });
  // 折叠状态写入 layout，避免数据刷新丢
  const st = JSON.parse(localStorage.getItem("qts_collapse") || "{}");
  st[id] = on;
  localStorage.setItem("qts_collapse", JSON.stringify(st));
}

function initCollapsible() {
  const saved = JSON.parse(localStorage.getItem("qts_collapse") || "{}");
  Object.keys(saved).forEach((id) => {
    const body = document.getElementById(id);
    if (body && saved[id]) {
      body.classList.add("collapsed");
      $$(`[data-collapse="${id}"]`).forEach((b) => {
        if (b.classList.contains("collapse-toggle")) b.textContent = "展开";
      });
    }
  });
  $$(".collapse-toggle, .col-head.collapsible").forEach((el) => {
    el.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      // 标题内其它按钮不触发
      if (
        ev.target.closest("button") &&
        !ev.target.classList.contains("collapse-toggle") &&
        !el.classList.contains("collapse-toggle")
      ) {
        return;
      }
      const id = el.dataset.collapse;
      if (!id) return;
      toggleCollapse(id);
    });
  });
}""",
)

# clear elements
t = t.replace(
    '$("#btn-extract").addEventListener("click", async () => {',
    '''$("#btn-clear-elements") &&
  $("#btn-clear-elements").addEventListener("click", async () => {
    if (!confirm("确认清空「交互元素」列表？（不删除已建树节点）")) return;
    state.elements = [];
    renderElements();
    drawGhost();
    toast("交互元素已清空", "ok");
  });

$("#btn-clear-marks2") &&
  $("#btn-clear-marks2").addEventListener("click", async () => {
    if (!confirm("确认取消本页全部标记？（与右键菜单一致）")) return;
    await clearPageMarks();
  });

$("#btn-extract").addEventListener("click", async () => {''',
)

# clearPageMarks may confirm internally - strip double confirm if exists
t = t.replace(
    'if (!confirm("取消本页全部标记（不影响树上已建节点结构）？")) return;',
    "",
)

p.write_text(t, encoding="utf-8")
print("js ok", "btn-clear-elements" in t, "toggleCollapse" in t)
