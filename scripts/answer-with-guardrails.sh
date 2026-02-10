#!/usr/bin/env bash
set -euo pipefail

# answer-with-guardrails.sh — helper entrypoint to enforce guardrails for interactive usage.
#
# It does not call an LLM. It outputs:
# - pre-response check status
# - retrieval results (FTS + pgvector if available)
# so an agent can answer with evidence.
#
# Usage:
#   ./scripts/answer-with-guardrails.sh /path/to/workspace "your question"

WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$PWD}}"
QUERY="${2:-}"

if [[ -z "$QUERY" ]]; then
  echo "Usage: $0 [workspace] <query>" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== guardrails: pre-response-check =="
if ! "$ROOT/scripts/monitoring/pre-response-check.sh" "$WORKSPACE"; then
  echo "(gaps detected)"
fi

echo ""
echo "== retrieval =="
"$ROOT/scripts/memory-retrieve.sh" auto "$QUERY" --hybrid || true
