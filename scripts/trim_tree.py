from pathlib import Path
p = Path("app/browser/tree.py")
t = p.read_text(encoding="utf-8")
start = t.find("def build_cases_from_tree")
assert start > 0
# keep everything before old builder; if auto_tree after builder, keep from auto_tree
nxt = t.find("def auto_tree_from_nav", start)
if nxt > start:
    # remove old builder but keep auto_tree onward
    t2 = t[:start] + t[nxt:]
else:
    t2 = t[:start].rstrip() + "\n"
# ensure import remains
assert "from .case_builder import build_cases_from_tree" in t2
p.write_text(t2, encoding="utf-8")
print("trimmed", len(t), "->", len(t2))
