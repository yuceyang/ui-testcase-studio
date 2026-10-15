from pathlib import Path
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
first = t.find("function renderTree")
second = t.find("function renderTree", first + 1)
assert first >= 0 and second > first
# keep second block: from second to end of that function (next function after it)
# The first renderTree ends before second
t2 = t[:first] + t[second:]
# also remove the orphan showCasesForNode if duplicated
p.write_text(t2, encoding="utf-8")
print("removed first renderTree", len(t), "->", len(t2))
print("count now", t2.count("function renderTree"))
