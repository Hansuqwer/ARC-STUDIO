# ARC Mobile Runtime Next-Gen Research

Status: research-backed strategy. Current implementation remains simulator-first and mock-only.

## Sources

| Source | Link | Learned | Consequence |
|---|---|---|---|
| React Native New Architecture | https://reactnative.dev/architecture/landing-page | RN New Architecture is default in 0.76+, adds Fabric, concurrent rendering, JSI/TurboModule speed. | ARC RN adapter should target TurboModule/JSI for low-overhead event emission, but keep native access behind capability approval. |
| Expo Modules API | https://docs.expo.dev/modules/overview/ | Expo Modules use Swift/Kotlin, support New Architecture, minimal boilerplate, performance near TurboModules. | First native SDK target should be Expo dev-client module; best DX and config-plugin path. |
| Flutter release archive | https://docs.flutter.dev/install/archive | Flutter current stable line is 3.44 in 2026 schedule; Flutter has mature testing/platform-channel patterns. | Flutter adapter should be second after Expo and stay plugin/stub-first. |
| Apple App Review Guidelines | https://developer.apple.com/app-store/review/guidelines/ | Apple emphasizes safety, public APIs, app container limits, explicit consent for camera/mic/screen/user activity recording, intended-purpose background modes. | ARC must generate review notes/privacy manifests and forbid hidden automation/background execution. |
| Apple Privacy Manifests | https://developer.apple.com/documentation/bundleresources/privacy-manifest-files | Page requires JS, but topic establishes required privacy declaration artifact. | Generate `PrivacyInfo.xcprivacy` from capability manifests in a later phase. |
| Apple App Intents | https://developer.apple.com/documentation/appintents | Page requires JS; App Intents are the system integration path for Shortcuts/Siri. | ARC should generate App Intents only for user-visible, approved, app-owned capabilities. |
| Apple BackgroundTasks | https://developer.apple.com/documentation/backgroundtasks | Page requires JS; background work is system-scheduled and constrained. | ARC should not promise autonomous background agents; only user-approved scheduled sync with OS constraints. |
| Android permissions | https://developer.android.com/privacy-and-security/permissions | Fetch timed out; official Android docs remain required source for manifest/permission mapping. | Keep Android manifest generation conservative and fail-closed. |
| Android background work | https://developer.android.com/guide/background/persistent | Fetch timed out; WorkManager remains the intended persistent work abstraction. | Use WorkManager only for explicit offline queue flush, not free-running agents. |
| ML Kit | https://developers.google.com/ml-kit | ML Kit runs optimized on-device, supports offline vision/NL APIs, and Gemini Nano GenAI APIs. | ARC on-device AI adapter should prefer platform-supported local inference before remote calls. |

## What “300% Better” Means

| Axis | Metric |
|---|---|
| 3x DX | One manifest -> Expo/Flutter/RN/iOS/Android stubs, simulator, tests, privacy files. |
| 3x safety | Every capability has permission map, user rationale, egress policy, approval scope, expiry, audit level. |
| 3x simulator iteration | `arc mobile simulate` and Theia panel show deterministic dry-run before any native bridge exists. |
| 3x offline/local-first | Queue, encrypted memory, local embeddings, replay logs work without network. |
| 3x cross-platform coverage | Capability cards map to Expo Modules, Flutter plugins, TurboModules, Swift/Kotlin. |
| 3x app-store posture | Generate Apple privacy manifest, Android manifest/data-safety notes, review notes. |
| 3x agent interop | SwarmGraph signed handoff, LangGraph/OpenAI/Claude tool adapters emit same action-plan protocol. |
| 3x observability | Mobile flight recorder + trace replay + golden fixtures + Maestro/Detox generation. |
| 3x privacy | Data egress budget, payload hashing, redaction, local-only adapters by default. |
| 3x repo-native fit | Runtime pack, CLI, TS protocol, Theia inspector, tests live in repo. |

## Executive Summary

Biggest opportunity: make ARC Mobile Runtime the first capability-card-driven, simulator-first, app-store-aware mobile agent runtime. ARC should become the “edge body” for SwarmGraph: SwarmGraph decides/verifies; ARC Mobile performs user-visible, permission-scoped, replayable device actions. ARC can win because the repo already has trust, policy, sandbox, runtime packs, flight recorder, TS protocol, and Theia UX, while mobile frameworks lack agent-safe audit/replay/governance.

## Top 25 Innovations

| # | Innovation | Why it matters | ARC opportunity | Risk | Priority |
|---|---|---|---|---|---|
| 1 | RN New Architecture + JSI | Fast native/JS boundary | Low-overhead trace/capability bridge | Native misuse | P1 |
| 2 | Expo Modules | Best native-module DX | First adapter target | Config/plugin drift | P1 |
| 3 | Flutter platform channels + isolates | Cross-platform + background compute | Deterministic simulator, plugin API | Plugin permission sprawl | P2 |
| 4 | App Intents/Shortcuts | System-sanctioned actions | Generate user-visible intents | Misleading intents | P3 |
| 5 | Android WorkManager | Durable constrained jobs | Offline queue flush only | Background overclaim | P4 |
| 6 | Privacy manifests | Required Apple disclosure | Generate from manifest | Wrong declarations | P2 |
| 7 | Android Data Safety/scoped permissions | Store compliance | Generate review artifacts | Policy drift | P2 |
| 8 | Secure Enclave/Keychain/Keystore | User-gated secrets | Encrypted memory capsule | Key loss | P3 |
| 9 | Biometric gates | Per-action user auth | Approval scope re-auth | Accessibility | P3 |
| 10 | ML Kit/Gemini Nano | Offline AI primitives | Local OCR/summarize adapters | Device/version limits | P4 |
| 11 | Core ML/ExecuTorch/ONNX/TFLite | Model portability | On-device inference interface | Thermal/battery | P5 |
| 12 | sqlite-vec/local embeddings | Zero-egress recall | Local vector memory | Storage growth | P3 |
| 13 | CRDT/offline sync | Conflict-free local-first | Replayable queue sync | Merge complexity | P5 |
| 14 | Deterministic action plans | Testable agents | Golden trace generation | Non-deterministic native APIs | P1 |
| 15 | Flight recorder on-device | Forensics | Hash-only sensitive events | Log leakage | P1 |
| 16 | Maestro/Detox generation | Test from plan | Auto mobile tests | Fragile UI selectors | P4 |
| 17 | Capability fuzzing | Red-team plans | Deny malicious plan shapes | False positives | P3 |
| 18 | Privacy budget | Data-egress limits | Visible egress ledger | UX complexity | P3 |
| 19 | Dev-client bridge | Fast local iteration | Gated, loopback-only bridge | Local server abuse | P4 |
| 20 | Theia mobile inspector | Visual plan review | Cap cards + trace replay | UI scope creep | P2 |
| 21 | App-store report generator | Review readiness | One-click review notes | Legal accuracy | P3 |
| 22 | Signed SwarmGraph handoff | Verified plan provenance | Signed plan envelope | Key mgmt | P2 |
| 23 | Payload hash/redaction | Privacy-preserving audit | Hash all sensitive payloads | Debuggability | P1 |
| 24 | Offline queue with replay | Robust UX | Queue actions until foreground approval | Background limits | P4 |
| 25 | Multi-SDK protocol mirror | Polyglot runtime | Python+TS+Dart/Swift/Kotlin schema | Schema drift | P2 |

## Top 20 Killer Features

| Feature | Pitch | Architecture | CLI | SwarmGraph/MCP | Risk | Score |
|---|---|---|---|---|---|---|
| Capability Cards | Visual, typed mobile permissions | Manifest -> cards -> policy | `capabilities` | SwarmGraph verifies card hash | Low | 24 |
| Dry-run Action Preview | See every action before run | ActionPlan + simulator | `simulate` | Plan imported from SwarmGraph | Low | 25 |
| Time-travel Replay | Replay mobile agent traces | JSONL events + hashes | `trace replay` | Evidence loop | Low | 24 |
| Privacy Budget | Count egress/read scopes | Budget ledger | `privacy-budget` | Budget can block graph | Med | 23 |
| App Store Report | Generate review notes | Manifest -> report | `generate ios-privacy` | N/A | Med | 22 |
| Android Manifest Generator | Minimal permissions | Capability -> manifest | `generate android-manifest` | N/A | Med | 22 |
| Expo Dev Adapter | Fastest first SDK | Expo Module + config plugin | `doctor --platform expo` | Tool bridge in dev only | Med | 24 |
| Flutter Stub Plugin | Typed Dart bridge | Platform interface | `doctor --platform flutter` | Same protocol | Low | 21 |
| RN TurboModule | High-perf bridge | JSI/TurboModule | `doctor --platform rn` | Same protocol | Med | 21 |
| Signed Handoff | Trustable plan transfer | Signed plan envelope | `handoff verify` | Core integration | Low | 24 |
| Local Memory Capsule | Encrypted app memory | SQLite + Keychain/Keystore | `memory inspect` | Graph may query via policy | Med | 23 |
| Local Embeddings | Zero-egress search | sqlite-vec/ONNX | `index local` | Retrieval evidence | Med | 22 |
| On-device AI Adapter | Local OCR/summarize | ML Kit/Core ML interface | `ai doctor` | Local tool provider | High | 20 |
| Test Generator | Plan -> Maestro/Detox | Selector schema | `test generate` | Test evidence | Med | 20 |
| Fixture Recorder | Turn sessions into fixtures | Trace -> fixture | `fixture capture` | Golden traces | Low | 23 |
| Red-team Simulator | Fuzz malicious plans | Mutator + policy | `fuzz` | Safety score | Low | 23 |
| MCP Dev Bridge | Gated local dev only | Token, loopback, TTL | `mcp dev-bridge` | Debug only | High | 17 |
| Approval Scopes | Time-bound permissions | Scope + expiry | `policy explain` | HITL gates | Low | 24 |
| Compliance Diff | Show privacy changes | Manifest diff | `privacy diff` | PR gate | Low | 23 |
| Device Lab CI | Real-device proof | Maestro/XCTest/Espresso | `device-lab` | Proof artifact | Med | 19 |

## Competitive Landscape

Expo, RN, Flutter, Capacitor, and Tauri mobile provide app/runtime foundations, but not agent-safe capability governance, SwarmGraph verification, privacy-budget gating, deterministic action replay, or app-store report generation. Firebase/Supabase solve backend/mobile patterns but bias cloud sync and do not provide agent action policy. LangGraph/OpenAI/Claude/CrewAI/Pydantic AI/Vercel AI SDK provide tool-calling patterns but not mobile OS permission mapping or app-store safety. MCP is powerful for desktop/server tools but risky on mobile; ARC should only allow a tokenized dev bridge with TTL and loopback. Native App Intents and Android App Actions are system-aligned but narrow; ARC should generate them from approved user-visible capabilities, not expose generic agent automation.

ARC should not copy generic app wrappers, always-on assistants, accessibility automation, hidden background workers, remote MCP gateways, or blanket permissions.

## Proposed Architecture: Edgebody Runtime

Layers:

1. Protocol: `MobileCapabilityManifest`, `MobileActionPlan`, `MobileRuntimeEvent`, `MobileTrace`, `MobilePolicyDecision`.
2. Capability registry: platform permission map, sensitivity, egress, approval, replayability.
3. Permission engine: OS permission check + user explanation + scope expiry.
4. Policy engine: default deny for sensitive/unknown/MCP/background/network.
5. Privacy budget: count reads, writes, egress, sensitive payload classes.
6. Data-egress guard: local-only by default; remote calls require signed approval.
7. Offline queue: foreground-authorized queued actions only.
8. Local encrypted memory: SQLite + platform key store; no cloud by default.
9. Local search/embeddings: sqlite-vec/ONNX/ML Kit/Core ML adapters.
10. On-device inference: ML Kit/Gemini Nano/Core ML/ExecuTorch providers with thermal budget.
11. Action simulator: deterministic dry-run and fixture generation.
12. Flight recorder: append-only JSONL, hash payloads, redaction.
13. Trace replay: compare against golden traces and generated mobile tests.
14. Dev bridge: gated, tokenized, loopback-only, disabled by default.
15. Theia inspector: cards, plan preview, trace replay, privacy report.
16. SwarmGraph handoff: signed plan, verified consensus, mobile execution evidence.
17. Compliance generator: `PrivacyInfo.xcprivacy`, Android manifest/data-safety notes.

## Advanced Capability Manifest

Required fields: `id`, `name`, `platforms`, `os_permissions`, `user_explanation`, `approval_mode`, `approval_scope`, `approval_expires_at`, `data_sensitivity`, `background_eligible`, `offline_supported`, `replayable`, `audit_level`, `mcp_exposure`, `simulator_fixture`, `test_fixture`, `privacy_manifest`, `android_manifest`, `egress_policy`, `redaction_rules`, `payload_hashing`, `determinism`, `app_store_notes`.

## Roadmap

| Phase | Goal | Deliverables | Tests | Safety Gates |
|---|---|---|---|---|
| 0 | Validate current state | audit CLI/runtime/tests | existing mobile tests | no unrelated diffs |
| 1 | Strengthen protocol | manifest v2 + TS mirror | schema/type tests | default deny |
| 2 | Simulator/replay | trace/replay/golden fixtures | deterministic hash tests | no native execution |
| 3 | Expo v1 | Expo module/config plugin | Jest + demo | dev-client only |
| 4 | Flutter v1 | Dart package/plugin stub | Dart tests | stub-only |
| 5 | RN TurboModule v1 | TurboModule interface | RN unit tests | New Architecture only |
| 6 | iOS App Intents | generator + examples | snapshot tests | user-visible only |
| 7 | Android Actions/WorkManager | manifest + queue proof | unit + emulator opt-in | no autonomous background |
| 8 | Local memory/search | encrypted SQLite + embeddings | replay/search tests | zero egress |
| 9 | On-device inference | adapter interfaces | opt-in local tests | thermal/privacy budgets |
| 10 | Theia inspector | cards + trace UI | UI tests | read-only inspector |
| 11 | Device lab CI | Maestro/Detox/XCTest/Espresso | opt-in CI | no real secrets |
| 12 | Compliance automation | privacy/report generators | schema snapshots | legal review required |

## Repo-Native Patch Plan

1. `feat(mobile): complete simulator trace and policy CLI` — CLI `trace`, `policy explain`, recorder/policy modules, tests.
2. `feat(mobile): add runtime pack fixtures and schemas` — `runtimes/mobile/spec`, fixtures, JSON schemas.
3. `feat(protocol): split mobile TS protocol mirror` — additive TS files/tests and index exports.
4. `docs(mobile): add Edgebody architecture and safety ADR` — SDK doc + ADR.
5. `feat(mobile): add compliance generators` — iOS/Android generators, snapshot tests.

## CLI Design

Safe commands only:

- `arc mobile doctor` — health, no device required.
- `arc mobile capabilities --manifest <path>` — list capabilities.
- `arc mobile simulate --manifest <path> --plan <path>` — dry-run only.
- `arc mobile trace <jsonl>` — inspect hash chain.
- `arc mobile replay <jsonl>` — compare golden trace.
- `arc mobile policy explain --capability/--plan` — fail-closed decision.
- `arc mobile privacy-budget` — summarize local budget.
- `arc mobile generate ios-privacy` — future privacy manifest generation.
- `arc mobile generate android-manifest` — future manifest generation.
- `arc mobile device-lab` — opt-in real device tests.
- `arc mobile mcp dev-bridge` — future dev-only, loopback/token/TTL.

## SDK Design

Expo first: Expo Module with Swift/Kotlin implementation, config plugin for privacy/permissions, mock mode default. Flutter second: plugin platform interface with Dart simulator facade. React Native third: TurboModule/JSI interface, no legacy bridge-only promise. Swift/Kotlin packages later expose native capability registration, permission explanation, event emission, trace recording, simulator mode, and test fixtures.

## 10 Wow Ideas

1. Capability Cards visualized in Theia.
2. Time-travel replay of mobile agent actions.
3. Privacy budget dashboard.
4. Simulator-generated App Store privacy report.
5. Agent action dry-run previews.
6. One-click fixture generation from simulator sessions.
7. SwarmGraph-to-device signed handoff.
8. On-device encrypted memory capsule.
9. Local embeddings with zero egress.
10. Red-team simulator for malicious mobile plans.

## Safety Review

Apple risks: hidden features, unintended background work, executing downloaded code, camera/mic/screen/user activity recording without explicit consent, misleading Siri/Shortcuts/App Intents. Google Play risks: undeclared data safety, overbroad permissions, background abuse, health/contact/location misuse. MCP risk: remote tool surface on a personal device. Accessibility risk: looks like automation/control of other apps. Mitigation: default-deny, mock-only MVP, no background automation, no unauthenticated local server, explicit approval, payload hashing, redaction, generated review notes, opt-in device lab.

## Final Recommendation

Architecture name: **ARC Edgebody Runtime**.

First SDK target: Expo Modules dev-client adapter.

Top 10 next features: trace/replay CLI, policy explain, runtime schemas, TS split mirror, Theia capability cards, privacy budget, compliance generator, Expo stub adapter, fixture generation, signed SwarmGraph handoff.

First 5 commits: use patch plan above.

Exact next command:

```bash
uv run --directory python arc mobile doctor --json
```
