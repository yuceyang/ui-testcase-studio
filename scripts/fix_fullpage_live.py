from pathlib import Path

# engine: full-page frame + scroll height
p = Path("app/browser/engine.py")
t = p.read_text(encoding="utf-8")
if "live_frame_full" not in t:
    t = t.replace(
        "    def live_frame(self) -> bytes:",
        '''    def live_page_height(self) -> int:
        def _inner() -> int:
            page = self._require_page()
            try:
                h = page.evaluate(
                    "() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight, innerHeight)"
                )
                return int(h or 900)
            except Exception:
                return 900

        return self._call(_inner)

    def live_frame_full(self) -> bytes:
        """整页截图，用于自适应高度展示。"""
        def _inner() -> bytes:
            page = self._require_page()
            return page.screenshot(type="jpeg", quality=70, full_page=True)

        return self._call(_inner, timeout=60)

    def live_frame(self) -> bytes:''',
    )
    p.write_text(t, encoding="utf-8")
    print("engine ok")

# routes
p = Path("app/routes_browser.py")
t = p.read_text(encoding="utf-8")
if "live/frame-full" not in t:
    t = t.replace(
        '@router.get("/live/frame")',
        '''@router.get("/live/frame-full")
def live_frame_full():
    from fastapi.responses import Response

    data = _run(lambda eng: eng.live_frame_full())
    return Response(content=data, media_type="image/jpeg")


@router.get("/live/page-height")
def live_page_height():
    return _run(lambda eng: {"height": eng.live_page_height()})


@router.get("/live/frame")''',
    )
    p.write_text(t, encoding="utf-8")
    print("routes ok")

# JS: poll full frame, remove inner scroll height lock
p = Path("static/js/browser.js")
j = p.read_text(encoding="utf-8")
j = j.replace(
    'const res = await fetch("/api/browser/live/frame", { cache: "no-store" });',
    'const res = await fetch("/api/browser/live/frame-full", { cache: "no-store" });',
)
p.write_text(j, encoding="utf-8")

# CSS
p = Path("static/css/browser.css")
c = p.read_text(encoding="utf-8")
c += """
/* 整页镜像自适应高度：内滚交给全局 */
#browser-col {
  height: auto !important;
  min-height: 600px !important;
  max-height: none !important;
  overflow: visible !important;
}
.live-wrap {
  height: auto !important;
  max-height: none !important;
  overflow: visible !important;
}
.live-stage {
  height: auto !important;
  max-height: none !important;
  overflow: visible !important;
}
#live-frame img {
  width: 100% !important;
  height: auto !important;
  max-height: none !important;
}
"""
p.write_text(c, encoding="utf-8")
print("all patched")
