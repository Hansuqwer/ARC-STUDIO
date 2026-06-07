# ARC Mobile Runtime — Simulator Preview

ARC Mobile Runtime is a **simulator-first, mock-only governance layer** for mobile AI agents.
It provides typed capability cards, fail-closed policy, deterministic dry-run simulation,
hash-linked traces, and a 9-command CLI. It is **not** a production native mobile SDK.

> **No real native access.** No camera, microphone, contacts, calendar, photos, files, location,
> health, background execution, or network-backed execution exists in any current package.
> All built-in capabilities are `.mock` simulator capabilities. Expo, React Native, and Flutter
> packages are stubs (no native code). See `docs/mobile/REAL_VS_MOCK.md` for the full matrix.

## Current status

Simulator Preview (alpha). Safe for demos and simulation tooling. Not production-ready.
Not enterprise-ready. See `docs/mobile/PRODUCTION_READINESS.md` for the release gate checklist.

## Safety baseline

- No real camera, contacts, photos, location, microphone, health, files, or background execution.
- No unauthenticated local server.
- No production mobile MCP gateway (denied in policy engine).
- Sensitive capabilities require explicit approval and remain mock-only.
- Events hash payloads and avoid dumping sensitive data.
- Traces record per-event hashes (previous-hash chain pending; see roadmap Phase 3).

## Architecture

SwarmGraph verifies intent and consensus. ARC Mobile Runtime receives deterministic action plans,
evaluates capability policy, simulates approved device-local actions (mock only), records
hash-linked traces, and sends evidence back to ARC Studio. The chain currently stops at
**static Python prediction** — no native mobile execution exists.

## CLI

```bash
arc mobile doctor --json
arc mobile capabilities --manifest runtimes/mobile/fixtures/capabilities.safe-demo.json --json
arc mobile policy explain --manifest runtimes/mobile/fixtures/capabilities.safe-demo.json --plan runtimes/mobile/fixtures/action-plan.echo.json --json
arc mobile simulate --manifest runtimes/mobile/fixtures/capabilities.safe-demo.json --plan runtimes/mobile/fixtures/action-plan.echo.json --json
arc mobile trace runtimes/mobile/fixtures/traces/echo.simulated.jsonl --json
```

## Capability model

Capabilities declare OS permission mapping, user-visible rationale, approval mode, data
sensitivity, offline/replay support, egress policy, MCP exposure eligibility, simulator
fixtures, audit requirements, redaction rules, and deterministic hashes.
All current capabilities are mock/simulator-only.

## Framework packages

| Package | Status |
|---|---|
| `arc-mobile-runtime` (Expo) | Simulator stub — TypeScript types only, no native code |
| `arc-mobile-runtime` (React Native) | Simulator stub — TypeScript types only, no TurboModule |
| `arc_mobile_runtime` (Flutter) | Package shell — pubspec.yaml only, no Dart source |

None of these packages provide real device access. Do not publish them as production SDKs.

## App-store posture

Future generators will produce Apple privacy manifests (`PrivacyInfo.xcprivacy`),
Android manifest/data-safety notes, and review notes from capability manifests.
These artifacts are advisory and require human review before any store submission.
No artifacts are generated yet — `privacy_manifest_intent: true` in manifests is a
declaration of intent only, not a generated file.

## Roadmap

See `docs/mobile/ROADMAP_TO_PRODUCTION.md` for the phased plan from simulator preview
to production SDK and enterprise readiness.
