#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$PWD}}"

if [[ ! -d "$WORKSPACE" ]]; then
  echo "Workspace not found: $WORKSPACE" >&2
  exit 2
fi

DB="$WORKSPACE/memory/supermemory.sqlite"
STATE="$WORKSPACE/memory/session-state.json"
BUF="$WORKSPACE/memory/last-messages.jsonl"

say() { printf '%s\n' "$*"; }

say "== index status =="
say "workspace: $WORKSPACE"

if [[ -f "$DB" ]]; then
  say "sqlite: $DB"
  say "sqlite_size_bytes: $(wc -c < "$DB" | tr -d ' ')"
  # count rows
  say "entries: $(sqlite3 "$DB" 'select count(*) from entry;' 2>/dev/null || echo '?')"
else
  say "sqlite: MISSING"
fi

if [[ -f "$STATE" ]]; then
  say "session_state: present"
else
  say "session_state: missing"
fi

if [[ -f "$BUF" ]]; then
  say "message_buffer_lines: $(wc -l < "$BUF" | tr -d ' ')"
else
  say "message_buffer: missing"
fi
