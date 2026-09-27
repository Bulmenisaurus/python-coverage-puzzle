#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CPYTHON = Path(os.environ.get("CPYTHON", ROOT.parent / "cpython"))
BASELINES = ROOT / "baselines"
CACHE = BASELINES / ".cache"
OUT = ROOT / "baseline_coverage.json"
GCNO = CPYTHON / "Objects" / "listobject.gcno"


def newer(path, than):
    return path.is_file() and path.stat().st_mtime > than.stat().st_mtime


def wrap(numbers):
    lines = []
    current = "    "
    last = len(numbers) - 1
    for index, number in enumerate(numbers):
        piece = str(number) + ("," if index < last else "")
        if current.strip() and len(current) + 1 + len(piece) > 80:
            lines.append(current.rstrip())
            current = "    " + piece
        elif current.strip():
            current += " " + piece
        else:
            current += piece
    if current.strip():
        lines.append(current.rstrip())
    return "[\n" + "\n".join(lines) + "\n  ]"


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    scripts = sorted(BASELINES.glob("*.py"))
    if not scripts:
        print(f"no scripts in {BASELINES}", file=sys.stderr)
        return 1

    for script in scripts:
        cache = CACHE / f"{script.stem}.json"
        if not cache.is_file() or newer(script, cache) or newer(GCNO, cache):
            print(f"rebuild {script.stem}", file=sys.stderr)
            subprocess.run(
                [ROOT / "coverage.sh", str(script), str(cache)],
                check=True,
            )
        else:
            print(f"cached {script.stem}", file=sys.stderr)

    runs = []
    for script in scripts:
        path = CACHE / f"{script.stem}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        runs.append((script.name, data))

    targets = runs[0][1]["targets"]
    for name, data in runs[1:]:
        if data["targets"] != targets:
            print(
                f"{name} targets differ from {runs[0][0]}; delete baselines/.cache and rerun",
                file=sys.stderr,
            )
            return 1

    target_set = set(targets)
    hit = set()
    for name, data in runs:
        extra = set(data["hit"]) - target_set
        if extra:
            sample = ", ".join(map(str, sorted(extra)[:5]))
            print(f"{name} has hits outside targets: {sample}", file=sys.stderr)
            return 1
        hit.update(data["hit"])

    hit_list = [n for n in targets if n in hit]
    missed = [n for n in targets if n not in hit]
    text = (
        "{\n"
        f'  "targets": {wrap(targets)},\n'
        f'  "hit": {wrap(hit_list)},\n'
        f'  "missed": {wrap(missed)}\n'
        "}\n"
    )
    OUT.write_text(text, encoding="utf-8")

    total, hit_n, missed_n = len(targets), len(hit_list), len(missed)
    coverage = 100.0 * hit_n / total if total else 0.0
    print(f"wrote {OUT.name}", file=sys.stderr)
    for name, data in runs:
        print(f"  {name} hit {len(data['hit'])}", file=sys.stderr)
    print(f"targets {total}", file=sys.stderr)
    print(f"hit {hit_n}", file=sys.stderr)
    print(f"missed {missed_n}", file=sys.stderr)
    print(f"coverage {coverage:.1f}%", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
