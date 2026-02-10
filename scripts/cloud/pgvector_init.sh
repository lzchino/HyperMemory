#!/usr/bin/env bash
set -euo pipefail

# Initialize BYO Postgres pgvector schema for HyperMemory Cloud L3.

: "${HYPERMEMORY_CLOUD_DATABASE_URL:?Set HYPERMEMORY_CLOUD_DATABASE_URL}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

python3 - "$ROOT/scripts/cloud/pgvector_schema.sql" <<'PY'
import os,sys
import psycopg

url=os.environ["HYPERMEMORY_CLOUD_DATABASE_URL"]
path=sys.argv[1]
sql=open(path,'r',encoding='utf-8').read()

with psycopg.connect(url) as con:
    con.execute(sql)
    con.commit()
print("OK")
PY
