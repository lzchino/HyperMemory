# Subsystem: Monitoring

Monitoring scripts prevent the agent from guessing and help detect regressions.

## Pre-response evidence check
- `scripts/monitoring/pre-response-check.sh`

It checks:
- session-state present
- message buffer present/stale
- SQLite FTS index present

If gaps are detected it exits non-zero and instructs retrieval/checkpoint.
