#!/usr/bin/env bash
set -euo pipefail

# buffer-message.sh — append an incoming message to a durable JSONL buffer.
#
# Usage:
#   buffer-message.sh --workspace /path/to/ws --role user --channel discord --sessionKey abc --message "hi"
#
# Writes:
#   <workspace>/memory/last-messages.jsonl

WORKSPACE=""
ROLE="user"
CHANNEL="unknown"
SESSION_KEY=""
MESSAGE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace|--repo) WORKSPACE="$2"; shift 2 ;;
    --role) ROLE="$2"; shift 2 ;;
    --channel) CHANNEL="$2"; shift 2 ;;
    --sessionKey|--session-key) SESSION_KEY="$2"; shift 2 ;;
    --message) MESSAGE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$WORKSPACE" ]]; then
  WORKSPACE="${OPENCLAW_WORKSPACE:-$PWD}"
fi

if [[ -z "$MESSAGE" ]]; then
  echo "Missing --message" >&2
  exit 2
fi

mkdir -p "$WORKSPACE/memory"
OUT="$WORKSPACE/memory/last-messages.jsonl"

TS_MS=$(python3 -c 'import time; print(int(time.time()*1000))')

python3 - "$OUT" "$TS_MS" "$CHANNEL" "$SESSION_KEY" "$ROLE" "$MESSAGE" <<'PY'
import json,sys
out,ts,channel,sessionKey,role,msg=sys.argv[1:]
obj={
  "ts": int(ts),
  "channel": channel or "unknown",
  "sessionKey": sessionKey or "",
  "role": role or "user",
  "message": msg,
}
with open(out,"a",encoding="utf-8") as f:
  f.write(json.dumps(obj, ensure_ascii=False)+"\n")
PY

echo "$OUT"
