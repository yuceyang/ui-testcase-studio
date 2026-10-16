/* 软件功能测试系统 — 工作台 */
"use strict";

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const state = {
  elements: [],
  tree: [],
  marked: [],
  shots: [],
  selectedNodeId: null,
  sessionId: "",
  frameTree: [],
  projectId: localStorage.getItem("qts_project_id") || "",
  liveReady: false,
  projectCases: [],
  committedCases: [],
  casesReady: false,
  checkedIds: new Set(),
  collapsedIds: new Set(),
};

let liveTimer = null;
let liveViewport = { width: 1680, height: 1050 };

function toast(msg, type = "") {
  const el = $("#toast");
  el.textContent = msg;
  el.className = "toast " + type;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add("hidden"), 3000);
}

async function api(path, options = {}) {
  const opt = { headers: { "Content-Type": "application/json" }, ...options };
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

/* ================= 项目 ================= */
async function loadProjectList() {
  try {
    const r = await api("/api/projects");
    const list = r.projects || [];
    const sel = $("#project-select");
    sel.innerHTML =
      `<option value="">选择项目…</option>` +
      list.map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join("");
    if (state.projectId) sel.value = state.projectId;
    $("#shot-dir").textContent = state.projectId
      ? `项目截图目录：data/projects/${state.projectId}/shots`
      : "存储目录：data/output/shots（未选项目时）";
  } catch {
    /* ignore */
  }
}

$("#btn-new-project").addEventListener("click", async () => {
  const name = prompt("项目名称（按被测系统划分）", "等保2.0");
  if (!name) return;
  try {
    const r = await api("/api/projects", { method: "POST", body: { name, base_url: $("#addr-url").value } });
    state.projectId = r.project.id;
    localStorage.setItem("qts_project_id", state.projectId);
    await loadProjectList();
    await saveProject(true);
    toast("项目已创建：" + name, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

$("#project-select").addEventListener("change", async (e) => {
  state.projectId = e.target.value;
  localStorage.setItem("qts_project_id", state.projectId || "");
  if (state.projectId) await loadProject();
  await loadProjectList();
});

async function saveProject(silent = false) {
  if (!state.projectId) {
    if (!silent) toast("请先新建/选择项目", "err");
    return;
  }
  // 仅在「已加载或已生成/已删改用例」时写入 cases，避免空数组覆盖
  const body = { cases: state.casesReady ? state.committedCases || [] : undefined };
  return api(`/api/projects/${state.projectId}/save-from-engine`, {
    method: "POST",
    body,
  })
    .then(async (r) => {
      const p = r.project || {};
      if (!silent) toast(`已保存（树 ${p.tree?.length || 0} / 用例 ${p.cases?.length || 0}）`, "ok");
      await loadShotList();
    })
    .catch((e) => {
      if (!silent) toast(e.message, "err");
      else throw e;
    });
}
let _saveTimer = null;
function scheduleAutoSave(delay = 800) {
  if (!state.projectId) return;
  clearTimeout(_saveTimer);
  const tip = $("#autosave-tip");
  if (tip) tip.textContent = "保存中…";
  _saveTimer = setTimeout(async () => {
    try {
      await saveProject(true);
      if (tip) tip.textContent = "已自动保存 " + new Date().toLocaleTimeString();
    } catch (e) {
      if (tip) tip.textContent = "保存失败";
    }
  }, delay);
}

async function flushSave() {
  if (!state.projectId) return;
  clearTimeout(_saveTimer);
  const tip = $("#autosave-tip");
  if (tip) tip.textContent = "保存中…";
  await saveProject(true);
  if (tip) tip.textContent = "已自动保存 " + new Date().toLocaleTimeString();
}

$("#btn-load-project").addEventListener("click", async () => {
  // 加载前先落盘，避免防抖未写完导致旧数据回滚
  try {
    await flushSave();
  } catch {
    /* ignore */
  }
  await loadProject();
});
$("#btn-del-project").addEventListener("click", async () => {
  if (!state.projectId) return toast("请先选择项目", "err");
  if (!confirm("确认删除该项目及其本地数据？")) return;
  try {
    await api(`/api/projects/${state.projectId}`, { method: "DELETE" });
    state.projectId = "";
    localStorage.removeItem("qts_project_id");
    await loadProjectList();
    toast("项目已删除", "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

function rebindCasesToTree() {
  const treeIds = new Set(state.tree.map((n) => n.id));
  const points = state.tree.filter((n) => n.node_type === "point" || n.node_type === "case");
  state.orphanCaseIds = new Set();
  for (const c of state.committedCases || []) {
    if (c.point_id && treeIds.has(c.point_id)) continue;
    let hit = points.find((p) => p.name && (c.title || "").includes(p.name));
    if (!hit && c.module_cat) {
      hit = state.tree.find((n) => n.node_type === "module" && n.name === c.module_cat);
    }
    if (hit) c.point_id = hit.id;
    else {
      c.point_id = "__unbound__";
      state.orphanCaseIds.add(c.id);
    }
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
    state.casesReady = true;
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

/* ================= 浏览器 / 实时镜像 ================= */
function setLiveVisible(on) {
  $("#live-empty").classList.toggle("hidden", on);
  $("#live-frame").classList.toggle("hidden", !on);
  state.liveReady = !!on;
}

function startLive() {
  stopLive();
  liveTimer = setInterval(refreshLiveFrame, 300);
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
    if (blob.size < 100) return;
    const img = $("#live-img");
    const old = img.src;
    img.src = URL.createObjectURL(blob);
    if (old && old.startsWith("blob:")) URL.revokeObjectURL(old);
    setLiveVisible(true);
    await loadLiveMeta(true);
    drawGhost();
  } catch {
    /* 未启动 */
  }
}

async function loadLiveMeta(quiet = true) {
  try {
    const m = await api("/api/browser/live/meta");
    if (m.viewport) liveViewport = m.viewport;
    if (m.url) $("#addr-url").value = m.url;
    if (!quiet && m.title != null) $("#br-status").textContent = `运行中 · ${(m.title || "").slice(0, 20)}`;
  } catch {
    /* ignore */
  }
}

async function refreshStatus() {
  try {
    const c = await api("/api/browser/current");
    const el = $("#br-status");
    if (!c.running) {
      el.textContent = "未启动";
      el.className = "badge";
      setLiveVisible(false);
    } else {
      el.textContent = `运行中 · ${c.title || c.url || ""}`.slice(0, 36);
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

$("#btn-stop").addEventListener("click", async () => {
  try {
    await api("/api/browser/close", { method: "POST", body: {} });
    stopLive();
    setLiveVisible(false);
    state.elements = [];
    renderElements();
    drawGhost();
    refreshStatus();
    toast("浏览器已关闭", "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

async function goAddress() {
  const url = $("#addr-url").value.trim();
  if (!url) return toast("请输入地址", "err");
  try {
    await ensureBrowser();
    startLive();
    setLiveVisible(true);
    const r = await api("/api/browser/live/navigate", { method: "POST", body: { url } });
    // 换页清叠框
    state.elements = [];
    renderElements();
    drawGhost();
    await refreshLiveFrame();
    refreshStatus();
    toast("已导航，可在镜像内点击登录", "ok");
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
    state.elements = [];
    renderElements();
    drawGhost();
    await refreshLiveFrame();
  } catch (e) {
    toast(e.message, "err");
  }
});
$("#btn-reload").addEventListener("click", async () => {
  try {
    await api("/api/browser/reload", { method: "POST", body: {} });
    await refreshLiveFrame();
  } catch (e) {
    toast(e.message, "err");
  }
});

/* --- 镜像内直操 --- */
function stageToViewport(clientX, clientY) {
  const img = $("#live-img");
  const rect = img.getBoundingClientRect();
  // 显示宽含 liveZoom；换算到真实视口坐标
  const displayW = rect.width;
  const scale = liveViewport.width / displayW;
  return {
    x: (clientX - rect.left) * scale,
    y: (clientY - rect.top) * scale,
  };
}

$("#live-img").addEventListener("click", async (ev) => {
  hideCtx();
  focusIme();
  const { x, y } = stageToViewport(ev.clientX, ev.clientY);

  // Ctrl+点击识别框：切换标记
  const rect = ev.target.closest && ev.target.closest(".shot-rect");
  if (rect && (ev.ctrlKey || ev.metaKey)) {
    ev.preventDefault();
    const id = rect.dataset.elId;
    const el = state.elements.find((e) => e.id === id) || state.marked.find((e) => e.id === id);
    if (!el) return;
    if (el.marked) await unmarkElement(id);
    else await markElement(id);
    renderElements();
    drawGhost();
    return;
  }

  const cross = $("#live-cross");
  const img = $("#live-img");
  cross.style.display = "block";
  cross.style.left = ev.clientX - img.getBoundingClientRect().left + img.offsetLeft + "px";
  cross.style.top = ev.clientY - img.getBoundingClientRect().top + img.offsetTop + "px";
  try {
    await api("/api/browser/live/click", { method: "POST", body: { x, y } });
    await refreshLiveFrame();
  } catch (e) {
    toast(e.message, "err");
  }
});

/* ===== 输入法（IME）===== */
let imeComposing = false;

function focusIme() {
  const p = $("#ime-proxy");
  if (!p) return;
  $("#live-stage").focus();
  p.focus();
}

function sendText(text) {
  if (!text || !state.liveReady) return Promise.resolve();
  return api("/api/browser/live/insert", { method: "POST", body: { text } });
}

function sendKey(key) {
  if (!state.liveReady) return Promise.resolve();
  return api("/api/browser/live/press", { method: "POST", body: { key } });
}

const ime = $("#ime-proxy");
if (ime) {
  ime.addEventListener("compositionstart", () => {
    imeComposing = true;
  });
  ime.addEventListener("compositionend", async (e) => {
    imeComposing = false;
    const text = e.data || ime.value || "";
    ime.value = "";
    if (text) {
      await sendText(text);
      await refreshLiveFrame();
    }
  });
  ime.addEventListener("input", async (e) => {
    // 组字过程中不发；完成后由 compositionend 发送
    if (imeComposing || e.isComposing) return;
    // 部分输入法/粘贴不触发 compositionend
    const v = ime.value;
    if (!v) return;
    ime.value = "";
    await sendText(v);
    await refreshLiveFrame();
  });
  ime.addEventListener("keydown", async (ev) => {
    // 组字中的按键（229）一律放行给输入法
    if (imeComposing || ev.isComposing || ev.keyCode === 229) return;

    const keyMapSpecial = {
      Enter: "Enter",
      Tab: "Tab",
      Backspace: "Backspace",
      Escape: "Escape",
      ArrowUp: "ArrowUp",
      ArrowDown: "ArrowDown",
      ArrowLeft: "ArrowLeft",
      ArrowRight: "ArrowRight",
      Delete: "Delete",
    };
    if (keyMapSpecial[ev.key]) {
      ev.preventDefault();
      ime.value = "";
      await sendKey(keyMapSpecial[ev.key]);
      await refreshLiveFrame();
      return;
    }
    if (ev.ctrlKey || ev.metaKey) {
      const m = {
        a: "Control+a",
        c: "Control+c",
        v: "Control+v",
        x: "Control+x",
      };
      const k = (ev.key || "").toLowerCase();
      if (k === "c") {
        // 复制页面选区
        ev.preventDefault();
        try {
          const text = await api("/api/browser/live/copy", { method: "POST", body: {} });
          if (text && text.text) {
            await navigator.clipboard.writeText(text.text).catch(() => {});
            toast("已复制选中文本");
          }
        } catch {
          /* ignore */
        }
        return;
      }
      if (m[k]) {
        // v/x 交给 paste / 原生
        if (k !== "v") ev.preventDefault();
        if (k !== "v") await sendKey(m[k]);
      }
      return;
    }
    // 普通单字符走 input/composition，这里不 preventDefault，保证 IME 用候选窗
  });
  ime.addEventListener("paste", async (ev) => {
    ev.preventDefault();
    const text = (ev.clipboardData || window.clipboardData).getData("text");
    if (text) {
      await sendText(text);
      await refreshLiveFrame();
    }
  });
}

// 点镜像空白（非图片）也聚焦
$("#live-stage").addEventListener("mousedown", (ev) => {
  if (ev.target.id === "live-stage" || ev.target.id === "live-empty") focusIme();
});

$("#live-stage").addEventListener(
  "wheel",
  (ev) => {
    if (!state.liveReady) return;
    ev.preventDefault();
    api("/api/browser/live/wheel", {
      method: "POST",
      body: { dx: ev.deltaX, dy: ev.deltaY },
    }).catch(() => {});
  },
  { passive: false }
);

// 键盘焦点统一交给 IME 代理（避免 keydown 拦截组字）
$("#live-stage").addEventListener("keydown", (ev) => {
  if (ev.target.id === "ime-proxy") return;
  // 舞台上的按键转到代理，保证输入法可用
  focusIme();
  ev.preventDefault();
  const imeEl = $("#ime-proxy");
  if (imeEl && ev.key && ev.key.length === 1 && !ev.ctrlKey && !ev.metaKey) {
    imeEl.value += ev.key;
    imeEl.dispatchEvent(new Event("input", { bubbles: true }));
  }
});

/* --- 右键菜单 --- */
function hideCtx() {
  $("#ctx-menu").classList.add("hidden");
}

function showCtx(x, y, items) {
  const menu = $("#ctx-menu");
  menu.innerHTML = items
    .map((it, i) => `<button data-i="${i}">${esc(it.label)}</button>`)
    .join("");
  menu.style.left = x + "px";
  menu.style.top = y + "px";
  menu.classList.remove("hidden");
  menu.querySelectorAll("button").forEach((b) => {
    b.addEventListener("click", () => {
      hideCtx();
      const it = items[Number(b.dataset.i)];
      if (it && it.onClick) it.onClick();
    });
  });
}

$("#live-stage").addEventListener("contextmenu", (ev) => {
  ev.preventDefault();
  const stage = $("#live-stage");
  const rect = stage.getBoundingClientRect();
  const lx = ev.clientX - rect.left + stage.scrollLeft;
  const ly = ev.clientY - rect.top + stage.scrollTop;

  // 命中识别框？
  const hit = ev.target.closest && ev.target.closest(".shot-rect");
  if (hit) {
    const elId = hit.dataset.elId;
    showCtx(lx, ly, [
      {
        label: "取消标记",
        onClick: async () => {
          await unmarkElement(elId);
          for (const n of state.tree) {
            if (n.element_ids && n.element_ids.includes(elId)) {
              await api(`/api/browser/tree/node/${n.id}`, {
                method: "PUT",
                body: { element_ids: n.element_ids.filter((x) => x !== elId) },
              });
            }
          }
          await loadTree();
          renderElements();
          drawGhost();
          toast("已取消标记");
        },
      },
      {
        label: "标记为模块/目录/功能点…",
        onClick: () => openMarkAs(elId),
      },
      {
        label: "一键取消本页全部标记",
        onClick: () => clearPageMarks(),
      },
    ]);
    return;
  }

  const items = [
    {
      label: "添加功能点到当前节点",
      onClick: () => {
        const name = prompt("功能点名称", "手动功能点");
        if (!name) return;
        api("/api/browser/tree/node", {
          method: "POST",
          body: { name, node_type: "point", parent_id: state.selectedNodeId },
        }).then(() => {
          loadTree();
          toast("已添加功能点");
        });
      },
    },
    {
      label: "标记为模块/目录/功能点…",
      onClick: () => openMarkAs(""),
    },
    {
      label: "一键取消本页全部标记",
      onClick: () => clearPageMarks(),
    },
    {
      label: "此处截图",
      onClick: () => $("#btn-shot").click(),
    },
  ];
  showCtx(lx, ly, items);
});

async function clearPageMarks() {
  
  const ids = state.elements.map((e) => e.id).concat(state.marked.map((m) => m.id));
  for (const id of ids) {
    try {
      await api(`/api/browser/unmark/${id}`, { method: "POST", body: {} });
    } catch {
      /* ignore */
    }
    for (const n of state.tree) {
      if (n.element_ids && n.element_ids.length) {
        const next = n.element_ids.filter((x) => x !== id);
        if (next.length !== n.element_ids.length) {
          await api(`/api/browser/tree/node/${n.id}`, {
            method: "PUT",
            body: { element_ids: next },
          });
        }
      }
    }
  }
  state.elements.forEach((e) => (e.marked = false));
  state.marked = [];
  await loadTree();
  await loadMarked();
  renderElements();
  drawGhost();
  toast("已取消本页标记", "ok");
}

$("#btn-clear-marks") &&
  $("#btn-clear-marks").addEventListener("click", () => clearPageMarks());

document.addEventListener("click", (e) => {
  if (!e.target.closest("#ctx-menu")) hideCtx();
});

/* ================= 叠框 ================= */
function drawGhost() {
  const img = $("#live-img");
  if (!img || !img.clientWidth || $("#live-frame").classList.contains("hidden")) return;
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

function highlightEl(id) {
  document.querySelectorAll(".shot-rect").forEach((r) => {
    r.classList.toggle("hover", r.dataset.elId === id);
  });
}

/* ================= 元素 ================= */
function treeElementIds() {
  const ids = new Set();
  for (const n of state.tree) {
    for (const id of n.element_ids || []) ids.add(id);
  }
  return ids;
}

function renderElements() {
  const tb = $("#el-table tbody");
  const q = ($("#el-filter").value || "").toLowerCase();
  const kind = $("#el-kind").value;
  const inTree = treeElementIds();
  const rows = state.elements.filter((e) => {
    if (inTree.has(e.id)) return false; // 已入树不再列出
    if (kind && e.kind !== kind) return false;
    if (!q) return true;
    return `${e.name} ${e.text} ${e.selector}`.toLowerCase().includes(q);
  });

  tb.innerHTML = rows
    .map(
      (e) => `
    <tr data-id="${e.id}">
      <td><input type="checkbox" class="el-check" data-id="${e.id}" ${e.marked ? "checked" : ""} /></td>
      <td><span class="tag">${esc(e.kind_label || e.kind)}</span></td>
      <td>${esc(e.name || e.text || "—")}</td>
      <td class="url">${esc(e.selector)}</td>
      <td>
        <button class="link-btn" data-act="mark-as" data-id="${e.id}">标记为…</button>
        <button class="link-btn" data-act="attach" data-id="${e.id}">挂到当前</button>
      </td>
    </tr>`
    )
    .join("");

  tb.querySelectorAll("button[data-act=mark-as]").forEach((btn) => {
    btn.addEventListener("click", () => openMarkAs(btn.dataset.id));
  });
  tb.querySelectorAll("button[data-act=attach]").forEach((btn) => {
    btn.addEventListener("click", () => markElement(btn.dataset.id));
  });
  tb.querySelectorAll(".el-check").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (cb.checked) markElement(cb.dataset.id, true);
      else unmarkElement(cb.dataset.id, true);
    });
  });
  tb.querySelectorAll("tr[data-id]").forEach((tr) => {
    tr.addEventListener("mouseenter", () => highlightEl(tr.dataset.id));
    tr.addEventListener("mouseleave", () => highlightEl(""));
  });

  const allCb = $("#el-select-all");
  if (allCb) {
    const visible = rows.map((r) => r.id);
    const n = visible.filter((id) => state.elements.find((x) => x.id === id)?.marked).length;
    allCb.checked = visible.length > 0 && n === visible.length;
    allCb.indeterminate = n > 0 && n < visible.length;
  }
}

$("#el-filter").addEventListener("input", renderElements);
$("#el-kind").addEventListener("change", renderElements);

$("#el-select-all").addEventListener("change", (e) => {
  $$("#el-table .el-check").forEach((cb) => {
    cb.checked = e.target.checked;
    if (e.target.checked) markElement(cb.dataset.id, true);
    else unmarkElement(cb.dataset.id, true);
  });
  renderElements();
});
$("#btn-sel-all").addEventListener("click", () => {
  $("#el-select-all").checked = true;
  $("#el-select-all").dispatchEvent(new Event("change"));
});
$("#btn-sel-none").addEventListener("click", () => {
  $("#el-select-all").checked = false;
  $("#el-select-all").dispatchEvent(new Event("change"));
});

$("#btn-clear-elements") &&
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

$("#btn-extract").addEventListener("click", async () => {
  try {
    await ensureBrowser();
    const r = await api("/api/browser/extract", { method: "POST", body: {} });
    state.elements = r.elements || [];
    state.frameTree = r.frame_tree || [];
    renderElements();
    drawGhost();
    await loadShotList();
    toast(`发现 ${state.elements.length} 个元素`, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

async function markElement(elId, quiet = false) {
  const el = state.elements.find((x) => x.id === elId);
  if (!el) return;
  try {
    const r = await api("/api/browser/mark", { method: "POST", body: { element: el } });
    const idx = state.elements.findIndex((x) => x.id === elId);
    if (idx >= 0) state.elements[idx] = { ...state.elements[idx], ...r.element, marked: true };
    await loadMarked();
    drawGhost();
    if (state.selectedNodeId) await attachElToNode(state.selectedNodeId, r.element.id);
    if (!quiet) toast("已标记", "ok");
  } catch (e) {
    if (!quiet) toast(e.message, "err");
  }
}

async function unmarkElement(elId, quiet = false) {
  try {
    await api(`/api/browser/unmark/${elId}`, { method: "POST", body: {} });
    const idx = state.elements.findIndex((x) => x.id === elId);
    if (idx >= 0) state.elements[idx] = { ...state.elements[idx], marked: false };
    await loadMarked();
    drawGhost();
    if (!quiet) toast("已取消");
  } catch (e) {
    if (!quiet) toast(e.message, "err");
  }
}

async function attachElToNode(nodeId, elId) {
  const n = state.tree.find((x) => x.id === nodeId);
  if (!n) return;
  const ids = new Set(n.element_ids || []);
  ids.add(elId);
  await api(`/api/browser/tree/node/${nodeId}`, {
    method: "PUT",
    body: { element_ids: Array.from(ids) },
  });
  await loadTree();
}

async function loadMarked() {
  try {
    const r = await api("/api/browser/marked");
    const all = r.elements || [];
    state.marked = all;
    // 与选中节点联动
    const n = state.tree.find((x) => x.id === state.selectedNodeId);
    let list = all;
    if (n && (n.element_ids || []).length) {
      const ids = new Set(n.element_ids);
      list = all.filter((e) => ids.has(e.id));
    } else if (n) {
      list = [];
    }
    $("#marked-count").textContent = String(list.length);
    $("#marked-list").innerHTML =
      list
        .map(
          (e) => `
      <div class="marked-item" data-id="${e.id}">
        <div><b>${esc(e.name || e.text || e.kind)}</b> <span class="k">${esc(e.kind)}</span></div>
        <div class="k">${esc(e.selector || "")}</div>
        <div class="row">
          <button class="mini" data-act="un" data-id="${e.id}">取消</button>
        </div>
      </div>`
        )
        .join("") || `<div class="muted">当前节点无关联标记</div>`;
    $("#marked-list").querySelectorAll("button[data-act=un]").forEach((b) => {
      b.addEventListener("click", () => unmarkElement(b.dataset.id));
    });
    drawGhost();
  } catch {
    /* ignore */
  }
}

/* ================= 树 ================= */
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

function caseCountForNode(id) {
  // 统计始终用「已入库全量」，不随列表过滤变化
  const list = state.committedCases || [];
  if (!list.length) return 0;
  const ids = descendantsOf(id);
  return list.filter((c) => ids.has(c.point_id)).length;
}

function renderTree() {
  const byParent = {};
  for (const n of state.tree) {
    const p = n.parent_id || "";
    (byParent[p] = byParent[p] || []).push(n);
  }
  // 已入库用例作为叶子挂在 point 下
  const casesByPoint = {};
  for (const c of state.committedCases || []) {
    (casesByPoint[c.point_id] = casesByPoint[c.point_id] || []).push(c);
  }
  const typeLabel = {
    module: "模块",
    title1: "一级",
    title2: "二级",
    title3: "三级",
    point: "功能点",
    case: "用例",
    unbound: "未绑定",
  };

  function nodeHtml(n) {
    const kids = byParent[n.id] || [];
    const cs = casesByPoint[n.id] || [];
    const st = n.status || "pending";
    const stCls = st === "pass" ? "st-pass" : st === "fail" ? "st-fail" : "";
    const cnt = caseCountForNode(n.id);
    const hasKids = kids.length > 0 || cs.length > 0;
    const collapsed = state.collapsedIds.has(n.id);
    const caseHtml = collapsed
      ? ""
      : cs
          .map(
            (c) => `
      <div class="tree-node tree-case" data-id="${c.id}" data-point="${c.point_id || ""}" style="height:24px;min-height:24px;max-height:24px;line-height:24px;margin:0;padding:0 4px">
        <input type="checkbox" class="tree-check" data-id="${c.id}" ${
              state.checkedIds.has(c.id) ? "checked" : ""
            } />
        <span class="badge-sm case">用例</span>
        <span class="nm">${esc(c.case_no || "")} ${esc((c.title || "").slice(0, 24))}</span>
      </div>`
          )
          .join("");
    const childHtml = collapsed ? "" : kids.map(nodeHtml).join("");
    return `
      <div class="tree-node ${state.selectedNodeId === n.id ? "active" : ""}" data-id="${n.id}" style="height:24px;min-height:24px;max-height:24px;line-height:24px;margin:0;padding:0 4px">
        <span class="twist ${hasKids ? "" : "empty"}" data-twist="${n.id}" title="折叠/展开">${
          hasKids ? (collapsed ? "▸" : "▾") : "&nbsp;"
        }</span>
        <input type="checkbox" class="tree-check" data-id="${n.id}" ${
          state.checkedIds.has(n.id) ? "checked" : ""
        } />
        <span class="badge-sm ${n.node_type}">${typeLabel[n.node_type] || n.node_type}</span>
        <span class="nm">${esc(n.name)}</span>
        ${cnt ? `<span class="case-cnt" title="测试用例数">${cnt}</span>` : ""}
        <span class="${stCls}">${st === "pass" ? "✓" : st === "fail" ? "✗" : ""}</span>
      </div>
      ${
        caseHtml || childHtml
          ? `<div class="tree-children">${caseHtml}${childHtml}</div>`
          : ""
      }`;
  }

  const rootNodes = state.tree.filter((n) => !n.parent_id);
  // 未绑定用例虚拟分组
  const unbound = casesByPoint["__unbound__"] || [];
  const unboundHtml = unbound.length
    ? `
      <div class="tree-node unbound-root" data-id="__unbound__" style="height:24px;min-height:24px;max-height:24px;line-height:24px;margin:0;padding:0 4px">
        <span class="twist" data-twist="__unbound__">${
          state.collapsedIds.has("__unbound__") ? "▸" : "▾"
        }</span>
        <input type="checkbox" class="tree-check" data-id="__unbound__" ${
          state.checkedIds.has("__unbound__") ? "checked" : ""
        } />
        <span class="badge-sm unbound">未绑定</span>
        <span class="nm">未绑定用例</span>
        <span class="case-cnt">${unbound.length}</span>
      </div>
      ${
        state.collapsedIds.has("__unbound__")
          ? ""
          : `<div class="tree-children">${unbound
              .map(
                (c) => `
        <div class="tree-node tree-case" data-id="${c.id}" data-point="__unbound__" style="height:24px;min-height:24px;max-height:24px;line-height:24px;margin:0;padding:0 4px">
          <input type="checkbox" class="tree-check" data-id="${c.id}" ${
                  state.checkedIds.has(c.id) ? "checked" : ""
                } />
          <span class="badge-sm case">用例</span>
          <span class="nm">${esc(c.case_no || "")} ${esc((c.title || "").slice(0, 24))}</span>
        </div>`
              )
              .join("")}</div>`
      }`
    : "";

  const total = (state.committedCases || []).length;
  const allChecked =
    state.tree.length > 0 &&
    state.tree.every((n) => state.checkedIds.has(n.id));
  const rootCollapsed = state.collapsedIds.has("__root__");
  const bodyHtml = rootCollapsed
    ? ""
    : `<div class="tree-children">${
        rootNodes.map(nodeHtml).join("") + unboundHtml
      }</div>`;
  const htmlTree = `
    <div class="tree-root">
      <div class="tree-node" data-id="__root__" style="height:24px;min-height:24px;max-height:24px;line-height:24px;margin:0;padding:0 4px">
        <span class="twist" data-twist="__root__">${rootCollapsed ? "▸" : "▾"}</span>
        <input type="checkbox" class="tree-check" data-id="__root__" ${
          allChecked ? "checked" : ""
        } title="全选/全不选" />
        <span class="badge-sm module">根</span>
        <span class="nm">项目全部用例</span>
        <span class="case-cnt">${total} 用例</span>
      </div>
      ${bodyHtml}
    </div>`;
  if (!rootNodes.length && !unbound.length) {
    $("#tree").innerHTML = `
      <div class="tree-empty">
        <div class="tree-empty-title">尚未建立功能点树</div>
        <div class="muted">1. 在镜像中登录并「发现元素」</div>
        <div class="muted">2. 「自动建树」或使用 ＋新增 / 批量标记为…</div>
        <div class="muted">3. 结构：模块 → 一/二/三级 → 功能点（缺级用 /）</div>
      </div>`;
  } else {
    $("#tree").innerHTML = htmlTree;
  }
  const el = $("#tree-case-total");
  if (el) {
    el.textContent = total + " 用例";
    el.style.display = "none"; // 总数已挪到根节点
  }

  $("#tree").querySelectorAll(".tree-node").forEach((el) => {
    el.addEventListener("click", (ev) => {
      if (ev.target.classList && ev.target.classList.contains("tree-check")) return;
      const id = el.dataset.id;
      if (el.classList.contains("tree-case")) {
        // 点用例 → 详情
        const list = state.committedCases || [];
        const i = list.findIndex((x) => x.id === id);
        if (i >= 0) {
          renderPreview({ cases: list, mode: "committed" });
          openCaseDetail(i);
        }
        return;
      }
      selectNode(id);
      showCasesForNode(id);
    });
    if (!el.classList.contains("tree-case")) {
      el.addEventListener("dblclick", () => openNodeEditor(el.dataset.id));
      el.addEventListener("contextmenu", (ev) => {
        ev.preventDefault();
        openNodeEditor(el.dataset.id);
      });
    }
  });
  $("#tree").querySelectorAll("[data-twist]").forEach((tw) => {
    tw.addEventListener("click", (ev) => {
      ev.stopPropagation();
      const id = tw.dataset.twist;
      if (state.collapsedIds.has(id)) state.collapsedIds.delete(id);
      else state.collapsedIds.add(id);
      renderTree();
    });
  });
  $("#tree").querySelectorAll(".tree-check").forEach((cb) => {
    const id = cb.dataset.id;
    const owner = cb.closest(".tree-node");
    const ownerPoint = owner && owner.dataset.point;
    if (id === "__root__") {
      cb.addEventListener("click", (ev) => ev.stopPropagation());
      cb.addEventListener("change", (ev) => {
        ev.stopPropagation();
        if (cb.checked) {
          state.tree.forEach((n) => state.checkedIds.add(n.id));
          (state.committedCases || []).forEach((c) => state.checkedIds.add(c.id));
          state.checkedIds.add("__unbound__");
        } else {
          state.checkedIds.clear();
        }
        renderTree();
      });
      return;
    }
    cb.addEventListener("click", (ev) => ev.stopPropagation());
    cb.addEventListener("mousedown", (ev) => ev.stopPropagation());
    cb.addEventListener("change", (ev) => {
      ev.stopPropagation();
      if (cb.checked) state.checkedIds.add(id);
      else state.checkedIds.delete(id);
      // 级联：子树节点 + 挂在子节点下的用例（用例不在 tree 数组）
      const ids = descendantsOf(id);
      ids.add(id);
      $$("#tree .tree-check").forEach((x) => {
        const el = x.closest(".tree-node");
        const cid = x.dataset.id;
        const pid = el && el.dataset.point;
        const hit = ids.has(cid) || (pid && ids.has(pid));
        if (hit) {
          x.checked = cb.checked;
          if (cb.checked) state.checkedIds.add(cid);
          else state.checkedIds.delete(cid);
        }
      });
    });
  });
}

function selectedTreeIds() {
  const ids = state.checkedIds || new Set();
  if (ids.has("__root__")) {
    return state.tree.map((n) => n.id);
  }
  return Array.from(ids).filter((x) => x !== "__unbound__");
}

/** 生成用例范围：勾选优先，否则当前单击选中的节点 */
function inScope(pointId, rootIds) {
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

function generateScopeIds() {
  const checked = selectedTreeIds();
  if (checked.length) return checked;
  if (state.selectedNodeId) return [state.selectedNodeId];
  return [];
}

$("#btn-del-tree-selected").addEventListener("click", async () => {
  const ids = selectedTreeIds();
  if (!ids.length) return toast("请勾选要删除的节点", "err");
  if (!confirm(`确认删除 ${ids.length} 个节点及其子节点和关联用例？`)) return;
  const all = new Set();
  ids.forEach((id) => {
    all.add(id);
    descendantsOf(id).forEach((x) => all.add(x));
  });
  for (const id of ids) {
    try {
      await api(`/api/browser/tree/node/${id}`, { method: "DELETE" });
    } catch {
      /* ignore */
    }
  }
  // 同步删掉子树关联用例，避免加载后复活
  state.committedCases = (state.committedCases || []).filter(
    (c) => !all.has(c.point_id) && !all.has(c.id)
  );
  state.projectCases = state.committedCases;
  state.casesReady = true;
  state.checkedIds = new Set(
    Array.from(state.checkedIds).filter((x) => !all.has(x))
  );
  if (state.selectedNodeId && all.has(state.selectedNodeId)) state.selectedNodeId = null;
  await loadTree();
  await flushSave();
  toast(`已删除 ${ids.length} 个节点及其用例`, "ok");
});

/* 批量移动 */
$("#btn-move-tree-selected").addEventListener("click", () => {
  const ids = selectedTreeIds();
  if (!ids.length) return toast("请勾选要移动的节点", "err");
  // 合并所有选中及其子节点
  const all = new Set(ids);
  ids.forEach((id) => descendantsOf(id).forEach((x) => all.add(x)));
  $("#move-hint").textContent = `将移动 ${all.size} 个节点（含子节点）`;
  $("#modal-move").dataset.ids = JSON.stringify([...all]);
  fillParentOptions($("#mv-parent"), null, state.selectedNodeId || "");
  // 移动目标不能是自己的子孙
  $("#modal-move").classList.remove("hidden");
});
$("#btn-close-move").addEventListener("click", () => $("#modal-move").classList.add("hidden"));
$("#btn-save-move").addEventListener("click", async () => {
  const ids = JSON.parse($("#modal-move").dataset.ids || "[]");
  const parent = $("#mv-parent").value || null;
  if (parent && ids.includes(parent)) return toast("不能移动到自身或子节点下", "err");
  const idSet = new Set(ids);
  // 只改「选中集合中的根节点」的父级，子节点随树自然跟走
  const roots = state.tree.filter((n) => idSet.has(n.id) && !idSet.has(n.parent_id));
  try {
    for (const n of roots) {
      await api(`/api/browser/tree/node/${n.id}`, {
        method: "PUT",
        body: { parent_id: parent },
      });
    }
    await loadTree();
    $("#modal-move").classList.add("hidden");
    toast(`已移动 ${roots.length} 个节点`, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

async function loadTree(opts = {}) {
  try {
    const r = await api("/api/browser/tree");
    state.tree = r.tree || [];
    renderTree();
    scheduleAutoSave();
  } catch {
    /* ignore */
  }
}

function showCasesForNode(nodeId) {
  // 已入库：只在树上；未入库生成台不展示
  const has = (state.committedCases || []).some(
    (c) => c.point_id === nodeId || descendantsOf(nodeId).has(c.point_id)
  );
  if (has) {
    $("#case-preview").innerHTML =
      `<div class="muted">该节点已入库用例在左侧树上（黄色「用例」）。此处仅未入库预览。</div>`;
    return;
  }
  // 未入库：默认不自动刷入，需点「预览」
  $("#case-preview").innerHTML =
    `<div class="muted">该节点尚无入库用例。点「预览」试生成，或「生成入库」写入树。</div>`;
}

function selectNode(id) {
  state.selectedNodeId = id;
  const n = state.tree.find((x) => x.id === id);
  renderTree();
  if (!n) return;
  const names = pathNames(id);
  const info = $("#sel-node-info");
  if (info) info.textContent = `${names} · ${n.status || "pending"}`;
  const ann = $("#node-annotation");
  if (ann) ann.value = n.annotation || "";
  const ids = new Set(n.element_ids || []);
  document.querySelectorAll(".shot-rect").forEach((r) => {
    r.classList.toggle("strong", ids.has(r.dataset.elId));
    r.classList.toggle("hover", ids.has(r.dataset.elId));
  });
  loadMarked();
  if (n.screenshot_id) {
    const s = state.shots.find((x) => x.id === n.screenshot_id);
    if (s) showShotDetail(s);
  }
}

function descendantsOf(id) {
  const ids = new Set([id]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const n of state.tree) {
      if (n.parent_id && ids.has(n.parent_id) && !ids.has(n.id)) {
        ids.add(n.id);
        changed = true;
      }
    }
  }
  return ids;
}

function fillParentOptions(sel, excludeId, selectedParent) {
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

function openMarkAs(elId, bulkIds) {
  const el = elId
    ? state.elements.find((x) => x.id === elId) || state.marked.find((x) => x.id === elId)
    : null;
  $("#mka-el-id").value = elId || "";
  const bulk = bulkIds || [];
  $("#mka-name").value = el?.name || el?.text || "";
  $("#mka-title").textContent = bulk.length ? `批量标记 ${bulk.length} 个元素` : "标记为功能点树节点";
  $("#mka-bulk-hint").style.display = bulk.length ? "block" : "none";
  $("#mka-bulk-hint").textContent = bulk.length
    ? "将按类型为每个元素建立树节点；名称用元素文本（可自动）"
    : "";
  $("#mka-name").disabled = bulk.length > 0;
  const cur = state.tree.find((n) => n.id === state.selectedNodeId);
  $("#mka-type").value = "point";
  fillParentOptions($("#mka-parent"), null, cur ? cur.id : "");
  $("#modal-mark-as").dataset.bulk = JSON.stringify(bulk);
  $("#modal-mark-as").classList.remove("hidden");
}

function openNodeEditor(id) {
  const n = state.tree.find((x) => x.id === id);
  if (!n) return;
  $("#mn-id").value = id;
  $("#mn-name").value = n.name || "";
  $("#mn-type").value = n.node_type || "point";
  fillParentOptions($("#mn-parent"), id, n.parent_id || "");
  $("#modal-node").classList.remove("hidden");
}

$("#btn-close-mark-as").addEventListener("click", () => $("#modal-mark-as").classList.add("hidden"));
$("#btn-close-node").addEventListener("click", () => $("#modal-node").classList.add("hidden"));

$("#btn-save-mark-as").addEventListener("click", async () => {
  const bulk = JSON.parse($("#modal-mark-as").dataset.bulk || "[]");
  const node_type = $("#mka-type").value;
  const parent_id = node_type === "module" ? null : $("#mka-parent").value || null;

  if (bulk.length) {
    try {
      for (const elId of bulk) {
        const el = state.elements.find((x) => x.id === elId) || state.marked.find((x) => x.id === elId);
        if (el && !el.marked) await markElement(elId, true);
        const name = (el?.name || el?.text || "节点").trim() || "节点";
        await api("/api/browser/tree/node", {
          method: "POST",
          body: {
            name,
            node_type,
            parent_id,
            url: el?.page_url || "",
            element_ids: elId ? [elId] : [],
          },
        });
      }
      $("#modal-mark-as").classList.add("hidden");
      $("#modal-mark-as").dataset.bulk = "[]";
      await loadTree();
      renderElements();
      drawGhost();
      toast(`已批量标记 ${bulk.length} 个为「${node_type}」`, "ok");
    } catch (e) {
      toast(e.message, "err");
    }
    return;
  }

  const elId = $("#mka-el-id").value;
  const el = state.elements.find((x) => x.id === elId) || state.marked.find((x) => x.id === elId);
  const name = ($("#mka-name").value || el?.name || "节点").trim();
  try {
    if (el && !el.marked && elId) await markElement(elId, true);
    const r = await api("/api/browser/tree/node", {
      method: "POST",
      body: {
        name,
        node_type,
        parent_id,
        url: el?.page_url || "",
        element_ids: elId ? [elId] : [],
      },
    });
    $("#modal-mark-as").classList.add("hidden");
    await loadTree();
    selectNode(r.node.id);
    drawGhost();
    toast(`已标为 ${node_type}：${name}`, "ok");
    renderElements();
  } catch (e) {
    toast(e.message, "err");
  }
});

$("#btn-bulk-mark-as").addEventListener("click", () => {
  const ids = $$("#el-table .el-check:checked").map((x) => x.dataset.id);
  if (!ids.length) return toast("请先勾选要批量标记的元素", "err");
  openMarkAs(ids[0], ids);
});

$("#btn-save-node").addEventListener("click", async () => {
  const id = $("#mn-id").value;
  const node_type = $("#mn-type").value;
  try {
    await api(`/api/browser/tree/node/${id}`, {
      method: "PUT",
      body: {
        name: $("#mn-name").value.trim(),
        node_type,
        parent_id: node_type === "module" ? null : $("#mn-parent").value || null,
      },
    });
    $("#modal-node").classList.add("hidden");
    await loadTree();
    selectNode(id);
    toast("已更新", "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

$("#btn-del-node").addEventListener("click", async () => {
  if (!confirm("删除节点及其子节点和关联用例？")) return;
  const id = $("#mn-id").value;
  try {
    await api(`/api/browser/tree/node/${id}`, { method: "DELETE" });
    const all = new Set([id, ...descendantsOf(id)]);
    state.committedCases = (state.committedCases || []).filter(
      (c) => !all.has(c.point_id) && !all.has(c.id)
    );
    state.projectCases = state.committedCases;
    $("#modal-node").classList.add("hidden");
    await loadTree();
    await flushSave();
  } catch (e) {
    toast(e.message, "err");
  }
});

/* 新增 / 批量导出 下拉 */
function bindDrop(btnId, menuId) {
  const btn = document.getElementById(btnId);
  const menu = document.getElementById(menuId);
  if (!btn || !menu) return;
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    $$(".drop-menu").forEach((m) => {
      if (m !== menu) m.classList.add("hidden");
    });
    menu.classList.toggle("hidden");
  });
}
document.addEventListener("click", () => $$(".drop-menu").forEach((m) => m.classList.add("hidden")));
bindDrop("btn-add-menu", "add-menu");
bindDrop("btn-export-menu", "export-menu");

$("#add-menu") &&
  $("#add-menu").addEventListener("click", async (e) => {
    const kind = e.target.dataset && e.target.dataset.add;
    if (!kind) return;
    $("#add-menu").classList.add("hidden");
    if (kind === "module") {
      const name = prompt("模块名称", "模块") || "模块";
      await api("/api/browser/tree/node", { method: "POST", body: { name, node_type: "module" } });
    } else if (kind === "title") {
      const lvl = prompt("目录层级 1/2/3", "1");
      const map = { "1": "title1", "2": "title2", "3": "title3" };
      const name = prompt("目录名（可填 /）", "/") || "/";
      await api("/api/browser/tree/node", {
        method: "POST",
        body: { name, node_type: map[lvl] || "title1", parent_id: state.selectedNodeId },
      });
    } else if (kind === "point") {
      const name = prompt("功能点名称", "功能点") || "功能点";
      await api("/api/browser/tree/node", {
        method: "POST",
        body: { name, node_type: "point", parent_id: state.selectedNodeId },
      });
    }
    await loadTree();
  });

$("#export-menu") &&
  $("#export-menu").addEventListener("click", async (e) => {
    const fmt = e.target && e.target.dataset && e.target.dataset.fmt;
    if (!fmt) return;
    $("#export-menu").classList.add("hidden");
    const ids = selectedTreeIds();
    if (!ids.length) return toast("请先勾选功能点树节点", "err");
    try {
      const r = await api("/api/browser/cases/from-tree", {
        method: "POST",
        body: {
          extra: { include_negative: true, include_auth_cases: true },
          point_ids: ids,
          sys_name: "",
          replace: true,
        },
      });
      state.sessionId = r.session_id;
      state.committedCases = r.cases || [];
      renderTree();
      const ex = await api("/api/export", {
        method: "POST",
        body: { session_id: r.session_id, format: fmt, point_ids: ids },
      });
      const name = (ex.path || "").split(/[\\/]/).pop();
      window.open(`/api/export/download/${encodeURIComponent(name)}`, "_blank");
      toast(`已导出 ${fmt.toUpperCase()}（${ex.count} 条）`, "ok");
    } catch (err) {
      toast("导出失败: " + err.message, "err");
    }
  });

$("#export-menu") &&
  $("#export-menu").addEventListener("click", async (e) => {
    const fmt = e.target.dataset && e.target.dataset.fmt;
    if (!fmt) return;
    $("#export-menu").classList.add("hidden");
    const ids = selectedTreeIds();
    if (!ids.length) return toast("请勾选要导出的功能点树节点", "err");
    try {
      const r = await api("/api/browser/cases/from-tree", {
        method: "POST",
        body: {
          extra: { include_negative: true, include_auth_cases: true },
          point_ids: ids,
          sys_name: "",
        },
      });
      state.sessionId = r.session_id;
      renderPreview({ cases: r.cases });
      const ex = await api("/api/export", {
        method: "POST",
        body: { session_id: r.session_id, format: fmt, point_ids: ids },
      });
      const name = ex.path.split(/[\\/]/).pop();
      window.open(`/api/export/download/${encodeURIComponent(name)}`, "_blank");
      toast(`已导出 ${fmt.toUpperCase()}（${ex.count} 条）`, "ok");
    } catch (err) {
      toast(err.message, "err");
    }
  });

$("#btn-auto-tree").addEventListener("click", async () => {
  try {
    const r = await api("/api/browser/discover-tree", {
      method: "POST",
      body: { module_name: "核心业务" },
    });
    state.tree = r.tree || [];
    state.elements = r.elements || state.elements;
    renderTree();
    renderElements();
    drawGhost();
    toast(`建树完成 ${state.tree.length} 节点`, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

/* 判定 */
async function setStatus(st) {
  if (!state.selectedNodeId) return toast("请选中树节点", "err");
  try {
    await api(`/api/browser/tree/node/${state.selectedNodeId}/status`, {
      method: "POST",
      body: { status: st, annotation: $("#node-annotation").value },
    });
    await loadTree();
    selectNode(state.selectedNodeId);
    toast("判定：" + st);
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

/* ================= 截图库 ================= */
async function loadShotList() {
  try {
    // 合并：项目已入库 + 当前会话临时截图
    let shots = [];
    if (state.projectId) {
      const p = await api(`/api/projects/${state.projectId}`);
      shots = (p.project.shots || []).map((s) => ({ ...s, committed: true }));
      const dir = p.project.shots_dir || "";
      $("#shot-dir").textContent = `截图库：${dir} · 自动截图默认开，未入库仅临时缓存`;
    } else {
      $("#shot-dir").textContent = "截图库：data/output/shots · 自动截图默认开";
    }
    try {
      const live = await api("/api/browser/shots");
      const tmp = (live.shots || []).filter((s) => !s.committed);
      shots = shots.concat(tmp);
    } catch {
      /* ignore */
    }
    state.shots = shots;
    $("#shot-list").innerHTML =
      shots
        .slice(-40)
        .reverse()
        .map(
          (s) => `
      <div class="shot-item" data-id="${s.id}">
        <img src="/api/browser/shot-file/${encodeURIComponent(s.file || s.id + ".png")}" alt="" />
        <div class="p">${s.committed ? "" : "[临时] "}${esc(s.tag || "")} · ${new Date((s.time || 0) * 1000).toLocaleString()}<br/>${esc(s.path || s.file || "")}</div>
        <button class="mini danger" data-act="del-shot" data-id="${s.id}" title="删除">删</button>
      </div>`
        )
        .join("") || `<div class="muted">暂无截图（自动截图已开时操作页面会自动缓存，入库后持久化）</div>`;

    $("#shot-list").querySelectorAll(".shot-item").forEach((el) => {
      el.addEventListener("click", (ev) => {
        if (ev.target.closest("[data-act=del-shot]")) return;
        const s = shots.find((x) => x.id === el.dataset.id);
        if (s) showShotDetail(s);
      });
    });
    $("#shot-list").querySelectorAll("[data-act=del-shot]").forEach((btn) => {
      btn.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        const id = btn.dataset.id;
        if (!confirm("删除该截图？")) return;
        try {
          await api(`/api/browser/shots/${id}`, { method: "DELETE" });
          // 同步项目内记录
          if (state.projectId) {
            const p = await api(`/api/projects/${state.projectId}`);
            const shots2 = (p.project.shots || []).filter((x) => x.id !== id);
            await api(`/api/projects/${state.projectId}`, {
              method: "PUT",
              body: { shots: shots2 },
            });
          }
          await loadShotList();
          toast("截图已删除", "ok");
        } catch (e) {
          toast(e.message, "err");
        }
      });
    });
  } catch {
    /* ignore */
  }
}

function showShotDetail(s) {
  $("#shot-detail-path").textContent = `路径：${s.path || s.file || ""}`;
  $("#shot-detail-img").src = `/api/browser/shot-file/${encodeURIComponent(s.file || s.id + ".png")}`;
  $("#modal-shot").classList.remove("hidden");
}
$("#btn-close-shot").addEventListener("click", () => $("#modal-shot").classList.add("hidden"));

$("#auto-shot").addEventListener("change", async (e) => {
  await api("/api/browser/screenshot/auto", { method: "POST", body: { enabled: e.target.checked } });
  toast(e.target.checked ? "已开启自动截图" : "已关闭自动截图");
});

// 默认开启自动截图
$("#auto-shot").checked = true;
api("/api/browser/screenshot/auto", { method: "POST", body: { enabled: true } }).catch(() => {});

$("#btn-shot").addEventListener("click", async () => {
  try {
    await ensureBrowser();
    const r = await api("/api/browser/screenshot", { method: "POST", body: { tag: "manual" } });
    // 绑到当前节点
    if (state.selectedNodeId) {
      await api(`/api/browser/tree/node/${state.selectedNodeId}`, {
        method: "PUT",
        body: { screenshot_id: r.id, screenshot_path: r.path },
      });
      await loadTree();
    }
    await loadShotList();
    showShotDetail(r);
  } catch (e) {
    toast(e.message, "err");
  }
});

/* ================= 用例 ================= */
function renderPreview(r) {
  const list = r.cases || [];
  const mode = r.mode || "preview";
  window._lastCases = list;
  $("#case-preview").dataset.mode = mode;
  if (!list.length) {
    $("#case-preview").innerHTML =
      mode === "committed"
        ? "暂无已入库用例"
        : "暂无预览。点「预览」或「生成入库」";
    return;
  }
  const tag = mode === "committed" ? "已入库" : "未入库";
  $("#case-preview").innerHTML =
    `<div class="muted" style="padding:4px 6px">当前显示：${tag} · ${list.length} 条</div>` +
    list
      .map(
        (c, i) => `
      <div class="t case-item" data-i="${i}" style="cursor:pointer">
        <b>${esc(c.case_no ? c.case_no + " " : "")}${esc(c.title)}</b><br>
        <span class="muted">${esc(c.module_cat || c.module || "")} / ${esc(c.title_l1 || "")} / ${esc(c.title_l2 || "")} · ${c.priority || ""} · ${esc(c.case_status || "")}</span>
      </div>`
      )
      .join("");
  $("#case-preview").querySelectorAll(".case-item").forEach((el) => {
    el.addEventListener("click", () => openCaseDetail(Number(el.dataset.i)));
  });
}

function openCaseDetail(i) {
  const c = (window._lastCases || [])[i];
  if (!c) return;
  $("#cd-id").value = c.id || "";
  $("#cd-point").value = c.point_id || "";
  if (c.point_id) state.selectedNodeId = c.point_id;
  $("#cd-no").value = c.case_no || "";
  $("#cd-status").value = c.case_status || "未执行";
  $("#cd-sys").value = c.sys_name || "";
  $("#cd-mod").value = c.module_cat || c.module || "";
  $("#cd-l1").value = c.title_l1 || "/";
  $("#cd-l2").value = c.title_l2 || "/";
  $("#cd-title").value = c.title || "";
  $("#cd-design").value = c.design_req || "";
  $("#cd-track").value = c.test_track || "";
  $("#cd-pre").value = c.preconditions || "";
  $("#cd-steps").value = c.steps || "";
  $("#cd-exp").value = c.expected || "";
  $("#cd-method").value = c.method || "GET";
  $("#cd-url").value = c.url || "";
  $("#cd-params").value = c.params || c.data || "-";
  $("#cd-remark").value = c.remark || "";
  // 截图：临时/入库都显示
  const fname =
    c.screenshot_file ||
    (c.screenshot_path || "").split(/[\\/]/).pop() ||
    "";
  const shotBox = $("#shot-list");
  if (fname) {
    const url = `/api/browser/shot-file/${encodeURIComponent(fname)}`;
    shotBox.innerHTML =
      `<div class="shot-item"><img src="${url}" alt="用例截图" />
       <div class="p">${c.committed ? "" : "[临时] "}${esc(c.screenshot_path || fname)}</div></div>` +
      (shotBox.innerHTML || "");
    $("#shot-dir").textContent = "用例截图：" + (c.screenshot_path || fname);
  } else {
    $("#shot-dir").textContent =
      "当前无关联截图。自动截图开启后操作页面会生成，入库后写入截图库。";
  }
  loadShotList().then(() => {
    if (fname) {
      const url = `/api/browser/shot-file/${encodeURIComponent(fname)}`;
      $("#shot-list").insertAdjacentHTML(
        "afterbegin",
        `<div class="shot-item"><img src="${url}" alt="用例截图" />
         <div class="p">[用例关联] ${esc(c.screenshot_path || fname)}</div></div>`
      );
    }
  });
  const n = state.tree.find((x) => x.id === c.point_id);
  if (n) {
    $("#node-annotation").value = n.annotation || "";
  }
  $("#modal-case").classList.remove("hidden");
}

$("#btn-close-case") &&
  $("#btn-close-case").addEventListener("click", () => $("#modal-case").classList.add("hidden"));

/* AI 修改 */
$("#btn-ai-edit") &&
  $("#btn-ai-edit").addEventListener("click", () => {
    $("#ai-prompt").value = "";
    $("#ai-loading").classList.add("hidden");
    $("#btn-ai-generate").disabled = false;
    $("#modal-ai-edit").classList.remove("hidden");
  });
$("#btn-ai-cancel") &&
  $("#btn-ai-cancel").addEventListener("click", () => $("#modal-ai-edit").classList.add("hidden"));

$("#btn-ai-generate") &&
  $("#btn-ai-generate").addEventListener("click", async () => {
    const prompt = $("#ai-prompt").value.trim();
    if (!prompt) return toast("请填写提示词", "err");
    const fields = $$(".ai-field:checked").map((x) => x.value);
    if (!fields.length) return toast("请勾选要修改的字段", "err");
    const id = $("#cd-id").value;
    const current = {
      title: $("#cd-title").value,
      design_req: $("#cd-design").value,
      preconditions: $("#cd-pre").value,
      steps: $("#cd-steps").value,
      expected: $("#cd-exp").value,
      remark: $("#cd-remark").value,
      test_track: $("#cd-track").value,
    };
    const btn = $("#btn-ai-generate");
    btn.disabled = true;
    $("#ai-loading").classList.remove("hidden");
    try {
      const r = await api("/api/case/ai-edit", {
        method: "POST",
        body: { caseId: id, currentContent: current, prompt, fields },
      });
      const d = r.data || {};
      if (fields.includes("title") || "title" in d) $("#cd-title").value = d.title ?? $("#cd-title").value;
      if (fields.includes("design_req") || "design_req" in d) $("#cd-design").value = d.design_req ?? $("#cd-design").value;
      if (fields.includes("preconditions") || "preconditions" in d) $("#cd-pre").value = d.preconditions ?? $("#cd-pre").value;
      if (fields.includes("steps") || "steps" in d) $("#cd-steps").value = d.steps ?? $("#cd-steps").value;
      if (fields.includes("expected") || "expected" in d) $("#cd-exp").value = d.expected ?? $("#cd-exp").value;
      if (fields.includes("remark") || "remark" in d) $("#cd-remark").value = d.remark ?? $("#cd-remark").value;
      $("#modal-ai-edit").classList.add("hidden");
      toast(r.mode === "ai" ? "AI 已改写并回填，可继续手改" : "已生成建议（演示模式），请手改确认", "ok");
    } catch (e) {
      toast("AI 修改失败: " + e.message, "err");
    } finally {
      btn.disabled = false;
      $("#ai-loading").classList.add("hidden");
    }
  });

$("#btn-save-case") &&
  $("#btn-save-case").addEventListener("click", () => {
    const i = (window._lastCases || []).findIndex((x) => x.id === $("#cd-id").value);
    if (i < 0) return;
    const c = window._lastCases[i];
    Object.assign(c, {
      case_no: $("#cd-no").value,
      case_status: $("#cd-status").value,
      sys_name: $("#cd-sys").value,
      module_cat: $("#cd-mod").value,
      title_l1: $("#cd-l1").value,
      title_l2: $("#cd-l2").value,
      title: $("#cd-title").value,
      design_req: $("#cd-design").value,
      test_track: $("#cd-track").value,
      preconditions: $("#cd-pre").value,
      steps: $("#cd-steps").value,
      expected: $("#cd-exp").value,
      method: $("#cd-method").value,
      url: $("#cd-url").value,
      params: $("#cd-params").value,
      remark: $("#cd-remark").value,
      human_modified: true,
    });
    renderPreview({ cases: window._lastCases });
    $("#modal-case").classList.add("hidden");
    toast("用例已更新（导出前请再点「生成入库」或直接导出当前会话）");
  });

/* 用例操作 */
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

$("#btn-build-cases").addEventListener("click", async () => {
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

$("#btn-go-cases").addEventListener("click", async () => {
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
    const scope = new Set(ids);
    const all = r.cases || [];
    // 双保险：仅保留 scope（含子树）内用例
    window._lastCases = all.filter((c) => scope.has(c.point_id) || inScope(c.point_id, ids));
    renderPreview({ cases: window._lastCases, mode: "preview" });
    toast(`已生成 ${window._lastCases.length} 条未入库用例，请确认后点「生成入库」`, "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

$("#btn-clear-cases") &&
  $("#btn-clear-cases").addEventListener("click", () => {
    window._lastCases = [];
    $("#case-preview").innerHTML =
      '<div class="muted">已清空生成台（不影响已入库用例）</div>';
    toast("生成台已清空");
  });

/* 折叠 */
function toggleCollapse(id) {
  const body = document.getElementById(id);
  if (!body) return;
  const on = body.classList.toggle("collapsed");
  const panel = body.closest(".col");
  if (panel) {
    panel.classList.toggle("is-collapsed", on);
    const sp = panel.previousElementSibling;
    if (sp && sp.classList && sp.classList.contains("splitter")) {
      sp.classList.toggle("hidden-split", on);
    }
  }
  window.dispatchEvent(new Event("resize"));
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
}

/* init */
refreshStatus();
loadProjectList();
loadMarked();
loadTree();
loadShotList();
startLive();
loadLiveMeta();
initSplitters();
initPopout();
initZoom();
initCollapsible();

/* ================= 配置 ================= */
$("#btn-config").addEventListener("click", async () => {
  try {
    const cfg = await api("/api/config");
    $("#cfg-provider").value = cfg.ai?.provider || "openai";
    $("#cfg-base").value = cfg.ai?.base_url || "";
    $("#cfg-model").value = cfg.ai?.model || "";
    $("#cfg-vision").value = cfg.ai?.vision_model || "";
    $("#cfg-temp").value = cfg.ai?.temperature ?? 0.3;
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

/* ================= 分栏拖动 ================= */
function initSplitters() {
  const root = document.documentElement;
  const saved = JSON.parse(localStorage.getItem("qts_layout") || "{}");
  if (saved.leftW) root.style.setProperty("--left-w", saved.leftW + "px");

  const persist = () => {
    const tree = $("#tree-panel");
    const side = $("#side-panel");
    localStorage.setItem(
      "qts_layout",
      JSON.stringify({
        leftW: parseInt(getComputedStyle(root).getPropertyValue("--left-w")) || 320,
        treeH: tree ? tree.getBoundingClientRect().height : 0,
        sideH: side ? side.getBoundingClientRect().height : 0,
      })
    );
  };

  // 初始高度
  const treeEl = $("#tree-panel");
  const sideEl = $("#side-panel");
  if (treeEl && saved.treeH) {
    treeEl.style.flex = "none";
    treeEl.style.height = saved.treeH + "px";
    sideEl.style.flex = "1";
    sideEl.style.height = "auto";
  }

  $$(".splitter").forEach((sp) => {
    sp.addEventListener("pointerdown", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      sp.classList.add("active");
      try {
        sp.setPointerCapture(ev.pointerId);
      } catch {
        /* ignore */
      }
      const kind = sp.dataset.split;
      const startY = ev.clientY;
      const startX = ev.clientX;

      if (kind === "left-v") {
        const tEl = $("#tree-panel");
        const sEl = $("#side-panel");
        const stackH = $("#left-stack").getBoundingClientRect().height;
        const h0 = tEl.getBoundingClientRect().height;
        const move = (e) => {
          const minSide = 160;
          const h = Math.min(Math.max(120, h0 + (e.clientY - startY)), stackH - minSide);
          tEl.style.flex = "none";
          tEl.style.height = h + "px";
          sEl.style.flex = "0 0 auto";
          sEl.style.height = Math.max(minSide, stackH - h) + "px";
        };
        const up = () => {
          sp.classList.remove("active");
          window.removeEventListener("pointermove", move);
          window.removeEventListener("pointerup", up);
          persist();
        };
        window.addEventListener("pointermove", move);
        window.addEventListener("pointerup", up);
        return;
      }

      if (kind === "main-v") {
        const leftEl = $("#left-stack");
        const w0 = leftEl.getBoundingClientRect().width;
        const move = (e) => {
          const w = Math.min(Math.max(w0 + (e.clientX - startX), 220), 560);
          root.style.setProperty("--left-w", w + "px");
        };
        const up = () => {
          sp.classList.remove("active");
          window.removeEventListener("pointermove", move);
          window.removeEventListener("pointerup", up);
          persist();
        };
        window.addEventListener("pointermove", move);
        window.addEventListener("pointerup", up);
        return;
      }

      if (kind === "right-v" || kind === "cases-v") {
        const rightEl = $("#right-stack");
        const brow = $("#browser-col");
        const elp = $("#elements-panel");
        const cap = $("#cases-panel");
        const hb = brow.getBoundingClientRect().height;
        const he = elp.getBoundingClientRect().height;
        const hc = cap.getBoundingClientRect().height;
        const move = (e) => {
          const dy = e.clientY - startY;
          if (kind === "right-v") {
            brow.style.flex = "none";
            brow.style.height = Math.max(160, hb + dy) + "px";
            elp.style.flex = "1 1 auto";
            elp.style.height = "auto";
          } else {
            cap.style.flex = "none";
            cap.style.height = Math.max(100, hc - dy) + "px";
            elp.style.flex = "1 1 auto";
            elp.style.height = "auto";
          }
        };
        const up = () => {
          sp.classList.remove("active");
          window.removeEventListener("pointermove", move);
          window.removeEventListener("pointerup", up);
        };
        window.addEventListener("pointermove", move);
        window.addEventListener("pointerup", up);
      }
    });
  });
}

function initPopout() {
  const pop = $("#popout-browser");
  const body = $("#popout-body");
  const chromeEl = $("#browser-chrome");
  const liveWrap = document.querySelector("#browser-col .live-wrap");
  const placeholder = $("#browser-placeholder");
  const bar = $("#popout-bar");
  const resize = $("#popout-resize");

  const popOut = () => {
    if (!pop.classList.contains("hidden")) return;
    // 只搬浏览器壳+镜像，占位留在主界面
    body.appendChild(chromeEl);
    body.appendChild(liveWrap);
    pop.classList.remove("hidden");
    placeholder.classList.remove("hidden");
    // 默认比例接近 16:10
    const w = Math.min(1100, window.innerWidth * 0.72);
    const h = Math.min(720, window.innerHeight * 0.78);
    pop.style.width = w + "px";
    pop.style.height = h + "px";
    pop.style.left = Math.max(12, window.innerWidth - w - 28) + "px";
    pop.style.top = "96px";
    pop.style.right = "auto";
    toast("浏览器区已弹出，可拖动标题栏 / 右下角缩放");
    drawGhost();
  };

  const dockBack = () => {
    if (pop.classList.contains("hidden")) return;
    const host = $("#browser-col");
    host.insertBefore(chromeEl, placeholder);
    host.insertBefore(liveWrap, placeholder);
    pop.classList.add("hidden");
    placeholder.classList.add("hidden");
    drawGhost();
  };

  $("#btn-popout").addEventListener("click", popOut);
  $("#btn-popout-dock").addEventListener("click", dockBack);
  $("#btn-popout-close").addEventListener("click", dockBack);
  $("#btn-dock-back").addEventListener("click", dockBack);

  // 拖动
  bar.addEventListener("pointerdown", (e) => {
    if (e.target.closest("button")) return;
    const rect = pop.getBoundingClientRect();
    const ox = e.clientX - rect.left;
    const oy = e.clientY - rect.top;
    const move = (ev) => {
      pop.style.left = Math.max(0, ev.clientX - ox) + "px";
      pop.style.top = Math.max(0, ev.clientY - oy) + "px";
      pop.style.right = "auto";
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  });

  // 缩放
  resize.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    const rect = pop.getBoundingClientRect();
    const startX = e.clientX;
    const startY = e.clientY;
    const w0 = rect.width;
    const h0 = rect.height;
    const move = (ev) => {
      pop.style.width = Math.max(480, w0 + (ev.clientX - startX)) + "px";
      pop.style.height = Math.max(320, h0 + (ev.clientY - startY)) + "px";
      drawGhost();
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  });
}

/* ================= 镜像缩放 ================= */
let liveZoom = 1;
function applyZoom() {
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
}
function setZoom(z) {
  liveZoom = Math.min(Math.max(z, 0.5), 3);
  applyZoom();
}
function initZoom() {
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
  }
  const stage = $("#live-stage");
  stage &&
    stage.addEventListener(
      "wheel",
      (ev) => {
        if (!ev.ctrlKey) return; // 普通滚轮仍滚动页面内容
        ev.preventDefault();
        const delta = ev.deltaY > 0 ? -0.1 : 0.1;
        setZoom(liveZoom + delta);
      },
      { passive: false }
    );
}

/* init */
refreshStatus();
loadProjectList();
loadMarked();
loadTree();
loadShotList();
startLive();
loadLiveMeta();
initSplitters();
initPopout();
initZoom();
