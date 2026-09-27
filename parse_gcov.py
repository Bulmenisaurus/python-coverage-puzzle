import json
import re
import sys

count_re = re.compile(r"^\s*([^:]+):\s*(\d+):")
source_re = re.compile(r"^\s*-:\s*0:Source:(.*)$")

path = sys.argv[1]
only = sys.argv[2] if len(sys.argv) > 2 else None
lines = sys.stdin if path == "-" else open(path, encoding="utf-8")

active = only is None
status = {}

for line in lines:
    source = source_re.match(line)
    if source:
        name = source.group(1).strip()
        active = only is None or name.endswith(only)
        continue
    if not active:
        continue

    match = count_re.match(line)
    if not match:
        continue

    count, lineno = match.group(1).strip(), int(match.group(2))
    if lineno == 0 or count == "-":
        continue

    # "#####" / "=====" are executable lines gcov saw and did not run.
    # A trailing "*" means the line ran, but not every block on it.
    hit = count not in {"#####", "====="}
    if status.get(lineno) == "hit":
        continue
    status[lineno] = "hit" if hit else "miss"

targets = sorted(status)
print(json.dumps({
    "targets": targets,
    "hit": [n for n in targets if status[n] == "hit"],
    "missed": [n for n in targets if status[n] == "miss"],
}))
