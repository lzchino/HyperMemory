#!/usr/bin/env bash
set -euo pipefail

# pre-response-check.sh — fast evidence check before answering memory-dependent questions.
#
# Exit codes:
#   0 = OK to answer
#   1 = gaps detected (run retrieval / checkpoint)
#   2 = usage/config error

WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$PWD}}"

if [[ ! -d "$WORKSPACE" ]]; then
  echo "Workspace not found: $WORKSPACE" >&2
  exit 2
fi

STATE="$WORKSPACE/memory/session-state.json"
BUF="$WORKSPACE/memory/last-messages.jsonl"
DB="$WORKSPACE/memory/supermemory.sqlite"

say() { printf '%s\n' "$*"; }

GAPS=0
say "== pre-response evidence check =="
say "workspace: $WORKSPACE"

# 1) session state
if [[ ! -f "$STATE" ]]; then
  say "GAP: missing session-state.json (no continuity)"
  GAPS=1
else
  # check staleness (8h)
  last=$(python3 -c 'import json,sys,time
p=sys.argv[1]
try:
  d=json.load(open(p))
  v=int(d.get("lastActivity",0))
except Exception:
  v=0
print(v)
' "$STATE")
  now=$(python3 -c 'import time; print(int(time.time()*1000))')
  age_ms=$((now - last))
  if [[ "$last" -le 0 || "$age_ms" -gt $((8*60*60*1000)) ]]; then
    say "WARN: session-state.json stale (>8h)"
  fi
fi

# 2) message buffer
if [[ ! -f "$BUF" ]]; then
  say "WARN: missing last-messages.jsonl (buffer not active)"
else
  # ensure recent message logged within 2h
  last_ts=$(tail -n 1 "$BUF" | python3 -c 'import json,sys
try:
  d=json.loads(sys.stdin.read() or "{}")
  print(int(d.get("ts",0)))
except Exception:
  print(0)
')
  now=$(python3 -c 'import time; print(int(time.time()*1000))')
  age_ms=$((now - last_ts))
  if [[ "$last_ts" -le 0 || "$age_ms" -gt $((2*60*60*1000)) ]]; then
    say "WARN: message buffer appears stale (>2h since last append)"
  fi
fi

# 3) FTS index exists
if [[ ! -f "$DB" ]]; then
  say "GAP: missing SQLite index ($DB). Run: ./scripts/memory-index.sh <ws>  (or: hypermemory --workspace <ws> index)"
  GAPS=1
fi

if [[ "$GAPS" -eq 0 ]]; then
  say "OK"
  exit 0
fi

say ""
say "Next actions:"
say "- Run retrieval before answering: ./scripts/memory-retrieve.sh auto \"<query>\"  (or: hypermemory --workspace <ws> retrieve auto \"<query>\")"
say "- After meaningful work: ./scripts/checkpoint.sh"
exit 1
