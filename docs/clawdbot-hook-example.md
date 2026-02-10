# Clawdbot hook example: bootstrap protocol injection

Goal: enforce **retrieval-before-answering** by injecting a high-priority protocol into the agent bootstrap context.

> Why bootstrap injection?
> Clawdbot hooks don’t currently intercept every user message event for arbitrary logic, but they *can* reliably add bootstrap context files. That makes the protocol visible at the start of each run.

## Example hook

Create a hook (name it whatever you want) with:

- `HOOK.md`
- `handler.js`

### `HOOK.md`

```yaml
---
name: hypermemory-guard
description: "Inject HyperMemory protocol into agent bootstrap context"
metadata: {"clawdbot": {"events": ["agent:bootstrap"]}}
---
```

### `handler.js`

```js
import path from 'node:path';

const CONTENT = `# HyperMemory Protocol — ENFORCED

When answering anything that depends on prior context (decisions, status, todos,
IDs/paths/ports, where something is, etc.), do NOT guess.

1) Evidence check:

- Run:
  bash /opt/hypermemory/scripts/monitoring/pre-response-check.sh

2) If gaps are detected, retrieve before answering:

- Run:
  OPENCLAW_WORKSPACE=/home/<user>/<workspace> \
    bash /opt/hypermemory/scripts/retrieval/memory-retrieve.sh auto "<query>"

3) After meaningful work:

- Run:
  /home/<user>/<workspace>/scripts/memory_checkpoint.sh /home/<user>/<workspace>

4) Periodically verify recall doesn’t regress:

- Run:
  /home/<user>/<workspace>/scripts/benchmark.sh /home/<user>/<workspace>
`;

export default async function handler(event) {
  if (event?.type !== 'agent' || event?.action !== 'bootstrap') return;

  const ctx = event.context ?? {};
  if (!Array.isArray(ctx.bootstrapFiles)) return;

  const workspaceDir = ctx.workspaceDir;
  const virtualPath = workspaceDir
    ? path.join(workspaceDir, 'HYPERMEMORY_PROTOCOL.md')
    : 'HYPERMEMORY_PROTOCOL.md';

  // Avoid duplicate injection.
  if (ctx.bootstrapFiles.some((f) => f?.name === 'HYPERMEMORY_PROTOCOL.md')) return;

  ctx.bootstrapFiles.push({
    name: 'HYPERMEMORY_PROTOCOL.md',
    path: virtualPath,
    content: CONTENT,
    missing: false,
  });
}
```

## Notes
- Keep services bound to loopback where possible.
- Never inject secrets into bootstrap content.
- Prefer local-first retrieval ordering: FTS → pgvector+CUDA → fallbacks.
