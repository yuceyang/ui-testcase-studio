from pathlib import Path

p = Path("app/routes_browser.py")
t = p.read_text(encoding="utf-8")
if "allow = set(pids)" in t:
    start = t.find('    pids = set(payload.get("point_ids") or [])')
    end = t.find('    return {\n        "ok": True,\n        "count": len(cases),', start)
    new = """    pids = set(payload.get("point_ids") or [])
    if pids:
        from .browser.tree import path_of

        def _hit(c):
            if c.point_id in pids:
                return True
            return any(n.get("id") in pids for n in path_of(c.point_id, tree))

        cases = [c for c in cases if _hit(c)]

"""
    if start > 0 and end > start:
        p.write_text(t[:start] + new + t[end:], encoding="utf-8")
        print("simplified")
    else:
        print("bounds", start, end)
else:
    print("ok already")
