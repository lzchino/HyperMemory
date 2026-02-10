# Protocol: Cloud Sync (Curated-only)

## Goal
Provide cross-machine durability without leaking raw conversation logs.

## Rules
1) Only sync curated items with score >= threshold.
2) Curated feed source is `memory/staging/MEMORY.pending.md`.
3) Always generate a reviewable payload (`cloud-push.payload.json`) before pushing.
4) Always redact and apply allowlist validation.
5) Cloud is a derived index; local files remain authoritative.
6) Cloud pull must be review-only; do not auto-edit `MEMORY.md`.

## Operational steps
- Prepare payload:
  - `python3 scripts/cloud/push_curated.py --workspace <ws>`
- Review payload:
  - `memory/staging/cloud-push.payload.json`
- Commit push:
  - `python3 scripts/cloud/push_curated.py --workspace <ws> --commit`
