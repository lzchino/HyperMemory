import path from 'node:path';

/**
 * Hook: fortress-lite-guard
 * Event: agent:bootstrap
 */

const CONTENT = `# Hypermemory Protocol (HyperMemory) — ENFORCED\n\nWhen answering anything that depends on prior context (decisions, status, todos, IDs/paths/ports, where something is, etc.), do NOT guess.\n\n1) Evidence check (fast):\n\n- Run:\n  bash scripts/monitoring/pre-response-check.sh <workspace>\n\n2) If gaps are detected, retrieve before answering:\n\n- Run:\n  bash scripts/memory-retrieve.sh auto \"<query>\"\n\n3) After meaningful work (or anything worth remembering):\n\n- Run:\n  bash scripts/checkpoint.sh <workspace>\n\n4) Periodically verify memory recall doesn’t regress:\n\n- Run:\n  bash scripts/memory-eval.sh <workspace> --fast\n\nSecurity: Only read MEMORY.md in main/private sessions. In shared/group contexts, do not load or quote MEMORY.md.\n`;

export default async function handler(event) {
  if (event?.type !== 'agent' || event?.action !== 'bootstrap') return;

  const ctx = event.context ?? {};
  if (!Array.isArray(ctx.bootstrapFiles)) return;

  const workspaceDir = ctx.workspaceDir;
  const virtualPath = workspaceDir ? path.join(workspaceDir, 'SUPERMEMORY_PROTOCOL.md') : 'SUPERMEMORY_PROTOCOL.md';

  if (ctx.bootstrapFiles.some((f) => f?.name === 'SUPERMEMORY_PROTOCOL.md')) return;

  ctx.bootstrapFiles.push({
    name: 'SUPERMEMORY_PROTOCOL.md',
    path: virtualPath,
    content: CONTENT,
    missing: false,
  });
}
