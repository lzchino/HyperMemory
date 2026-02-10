# Subsystem: Core

Core scripts maintain durability and continuity.

## Files
- `memory/YYYY-MM-DD.md` — daily log
- `MEMORY.md` — curated memory
- `memory/session-state.json` — continuity state
- `memory/last-messages.jsonl` — message buffer (optional)

## Scripts
- `scripts/core/buffer-message.sh`
  - Appends inbound messages to `memory/last-messages.jsonl`.

- `scripts/core/update-session-state.sh`
  - Updates `memory/session-state.json` with current topic/pending work.

- `scripts/core/curated-memory-write.sh`
  - Writes scored items to the daily file.
  - Promotes score >= threshold to `memory/staging/MEMORY.pending.md`.
