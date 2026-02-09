# Security

HyperMemory is a memory system. Treat it like one.

## What must never be committed
- `memory/` (daily logs)
- `MEMORY.md` (curated memory)
- `.env*`
- `DATABASE_URL` values (they contain passwords)
- any API keys / tokens
- `~/.config/gh/hosts.yml` (GitHub auth)

This repo ships with a `.gitignore` that blocks common sensitive paths. Keep it.

## Recommended bindings
Keep these services bound to loopback (`127.0.0.1`) unless you have a strong reason:
- mf-embeddings (default `127.0.0.1:8080`)
- Postgres (default `127.0.0.1:5432`)

If you reverse-proxy, explicitly deny access to `8080` and `5432` from the public internet.

## File permissions
Recommended:
- env files containing DB URLs/tokens: `chmod 600`
- config directories: `chmod 700`

## Threat model (quick)
- Your memory content can contain customer data, credentials locations, internal IPs.
- The embed server can be used to exfiltrate prompts if exposed.
- The vector DB can reveal semantic neighbors of your memory if exposed.

## If you suspect a leak
- rotate any secrets referenced
- change DB passwords
- invalidate tokens
- delete published history if secrets were committed (use GitHub secret scanning + rewrite history)
