#!/usr/bin/env bash
set -euo pipefail

# Back-compat wrapper. Prefer: hypermemory search (not yet implemented)
# This retains the old behavior: direct SQLite FTS query.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE="${OPENCLAW_WORKSPACE:-$ROOT}"
DB="$WORKSPACE/memory/supermemory.sqlite"
QUERY="${1:-}"

if [[ -z "$QUERY" ]]; then
  echo "Usage: $0 <query>" >&2
  exit 2
fi

if [[ ! -f "$DB" ]]; then
  echo "Missing FTS DB: $DB (run ./scripts/memory-index.sh)" >&2
  exit 1
fi

# Escape double quotes for an FTS5 phrase query and wrap in quotes.
Q_ESC=${QUERY//\"/\"\"}
MATCH="\"$Q_ESC\""

sqlite3 -separator ' | ' "$DB" "
SELECT source, source_key, chunk_ix, substr(text,1,140)
FROM entry_fts
WHERE entry_fts MATCH '$MATCH'
ORDER BY rank
LIMIT 20;
"
