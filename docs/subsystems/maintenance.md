# Subsystem: Maintenance

Maintenance keeps memory clean and indexes healthy.

## Distillation
- `scripts/maintenance/memory-distill.sh`
  - Promotes tagged curated bullets (e.g. `[M3]`) into `MEMORY.md`

## Checkpoint
- `scripts/checkpoint.sh`
  - distill
  - reindex SQLite
  - run eval (fast)
