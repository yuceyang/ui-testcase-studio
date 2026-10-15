/* 内置浏览器工作区交互 */
"use strict";

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const state = {
  elements: [],
  tree: [],
  marked: [],
  shots: [],
  selectedNodeId: null,
  selectedShotId: "",
  sessionId: "",
  frameTree: [],
};

function toast(msg, type = "") {
  const el = $("#toast");
  el.textContent = msg;
  el.className = "toast " + type;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add("hidden"), 3000);
}

async function api(path, options = {}) {
  const opt = {
    headers: { "Content-Type": "application/json" },
    ...options,
  };
  if (opt.body && typeof opt.body !== "string") opt.body = JSON.stringify(opt.body);
  const res = await fetch(path, opt);
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text }; }
  if (!res.ok) {
    const msg = data.detail || data.message || res.statusText;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

/* ================= 浏览器 / 实时镜像 ================= */
let liveTimer = null;
let liveViewport = { width: 1680, height: 1050 };

function startLive() {
  stopLive();
  liveTimer = setInterval(refreshLiveFrame, 320);
}
function stopLive() {
  if (liveTimer) clearInterval(liveTimer);
  liveTimer = null;
}

async function refreshLiveFrame() {
  try {
    const res = await fetch("/api/browser/live/frame", { cache: "no-store" });
    if (!res.ok) return;
    const blob = await res.blob();
    const img = $("#live-img");
    const old = img.src;
    img.src = URL.createObjectURL(blob);
    if (old && old.startsWith("blob:")) URL.revokeObjectURL(old);
    // 记录显示尺寸，供点击换算
  } catch {
    /* 未启动时忽略 */
  }
}

async function loadLiveMeta() {
  try {
    const m = await api("/api/browser/live/meta");
    if (m.viewport) liveViewport = m.viewport;
    if (m.title != null) $("#page-title").textContent = m.title || m.url || "";
    if (m.url) $("#addr-url").value = m.url;
  } catch {
    /* ignore */
  }
}

$("#btn-start").addEventListener("click", async () => {
  try {
    await api("/api/browser/start", { method: "POST", body: { headless: true } });
    startLive();
    await loadLiveMeta();
    toast("浏览器已启动，请在地址栏输入网址并手动登录", "ok");
    refreshStatus();
  } catch (e) {
    toast(e.message, "err");
  }
});

async function refreshStatus() {
  try {
    const c = await api("/api/browser/current");
    const el = $("#br-status");
    if (!c.running) {
      el.textContent = "浏览器未启动";
      el.className = "badge";
    } else {
      el.textContent = `运行中 · ${c.title || c.url || ""}`.slice(0, 48);
      el.className = "badge ok";
    }
  } catch {
    $("#br-status").textContent = "状态未知";
    $("#br-status").className = "badge err";
  }
}

async function ensureBrowser() {
  const c = await api("/api/browser/current");
  if (!c.running) {
    await api("/api/browser/start", { method: "POST", body: { headless: true } });
    startLive();
  }
}

async function goAddress() {
  const url = $("#addr-url").value.trim();
  if (!url) return toast("请输入地址", "err");
  try {
    await ensureBrowser();
    const r = await api("/api/browser/live/navigate", { method: "POST", body: { url } });
    $("#page-title").textContent = r.title || r.url || "";
    // 换页后旧元素坐标失效，清空叠框，待重新发现
    state.elements = [];
    state.marked = state.marked.filter((m) => false); // 标记过期，需重新点选
    renderElements();
    await loadMarked();
    drawGhost();
    await loadLiveMeta();
    await refreshLiveFrame();
    toast("已导航，可手动登录；请重新「自动发现元素」", "ok");
    refreshStatus();
  } catch (e) {
    toast(e.message, "err");
  }
}
$("#btn-go").addEventListener("click", goAddress);
$("#addr-url").addEventListener("keydown", (e) => {
  if (e.key === "Enter") goAddress();
});

$("#btn-back").addEventListener("click", async () => {
  try {
    await api("/api/browser/back", { method: "POST", body: {} });
    await loadLiveMeta();
  } catch (e) {
    toast(e.message, "err");
  }
});
$("#btn-reload").addEventListener("click", async () => {
  try {
    await api("/api/browser/reload", { method: "POST", body: {} });
  } catch (e) {
    toast(e.message, "err");
  }
});

// 镜像点击 → 视口坐标
$("#live-img").addEventListener("click", async (ev) => {
  const img = $("#live-img");
  if (!img.clientWidth) return;
  const rect = img.getBoundingClientRect();
  const scale = liveViewport.width / img.clientWidth;
  const x = (ev.clientX - rect.left) * scale;
  const y = (ev.clientY - rect.top) * scale;
  const cross = $("#live-cross");
  cross.style.display = "block";
  cross.style.left = ev.clientX - rect.left + img.offsetLeft + "px";
  cross.style.top = ev.clientY - rect.top + img.offsetTop + "px";
  try {
    const r = await api("/api/browser/live/click", { method: "POST", body: { x, y } });
    if (r.title != null) $("#page-title").textContent = r.title || r.url || "";
  } catch (e) {
    toast(e.message, "err");
  }
});

// 键入到焦点（登录表单）
async function sendType() {
  const text = $("#type-input").value;
  try {
    await api("/api/browser/live/type", { method: "POST", body: { text } });
    toast("已键入", "ok");
  } catch (e) {
    toast(e.message, "err");
  }
}
$("#btn-send-type").addEventListener("click", sendType);
$("#type-input").addEventListener("keydown", async (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    await sendType();
    await api("/api/browser/live/key", { method: "POST", body: { key: "Enter" } }).catch(() => {});
  }
});
$("#btn-send-enter").addEventListener("click", async () => {
  try {
    const r = await api("/api/browser/live/key", { method: "POST", body: { key: "Enter" } });
    if (r.title != null) $("#page-title").textContent = r.title || "";
  } catch (e) {
    toast(e.message, "err");
  }
});
$("#btn-send-tab").addEventListener("click", async () => {
  try {
    await api("/api/browser/live/key", { method: "POST", body: { key: "Tab" } });
  } catch (e) {
    toast(e.message, "err");
  }
});
$("#btn-clear-input").addEventListener("click", async () => {
  try {
    await api("/api/browser/live/clear", { method: "POST", body: {} });
  } catch (e) {
    toast(e.message, "err");
  }
});

$("#auto-shot").addEventListener("change", async (e) => {
  try {
    await api("/api/browser/screenshot/auto", { method: "POST", body: { enabled: e.target.checked } });
    toast(e.target.checked ? "已开启自动截图" : "已关闭自动截图");
  } catch (err) {
    toast(err.message, "err");
  }
});

$("#btn-shot").addEventListener("click", async () => {
  try {
    const r = await api("/api/browser/screenshot", { method: "POST", body: { tag: "manual" } });
    await loadShots();
    toast("已截图 " + (r.file || ""), "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

/* ================= 截图（仅记录） ================= */
async function loadShots() {
  try {
    const r = await api("/api/browser/shots");
    state.shots = r.shots || [];
  } catch {
    /* ignore */
  }
}

/* 元素框叠在实时镜像上，保证点选对应 */
function drawGhost() {
  const img = $("#live-img");
  if (!img || !img.clientWidth) return;
  let ghost = $("#live-overlay");
  if (!ghost) {
    ghost = document.createElement("div");
    ghost.id = "live-overlay";
    ghost.className = "shot-overlay";
    img.parentElement.appendChild(ghost);
  }
  ghost.innerHTML = "";
  const scale = img.clientWidth / (liveViewport.width || img.naturalWidth || 1);
  const markedIds = new Set(state.marked.map((e) => e.id));
  const drawOne = (el, strong) => {
    const b = el.bbox;
    if (!b || !b.w || b.w < 2) return;
    const rect = document.createElement("div");
    rect.className = "shot-rect" + (strong ? " strong" : "");
    rect.dataset.elId = el.id;
    rect.style.left = b.x * scale + "px";
    rect.style.top = b.y * scale + "px";
    rect.style.width = b.w * scale + "px";
    rect.style.height = b.h * scale + "px";
    rect.title = el.name || el.text || el.selector || "";
    ghost.appendChild(rect);
  };
  for (const el of state.elements) {
    if (!markedIds.has(el.id)) drawOne(el, false);
  }
  for (const el of state.marked) drawOne(el, true);
}

$("#live-img").addEventListener("load", drawGhost);
window.addEventListener("resize", drawGhost);

// 点表格行 → 镜像上高亮对应框
function highlightEl(id) {
  document.querySelectorAll(".shot-rect").forEach((r) => {
    r.classList.toggle("hover", r.dataset.elId === id);
  });
}

/* ================= 元素发现 ================= */
$("#btn-extract").addEventListener("click", async () => {
  try {
    const r = await api("/api/browser/extract", { method: "POST", body: {} });
    state.elements = r.elements || [];
    state.frameTree = r.frame_tree || [];
    $("#page-title").textContent = r.title || r.url || "";
    renderFrameOptions();
    renderElements();
    await loadShots();
    drawGhost();
    toast(`发现 ${state.elements.length} 个交互元素（含 ${r.counts?.frames || 1} 个 frame）`, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

function renderFrameOptions() {
  const sel = $("#el-frame");
  const paths = new Set([""]);
  const walk = (nodes) => {
    for (const n of nodes || []) {
      paths.add(n.path);
      walk(n.children);
    }
  };
  walk(state.frameTree);
  sel.innerHTML = `<option value="">全部 frame</option>` +
    Array.from(paths).filter(Boolean).map((p) => `<option value="${esc(p)}">${esc(p)}</option>`).join("");
}

function renderElements() {
  const tb = $("#el-table tbody");
  const q = ($("#el-filter").value || "").toLowerCase();
  const kind = $("#el-kind").value;
  const frame = $("#el-frame").value;

  const rows = state.elements.filter((e) => {
    if (kind && e.kind !== kind) return false;
    if (frame && e.frame_path !== frame) return false;
    if (!q) return true;
    return `${e.name} ${e.text} ${e.selector} ${e.tag}`.toLowerCase().includes(q);
  });

  $("#el-count").textContent = `${state.elements.length} 个元素，显示 ${rows.length}`;
  tb.innerHTML = rows
    .map(
      (e) => `
    <tr data-id="${e.id}">
      <td><input type="checkbox" class="el-check" data-id="${e.id}" ${e.marked ? "checked" : ""} /></td>
      <td><span class="tag">${esc(e.kind_label || e.kind)}</span></td>
      <td>
        <div class="name">${esc(e.name || e.text || "—")}</div>
        <div class="url">${esc((e.attrs && (e.attrs.placeholder || e.attrs.type)) || "")}</div>
      </td>
      <td class="url">${esc(e.selector)}</td>
      <td class="url">${esc(e.frame_path || "main")}</td>
      <td>
        <button class="link-btn" data-act="mark" data-id="${e.id}">标功能点</button>
      </td>
    </tr>`
    )
    .join("");

  tb.querySelectorAll("button[data-act=mark]").forEach((btn) => {
    btn.addEventListener("click", () => markElement(btn.dataset.id));
  });
  tb.querySelectorAll(".el-check").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (cb.checked) markElement(cb.dataset.id);
      else unmarkElement(cb.dataset.id);
    });
  });
  // 表格悬停 → 镜像框高亮
  tb.querySelectorAll("tr[data-id]").forEach((tr) => {
    tr.addEventListener("mouseenter", () => highlightEl(tr.dataset.id));
    tr.addEventListener("mouseleave", () => highlightEl(""));
  });
}

$("#el-filter").addEventListener("input", renderElements);
$("#el-kind").addEventListener("change", renderElements);
$("#el-frame").addEventListener("change", renderElements);

async function markElement(elId) {
  const el = state.elements.find((x) => x.id === elId);
  if (!el) return;
  try {
    const r = await api("/api/browser/mark", { method: "POST", body: { element: el } });
    const idx = state.elements.findIndex((x) => x.id === elId);
    if (idx >= 0) state.elements[idx] = { ...state.elements[idx], ...r.element, marked: true };
    await loadMarked();
    drawGhost();
    // 若有选中树节点，把元素挂上去
    if (state.selectedNodeId) {
      await attachElToNode(state.selectedNodeId, r.element.id);
    }
    toast("已标为功能点", "ok");
  } catch (e) {
    toast(e.message, "err");
  }
}

async function unmarkElement(elId) {
  try {
    await api(`/api/browser/unmark/${elId}`, { method: "POST", body: {} });
    await loadMarked();
  } catch (e) {
    toast(e.message, "err");
  }
}

async function loadMarked() {
  try {
    const r = await api("/api/browser/marked");
    state.marked = r.elements || [];
    $("#marked-count").textContent = String(state.marked.length);
    $("#marked-list").innerHTML = state.marked
      .map(
        (e) => `
      <div class="marked-item" data-id="${e.id}">
        <div><b>${esc(e.name || e.text || e.kind)}</b> <span class="k">${esc(e.kind)}</span></div>
        <div class="k">${esc(e.selector)}</div>
        <div class="k">${esc(e.frame_path || "main")}</div>
        <div class="row">
          <input data-id="${e.id}" class="mk-note" placeholder="备注" value="${esc(e.note || "")}" />
          <button class="mini" data-act="un" data-id="${e.id}">取消</button>
        </div>
      </div>`
      )
      .join("") || `<div class="muted">尚未标记元素。点击中间表格「标功能点」。</div>`;

    $("#marked-list").querySelectorAll("button[data-act=un]").forEach((b) => {
      b.addEventListener("click", () => unmarkElement(b.dataset.id));
    });
    $("#marked-list").querySelectorAll(".mk-note").forEach((inp) => {
      inp.addEventListener("change", async () => {
        await api(`/api/browser/marked/${inp.dataset.id}`, {
          method: "PUT",
          body: { note: inp.value },
        });
      });
    });
    drawGhost();
  } catch {
    /* ignore */
  }
}

/* ================= 树 ================= */
function renderTree() {
  const byParent = {};
  for (const n of state.tree) {
    const p = n.parent_id || "";
    (byParent[p] = byParent[p] || []).push(n);
  }
  const typeLabel = {
    module: "模块",
    title1: "一级",
    title2: "二级",
    title3: "三级",
    point: "功能点",
    case: "验证",
  };
  const typeCls = {
    module: "module",
    title1: "",
    title2: "",
    title3: "",
    point: "point",
    case: "case",
  };

  function nodeHtml(n) {
    const kids = byParent[n.id] || [];
    const st = n.status || "pending";
    const stCls = st === "pass" ? "st-pass" : st === "fail" ? "st-fail" : "";
    return `
      <div class="tree-node ${state.selectedNodeId === n.id ? "active" : ""}" data-id="${n.id}">
        <span class="badge-sm ${typeCls[n.node_type] || ""}">${typeLabel[n.node_type] || n.node_type}</span>
        <span class="nm">${esc(n.name)}</span>
        <span class="${stCls}">${st === "pass" ? "✓" : st === "fail" ? "✗" : ""}</span>
      </div>
      ${kids.length ? `<div class="tree-children">${kids.map(nodeHtml).join("")}</div>` : ""}`;
  }

  const roots = byParent[""] || byParent[null] || state.tree.filter((n) => !n.parent_id);
  // 保持已有 parentId 为 null 的根
  const rootNodes = state.tree.filter((n) => !n.parent_id);
  $("#tree").innerHTML = rootNodes.map(nodeHtml).join("") || `<div class="muted" style="padding:12px">空树。点「自动建功能点树」或手动添加。</div>`;

  $("#tree").querySelectorAll(".tree-node").forEach((el) => {
    el.addEventListener("click", () => selectNode(el.dataset.id));
    el.addEventListener("dblclick", async () => {
      const n = state.tree.find((x) => x.id === el.dataset.id);
      const name = prompt("节点名称", n.name);
      if (name != null && name.trim()) {
        await api(`/api/browser/tree/node/${n.id}`, { method: "PUT", body: { name: name.trim() } });
        await loadTree();
      }
    });
  });
}

async function loadTree() {
  try {
    const r = await api("/api/browser/tree");
    state.tree = r.tree || [];
    renderTree();
  } catch {
    /* ignore */
  }
}

function selectNode(id) {
  state.selectedNodeId = id;
  const n = state.tree.find((x) => x.id === id);
  renderTree();
  if (!n) return;
  const names = pathNames(id);
  $("#sel-node-info").textContent = `${names} · 状态 ${n.status || "pending"}`;
  $("#node-annotation").value = n.annotation || "";
}

function pathNames(id) {
  const by = Object.fromEntries(state.tree.map((n) => [n.id, n]));
  const chain = [];
  let cur = by[id];
  let g = 0;
  while (cur && g < 20) {
    chain.unshift(cur.name);
    cur = by[cur.parent_id];
    g++;
  }
  return chain.join(" / ");
}

async function attachElToNode(nodeId, elId) {
  try {
    const n = state.tree.find((x) => x.id === nodeId);
    if (!n) return;
    const ids = new Set(n.element_ids || []);
    ids.add(elId);
    await api(`/api/browser/tree/node/${nodeId}`, {
      method: "PUT",
      body: { element_ids: Array.from(ids) },
    });
    await loadTree();
    selectNode(nodeId);
  } catch {
    /* ignore */
  }
}

$("#btn-add-module").addEventListener("click", async () => {
  const name = prompt("模块名称", "测试模块");
  if (!name) return;
  await api("/api/browser/tree/node", { method: "POST", body: { name, node_type: "module" } });
  await loadTree();
});

$("#btn-add-title").addEventListener("click", async () => {
  const name = prompt("标题名称（一级/二级/三级请选节点后改类型，这里默认二级）");
  if (!name) return;
  await api("/api/browser/tree/node", {
    method: "POST",
    body: { name, node_type: "title2", parent_id: state.selectedNodeId },
  });
  await loadTree();
});

$("#btn-add-point").addEventListener("click", async () => {
  const name = prompt("功能点名称", "查询功能");
  if (!name) return;
  await api("/api/browser/tree/node", {
    method: "POST",
    body: { name, node_type: "point", parent_id: state.selectedNodeId },
  });
  await loadTree();
});

$("#btn-auto-tree").addEventListener("click", async () => {
  const module_name = prompt("模块名称", "核心业务") || "核心业务";
  try {
    const r = await api("/api/browser/discover-tree", { method: "POST", body: { module_name } });
    state.tree = r.tree || [];
    state.elements = r.elements || state.elements;
    state.frameTree = r.frame_tree || state.frameTree;
    renderTree();
    renderFrameOptions();
    renderElements();
    toast(`自动建树完成：${state.tree.length} 节点`, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

/* 判定 */
async function setStatus(st) {
  if (!state.selectedNodeId) return toast("请先选中树节点", "err");
  try {
    await api(`/api/browser/tree/node/${state.selectedNodeId}/status`, {
      method: "POST",
      body: { status: st, annotation: $("#node-annotation").value },
    });
    await loadTree();
    selectNode(state.selectedNodeId);
    toast("已更新判定: " + st, st === "fail" ? "err" : "ok");
  } catch (e) {
    toast(e.message, "err");
  }
}
$("#btn-pass").addEventListener("click", () => setStatus("pass"));
$("#btn-fail").addEventListener("click", () => setStatus("fail"));
$("#btn-pending").addEventListener("click", () => setStatus("pending"));
$("#btn-ignore").addEventListener("click", () => setStatus("ignored"));

$("#node-annotation").addEventListener("change", async () => {
  if (!state.selectedNodeId) return;
  await api(`/api/browser/tree/node/${state.selectedNodeId}`, {
    method: "PUT",
    body: { annotation: $("#node-annotation").value },
  });
});

/* ================= 用例 ================= */
$("#btn-preview").addEventListener("click", async () => {
  try {
    const r = await api("/api/browser/tree/preview-cases", {
      method: "POST",
      body: { include_negative: true, include_auth_cases: true },
    });
    renderPreview(r);
  } catch (e) {
    toast(e.message, "err");
  }
});

function renderPreview(r) {
  const titles = r.titles || [];
  $("#case-preview").innerHTML =
    titles.map((t) => `<div class="t"><b>${esc(t.title)}</b><br><span class="muted">${esc(t.module)} · ${t.priority}</span></div>`).join("") ||
    "暂无用例";
  toast(`预览 ${r.count || titles.length} 条`, "ok");
}

$("#btn-build-cases").addEventListener("click", async () => {
  try {
    const r = await api("/api/browser/cases/from-tree", {
      method: "POST",
      body: {
        extra: { include_negative: true, include_auth_cases: true, max_cases_per_point: 8 },
      },
    });
    state.sessionId = r.session_id;
    renderPreview({ titles: r.cases.map((c) => ({ title: c.title, module: c.module, priority: c.priority })), count: r.count });
    toast(`已生成 ${r.count} 条并入库`, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

$("#btn-export").addEventListener("click", async () => {
  if (!state.sessionId) {
    toast("请先点「生成入库」", "err");
    return;
  }
  try {
    const r = await api("/api/export", {
      method: "POST",
      body: { session_id: state.sessionId, format: "xlsx" },
    });
    const name = r.path.split(/[\\/]/).pop();
    toast("导出成功: " + name, "ok");
    window.open(`/api/export/download/${encodeURIComponent(name)}`, "_blank");
  } catch (e) {
    toast(e.message, "err");
  }
});

$("#btn-go-cases").addEventListener("click", () => $("#btn-build-cases").click());

/* ================= 配置 ================= */
$("#btn-config").addEventListener("click", async () => {
  try {
    const cfg = await api("/api/config");
    $("#cfg-provider").value = cfg.ai?.provider || "openai";
    $("#cfg-base").value = cfg.ai?.base_url || "";
    $("#cfg-model").value = cfg.ai?.model || "";
    $("#cfg-vision").value = cfg.ai?.vision_model || "";
    $("#cfg-temp").value = cfg.ai?.temperature ?? 0.3;
    $("#cfg-key").placeholder = cfg.ai?.api_key ? "已配置" : "sk-...";
    $("#modal-config").classList.remove("hidden");
  } catch (e) {
    toast(e.message, "err");
  }
});
$("#btn-close-config").addEventListener("click", () => $("#modal-config").classList.add("hidden"));
$("#btn-save-config").addEventListener("click", async () => {
  const body = {
    ai: {
      provider: $("#cfg-provider").value,
      base_url: $("#cfg-base").value.trim(),
      model: $("#cfg-model").value.trim(),
      vision_model: $("#cfg-vision").value.trim(),
      temperature: Number($("#cfg-temp").value) || 0.3,
    },
  };
  const key = $("#cfg-key").value.trim();
  if (key) body.ai.api_key = key;
  try {
    await api("/api/config", { method: "PUT", body });
    toast("配置已保存", "ok");
    $("#modal-config").classList.add("hidden");
  } catch (e) {
    toast(e.message, "err");
  }
});
$("#btn-save-config-disk").addEventListener("click", async () => {
  try {
    const r = await api("/api/config/save", { method: "POST", body: {} });
    toast("已写入 " + r.path, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

/* 初始化 */
refreshStatus();
loadShots();
loadMarked();
loadTree();
startLive();
loadLiveMeta();
