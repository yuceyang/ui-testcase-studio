/* 软件功能测试系统 — 前端交互 */
"use strict";

const state = {
  sessionId: "",
  points: [],
  cases: [],
  config: null,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

/* ---------- 工具 ---------- */
function toast(msg, type = "") {
  const el = $("#toast");
  el.textContent = msg;
  el.className = "toast " + type;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add("hidden"), 3200);
}

function showLog(sel, text, scroll = true) {
  const el = $(sel);
  if (!el) return;
  el.classList.remove("hidden");
  el.textContent = text;
  if (scroll) el.scrollTop = el.scrollHeight;
}

function appendLog(sel, line) {
  const el = $(sel);
  if (!el) return;
  el.classList.remove("hidden");
  el.textContent += (el.textContent ? "\n" : "") + line;
  el.scrollTop = el.scrollHeight;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
  if (!res.ok) {
    const msg = data.detail || data.message || data.raw || res.statusText;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

/* ---------- 步骤切换 ---------- */
function gotoPanel(id) {
  $$(".panel").forEach((p) => p.classList.remove("active"));
  $$(".step").forEach((s) => s.classList.remove("active"));
  const panel = $("#" + id);
  if (panel) panel.classList.add("active");
  const step = $(`.step[data-panel="${id}"]`);
  if (step) step.classList.add("active");
}

$$(".step").forEach((btn) => {
  btn.addEventListener("click", () => gotoPanel(btn.dataset.panel));
});

/* ---------- 鉴权模式 ---------- */
const authBlocks = {
  cookie: "#auth-cookie",
  bearer: "#auth-bearer",
  basic: "#auth-basic",
  api_key: "#auth-apikey",
  custom_headers: "#auth-custom",
  none: null,
};

$("#auth-mode").addEventListener("change", (e) => {
  Object.values(authBlocks).forEach((sel) => {
    if (sel) $(sel).classList.add("hidden");
  });
  const sel = authBlocks[e.target.value];
  if (sel) $(sel).classList.remove("hidden");
});

function collectAuth() {
  const mode = $("#auth-mode").value;
  const headers = {};
  const customText = $("#auth-custom-val").value.trim();
  if (customText) {
    customText.split(/\r?\n/).forEach((line) => {
      const i = line.indexOf(":");
      if (i > 0) headers[line.slice(0, i).trim()] = line.slice(i + 1).trim();
    });
  }
  return {
    mode,
    cookie: $("#auth-cookie-val").value.trim(),
    token: $("#auth-token").value.trim(),
    username: $("#auth-user").value.trim(),
    password: $("#auth-pass").value,
    api_key_header: $("#auth-key-h").value.trim() || "Authorization",
    api_key_value: $("#auth-key-v").value.trim(),
    custom_headers: headers,
  };
}

/* ---------- 1. 发现 ---------- */
$("#btn-discover").addEventListener("click", async () => {
  const base_url = $("#base-url").value.trim();
  if (!base_url) {
    toast("请填写系统入口 URL", "err");
    return;
  }
  const seed_urls = $("#seed-urls").value
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean);

  const btn = $("#btn-discover");
  btn.disabled = true;
  btn.textContent = "发现中…";
  showLog("#discover-log", "开始只读抓取与功能点分析…");

  try {
    const result = await api("/api/discover", {
      method: "POST",
      body: { base_url, auth: collectAuth(), seed_urls },
    });
    state.sessionId = result.session_id;
    state.points = result.functional_points || [];
    renderPoints();

    const w = (result.warnings || []).map((x) => "[提示] " + x).join("\n");
    showLog(
      "#discover-log",
      `完成。\n会话: ${result.session_id}\n功能点: ${result.total} 个\n` +
        `统计: ${JSON.stringify(result.stats || {}, null, 2)}\n` +
        (w ? "\n" + w : "")
    );
    toast(`发现 ${result.total} 个功能点`, "ok");
    gotoPanel("panel-points");
  } catch (e) {
    showLog("#discover-log", "[失败] " + e.message);
    toast("发现失败: " + e.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "开始发现功能点";
  }
});

/* ---------- 2. 功能点表 ---------- */
function renderPoints() {
  const tbody = $("#points-table tbody");
  const filter = ($("#points-filter").value || "").toLowerCase();
  const source = $("#points-source").value;

  const rows = state.points.filter((p) => {
    if (source && p.source !== source) return false;
    if (!filter) return true;
    const blob = `${p.name} ${p.url} ${p.path} ${(p.tags || []).join(" ")}`.toLowerCase();
    return blob.includes(filter);
  });

  $("#points-count").textContent = `共 ${state.points.length} 条，显示 ${rows.length} 条`;
  $("#points-empty").style.display = rows.length ? "none" : "block";
  $("#points-table").style.display = rows.length ? "table" : "none";

  tbody.innerHTML = rows
    .map(
      (p) => `
    <tr data-id="${p.id}">
      <td><input type="checkbox" class="pt-sel" ${p.selected ? "checked" : ""} data-id="${p.id}" /></td>
      <td><span class="tag ${p.source}">${p.source}</span></td>
      <td>${p.method}</td>
      <td><div class="name">${esc(p.name)}</div><div class="url">${esc(p.path || "")}</div></td>
      <td class="url">${esc(p.url)}</td>
      <td>${esc((p.summary || "").slice(0, 80))}${p.notes ? `<br><em>${esc(p.notes)}</em>` : ""}</td>
      <td>
        <button class="link-btn" data-act="edit" data-id="${p.id}">编辑</button>
        <button class="link-btn danger" data-act="del" data-id="${p.id}">删除</button>
      </td>
    </tr>`
    )
    .join("");

  tbody.querySelectorAll(".pt-sel").forEach((cb) => {
    cb.addEventListener("change", () => {
      const p = state.points.find((x) => x.id === cb.dataset.id);
      if (p) p.selected = cb.checked;
    });
  });

  tbody.querySelectorAll("button[data-act]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.id;
      if (btn.dataset.act === "edit") openPointEditor(id);
      else {
        state.points = state.points.filter((p) => p.id !== id);
        renderPoints();
      }
    });
  });
}

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

$("#points-filter").addEventListener("input", renderPoints);
$("#points-source").addEventListener("change", renderPoints);

$("#btn-sel-all").addEventListener("click", () => {
  state.points.forEach((p) => (p.selected = true));
  renderPoints();
});
$("#btn-sel-none").addEventListener("click", () => {
  state.points.forEach((p) => (p.selected = false));
  renderPoints();
});
$("#btn-del-selected").addEventListener("click", () => {
  const n = state.points.filter((p) => p.selected).length;
  if (!n) return toast("未勾选", "err");
  if (!confirm(`确认删除 ${n} 个勾选功能点？`)) return;
  state.points = state.points.filter((p) => !p.selected);
  renderPoints();
});

function openPointEditor(id) {
  const p = state.points.find((x) => x.id === id);
  if (!p) return;
  $("#mp-id").value = p.id;
  $("#mp-name").value = p.name || "";
  $("#mp-url").value = p.url || "";
  $("#mp-summary").value = p.summary || "";
  $("#mp-notes").value = p.notes || "";
  $("#modal-point").classList.remove("hidden");
}

$("#btn-close-point").addEventListener("click", () => $("#modal-point").classList.add("hidden"));
$("#btn-save-point").addEventListener("click", () => {
  const id = $("#mp-id").value;
  const p = state.points.find((x) => x.id === id);
  if (!p) return;
  p.name = $("#mp-name").value.trim();
  p.url = $("#mp-url").value.trim();
  p.summary = $("#mp-summary").value.trim();
  p.notes = $("#mp-notes").value.trim();
  $("#modal-point").classList.add("hidden");
  renderPoints();
  toast("功能点已更新（内存）", "ok");
});

$("#btn-to-generate").addEventListener("click", () => {
  const n = state.points.filter((p) => p.selected).length;
  if (!n) return toast("请至少勾选一个功能点", "err");
  toast(`已选中 ${n} 个功能点`);
  gotoPanel("panel-generate");
});

/* ---------- 3. 生成 ---------- */
$("#opt-vision").addEventListener("change", (e) => {
  $("#vision-block").classList.toggle("hidden", !e.target.checked);
});

$("#btn-generate").addEventListener("click", async () => {
  if (!state.sessionId) {
    toast("请先完成功能点发现", "err");
    gotoPanel("panel-auth");
    return;
  }
  const selected = state.points.filter((p) => p.selected);
  if (!selected.length) return toast("未勾选功能点", "err");

  const useVision = $("#opt-vision").checked;
  const paths = $("#vision-paths").value
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter(Boolean);

  const btn = $("#btn-generate");
  btn.disabled = true;
  btn.textContent = "AI 生成中…";
  showLog("#generate-log", "调用 AI 生成查询类测试用例，请稍候…\n（可能需要 10–60 秒）");

  try {
    const result = await api("/api/generate", {
      method: "POST",
      body: {
        session_id: state.sessionId,
        point_ids: selected.map((p) => p.id),
        use_vision: useVision,
        screenshot_paths: paths,
        extra: {
          text: $("#extra-text").value,
          focus_modules: $("#extra-focus").value
            .split(/[,，、]/)
            .map((s) => s.trim())
            .filter(Boolean),
          include_negative: $("#opt-negative").checked,
          include_auth_cases: $("#opt-auth").checked,
          max_cases_per_point: Number($("#extra-max").value) || 8,
        },
      },
    });
    state.cases = result.cases || [];
    renderCases();
    const w = (result.warnings || []).map((x) => "[警告] " + x).join("\n");
    showLog(
      "#generate-log",
      `生成完成。\n模型: ${result.model}\n用例: ${result.cases.length} 条\n` +
        `摘要: ${result.raw_summary || "—"}\n` + (w ? "\n" + w : "")
    );
    toast(`已生成 ${state.cases.length} 条用例`, "ok");
    gotoPanel("panel-cases");
  } catch (e) {
    showLog("#generate-log", "[失败] " + e.message);
    toast("生成失败: " + e.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "调用 AI 生成用例";
  }
});

/* ---------- 4. 用例 ---------- */
const catLabel = {
  positive: "正向",
  negative: "异常",
  boundary: "边界",
  auth: "鉴权",
  performance: "性能",
};

function renderCases() {
  const wrap = $("#cases-list");
  const filter = ($("#cases-filter").value || "").toLowerCase();
  const prio = $("#cases-priority").value;
  const cat = $("#cases-category").value;

  const rows = state.cases.filter((c) => {
    if (prio && c.priority !== prio) return false;
    if (cat && c.category !== cat) return false;
    if (!filter) return true;
    return `${c.title} ${c.module} ${c.url}`.toLowerCase().includes(filter);
  });

  $("#cases-count").textContent = `共 ${state.cases.length} 条，显示 ${rows.length} 条`;
  $("#cases-empty").style.display = rows.length ? "none" : "block";

  wrap.innerHTML = rows
    .map(
      (c) => `
    <div class="case ${c.approved ? "" : "rejected"}" data-id="${c.id}">
      <div class="case-head">
        <input type="checkbox" class="case-sel" data-id="${c.id}" />
        <div class="case-title">${esc(c.title)}</div>
        <span class="tag prio-${c.priority}">${c.priority}</span>
        <span class="tag">${catLabel[c.category] || c.category}</span>
        ${c.human_modified ? '<span class="tag page">已人工修改</span>' : ""}
      </div>
      <div class="case-meta">
        <span>模块: ${esc(c.module)}</span>
        <span>方法: ${c.method}</span>
        <span>通过审阅: ${c.approved ? "是" : "否"}</span>
      </div>
      <div class="case-body">
        <div><b>前置条件</b>${esc(c.preconditions) || "—"}</div>
        <div><b>测试数据</b>${esc(c.data) || "—"}</div>
        <div><b>操作步骤</b>${esc(c.steps) || "—"}</div>
        <div><b>预期结果</b>${esc(c.expected) || "—"}</div>
        <div><b>URL</b><span style="word-break:break-all">${esc(c.url)}</span></div>
        <div><b>鉴权 / 理由</b>${esc(c.auth_notes) || "—"}${c.ai_rationale ? "<br>" + esc(c.ai_rationale) : ""}</div>
      </div>
      <div class="case-actions">
        <button class="btn" data-act="edit" data-id="${c.id}">编辑</button>
        <button class="btn" data-act="approve" data-id="${c.id}">${c.approved ? "取消通过" : "标记通过"}</button>
        <button class="btn danger" data-act="del" data-id="${c.id}">删除</button>
      </div>
    </div>`
    )
    .join("");

  wrap.querySelectorAll("button[data-act]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      const c = state.cases.find((x) => x.id === id);
      if (!c) return;
      const act = btn.dataset.act;
      try {
        if (act === "edit") {
          openCaseEditor(c);
        } else if (act === "approve") {
          await api(`/api/session/${state.sessionId}/cases/${id}/approve`, {
            method: "POST",
            body: { approved: !c.approved },
          });
          c.approved = !c.approved;
          renderCases();
          toast(c.approved ? "已通过" : "已取消通过");
        } else if (act === "del") {
          if (!confirm("确认删除该用例？")) return;
          await api(`/api/session/${state.sessionId}/cases/${id}`, { method: "DELETE" });
          state.cases = state.cases.filter((x) => x.id !== id);
          renderCases();
          toast("已删除");
        }
      } catch (e) {
        toast(e.message, "err");
      }
    });
  });
}

$("#cases-filter").addEventListener("input", renderCases);
$("#cases-priority").addEventListener("change", renderCases);
$("#cases-category").addEventListener("change", renderCases);

$("#btn-del-cases").addEventListener("click", async () => {
  const ids = $$(".case-sel:checked").map((x) => x.dataset.id);
  if (!ids.length) return toast("未勾选用例", "err");
  if (!confirm(`确认删除 ${ids.length} 条用例？`)) return;
  for (const id of ids) {
    await api(`/api/session/${state.sessionId}/cases/${id}`, { method: "DELETE" });
  }
  state.cases = state.cases.filter((c) => !ids.includes(c.id));
  renderCases();
  toast(`已删除 ${ids.length} 条`, "ok");
});

$("#btn-regen").addEventListener("click", async () => {
  const caseIds = $$(".case-sel:checked").map((x) => x.dataset.id);
  if (!caseIds.length) return toast("请勾选要重新生成的用例", "err");
  const btn = $("#btn-regen");
  btn.disabled = true;
  try {
    const result = await api(`/api/session/${state.sessionId}/cases/regenerate`, {
      method: "POST",
      body: {
        case_ids: caseIds,
        extra: {
          text: $("#extra-text").value,
          include_negative: $("#opt-negative").checked,
          include_auth_cases: $("#opt-auth").checked,
          max_cases_per_point: Number($("#extra-max").value) || 8,
        },
      },
    });
    state.cases = result.cases || state.cases;
    renderCases();
    toast("已重新生成", "ok");
  } catch (e) {
    toast(e.message, "err");
  } finally {
    btn.disabled = false;
  }
});

function openCaseEditor(c) {
  $("#mc-id").value = c.id;
  $("#mc-title").value = c.title || "";
  $("#mc-module").value = c.module || "";
  $("#mc-priority").value = c.priority || "P1";
  $("#mc-category").value = c.category || "positive";
  $("#mc-pre").value = c.preconditions || "";
  $("#mc-steps").value = c.steps || "";
  $("#mc-expected").value = c.expected || "";
  $("#mc-data").value = c.data || "";
  $("#mc-method").value = c.method || "GET";
  $("#mc-url").value = c.url || "";
  $("#mc-auth").value = c.auth_notes || "";
  $("#mc-rationale").value = c.ai_rationale || "";
  $("#modal-case").classList.remove("hidden");
}

$("#btn-close-case").addEventListener("click", () => $("#modal-case").classList.add("hidden"));
$("#btn-save-case").addEventListener("click", async () => {
  const id = $("#mc-id").value;
  const c = state.cases.find((x) => x.id === id);
  if (!c) return;
  const payload = {
    id: c.id,
    point_id: c.point_id,
    title: $("#mc-title").value.trim(),
    module: $("#mc-module").value.trim(),
    priority: $("#mc-priority").value,
    category: $("#mc-category").value,
    preconditions: $("#mc-pre").value.trim(),
    steps: $("#mc-steps").value.trim(),
    expected: $("#mc-expected").value.trim(),
    data: $("#mc-data").value.trim(),
    method: $("#mc-method").value,
    url: $("#mc-url").value.trim(),
    auth_notes: $("#mc-auth").value.trim(),
    ai_rationale: $("#mc-rationale").value.trim(),
    approved: c.approved,
    human_modified: true,
  };
  try {
    const updated = await api(`/api/session/${state.sessionId}/cases/${id}`, {
      method: "PUT",
      body: payload,
    });
    Object.assign(c, updated);
    $("#modal-case").classList.add("hidden");
    renderCases();
    toast("用例已保存", "ok");
  } catch (e) {
    toast(e.message, "err");
  }
});

$("#btn-to-export").addEventListener("click", () => gotoPanel("panel-export"));

/* ---------- 5. 导出 ---------- */
async function doExport(fmt) {
  if (!state.sessionId) return toast("无会话", "err");
  try {
    const result = await api("/api/export", {
      method: "POST",
      body: { session_id: state.sessionId, format: fmt },
    });
    const name = result.path.split(/[\\/]/).pop();
    appendLog("#export-log", `已导出 ${result.count} 条 → ${name}`);
    $("#export-files").innerHTML =
      `<li><a href="/api/export/download/${encodeURIComponent(name)}" download>${name}</a><span>${result.count} 条</span></li>` +
      $("#export-files").innerHTML;
    toast("导出成功", "ok");
  } catch (e) {
    toast(e.message, "err");
    appendLog("#export-log", "[失败] " + e.message);
  }
}

$("#btn-export-xlsx").addEventListener("click", () => doExport("xlsx"));
$("#btn-export-md").addEventListener("click", () => doExport("md"));
$("#btn-export-csv").addEventListener("click", () => doExport("csv"));

/* ---------- 配置 ---------- */
async function loadConfig() {
  try {
    const cfg = await api("/api/config");
    state.config = cfg;
    $("#cfg-provider").value = cfg.ai?.provider || "openai";
    $("#cfg-base").value = cfg.ai?.base_url || "";
    $("#cfg-key").value = "";
    $("#cfg-key").placeholder = cfg.ai?.api_key ? `已配置 ${cfg.ai.api_key}` : "sk-...";
    $("#cfg-model").value = cfg.ai?.model || "";
    $("#cfg-vision").value = cfg.ai?.vision_model || "";
    $("#cfg-temp").value = cfg.ai?.temperature ?? 0.3;
    $("#vision-model-label").textContent = cfg.ai?.vision_model || cfg.ai?.model || "-";
  } catch {
    /* ignore */
  }
}

$("#btn-config").addEventListener("click", () => {
  loadConfig();
  $("#modal-config").classList.remove("hidden");
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
    toast("配置已更新", "ok");
    $("#modal-config").classList.add("hidden");
    $("#vision-model-label").textContent = body.ai.vision_model;
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

$("#btn-ai-test").addEventListener("click", async () => {
  const btn = $("#btn-ai-test");
  btn.disabled = true;
  btn.textContent = "测试中…";
  try {
    const r = await api("/api/ai/test", { method: "POST", body: {} });
    if (r.ok) toast(`AI 连通正常：${r.reply || "OK"}`, "ok");
    else toast("AI 不可用: " + (r.error || "未知错误"), "err");
  } catch (e) {
    toast(e.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "测试 AI 连通";
  }
});

/* ---------- 健康检查 ---------- */
async function health() {
  const el = $("#health-badge");
  try {
    const h = await api("/api/health");
    el.textContent = `${h.ai_provider} · ${h.ai_model} · ${h.policy === "query_only" ? "只读查询" : h.policy}`;
    el.className = "badge ok";
    $("#vision-model-label").textContent = h.vision_model || h.ai_model;
  } catch {
    el.textContent = "服务异常";
    el.className = "badge err";
  }
}

/* ---------- 启动 ---------- */
health();
loadConfig();
