# ARC Mobile Runtime SDK

ARC Mobile Runtime is the device-native "edge body" runtime for ARC Studio — a privacy-first, local-first, simulator-first foundation for mobile AI agents.

## What it is

A typed, hashable, auditable capability system for mobile agent actions. It answers: what can an AI agent do on a mobile device, under what approval conditions, with what privacy implications, and how do we simulate it safely before deployment?

## What it is NOT

- Not a generic mobile app template
- Not a generic React Native wrapper around API calls  
- Not a cloud-first mobile agent service
- Not background automation (blocked in MVP)
- Not a system that bypasses OS permission prompts

## Strategic positioning

```
SwarmGraph IR          — the graph/consensus/verification brain
ARC Mobile Runtime     — the device-native "edge body" runtime
```

They complement each other: SwarmGraph orchestrates multi-agent workflows; Mobile Runtime exposes what those agents can safely do on a device.

## MVP status

**All capabilities are mock/simulator-only.** No real native bridges exist.

| Feature | Status |
|---|---|
| 13 mock capabilities | ✅ |
| Typed Pydantic models | ✅ |
| Deterministic hashing | ✅ |
| Fail-closed validation | ✅ |
| Safe action simulator | ✅ |
| Runtime Pack integration | ✅ |
| CLI commands | ✅ |
| TypeScript mirror | ✅ |
| Flutter/Expo/RN stubs | ✅ (types only) |
| Real iOS native bridge | ❌ Post-MVP |
| Real Android native bridge | ❌ Post-MVP |
| Background execution | ❌ Blocked in MVP |
| Network by default | ❌ Blocked in MVP |

## Permission model

Every capability declares:
- `data_sensitivity` — none/low/medium/high/critical
- `approval_mode` — none/recommended/required/blocking
- `required_permissions` — platform-specific permission IDs
- `requires_hitl` / `requires_trust` — HITL/trust gate requirements

Sensitive capabilities (camera, microphone, contacts, location, photos, calendar) must end with `.mock` in MVP. Real versions require post-MVP native bridges.

## Capability manifest

The manifest is stored in `arc-mobile-capabilities.json` and is:
- Typed (Pydantic v2)
- Deterministically hashable (SHA-256, canonical JSON)
- Fail-closed on validation
- Auditable (hash-pinned)

```bash
arc mobile capabilities --json      # list all capabilities
arc mobile validate <path> --json   # validate a manifest
arc mobile doctor --json            # SDK health check
```

## Simulator

The action simulator takes a `MobileActionPlan` and returns a `MobileActionSimulationReport`. It:
- Predicts required permissions and approvals
- Blocks real sensitive capabilities
- Blocks background execution
- Blocks network by default
- Assigns risk levels
- Never executes anything

```bash
arc mobile simulate action_plan.json --json
```

## Runtime Pack integration

```bash
arc mobile init-runtime-pack ./my-mobile-pack --json
arc runtime-pack validate ./my-mobile-pack --json
arc runtime-pack inspect ./my-mobile-pack --json
```

The pack declares `runtime_kind: mobile`, no real entrypoints, no paid calls, no network by default.

## CLI examples

```bash
# Health check
arc mobile doctor --json

# List capabilities
arc mobile capabilities --json

# Validate a manifest
arc mobile validate runtimes/mobile/arc-mobile-capabilities.json --json

# Simulate an action plan
arc mobile simulate tests/mobile/fixtures/mock_action_plan.json --json

# Initialize a runtime pack
arc mobile init-runtime-pack /tmp/my-mobile-pack --id org.myapp --name "My App" --json

# Validate the pack
arc runtime-pack validate /tmp/my-mobile-pack --json
```

## Flutter / Expo / React Native stubs

Safe stub packages are in `runtimes/mobile/`:
- `flutter/packages/arc_mobile_runtime/` — Dart types only
- `expo/packages/arc-mobile-runtime/` — TypeScript types + mock simulator
- `react-native/packages/arc-mobile-runtime/` — TypeScript types + mock simulator

These expose types and mock capability declarations. No real sensitive native bridges exist in MVP.

## App-store risk model

ARC Mobile Runtime MVP is app-store safe because:
- No background execution
- No automation of sensitive actions
- No real access to camera/microphone/contacts/location/photos
- All capabilities are mock/simulator-only
- No unauthenticated local servers
- No hidden data egress

Real native bridges (post-MVP) will require individual App Store/Play Store privacy manifest declarations per capability.

## Future real native bridges (post-MVP)

When real bridges are added, each capability must:
- Declare an `NSUsageDescription` (iOS) or `uses-permission` (Android)
- Be gated by explicit user consent
- Be auditable (audit trail in flight recorder)
- Support HITL approval for write operations
- Be redactable before any export

## Relation to other ARC packages

| Package | Integration |
|---|---|
| Runtime Pack SDK | Mobile manifest → runtime pack |
| Policy Linter | Capability validation rules mirror policy linter patterns |
| Flight Recorder | Future: record mobile action events |
| Observability Export | Future: export mobile traces as OTel spans |
| Capability Cards | Future: mobile capabilities → capability cards |
