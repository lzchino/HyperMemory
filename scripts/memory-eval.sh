#!/usr/bin/env bash
set -euo pipefail

# memory-eval.sh — minimal eval harness for HyperMemory
#
# Supports two JSONL formats (one object per line):
#   A) {"query":"...","expected":"...","category":"..."}
#   B) {"q":"...","minHits":1}
#
# Pass criteria:
#   - expected mode: expected substring appears in retrieve output OR files
#   - minHits mode: retrieve output has >=minHits hit lines OR query appears in files
#
# Usage:
#   scripts/memory-eval.sh [workspace]
#   scripts/memory-eval.sh [workspace] --fast
#   scripts/memory-eval.sh [workspace] --verbose

WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$PWD}}"
shift 1 || true

FAST=false
VERBOSE=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fast) FAST=true; shift ;;
    --verbose|-v) VERBOSE=true; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ ! -d "$WORKSPACE" ]]; then
  echo "Workspace not found: $WORKSPACE" >&2
  exit 2
fi

EVAL="$WORKSPACE/memory/eval-queries.jsonl"
if [[ ! -f "$EVAL" ]]; then
  echo "Eval queries not found: $EVAL" >&2
  exit 2
fi

RETRIEVE="$WORKSPACE/scripts/memory-retrieve.sh"
if [[ ! -x "$RETRIEVE" ]]; then
  # Back-compat for older installs
  if [[ -x "$WORKSPACE/scripts/retrieval/memory-retrieve.sh" ]]; then
    RETRIEVE="$WORKSPACE/scripts/retrieval/memory-retrieve.sh"
  fi
fi
if [[ ! -x "$RETRIEVE" ]]; then
  echo "Retrieve script not found/executable: $RETRIEVE" >&2
  exit 2
fi

TOTAL=0; PASS=0; FAIL=0; PASS_RETRIEVE=0; PASS_FILE=0

file_has() {
  local needle="$1"
  # Search daily files + MEMORY.md if present
  local targets=("$WORKSPACE/memory"/*.md)
  [[ -f "$WORKSPACE/MEMORY.md" ]] && targets+=("$WORKSPACE/MEMORY.md")
  grep -RIl -- "$needle" "${targets[@]}" 2>/dev/null | head -n 1
}

# Read JSONL lines and parse using python (no jq dependency)
# Use process substitution so counters update in this shell (no pipeline subshell).
while IFS=$'\t' read -r q expected category minHits; do

  [[ -z "$q" ]] && continue
  TOTAL=$((TOTAL+1))

  found_file=false
  found_retrieve=false
  out=""

  if [[ -n "$expected" ]]; then
    # expected mode
    if [[ -n "$(file_has "$expected" || true)" ]]; then
      found_file=true
    fi
    if ! $FAST && ! $found_file; then
      out=$("$RETRIEVE" auto "$q" 2>/dev/null || true)
      if echo "$out" | tr '[:upper:]' '[:lower:]' | grep -qF "$(echo "$expected" | tr '[:upper:]' '[:lower:]')"; then
        found_retrieve=true
      fi
    fi
  else
    # minHits mode
    if [[ -n "$(file_has "$(echo "$q" | head -c 80)" || true)" ]]; then
      found_file=true
    fi
    if ! $FAST; then
      out=$("$RETRIEVE" auto "$q" 2>/dev/null || true)
      hits=$(echo "$out" | grep -cE '^\[[0-9.]+\]' 2>/dev/null || echo 0)
      # also count lines that look like vector results if format differs
      if [[ "$hits" -eq 0 ]]; then
        hits=$(echo "$out" | grep -cE '^-- ' 2>/dev/null || echo 0)
      fi
      if [[ "${hits:-0}" -ge "${minHits:-1}" ]]; then
        found_retrieve=true
      fi
    fi
  fi

  if $found_retrieve; then
    PASS=$((PASS+1)); PASS_RETRIEVE=$((PASS_RETRIEVE+1))
    status="PASS(retrieve)"
  elif $found_file; then
    PASS=$((PASS+1)); PASS_FILE=$((PASS_FILE+1))
    status="PASS(file)"
  else
    FAIL=$((FAIL+1))
    status="FAIL"
  fi

  printf '%-14s %-45s [%s]\n' "$status" "$(echo "$q" | head -c 45)" "$category"
  if $VERBOSE; then
    if [[ -n "$expected" ]]; then
      echo "  expected: $expected"
    else
      echo "  minHits: $minHits"
    fi
    echo "  out: $(echo "$out" | head -c 250 | tr '\n' ' ')"
  fi

done < <(
  python3 -c 'import json,sys
p=sys.argv[1]
for raw in open(p,"r",encoding="utf-8"):
  line=raw.strip()
  if not line or line.startswith("#"):
    continue
  try:
    d=json.loads(line)
  except Exception:
    continue
  q=d.get("query") or d.get("q") or ""
  if not q:
    continue
  expected=d.get("expected") or ""
  category=d.get("category") or "unknown"
  minHits=d.get("minHits")
  if minHits is None or str(minHits).strip()=="":
    minHits=1
  print(f"{q}\t{expected}\t{category}\t{minHits}")
' "$EVAL"
)

RECALL=0
if [[ $TOTAL -gt 0 ]]; then
  RECALL=$((PASS*100/TOTAL))
fi

echo ""
echo "== summary =="
echo "total=$TOTAL pass=$PASS fail=$FAIL recall=${RECALL}%"
echo "pass_retrieve=$PASS_RETRIEVE pass_file=$PASS_FILE"
