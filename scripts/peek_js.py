from pathlib import Path
t = Path("static/js/browser.js").read_text(encoding="utf-8")
i = t.find('kind === "right-v"')
print(t[i:i+520])
