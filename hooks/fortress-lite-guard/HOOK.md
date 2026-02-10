---
name: fortress-lite-guard
description: "Injects HyperMemory guardrail protocol into Clawdbot bootstrap context"
metadata: {"clawdbot":{"emoji":"🛡️","events":["agent:bootstrap"]}}
---

# Fortress-lite Guard (HyperMemory)

This is a Clawdbot hook example that injects `SUPERMEMORY_PROTOCOL.md` into the agent bootstrap context.

It does not intercept every user message (Clawdbot currently lacks a universal message-received hook), but it strongly biases the agent toward:
- running `scripts/monitoring/pre-response-check.sh`
- retrieving before answering when gaps are detected
- running `scripts/checkpoint.sh` after meaningful work
