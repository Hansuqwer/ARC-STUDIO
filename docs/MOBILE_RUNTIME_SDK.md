# ARC Mobile Runtime SDK

ARC Mobile Runtime is the **Edgebody** runtime for ARC Studio: device-facing, mobile-first, local-first, permission-aware, replayable, and inspectable.

Current status: simulator-first and mock-only. No production native access exists.

## Safety baseline

- No real camera, contacts, photos, location, microphone, health, files, or background execution in MVP.
- No unauthenticated local server.
- No production mobile MCP gateway.
- Sensitive capabilities require explicit approval and remain mock-only.
- Events hash payloads and avoid dumping sensitive data.

## Architecture

SwarmGraph verifies intent and consensus. ARC Mobile Runtime receives deterministic action plans, evaluates capability policy, simulates or executes approved device-local actions, records hash-linked traces, and sends evidence back to ARC Studio.

## CLI

```bash
arc mobile doctor --json
arc mobile capabilities --manifest runtimes/mobile/fixtures/capabilities.safe-demo.json --json
arc mobile policy explain --manifest runtimes/mobile/fixtures/capabilities.safe-demo.json --plan runtimes/mobile/fixtures/action-plan.echo.json --json
arc mobile simulate --manifest runtimes/mobile/fixtures/capabilities.safe-demo.json --plan runtimes/mobile/fixtures/action-plan.echo.json --json
arc mobile trace runtimes/mobile/fixtures/traces/echo.simulated.jsonl --json
```

## Capability model

Capabilities declare OS permission mapping, user-visible rationale, approval mode, data sensitivity, offline/replay support, egress policy, MCP exposure eligibility, simulator fixtures, audit requirements, redaction rules, and deterministic hashes.

## App-store posture

Future generators will produce Apple privacy manifests, Android manifest/data-safety notes, and review notes from capability manifests. These artifacts are advisory and require human review.
