"""合并：把 prj_1d4729fd69 的树并入 等保2.0，并绑定用例。"""
from pathlib import Path
import json
from datetime import datetime

root = Path("data/projects")
p_tree = json.loads((root / "prj_1d4729fd69" / "project.json").read_text(encoding="utf-8"))
p_cases = json.loads((root / "prj_c741c9baf2" / "project.json").read_text(encoding="utf-8"))

tree = p_tree.get("tree") or []
cases = p_cases.get("cases") or []
tree_ids = {n.get("id") for n in tree}
points = [n for n in tree if n.get("node_type") in ("point", "case")]

bound = 0
for c in cases:
    if c.get("point_id") in tree_ids:
        bound += 1
        continue
    title = c.get("title") or ""
    hit = next((p for p in points if p.get("name") and p["name"] in title), None)
    if hit:
        c["point_id"] = hit["id"]
        bound += 1
    else:
        c["point_id"] = "__unbound__"

merged = dict(p_cases)
merged["name"] = "等保2.0"
merged["tree"] = tree
merged["cases"] = cases
merged["marked_elements"] = (p_tree.get("marked_elements") or []) + (p_cases.get("marked_elements") or [])
merged["updated_at"] = datetime.now().timestamp()
Path("data/projects/prj_c741c9baf2/project.json").write_text(
    json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("merged tree", len(tree), "cases", len(cases), "bound", bound)
# 删除被拆出来的空壳项目（只含树、已并入）
import shutil
shutil.rmtree("data/projects/prj_1d4729fd69", ignore_errors=True)
print("removed prj_1d4729fd69")
