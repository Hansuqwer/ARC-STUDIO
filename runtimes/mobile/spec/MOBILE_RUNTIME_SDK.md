# ARC Mobile Runtime SDK

ARC Mobile Runtime is the ARC Edgebody runtime: a device-facing, permission-aware, simulator-first runtime beside SwarmGraph.

MVP constraints:

- No camera, contacts, photos, location, microphone, health, or file access.
- No background autonomous execution.
- No production MCP gateway.
- No unauthenticated local server.
- Fixtures and mocks only.

## Architecture

SwarmGraph produces signed, verified plans. ARC Mobile Runtime receives deterministic `MobileActionPlan` objects, evaluates `MobileCapabilityManifest` policy, simulates execution, emits `MobileRuntimeEvent` records, and stores append-only `MobileTrace` JSONL.

## CLI lifecycle

```bash
arc mobile doctor --json
arc mobile capabilities --manifest runtimes/mobile/fixtures/capabilities.safe-demo.json --json
arc mobile policy explain --manifest runtimes/mobile/fixtures/capabilities.safe-demo.json --plan runtimes/mobile/fixtures/action-plan.echo.json --json
arc mobile simulate --manifest runtimes/mobile/fixtures/capabilities.safe-demo.json --plan runtimes/mobile/fixtures/action-plan.echo.json --trace /tmp/echo.jsonl --json
arc mobile trace /tmp/echo.jsonl --json
```

## Capability manifest

Each capability declares platform support, OS permissions, approval mode, sensitivity, background/network flags, replayability, audit support, MCP exposure, simulator fixture support, and deterministic hash fields.

## Dry-run simulator

The simulator never calls native APIs. It checks capability IDs, blocks unknown/sensitive/non-mock/background/network plans, predicts approvals, and emits deterministic hashes.

## Flight recorder

Trace events hash payloads and store metadata needed for replay without dumping sensitive payloads.

## MCP dev bridge

MCP is dev-only future work. It must be loopback-only, tokenized, TTL-limited, disabled by default, and never expose sensitive capabilities without explicit review.

## App-store posture

Future generators should emit Apple privacy manifests, Android manifest/data-safety notes, and review notes from this manifest. Generated docs are advisory and require human legal/product review.
