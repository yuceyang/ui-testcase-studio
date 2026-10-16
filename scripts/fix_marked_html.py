from pathlib import Path
p = Path("static/index.html")
t = p.read_text(encoding="utf-8")
t = t.replace('id="marked-body" class="collapse-body"', 'id="marked-body" class="collapse-body grow"')
p.write_text(t, encoding="utf-8")
print("ok", 'marked-body" class="collapse-body grow"' in t or "collapse-body grow" in t)
