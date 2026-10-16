from pathlib import Path
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
start = t.find("function initSplitters()")
end = t.find("function initPopout()")
if end < 0:
    end = t.find("function initZoom()")
assert start > 0 and end > start
new = r'''function initSplitters() {
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
        const h0 = tEl.getBoundingClientRect().height;
        const move = (e) => {
          const h = Math.max(80, h0 + (e.clientY - startY));
          tEl.style.flex = "none";
          tEl.style.height = h + "px";
          sEl.style.flex = "1 1 auto";
          sEl.style.height = "auto";
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

'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("initSplitters rewritten")
