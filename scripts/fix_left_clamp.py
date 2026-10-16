from pathlib import Path
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
start = t.find('if (kind === "left-v") {')
end = t.find('if (kind === "main-v")', start)
if start < 0 or end < 0:
    print("bounds", start, end)
else:
    new = '''if (kind === "left-v") {
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

      '''
    p.write_text(t[:start] + new + t[end:], encoding="utf-8")
    print("js clamp ok")
