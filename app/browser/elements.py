"""DOM / iframe 交互元素提取。"""
from __future__ import annotations

import re
import uuid
from typing import Any


# 注入到页面（含子 frame）执行
EXTRACT_JS = r"""
() => {
  const sel = (el) => {
    if (el.id) return '#' + CSS.escape(el.id);
    if (el.name) return `[name="${el.name}"]`;
    const cls = (el.className && typeof el.className === 'string')
      ? el.className.trim().split(/\s+/).filter(c => c && !c.includes(':')).slice(0, 2)
      : [];
    let s = el.tagName.toLowerCase();
    if (cls.length) s += '.' + cls.map(c => CSS.escape(c)).join('.');
    // 加 nth 保证相对唯一
    try {
      const parent = el.parentElement;
      if (parent) {
        const same = Array.from(parent.children).filter(c => c.tagName === el.tagName);
        if (same.length > 1) s += `:nth-of-type(${same.indexOf(el) + 1})`;
      }
    } catch (e) {}
    return s;
  };

  const accessible = (el) => {
    const al = el.getAttribute && el.getAttribute('aria-label');
    if (al) return al.trim();
    const t = (el.innerText || el.textContent || '').trim();
    if (t) return t.slice(0, 80);
    const ph = el.getAttribute && el.getAttribute('placeholder');
    if (ph) return ph.trim();
    const title = el.getAttribute && el.getAttribute('title');
    if (title) return title.trim();
    const val = el.getAttribute && el.getAttribute('value');
    if (val && el.tagName === 'INPUT') return val.trim();
    return (el.getAttribute && el.getAttribute('name')) || '';
  };

  const kindOf = (el) => {
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    const role = (el.getAttribute('role') || '').toLowerCase();
    if (tag === 'button' || role === 'button' || (tag === 'a' && type === 'button')) return 'button';
    if (tag === 'input') {
      if (['text','search','number','email','password','tel','url','date','datetime-local','time','week','month'].includes(type) || !type) return 'input';
      if (type === 'button' || type === 'submit' || type === 'reset') return 'button';
      if (type === 'checkbox' || type === 'radio') return 'check';
      if (type === 'file') return 'file';
      return 'input';
    }
    if (tag === 'textarea') return 'input';
    if (tag === 'select') return 'select';
    if (tag === 'a') return 'link';
    if (el.isContentEditable) return 'input';
    return 'other';
  };

  const interactiveSelector = [
    'button', 'a[href]', 'input:not([type=hidden])', 'select', 'textarea',
    '[role=button]', '[role=tab]', '[role=menuitem]', '[role=link]',
    '[onclick]', '[ng-click]', '[data-action]', '.btn', '.ant-btn',
    'el-button', '[class*=btn]', '[class*=button]'
  ].join(',');

  const out = [];
  const nodes = document.querySelectorAll(interactiveSelector);
  for (const el of nodes) {
    try {
      if (el.disabled) {
        // 仍收集，标记 disabled
      }
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      // 隐藏元素跳过
      const style = window.getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
      out.push({
        tag: el.tagName.toLowerCase(),
        kind: kindOf(el),
        text: ((el.innerText || '') + '').trim().slice(0, 120),
        name: accessible(el).slice(0, 80),
        selector: sel(el),
        xpath: (() => {
          try {
            let p = [], n = el;
            while (n && n.nodeType === 1) {
              let i = 1, s = n.tagName.toLowerCase();
              let b = n.previousElementSibling;
              while (b) { if (b.tagName === n.tagName) i++; b = b.previousElementSibling; }
              p.unshift(s + '[' + i + ']');
              n = n.parentElement;
            }
            return '/' + p.join('/');
          } catch (e) { return ''; }
        })(),
        attrs: {
          id: el.id || '',
          name: el.getAttribute('name') || '',
          type: el.getAttribute('type') || '',
          placeholder: el.getAttribute('placeholder') || '',
          href: el.getAttribute('href') || '',
          class: (typeof el.className === 'string' ? el.className : '').slice(0, 120),
          disabled: !!el.disabled,
          readonly: el.readOnly === true,
        },
        bbox: {
          // 视口坐标：与「非整页截图」像素 1:1 对应，避免叠加错位
          x: Math.round(r.x),
          y: Math.round(r.y),
          w: Math.round(r.width),
          h: Math.round(r.height),
        },
        url: el.href || '',
      });
    } catch (e) {}
  }

  // 导航/菜单树线索
  const navHints = [];
  const navRoots = document.querySelectorAll(
    'nav, .menu, .sidebar, .el-menu, .ant-menu, [class*=menu], [class*=nav], [class*=sidebar], [role=navigation]'
  );
  for (const root of Array.from(navRoots).slice(0, 4)) {
    const links = root.querySelectorAll('a, [role=menuitem], .el-menu-item, .ant-menu-item, li');
    for (const a of Array.from(links).slice(0, 80)) {
      const text = (a.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 40);
      const href = a.getAttribute('href') || '';
      const tag = a.tagName.toLowerCase();
      if (!text && !href) continue;
      navHints.push({ text, href, tag, depth: 0 });
    }
  }

  return {
    url: location.href,
    title: document.title,
    elements: out,
    navHints: navHints.slice(0, 60),
  };
}
"""


def new_el_id() -> str:
    return "el_" + uuid.uuid4().hex[:10]


def parse_extract(raw: dict[str, Any], frame_path: str = "main", page_url: str = "") -> list[dict]:
    elements: list[dict] = []
    for item in raw.get("elements") or []:
        kind = item.get("kind") or "other"
        # 只读测试关注的交互类型
        if kind not in ("button", "input", "select", "link", "check", "file", "other"):
            continue
        bbox = item.get("bbox") or {}
        elements.append(
            {
                "id": new_el_id(),
                "frame_path": frame_path,
                "tag": item.get("tag", ""),
                "kind": kind,
                "text": (item.get("text") or "")[:120],
                "name": (item.get("name") or "")[:80],
                "selector": item.get("selector") or "",
                "xpath": item.get("xpath") or "",
                "attrs": item.get("attrs") or {},
                "bbox": bbox,
                "url": item.get("url") or "",
                "page_url": page_url,
                "marked": False,
                "note": "",
                "screenshot_id": "",
            }
        )
    return elements


def extract_nav_tree(nav_hints: list[dict]) -> list[dict]:
    """从导航线索粗提层级（菜单文字 → 树节点）。"""
    seen = set()
    nodes = []
    for h in nav_hints:
        text = (h.get("text") or "").strip()
        if not text or len(text) < 2:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        nodes.append({"name": text, "href": h.get("href") or "", "tag": h.get("tag") or ""})
    return nodes


def classify_kind_label(kind: str) -> str:
    return {
        "button": "按钮",
        "input": "输入框",
        "select": "下拉框",
        "link": "链接",
        "check": "勾选/单选",
        "file": "上传",
        "other": "其他",
    }.get(kind, kind)
