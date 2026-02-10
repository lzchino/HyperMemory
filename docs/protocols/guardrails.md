# Protocol: Guardrails

## Pre-response rule
If a question depends on prior context (decisions, IDs, ports, paths, status, todos), do not answer from intuition.

Required steps:
1) Run pre-response evidence check
2) If gaps are detected, retrieve
3) Answer with cited evidence
4) After meaningful work, checkpoint

Commands:
- Evidence check:
  - `bash scripts/monitoring/pre-response-check.sh <workspace>`
- Retrieve:
  - `bash scripts/memory-retrieve.sh auto "<query>"`
- Checkpoint:
  - `bash scripts/checkpoint.sh <workspace>`
