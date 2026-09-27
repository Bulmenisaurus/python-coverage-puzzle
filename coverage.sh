#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CPYTHON="${CPYTHON:-$(cd "$ROOT/../cpython" && pwd)}"
SCRIPT="$(realpath "$1")"
OUT="${2:-output.json}"
TARGET="Objects/listobject.c"

if [[ ! -x "$CPYTHON/python" ]]; then
  echo "coverage python missing: $CPYTHON/python" >&2
  exit 1
fi

# Instrumented python writes *.gcda on every exit, including --version.
# Read the source tree instead of executing it.
version="$(sed -n 's/^#define PY_VERSION[[:space:]]*"\([0-9.]*\).*/\1/p' "$CPYTHON/Include/patchlevel.h")"
case "$version" in
  3.14.*) ;;
  *) echo "expected CPython 3.14, found $version in $CPYTHON" >&2; exit 1 ;;
esac

# Previous runs merge into these files. .gcno must stay; it is the compile-time graph.
find "$CPYTHON" -name '*.gcda' -delete
find "$CPYTHON" -name '*.gcov' -delete
find "$CPYTHON" -name '*.gcov.json.gz' -delete

RUNDIR="$(mktemp -d)"
trap 'rm -rf "$RUNDIR"' EXIT

# /home/.../cpython/Objects/listobject.gcda -> $RUNDIR/Objects/listobject.gcda
strip="$(awk -F/ '{print NF-1}' <<<"$CPYTHON")"
export GCOV_PREFIX="$RUNDIR"
export GCOV_PREFIX_STRIP="$strip"

# A failing script still executed lines; keep going and report those.
set +e
"$CPYTHON/python" -I -S "$SCRIPT"
set -e

mkdir -p "$RUNDIR/Objects"
ln -s "$CPYTHON/Objects/listobject.gcno" "$RUNDIR/Objects/listobject.gcno"

# --stdout avoids the header *.gcov files. cwd must be the CPython root
# so gcov can open the relative path stored in the .gcno.
(
  cd "$CPYTHON"
  gcov --stdout -o "$RUNDIR/Objects" "$TARGET"
) | python3 "$ROOT/parse_gcov.py" - listobject.c > "$OUT"

python3 - "$OUT" << 'PY' >&2
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
targets, hit, missed = len(data["targets"]), len(data["hit"]), len(data["missed"])
coverage = 100.0 * hit / targets if targets else 0.0
print(f"wrote {sys.argv[1]}")
print(f"targets {targets}")
print(f"hit {hit}")
print(f"missed {missed}")
print(f"coverage {coverage:.1f}%")
PY
