#!/usr/bin/env bash
set -euo pipefail

# update-session-state.sh — maintain lightweight session continuity state.
#
# Usage:
#   update-session-state.sh --workspace /path/to/ws \
#     --currentTopic "X" --pendingWork "Y" --recentContext "..." \
#     --lastChannel discord --lastSessionKey abc

WORKSPACE=""
CURRENT_TOPIC=""
PENDING_WORK=""
RECENT_CONTEXT=""
LAST_CHANNEL=""
LAST_SESSION_KEY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace|--repo) WORKSPACE="$2"; shift 2 ;;
    --currentTopic|--current-topic) CURRENT_TOPIC="$2"; shift 2 ;;
    --pendingWork|--pending-work) PENDING_WORK="$2"; shift 2 ;;
    --recentContext|--recent-context) RECENT_CONTEXT="$2"; shift 2 ;;
    --lastChannel|--last-channel) LAST_CHANNEL="$2"; shift 2 ;;
    --lastSessionKey|--last-session-key) LAST_SESSION_KEY="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$WORKSPACE" ]]; then
  WORKSPACE="${OPENCLAW_WORKSPACE:-$PWD}"
fi

mkdir -p "$WORKSPACE/memory"
STATE="$WORKSPACE/memory/session-state.json"

NOW_MS=$(python3 -c 'import time; print(int(time.time()*1000))')

python3 - "$STATE" "$NOW_MS" "$CURRENT_TOPIC" "$PENDING_WORK" "$RECENT_CONTEXT" "$LAST_CHANNEL" "$LAST_SESSION_KEY" <<'PY'
import json,sys
path,now_ms,topic,pending,ctx,lastChannel,lastSessionKey=sys.argv[1:]
now=int(now_ms)
try:
  data=json.load(open(path,"r",encoding="utf-8"))
except Exception:
  data={}

def set_if(val, key):
  if val is not None and str(val)!='':
    data[key]=val

# stable fields
set_if(topic, "currentTopic")
set_if(pending, "pendingWork")
set_if(ctx, "recentContext")
set_if(lastChannel, "lastChannel")
set_if(lastSessionKey, "lastSessionKey")

# bookkeeping
data["lastActivity"]=now
if "lastFlush" not in data:
  data["lastFlush"]=now
if "channelContext" not in data or not isinstance(data.get("channelContext"), dict):
  data["channelContext"]={}

with open(path,"w",encoding="utf-8") as f:
  json.dump(data,f,ensure_ascii=False,indent=2)
PY

echo "$STATE"
