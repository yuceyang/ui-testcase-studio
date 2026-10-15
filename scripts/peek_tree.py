from pathlib import Path
t = Path("app/browser/tree.py").read_text(encoding="utf-8")
print("count", t.count("def build_cases_from_tree"))
i = t.find("def build_cases_from_tree")
print("at", i)
print(t[i:i+100])
# cut old function: from second def or first def after import
idx = t.find("from .case_builder import")
print("import at", idx)
print(t[idx:idx+80])
