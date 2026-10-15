from pathlib import Path
p = Path("static/js/browser.js")
t = p.read_text(encoding="utf-8")
first = t.find("async function saveProject")
second = t.find("async function saveProject", first + 1)
if second < 0:
    print("only one")
else:
    # delete second function block until next top-level function or comment
    # find next "function " after second that is at line start-ish
    rest = t[second:]
    # second saveProject body ends before "async function loadProject" or "function "
    end_rel = rest.find("\nasync function loadProject")
    if end_rel < 0:
        end_rel = rest.find("\nfunction ")
    if end_rel < 0:
        end_rel = rest.find("\n/* ")
    end = second + end_rel
    t2 = t[:second] + t[end:]
    p.write_text(t2, encoding="utf-8")
    print("removed second", len(t), len(t2), t2.count("function saveProject"))
