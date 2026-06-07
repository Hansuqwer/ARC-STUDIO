# ARC Mobile Runtime SDK — Roadmap to Production & Enterprise

**Date:** 2026-06-07
**Branch:** arcStudioMobileSDK
**Status of this document:** Planning roadmap. Describes target states and required work. Does not itself change product status or unlock claims.
**Grounded in:** Line-by-line audit of `python/src/agent_runtime_cockpit/mobile/`, `cli/mobile.py`, `mobile_sdk_mapping.py`, adapters, `packages/arc-protocol-ts/src/mobile-*.ts`, `runtimes/mobile/**`, tests, fixtures, schemas, and docs (see `docs/mobile/AUDIT_REPORT_2026-06-07.md`).

> **Truth basis:** Code is treated as the only proof. Mock is mock. Roadmap is roadmap. Package shells are not SDKs. JSON Schema files that are never invoked are docs, not validation. Every production claim below is gated; every enterprise claim has controls; every native capability has permission/approval/audit/privacy/test/rollback requirements.

---

## 1. Executive Roadmap Verdict

ARC Mobile Runtime SDK is today a **simulator-first, mock-only governance MVP** implemented almost entirely in Python. It is genuinely good at what it actually is: typed capability cards, fail-closed validation, static plan simulation, hash-pinned manifests, JSONL trace recording, a clean 9-command CLI, a runtime-pack bridge, a TypeScript type mirror, and a read-only Theia widget. It is **not** a mobile SDK in the executable sense — the Expo, React Native, and Flutter "packages" are stubs (`main: src/index.ts`, no build, no native code; Flutter has zero Dart files), and there is no native iOS/Android bridge anywhere in the tree.

**Current maturity level:** Simulator Preview (alpha). Production-equivalent only for the *governance/simulation library*, not for device execution.

**Target maturity levels:**
- v0.2 — Honest Simulator Preview (hardened, strictly labeled).
- v0.5 — SDK Developer Preview (Expo mock-native bridge, generated types, replay).
- v0.8 — Mobile SDK Beta (Expo dev-client real, RN/Flutter scaffolds, approval engine).
- v1.0 — Production Mobile SDK (signed plans, scoped approvals, tamper-evident traces, app-store artifact generators, ≥1 framework production-ready).
- Enterprise v1.x — Org policy, tenant isolation, RBAC/ABAC, SIEM, MDM, SBOM, kill switch.

**Recommended positioning right now:** Call it the **"ARC Mobile Runtime — Simulator Preview"** and, more precisely, a **mobile agent governance layer**. Do not call it a "mobile SDK" without the "simulator preview" qualifier until Phase 6 ships a buildable Expo module with native code.

**Highest-risk overclaims (must be neutralized in Phase 0):**
1. `privacy_manifest: true` boolean implies a generated Apple privacy artifact. None exists.
2. "Flight recorder / hash-linked traces" implies tamper-evidence. There is no previous-hash chain; events hash only themselves and the timestamp is hard-coded to `2026-01-01T00:00:00Z`.
3. Package names (`arc-mobile-runtime`, `@arc/mobile-expo`, `arc_mobile_runtime`) imply installable SDKs. They are stubs.
4. `mobile_sdk_mapping.py` comment "no field is silently dropped" while the forward direction drops 7 governance fields.
5. `hashing.py` docstring claims `schema_version` is excluded from hashing; it is not.

**Strategic opportunity:** No mainstream mobile framework (Expo, RN, Flutter, Capacitor) ships agent-safe capability governance: typed permission cards, fail-closed policy, deterministic dry-run, tamper-evident replay, and app-store artifact generation. ARC already has the governance spine in Python. If it is honestly labeled and expanded Expo-first with signed plans and scoped approvals, ARC can be the **governance and replay layer for mobile AI agents** — the "edge body" for SwarmGraph — rather than yet another app runtime.

**Recommended first production target:** Expo Module (dev-client) with Swift/Kotlin native scaffold + config plugin + PrivacyInfo.xcprivacy generation. Best DX, best config-plugin story, fastest path to compliance artifacts.

**Recommended first enterprise target:** Org/tenant policy engine + signed audit export (SIEM), built on the existing deterministic policy/validation core. This reuses the strongest existing code and is framework-independent.

### Top 10 Roadmap Principles
1. Honesty before features — labels follow evidence, never the reverse.
2. Mock-only means mock-only — no real sensitive native access until the signed-plan + approval + tamper-evident-trace chain exists.
3. One source of truth for the protocol — generate Python/TS/Dart/Swift/Kotlin types from JSON Schema; never hand-maintain drift.
4. Fail-closed everywhere — unknown/sensitive/background/network/MCP default deny.
5. Tamper-evident traces precede real execution — prev-hash chain + signing before any native capability runs.
6. App-store compliance is designed in from day one — privacy artifacts generated before native permissions are requested.
7. Local-first, zero-egress by default — network requires explicit signed approval.
8. Expo first, RN second, Flutter third — unless device-lab evidence changes the order.
9. Every capability ships with policy + tests + fixtures + docs + compliance mapping, or it does not ship.
10. Every release has migration notes; every roadmap item has acceptance criteria.

### Top 10 Non-Negotiable Safety Constraints
1. No hidden background agents; no autonomous background execution.
2. No unauthenticated local server; no remote network listener.
3. No production MCP gateway on device until a dev-only loopback/token/TTL bridge passes security review.
4. No real camera/mic/contacts/calendar/photos/location/health without scoped, unexpired, user-granted approval bound to a signed plan.
5. No blanket permissions; least-privilege per capability.
6. No undeclared data collection; no cloud sync by default.
7. No executing downloaded code on device.
8. No accessibility-service automation of other apps.
9. Security decisions stay deterministic (no LLM allow/deny).
10. Secrets always redacted in logs/UI/audit; traces redact payloads (hash-only).

### Decision Table

| Stage | Label | Current status | Target status | Go/No-Go |
|---|---|---|---|---|
| Internal demo | Simulator Preview | Working, honest | Maintain | **GO** |
| Public preview | Simulator Preview (labeled) | Overclaims present | After Phase 0 truth-labeling | **NO-GO until Phase 0** |
| Developer beta | SDK Developer Preview | Not started | After Phase 1–6 (Expo) | **NO-GO** |
| Production SDK | Production Mobile SDK | Not started | After Phase 7 + ≥1 framework prod | **NO-GO** |
| Enterprise SDK | Enterprise | Not started | After Phase 12 | **NO-GO** |
| App Store release | — | No artifacts, no native | After Phase 5 + 6 + 11 entry gates | **NO-GO** |
| Google Play release | — | Same | Same | **NO-GO** |
| MCP mobile gateway | — | Denied in policy (correct) | v1 dev-bridge only after security review | **NO-GO (intentional)** |

---

## 2. Product Vision

**What ARC Mobile Runtime is:** A governance, simulation, and audit layer for mobile AI agents. It turns agent intent (action plans, often produced/verified by SwarmGraph) into typed, policy-gated, permission-mapped, approval-scoped, replayable, audit-logged mobile actions — starting as a deterministic simulator and progressively gaining governed native execution behind strict safety gates.

**What it is not:** It is not an app framework competing with Expo/RN/Flutter; it rides on them. It is not a general OS-automation tool, not an always-on assistant, not a background daemon, not a remote tool gateway. It is not (today) a native SDK with device access.

**Why it exists:** Mobile AI agents need stronger controls than server agents because they run on personal devices with sensitive sensors, the user is physically present, and app stores enforce strict privacy/consent rules. No mainstream mobile framework provides capability cards, fail-closed policy, deterministic dry-run, tamper-evident replay, and app-store artifact generation. ARC fills that gap.

**Who it serves:** (1) Agent/app developers shipping AI features on mobile who need provable safety; (2) security/compliance reviewers who need audit + replay + app-store evidence; (3) enterprises needing tenant policy, RBAC, SIEM, and MDM over on-device agent actions.

**What problem it solves:** "How do I let an AI agent take device actions on a phone without overreaching permissions, leaking data, failing app review, or being unable to prove what it did?"

**Differentiation:**

| Compared to | They provide | ARC adds |
|---|---|---|
| Expo / RN / Flutter | App runtime, native modules | Agent capability governance, policy, dry-run, replay |
| Capacitor / Tauri Mobile | Webview-native bridge | Same governance gap |
| Firebase / Supabase | Backend, sync (cloud-biased) | Local-first, zero-egress default, action policy |
| LangGraph / OpenAI tools / Claude tools | Tool-calling patterns | OS permission mapping, app-store safety, on-device approval |
| MCP | Desktop/server tool surface | Mobile-safe posture (no remote gateway; dev-only bridge) |
| Generic mobile automation | UIAutomation/Accessibility | Sanctioned, user-visible, approved capabilities only |

**Why simulator-first is an advantage:** Deterministic dry-run lets developers, reviewers, and CI see exactly what an agent *would* do before any native bridge or permission exists. It produces golden traces and test fixtures, de-risks app review, and means the governance layer is proven before execution is added.

**Why enterprise governance matters:** On-device agent actions touch contacts, calendars, location, and files. Enterprises require tenant isolation, org policy, RBAC/ABAC, audit export to SIEM, device posture/MDM, retention, and a kill switch before they will deploy.

**Why app-store compliance from day one:** Apple and Google reject undeclared data collection, overbroad permissions, hidden background work, and missing privacy manifests. Generating these artifacts from the capability manifest — before requesting native permissions — is the only way to keep review risk low.

**Positioning statement (one paragraph):** ARC Mobile Runtime is a simulator-first governance and audit layer for mobile AI agents that turns verified agent action plans into typed, policy-gated, permission-mapped, approval-scoped, replayable, and audit-logged device actions. Today it is a hardened mock-only simulator and governance library; it expands phase-by-phase into a production mobile SDK (Expo first) with signed plans, scoped approvals, tamper-evident traces, and generated app-store compliance artifacts, and then into an enterprise control plane with org policy, RBAC, SIEM, and MDM — without ever granting real sensitive native access until the full safety chain is proven.

**Tagline:** *Governed, replayable AI actions for mobile — simulator-first, app-store-aware.*

**Do-not-overclaim statement:** ARC Mobile Runtime is currently a simulator preview and governance library. It has no real native device access, no production framework SDK, and no enterprise control plane. Do not describe it as a production mobile SDK, an enterprise SDK, or a native bridge until the corresponding phase gates in this roadmap are met with cited evidence.

---

## 3. Roadmap Principles (Detailed)

1. **Honesty before features.** No status label changes until evidence exists and `scripts/check-banned-claims.sh` passes. The word "SDK" is qualified with "simulator preview" until a buildable native module ships.
2. **Mock-only means mock-only.** A `.mock` capability must never touch a real OS API. CI greps the mobile source tree for forbidden primitives (already enforced in `test_mobile.py::TestSafety`); extend it to native dirs as they are added.
3. **No native sensitive access without signed policy + approval.** Entry criteria for any real capability (Phase 11) require signed plan verification, scoped/unexpired approval, generated compliance artifact, device-lab tests, and a rollback flag.
4. **No hidden background agents.** Background execution stays hard-blocked in validation and simulator; any future background work is OS-scheduled, user-visible, and limited to explicit offline-queue flush.
5. **No unauthenticated local server.** No HTTP listener on device. The only future bridge is loopback + token + TTL, disabled by default (Phase 20/MCP).
6. **No production MCP gateway** until the dev bridge is proven safe under a written threat model and security review.
7. **Privacy by default.** Payloads are hashed in traces; secrets are redacted; metadata is schema-constrained.
8. **Local-first by default.** No network egress unless a signed approval grants it; `network_by_default` stays `false`.
9. **Explicit user approval** for sensitive reads/writes — modeled as scoped, expiring `ApprovalGrant`s with consent receipts.
10. **Enterprise policy before enterprise claims.** Tenant/org/RBAC controls must exist and be tested before any "enterprise" wording.
11. **Generated schemas, not drift.** JSON Schema is the single source of truth; Python/TS/Dart/Swift/Kotlin types are generated and parity-tested.
12. **Tamper-evident traces before real execution.** Prev-hash chain + signing land (Phase 3/7) before any native capability runs (Phase 11).
13. **App-store compliance artifacts before native permissions.** Phase 5 generators ship before Phase 11 native capabilities.
14. **One source of truth for capabilities.** The capability registry is canonical; SDK cards, runtime packs, and framework configs derive from it.
15. **Expo first, RN second, Flutter third** unless device-lab evidence reorders.
16. **Real-device tests only after simulator gates pass.** Device-lab is opt-in and gated.
17. **No cloud/network egress by default.**
18. **Every capability has policy, tests, fixtures, docs, and compliance mapping.**
19. **Every release has migration notes.**
20. **Every roadmap item has acceptance criteria** (enforced in this document's tables).

---

## 4. Current-State Inventory

| Area | Current state | Real/mock/stub/docs-only | Risks | Immediate action |
|---|---|---|---|---|
| Python models (`models.py`) | Full Pydantic v2 models, `extra="ignore"` on `_Base` | Real | Unknown fields silently swallowed | Add strict mode (`extra="forbid"`) |
| Capability catalog (`capabilities.py`) | 13 `.mock` capabilities, sealed with hash | Real (mock catalog) | No duplicate-ID guard | Assert unique IDs at load |
| Manifest loader (`manifest.py`) | `json.loads`+`model_validate`; builds default | Real | JSON Schemas never invoked | Wire schema validation into loader |
| Validation (`validation.py`) | 11 rules V1–V11, structured findings | Real | V4 write rule is WARNING; no dup-ID; no platform cross-check | Promote V4 to error (strict); add checks |
| Simulator (`simulator.py`) | Pure static prediction, fail-closed blocks | Real (simulator) | `extra_capabilities` non-sensitive-prefix bypass | Add sensitivity guard on extras |
| Policy (`policy.py`) | Wraps validate+simulate; MCP denied | Real | No policy version; no org/device context; not logged | Add `policy_version`; decision logging |
| Trace recorder (`recorder.py`) | JSONL events + per-event hash + trace hash | Partial | Fixed timestamp `2026-01-01`; no prev-hash chain | Real clock + `prev_event_hash` |
| Hashing (`hashing.py`) | SHA-256, sorted keys, `_VOLATILE` strip | Real | Docstring/code mismatch on `schema_version`; no domain separation | Fix docstring; add domain prefixes |
| Redaction (`redaction.py`) | Key+value redaction, recursive dicts | Real | List string items not redacted | Redact string items in lists |
| CLI (`cli/mobile.py`) | 9 commands, JSON envelopes, exit codes | Real | No CLI tests; `pin` mutates in place; `simulate` arg ambiguity | Add CLI tests; `--dry-run`; standardize args |
| Runtime-pack bridge (`runtime_pack.py`) | Mobile manifest → runtime pack | Lossy | Capability detail flattened to ID list | Emit `capabilities_detail` |
| SDK mapping (`mobile_sdk_mapping.py`) | Bidirectional cap ↔ SDK card | Partial/lossy | Forward drops 7 governance fields; misleading comment | Fix docstring; record dropped fields |
| TS protocol (`mobile-*.ts`) | Interface mirror + weak guards | Real (types) / Stub (validation) | Guards check 2 fields; no runtime validation | Generate validators (Zod) |
| Expo package | `main: src/index.ts`, ~25-line stub | Stub | Not publishable; no native code/config plugin | Mark private; add build; scaffold module |
| RN package | JS stub identical to Expo | Stub | No TurboModule/JSI/Podspec/Gradle | Mark private; scaffold TurboModule |
| Flutter package | `pubspec.yaml` only, zero Dart | Empty stub | Not importable | Add `lib/`, platform interface |
| Fixtures (`runtimes/mobile/fixtures`, `tests/mobile/fixtures`) | Valid manifest, plans, one trace JSONL | Real (happy-path) | No failure/malicious/dup-ID fixtures | Add negative fixtures |
| Tests | ~40 Python lib tests + 2 TS tests + mapping tests | Real (partial) | No CLI/recorder-chain/fuzz/security tests | Expand matrix |
| Docs (`docs/mobile/*`, research) | Honest matrices + checklist + research | Real (docs-only) | Two misleading items inherited from code | Sync docs after code fixes |
| Privacy artifacts | None generated; boolean flag only | Docs-only/Missing | Misleading `privacy_manifest:true` | Rename field; build generator (Phase 5) |
| Android artifacts | None | Missing | — | Build generator (Phase 5) |
| iOS native bridge | None | Missing | — | Phase 6 |
| Android native bridge | None | Missing | — | Phase 9 |
| MCP bridge | Denied in policy | Intentionally absent | — | Phase 20 dev-bridge only |
| Enterprise controls | None | Missing | — | Phase 12 |
| CI/release | Python suite runs; no mobile package build CI | Partial | Stubs could be published unbuilt | Phase 1/6 pipelines |
| Package publishing | Not configured for dist | Missing | Accidental publish of TS source | Mark private now |
| Theia UI (`arc-mobile-widget.tsx`) | Read-only capability table + doctor | Real (read-only) | — | Extend to cards (Phase 5) |
| SwarmGraph integration | Described in research only | Roadmap | — | Phase 7 signed handoff |

---

## 5. Gap Analysis

### Honesty & Labeling Gaps

| Gap | Severity | Why it matters | Files | Required fix | Acceptance criteria |
|---|---|---|---|---|---|
| SDK packages are stubs | High | Users may `npm install` expecting an SDK | Expo/RN/Flutter package dirs | Mark private; add "stub" to description; build step before publish | `npm publish` blocked; description says "simulator stub" |
| "Runtime" implies execution | Medium | Implies device execution | Docs, package names | Qualify as "Simulator Preview" in titles | All README titles carry qualifier |
| `privacy_manifest: bool` implies generated compliance | High | Dev assumes privacy declared | `models.py`, manifests, fixtures | Rename `privacy_manifest_intent`; validator warning | No field implies a generated artifact |
| "Trace recorder" implies tamper-proof audit | High | False audit confidence | `recorder.py`, docs | Add prev-hash chain + signing; update docs | Tamper test fails on reorder/delete |
| "Mobile SDK" implies native bridge | High | Implies device APIs | Docs, packages | Qualify until Phase 6 | Docs state "no native bridge" until Phase 6 |
| "Device-facing" implies real device APIs | Medium | Same | `MOBILE_RUNTIME_SDK.md` | Reword to "device-action governance (simulated)" | Wording corrected |

### Protocol Gaps

| Gap | Severity | Why | Files | Fix | Acceptance |
|---|---|---|---|---|---|
| Loose Pydantic handling (`extra="ignore"`) | High | Silent field loss; smuggling | `models.py` | Strict mode | Unknown field → error in strict |
| No strict schema mode | High | Can't enforce in prod | `models.py`, `manifest.py` | `strict=True` loader | Test proves rejection |
| Missing schemas for plans/reports/traces/policy | Medium | No cross-lang contract | `runtimes/mobile/spec/` | Author all schemas | All 6 schemas exist + validated in CI |
| Missing generated type parity | Medium | Drift across langs | new generator | Codegen from schema | Parity test passes |
| Missing TS runtime validation | Medium | Guards trivially fooled | `mobile-*.ts` | Zod validators | Invalid object rejected |
| Missing Dart/Swift/Kotlin types | Medium | No native parity | new dirs | Generate stubs | Generated + compiled |
| Missing migration/versioning | Medium | Breaking changes unmanaged | `models.py`, schemas | `schema_version` migration map | v1→v2 migration test |

### Simulator Gaps

| Gap | Severity | Why | Fix | Acceptance |
|---|---|---|---|---|
| Static prediction only | Medium | No behavior modeling | Fixture-backed exec (Phase 4) | Fixture outputs produced |
| No fixture-backed execution | Medium | Can't validate I/O | Capability fixture registry | Step output matches fixture |
| No input/output validation | Medium | Bad payloads pass | Per-capability I/O schemas | Bad input → blocked |
| No device/platform modeling | Low | Can't model OS差异 | `DeviceContext` model | Platform-specific sim test |
| No OS permission-state modeling | Medium | Approval realism | Permission-state input | Denied permission → blocked |
| No approval-state modeling | High | Approval not enforced | Approval engine (Phase 7) | Unapproved sensitive → blocked |
| No signed plan verification | High | Plan provenance unverified | Signed envelope (Phase 7) | Bad signature → reject |
| No policy version pinning | Medium | Decisions not reproducible | `policy_version` in decision | Version present in output |
| No golden replay engine | Medium | Can't prove determinism | Replay CLI (Phase 3) | Replay matches golden |

### Trace/Audit Gaps

| Gap | Severity | Why | Fix | Acceptance |
|---|---|---|---|---|
| No previous-hash chain | High | Reorder/delete undetectable | `prev_event_hash` field | Tamper test fails closed |
| No trace signing | High | Forgeable | HMAC/asymmetric sign | Verify CLI detects forgery |
| No manifest hash in events | Medium | Can't bind event→manifest | Add field | Event carries manifest_hash |
| No plan hash in events | Medium | Can't bind event→plan | Add field | Event carries plan_hash |
| No policy hash/version in events | Medium | Can't bind event→policy | Add field | Event carries policy_version |
| No app build/device posture | Medium | No environment provenance | Add fields | Present in event |
| No tenant/user approval evidence | High | No accountability | Add approval ref | Present in event |
| No SIEM export | Medium | Enterprise blocker | Export module (Phase 12) | CEF/JSON export test |
| No retention/export/deletion | Medium | Compliance blocker | Retention policy | Delete/export API test |

### Mobile SDK Gaps

| Gap | Severity | Fix | Acceptance |
|---|---|---|---|
| No Expo Module | High | Phase 6 scaffold | `expo prebuild` succeeds |
| No Expo config plugin | High | Phase 6 | Plugin injects permissions |
| No Swift/Kotlin native | High | Phase 6 | Native build passes |
| No RN TurboModule | High | Phase 9 | Codegen + build pass |
| No RN Codegen | High | Phase 9 | Spec compiles |
| No Flutter platform interface | High | Phase 10 | `flutter analyze` passes |
| No Flutter plugin | High | Phase 10 | Example app builds |
| No example apps | High | Phases 6/9/10 | Smoke test runs |
| No mobile build pipeline | High | Phases 1/6 | CI builds packages |
| No publishable dist | High | Phase 6 | `npm pack` valid |
| No semantic release | Medium | Phase 1 CI | Versioned release |

### Security Gaps

| Gap | Severity | Fix | Acceptance |
|---|---|---|---|
| No signed plan envelope | High | Phase 7 | Bad sig rejected |
| No scoped approval grants | High | Phase 7 | Scope enforced |
| No revocation | High | Phase 7 | Revoked grant denied |
| No data-egress guard | High | Phase 8 | Egress over budget blocked |
| No secure local storage | High | Phase 8 | Keychain/Keystore used |
| No MDM/device posture | Medium | Phase 12 | Posture gate enforced |
| No app attestation | Medium | Phase 12 | Attestation verified |
| No org policy | High | Phase 12 | Org policy applied |
| No RBAC/ABAC | High | Phase 12 | Role denies action |

### Compliance Gaps

| Gap | Severity | Fix | Acceptance |
|---|---|---|---|
| No PrivacyInfo.xcprivacy generator | High | Phase 5 | Snapshot test |
| No Android manifest generator | High | Phase 5 | Snapshot test |
| No Android Data Safety generator | High | Phase 5 | Snapshot test |
| No permission rationale generator | Medium | Phase 5 | Strings generated |
| No consent receipts | Medium | Phase 7 | Receipt issued |
| No app-store review notes | Medium | Phase 5 | Notes generated |
| No legal/product review workflow | Medium | Phase 5 | Human-review flag required |

---

## 6. Target Architecture (Phased)

### Current architecture
```
MobileActionPlan(JSON) → simulate_action_plan() [static] → SimulationReport
                                   ↓
                         build_trace() [fixed ts, no prev-hash] → JSONL
validate_manifest()/explain_plan_policy() [Python rules] → PolicyDecision
CLI (Typer, JSON) ;  Theia widget (read-only)
            ── chain stops at static Python prediction ──
```

### v0.2 — Honest Simulator Preview
```
[Docs relabeled + package banners]
JSON Schemas (manifest, plan, report, event, trace, policy)  ← single source
        ↓ (validated in loader + CI)
models.py (strict mode) → validation.py (dup-ID, platform xcheck, V4=error)
        ↓
simulator.py (extras sensitivity guard) → report
recorder.py (real clock + prev_event_hash chain) → JSONL
CLI: + replay, + trace verify ;  TS: generated validators
mobile_sdk_mapping.py (lossless-documented, dropped-fields recorded)
```

### v0.5 — SDK Developer Preview
```
Capability Registry (canonical) ──→ generates:
   • TS types + Zod validators
   • Dart/Swift/Kotlin model stubs
   • Expo config-plugin permission map
Fixture-backed simulator (I/O schemas, mock state store)
Golden trace replay engine
Expo Module (mock-native bridge: Swift/Kotlin scaffolds) + example app + Jest
Compliance generators (dry-run): PrivacyInfo.xcprivacy, Android manifest (advisory)
Theia capability cards ;  Signed plan prototype (unenforced)
```

### v1.0 — Production Mobile SDK
```
SwarmGraph → SIGNED MobileActionPlan (envelope: plan_hash, org, user, issued_at, sig)
        ↓ verify signature + provenance
Policy Engine v2 (app/user/device context, policy_version pin, MCP gate)
        ↓ approved steps
Approval Engine (scoped grants, expiry, revocation, consent receipt, biometric/PIN)
        ↓ granted
Native Bridge Abstraction → {Expo Module | RN TurboModule | Flutter plugin}
        ↓ execute (governed, least-privilege)
Trace Recorder v2 (prev-hash chain, real ts, payload-hash+redaction, SIGNED root)
        ↓
Compliance Generators (PrivacyInfo.xcprivacy, Android manifest, Data Safety, review notes)
Secure Local Store (Keychain/Keystore + encrypted SQLite) ; Offline queue ; Privacy budget
```

### Enterprise architecture
```
Admin Console/API → Org Policy Bundles (signed) → Policy Engine v2 (+RBAC/ABAC, tenant ctx)
Device Posture / MDM hooks + App Attestation ──→ admission control
Approval Engine (+ enterprise approval routing)
Trace Recorder v2 ──→ SIEM Export (CEF/JSON) ──→ Audit Retention + Legal Hold
Remote Kill Switch + Feature Flags ; Customer-managed keys (optional)
SBOM + SLSA provenance + signed packages ; Private package registry
Compliance Report Generator ; SLA/SLO telemetry ; Incident response runbooks
```

---

## 7. Milestone Roadmap

### Phase 0 — Roadmap, Truth Labeling, Stabilization
- **Goal:** Make the current state honest, safe, maintainable.
- **Scope:** Docs relabeling, package banners, SDK-mapping docstring fix, strict validation mode, duplicate-ID validation, hashing doc/impl fix, recorder timestamp + prev-hash, redaction list fix, privacy_manifest rename.
- **Out of scope:** Any native code, any new framework work, any execution.
- **Deliverables:** Relabeled `MOBILE_RUNTIME_SDK.md`; `private:true` on Expo/RN packages; `mobile_sdk_mapping.py` docstring + dropped-field record; `models.py` strict mode; dup-ID checks; `hashing.py` fix; `recorder.py` real clock + `prev_event_hash`; `redaction.py` list fix; `privacy_manifest_intent` rename; this roadmap committed.
- **Files:** `models.py`, `validation.py`, `hashing.py`, `recorder.py`, `redaction.py`, `mobile_sdk_mapping.py`, `cli/mobile.py`, package.json×2, docs.
- **Risks:** Renames are breaking → provide migration alias + notes.
- **Security gates:** No new execution surface; CI forbidden-primitive grep still green.
- **Compliance gates:** None (no artifacts yet).
- **Tests:** Strict-mode rejection, dup-ID, prev-hash tamper, redaction list, CLI smoke.
- **Docs:** Update REAL_VS_MOCK, PRODUCTION_READINESS, NO_OVERCLAIM.
- **Acceptance:** All audit P0 items closed; `check-banned-claims.sh` passes; suite green.
- **Demo:** `arc mobile simulate` + `arc mobile trace verify` show real timestamps + chain.
- **Release:** Tag `v0.2.0-preview`.
- **Rollback:** Revert renames via alias; no data migration needed.

### Phase 1 — Schema & Protocol Hardening
- **Goal:** One source of truth.
- **Scope:** JSON Schema for manifest/plan/report/event/trace/policy; codegen for TS types + validators; Python parity tests; Dart/Swift/Kotlin model stubs; migration strategy.
- **Out of scope:** Native execution, approval engine.
- **Deliverables:** 6 schemas under `runtimes/mobile/spec/`; `tools/mobile/schema_codegen.py`; generated `mobile-*.validated.ts` (Zod); parity test; migration map doc.
- **Files:** `runtimes/mobile/spec/*.schema.json`, `packages/arc-protocol-ts/src/*`, new `generated/` dirs.
- **Risks:** Codegen drift → CI check that regenerates and diffs.
- **Security gates:** Schemas enforce `.mock`, background/network=false, mcp_exposable=false.
- **Tests:** Schema validates all fixtures; parity Python↔TS; regen-diff clean.
- **Acceptance:** `arc mobile schema check` passes; loader validates against schema.
- **Release:** `v0.2.x`.

### Phase 2 — Validation & Policy Hardening
- **Goal:** Fail-closed, enterprise-extensible governance.
- **Deliverables:** Strict mode default-on for production loader; capability-ID regex (`^[a-z0-9]+(\.[a-z0-9_]+)+$`); dup capability/step ID detection; permission registry (`ios.*`, `android.*` allowlist); platform cross-check; metadata redaction enforcement; V4 write→error in strict; policy versioning; policy decision audit context; `EnterprisePolicyHook` interface.
- **Files:** `validation.py`, `policy.py`, new `mobile/permission_registry.py`, `mobile/policy_context.py`.
- **Security gates:** Unknown permission ID → error; duplicate IDs → error.
- **Tests:** Regex, dup IDs, unknown permission, platform mismatch, strict V4, policy_version present.
- **Acceptance:** Strict mode rejects all negative fixtures; policy decisions carry version.

### Phase 3 — Trace & Replay
- **Goal:** Credible, tamper-evident traces.
- **Deliverables:** `prev_event_hash`; embed plan_hash/manifest_hash/policy_version/sdk_version/app_build; deterministic + wall-clock modes; `arc mobile trace verify`; `arc mobile replay`; golden trace tests; tamper tests; redacted fixture snapshots; SIEM export design doc.
- **Files:** `recorder.py`, `cli/mobile.py`, new `mobile/replay.py`, fixtures.
- **Security gates:** Reorder/delete/insert detected; signing prototype.
- **Tests:** Chain verify, tamper (reorder/delete/mutate), replay==golden, deterministic mode stable.
- **Acceptance:** `trace verify` fails on any mutation; `replay` matches golden byte-for-byte in deterministic mode.

### Phase 4 — Fixture-Backed Simulator
- **Goal:** Move from static prediction to deterministic mock execution.
- **Deliverables:** Capability fixture registry; per-capability input/output schemas; mock state store; memory/calendar/contacts/photos/location fixture outputs; failure + malicious fixtures; fuzz tests; replay comparison; Theia sim visualization design.
- **Files:** new `mobile/fixtures_registry.py`, `mobile/mock_store.py`, `runtimes/mobile/fixtures/**`.
- **Security gates:** Fixture outputs contain no real PII; malicious fixtures blocked.
- **Tests:** Output matches fixture; bad input blocked; fuzz finds no crash/bypass.
- **Acceptance:** Every `.mock` capability has input/output schema + fixture + failure case.

### Phase 5 — Compliance Generators
- **Goal:** Advisory app-store artifacts from manifests.
- **Deliverables:** `PrivacyInfo.xcprivacy` generator; iOS usage-string generator; Android manifest generator; Data Safety notes; review notes; human-review flag; snapshot tests; CLI commands; non-legal-status docs; CI compliance diff.
- **Files:** new `mobile/compliance/` (ios.py, android.py, review_notes.py), `cli/mobile.py`.
- **Compliance gates:** Output marked "advisory, requires human review"; never auto-submitted.
- **Tests:** Snapshot for each generator; diff detects permission change.
- **Acceptance:** Generators produce valid artifacts from the safe-demo manifest; snapshots stable.

### Phase 6 — Expo SDK Preview (first real framework target)
- **Goal:** First buildable mobile framework module (mock-native).
- **Deliverables:** Expo Module structure; Swift + Kotlin scaffolds (mock implementations, no sensitive access); config plugin; TS API; mock-native bridge; event emitter; trace writer; permission-state introspection (mock); example app; Jest tests; native build checks; dev-client instructions; build pipeline.
- **Files:** `runtimes/mobile/expo/packages/arc-mobile-runtime/{ios,android,src,plugin}`, example app, CI.
- **Security gates:** Native code returns fixtures only; CI greps for `AVCapture`/`CLLocation`/etc in native dirs and fails if present.
- **Tests:** Jest, native build (xcodebuild/gradle), config-plugin snapshot, example smoke.
- **Acceptance:** `expo prebuild` + iOS/Android build succeed; example app runs simulator; no sensitive API referenced.
- **Release:** `@arc/mobile-runtime-expo@0.5.0`.

### Phase 7 — Signed Plan & Approval Engine
- **Goal:** Safely cross from planning into governed execution.
- **Deliverables:** Signed plan envelope; signature verification; plan provenance; `ApprovalGrant` model; approval scopes; expiry + revocation; user-visible approval prompt model; biometric/PIN abstraction; `ConsentReceipt`; policy binds to approval evidence; tests for expired/revoked/spoofed.
- **Files:** new `mobile/signing.py`, `mobile/approval.py`, `mobile/consent.py`, `policy.py`, `models.py`.
- **Security gates:** No sensitive step executes without valid signature + unexpired scoped grant.
- **Tests:** Bad sig, expired grant, revoked grant, scope mismatch, replay attack.
- **Acceptance:** All spoof/expiry/replay tests fail closed; consent receipt recorded in trace.

### Phase 8 — Secure Local Storage & Privacy Budget
- **Goal:** Local-first storage + egress control.
- **Deliverables:** Keychain/Keystore abstraction; encrypted local memory capsule; SQLite schema; data classification tags; privacy budget ledger; egress policy; export/delete APIs; offline mode; retention controls; leakage/migration tests.
- **Files:** native storage modules + `mobile/privacy_budget.py`, `mobile/local_store.py`.
- **Security gates:** Data at rest encrypted; egress over budget blocked.
- **Tests:** Leakage, migration, budget enforcement, export/delete.
- **Acceptance:** No plaintext sensitive data at rest; egress respects budget.

### Phase 9 — React Native SDK
- **Goal:** RN New Architecture support.
- **Deliverables:** TurboModule interface; Codegen specs; iOS + Android native modules; JSI/event bridge; package exports; example app; native tests; RN version matrix; build pipeline.
- **Files:** `runtimes/mobile/react-native/packages/arc-mobile-runtime/**`.
- **Acceptance:** Codegen compiles; iOS/Android build; example runs; events bridge.
- **Release:** `@arc/mobile-runtime-rn@0.8.0` (beta label).

### Phase 10 — Flutter SDK
- **Goal:** Flutter platform interface + plugin.
- **Deliverables:** Dart API; platform interface; Method/EventChannel bridge; iOS + Android implementations; example app; unit/widget/integration tests; pub.dev readiness; build pipeline.
- **Files:** `runtimes/mobile/flutter/packages/arc_mobile_runtime/{lib,android,ios,example}`.
- **Acceptance:** `flutter analyze` clean; example builds; channels work.
- **Release:** `arc_mobile_runtime@0.8.0` (beta).

### Phase 11 — Native Capability Expansion (gated)
- **Goal:** Carefully introduce real native capabilities.
- **Entry criteria (ALL required before ANY real capability):** signed plan verification live (Phase 7); scoped approval engine live (Phase 7); tamper-evident signed traces live (Phase 3+7); compliance generators live (Phase 5); device-lab CI; rollback flag + kill switch.
- **Deliverables (per capability):** real implementation behind flag; permission mapping; approval model; compliance artifact; device-lab tests; UX; rollback; review notes.
- **Order:** see Section 22.
- **Acceptance:** Each capability passes its own entry gate; default-off feature flag; kill switch verified.

### Phase 12 — Enterprise Readiness
- **Goal:** Enterprise-grade governance + ops.
- **Deliverables:** Org/tenant policy engine; admin policy bundles (signed); RBAC/ABAC; MDM hooks; device posture; app attestation; SIEM export; audit retention; admin dashboard/API; feature flags; remote kill switch; compliance report generator; SBOM; SLSA/provenance; signed packages; vuln scanning; enterprise release channel.
- **Acceptance:** Tenant isolation test; RBAC denial test; SIEM export test; SBOM emitted; signed packages verified.

---

## 8. Work Breakdown Structure

| Epic | Story | Task | Files/modules | Owner type | Dependencies | Acceptance | Tests |
|---|---|---|---|---|---|---|---|
| Docs honesty | Relabel | Title + banners | docs, package.json | Tech writer | — | Banners present | check-banned-claims |
| Docs honesty | Field rename | `privacy_manifest_intent` | models, fixtures | Backend | — | No misleading bool | validation test |
| Schema gen | Author schemas | 6 JSON Schemas | spec/ | Protocol | Phase 0 | Validate fixtures | schema check |
| Schema gen | Codegen | TS/Dart/Swift/Kotlin | tools/, generated/ | Protocol | schemas | Parity | parity test |
| Python hardening | Strict mode | `extra="forbid"` | models.py | Backend | — | Reject unknown | strict test |
| Python hardening | Dup IDs | unique check | validation.py | Backend | — | Reject dup | dup test |
| Validation hardening | Permission registry | allowlist | permission_registry.py | Security | schemas | Unknown→error | registry test |
| Policy hardening | Versioning | policy_version | policy.py | Security | — | Present in decision | policy test |
| Policy hardening | Enterprise hook | interface | policy_context.py | Security | versioning | Hook callable | hook test |
| Trace/replay | Prev-hash | chain field | recorder.py | Security | — | Tamper detected | tamper test |
| Trace/replay | Replay CLI | replay cmd | replay.py, cli | Backend | prev-hash | Match golden | replay test |
| Simulator fixtures | Registry | fixture registry | fixtures_registry.py | Backend | schemas | Output matches | fixture test |
| Simulator fixtures | Fuzz | property tests | tests/ | QA | registry | No bypass | fuzz test |
| CLI | New commands | verify/replay/generate | cli/mobile.py | Backend | phases 3/5 | JSON stable | CLI tests |
| TS protocol | Validators | Zod | arc-protocol-ts | Frontend | schemas | Reject invalid | validator test |
| Expo SDK | Module | Swift/Kotlin scaffold | expo/** | Mobile | phases 1–5 | Build passes | native build |
| Expo SDK | Config plugin | plugin | expo/plugin | Mobile | module | Injects perms | plugin snapshot |
| RN SDK | TurboModule | codegen+native | react-native/** | Mobile | Expo | Build passes | native test |
| Flutter SDK | Plugin | platform interface | flutter/** | Mobile | Expo | analyze clean | dart test |
| Native iOS | Permission map | Info.plist | ios native | Mobile | compliance | Strings present | snapshot |
| Native Android | Permission map | manifest | android native | Mobile | compliance | Perms present | snapshot |
| Compliance | iOS privacy | generator | compliance/ios.py | Compliance | schemas | Valid xcprivacy | snapshot |
| Compliance | Android safety | generator | compliance/android.py | Compliance | schemas | Valid notes | snapshot |
| App-store | Review notes | generator | compliance/review_notes.py | Compliance | generators | Notes produced | snapshot |
| Enterprise | Org policy | engine | enterprise/policy.py | Security | policy hook | Org applied | tenant test |
| Enterprise | RBAC | roles | enterprise/rbac.py | Security | org policy | Role denies | rbac test |
| Enterprise | SIEM | export | enterprise/siem.py | Security | trace v2 | CEF valid | export test |
| Security | Signed plans | envelope | signing.py | Security | schemas | Bad sig reject | sig test |
| Security | Approval | engine | approval.py | Security | signing | Scope enforce | approval test |
| CI/CD | Package build | workflows | .github/workflows | Release | packages | Build green | CI |
| Release eng | Semantic release | versioning | CI | Release | build | Tagged release | release test |
| Examples/docs | Example apps | demos | examples/ | DevRel | SDKs | Smoke runs | smoke test |
| Theia UI | Capability cards | widget | arc-mobile-widget.tsx | Frontend | schemas | Cards render | jest-axe |
| SwarmGraph | Signed handoff | integration | signing.py | Backend | signing | Verified plan | handoff test |
| MCP dev bridge | Loopback bridge | gated bridge | mcp dev-bridge | Security | approval | Token+TTL | bridge test |
| Testing/QA | Matrix | CI matrix | CI | QA | all | Matrix green | — |

---

## 9. Backlog (100+ items)

> ID format: `MOB-###`. Estimate: S(<1d) / M(1–3d) / L(1–2wk) / XL(>2wk).

### Immediate (P0, this week / next 2 weeks — Phase 0)

| ID | Title | P | Type | Files | Deps | Acceptance | Tests | Est | Target |
|---|---|---|---|---|---|---|---|---|---|
| MOB-001 | Real timestamp in recorder + `--deterministic` flag | P0 | bug | recorder.py, cli | — | Prod traces use wall clock; CI deterministic | recorder ts test | S | v0.2 |
| MOB-002 | Add `prev_event_hash` chain | P0 | security | recorder.py | 001 | Reorder/delete detected | tamper test | M | v0.2 |
| MOB-003 | Promote V4 write→error in strict mode | P0 | security | validation.py | 010 | Write w/o HITL/trust fails strict | v4 test | S | v0.2 |
| MOB-004 | Duplicate capability ID detection | P0 | security | validation.py | — | Dup IDs → error | dup test | S | v0.2 |
| MOB-005 | Duplicate step ID detection | P0 | security | validation.py | — | Dup step IDs → error | dup step test | S | v0.2 |
| MOB-006 | Fix `hashing.py` docstring re schema_version | P0 | docs | hashing.py | — | Docstring matches code | — | S | v0.2 |
| MOB-007 | Decide+implement schema_version hash policy | P0 | refactor | hashing.py | 006 | Documented + tested | hash test | S | v0.2 |
| MOB-008 | Fix `redact_list` to redact string items | P0 | security | redaction.py | — | Secret string in list redacted | redaction test | S | v0.2 |
| MOB-009 | Rename `privacy_manifest`→`privacy_manifest_intent` + alias | P0 | refactor | models.py, fixtures | — | No misleading bool; alias works | migration test | M | v0.2 |
| MOB-010 | Strict mode (`extra="forbid"`) loader path | P0 | security | models.py, manifest.py | — | Unknown field rejected in strict | strict test | M | v0.2 |
| MOB-011 | Mark Expo/RN packages `private:true` | P0 | release | package.json×2 | — | npm publish blocked | — | S | v0.2 |
| MOB-012 | Fix `mobile_sdk_mapping.py` docstring + record dropped fields | P0 | docs | mobile_sdk_mapping.py | — | Accurate; dropped fields in metadata | mapping test | S | v0.2 |
| MOB-013 | Add `--dry-run` to `arc mobile pin` | P0 | feature | cli/mobile.py | — | Dry-run prints, no write | cli test | S | v0.2 |
| MOB-014 | CLI smoke tests for all 9 commands | P0 | test | tests/ | — | Happy+error path each | cli tests | M | v0.2 |
| MOB-015 | `extra_capabilities` sensitivity guard in simulator | P0 | security | simulator.py | — | Non-mock sensitive extra blocked | sim test | S | v0.2 |
| MOB-016 | Catalog unique-ID assertion at import | P0 | bug | capabilities.py | — | Import fails on dup | import test | S | v0.2 |
| MOB-017 | Negative fixtures (dup-ID, malformed, malicious metadata) | P0 | test | fixtures/ | 004 | Fixtures exist + tested | fixture tests | M | v0.2 |
| MOB-018 | Update REAL_VS_MOCK/PRODUCTION_READINESS/NO_OVERCLAIM | P0 | docs | docs/mobile | 001–016 | Docs match code | check-banned-claims | S | v0.2 |
| MOB-019 | Theia widget: add "simulator preview" banner + prev-hash status | P0 | docs | arc-mobile-widget.tsx | 002 | Banner visible | jest-axe | S | v0.2 |
| MOB-020 | `arc mobile trace verify` command | P0 | feature | cli, recorder | 002 | Detects tamper, exit 1 | verify test | M | v0.2 |

### Short-term (P1, 30–60 days — Phases 1–3)

| ID | Title | P | Type | Files | Deps | Acceptance | Est | Target |
|---|---|---|---|---|---|---|---|---|
| MOB-021 | JSON Schema: manifest | P1 | feature | spec/ | — | Validates fixtures | M | v0.2 |
| MOB-022 | JSON Schema: action plan | P1 | feature | spec/ | — | Validates fixtures | S | v0.2 |
| MOB-023 | JSON Schema: simulation report | P1 | feature | spec/ | — | Validates output | S | v0.2 |
| MOB-024 | JSON Schema: runtime event | P1 | feature | spec/ | exists | Tighten + validate | S | v0.2 |
| MOB-025 | JSON Schema: trace | P1 | feature | spec/ | 024 | Validates JSONL | S | v0.2 |
| MOB-026 | JSON Schema: policy decision | P1 | feature | spec/ | — | Validates decision | S | v0.2 |
| MOB-027 | Wire schema validation into `load_manifest` | P1 | security | manifest.py | 021 | Invalid manifest rejected | M | v0.2 |
| MOB-028 | Schema codegen tool | P1 | feature | tools/mobile | 021–026 | Regen-diff clean | L | v0.5 |
| MOB-029 | Generate TS types from schema | P1 | refactor | arc-protocol-ts | 028 | Replaces hand mirror | M | v0.5 |
| MOB-030 | Zod runtime validators (TS) | P1 | security | arc-protocol-ts | 029 | Invalid rejected | M | v0.5 |
| MOB-031 | Python↔TS parity test | P1 | test | tests/ | 029 | Fields match | S | v0.5 |
| MOB-032 | Capability-ID regex validation | P1 | security | validation.py | — | Bad ID → error | S | v0.2 |
| MOB-033 | Permission registry (ios/android allowlist) | P1 | security | permission_registry.py | — | Unknown perm → error | M | v0.5 |
| MOB-034 | Platform cross-check (manifest vs capability) | P1 | security | validation.py | — | Mismatch → error | S | v0.5 |
| MOB-035 | Metadata schema constraint | P1 | security | models.py, validation | 010 | Arbitrary metadata bounded | M | v0.5 |
| MOB-036 | `policy_version` in MobilePolicyDecision | P1 | feature | policy.py | — | Present in output | S | v0.5 |
| MOB-037 | Policy decision logging to audit file | P1 | security | policy.py | 036 | Decisions appended | M | v0.5 |
| MOB-038 | EnterprisePolicyHook interface | P1 | feature | policy_context.py | 036 | Hook callable | M | v0.5 |
| MOB-039 | Embed plan/manifest/policy hashes in events | P1 | security | recorder.py | 002 | Present in event | M | v0.5 |
| MOB-040 | Embed sdk_version/app_build in events | P1 | feature | recorder.py | 039 | Present in event | S | v0.5 |
| MOB-041 | Trace signing (HMAC prototype) | P1 | security | recorder.py | 002 | Forgery detected | M | v0.5 |
| MOB-042 | `arc mobile replay` command | P1 | feature | replay.py, cli | 002 | Matches golden | M | v0.5 |
| MOB-043 | Golden trace fixtures + replay test | P1 | test | fixtures, tests | 042 | Replay==golden | M | v0.5 |
| MOB-044 | Tamper test suite (reorder/delete/mutate) | P1 | test | tests | 002 | All fail closed | M | v0.5 |
| MOB-045 | Schema migration map (v1→v2) doc + code | P1 | feature | models.py, docs | 010 | Migration test passes | M | v0.5 |
| MOB-046 | `arc mobile schema export` / `schema check` | P1 | feature | cli | 021–026 | Schemas emitted/checked | S | v0.5 |
| MOB-047 | Runtime-pack bridge: emit `capabilities_detail` | P1 | bug | runtime_pack.py | — | Detail preserved | S | v0.5 |
| MOB-048 | Honor `gate_policy` in arc_runtime_sdk_pack | P1 | bug | arc_runtime_sdk_pack.py | — | Gate reflected | M | v0.5 |
| MOB-049 | Standardize `simulate` to `--plan` only (+deprecation) | P1 | refactor | cli | — | One arg path | S | v0.5 |
| MOB-050 | Fuzz/property tests for manifest + plan | P1 | test | tests | 010 | No crash/bypass | M | v0.5 |

### Mid-term (P2, 60–90 days — Phases 4–6)

| ID | Title | P | Type | Deps | Acceptance | Est | Target |
|---|---|---|---|---|---|---|---|
| MOB-051 | Capability fixture registry | P2 | feature | 021 | Each cap has fixture | L | v0.5 |
| MOB-052 | Per-capability input schemas | P2 | feature | 051 | Bad input blocked | M | v0.5 |
| MOB-053 | Per-capability output schemas | P2 | feature | 051 | Output validated | M | v0.5 |
| MOB-054 | Mock state store | P2 | feature | 051 | Memory write/read consistent | M | v0.5 |
| MOB-055 | Failure fixtures per capability | P2 | test | 051 | Failures modeled | M | v0.5 |
| MOB-056 | Malicious plan fixtures | P2 | security | 051 | Blocked | M | v0.5 |
| MOB-057 | Replay comparison in simulator | P2 | test | 042 | Deterministic | M | v0.5 |
| MOB-058 | iOS PrivacyInfo.xcprivacy generator | P2 | compliance | 021 | Valid artifact | L | v0.5 |
| MOB-059 | iOS usage-string generator | P2 | compliance | 058 | Strings present | M | v0.5 |
| MOB-060 | Android manifest generator | P2 | compliance | 021 | Perms present | L | v0.5 |
| MOB-061 | Android Data Safety generator | P2 | compliance | 060 | Notes valid | M | v0.5 |
| MOB-062 | App-store review notes generator | P2 | compliance | 058,060 | Notes produced | M | v0.5 |
| MOB-063 | Human-review flag on all generators | P2 | compliance | 058 | Flag required | S | v0.5 |
| MOB-064 | `arc mobile generate ios-privacy` | P2 | feature | 058 | Emits file | S | v0.5 |
| MOB-065 | `arc mobile generate android-manifest` | P2 | feature | 060 | Emits file | S | v0.5 |
| MOB-066 | `arc mobile generate data-safety` | P2 | feature | 061 | Emits notes | S | v0.5 |
| MOB-067 | `arc mobile generate review-notes` | P2 | feature | 062 | Emits notes | S | v0.5 |
| MOB-068 | CI compliance diff | P2 | compliance | 058–062 | Diff on perm change | M | v0.5 |
| MOB-069 | Expo Module package structure | P2 | feature | 028 | `expo prebuild` ok | L | v0.5 |
| MOB-070 | Expo Swift scaffold (mock) | P2 | feature | 069 | xcodebuild ok | L | v0.5 |
| MOB-071 | Expo Kotlin scaffold (mock) | P2 | feature | 069 | gradle ok | L | v0.5 |
| MOB-072 | Expo config plugin | P2 | feature | 069,059 | Injects perms | M | v0.5 |
| MOB-073 | Expo TS API + mock-native bridge | P2 | feature | 069 | API callable | M | v0.5 |
| MOB-074 | Expo event emitter + trace writer | P2 | feature | 073 | Events flow | M | v0.5 |
| MOB-075 | Expo permission-state introspection (mock) | P2 | feature | 073 | Returns mock state | S | v0.5 |
| MOB-076 | Expo example app | P2 | feature | 073 | Runs on simulator | M | v0.5 |
| MOB-077 | Expo Jest tests | P2 | test | 073 | Green | M | v0.5 |
| MOB-078 | Expo native build CI | P2 | release | 070,071 | iOS+Android build | M | v0.5 |
| MOB-079 | Expo package build pipeline (tsc→dist) | P2 | release | 069 | `npm pack` valid | M | v0.5 |
| MOB-080 | CI grep: no sensitive native API in Expo native dirs | P2 | security | 070,071 | Fails if present | S | v0.5 |
| MOB-081 | Theia capability cards UI | P2 | feature | 029 | Cards render | M | v0.5 |
| MOB-082 | Theia simulator visualization | P2 | feature | 081 | Steps shown | M | v0.8 |

### Long-term (P3, 90 days–6 months — Phases 7–11)

| ID | Title | P | Type | Deps | Acceptance | Est | Target |
|---|---|---|---|---|---|---|---|
| MOB-083 | Signed plan envelope + verification | P3 | security | 041 | Bad sig reject | L | v0.8 |
| MOB-084 | Plan provenance metadata | P3 | security | 083 | Provenance present | M | v0.8 |
| MOB-085 | ApprovalGrant model + scopes | P3 | security | 083 | Scope enforced | L | v0.8 |
| MOB-086 | Approval expiry + revocation | P3 | security | 085 | Expired/revoked deny | M | v0.8 |
| MOB-087 | Biometric/PIN abstraction | P3 | security | 085 | Re-auth modeled | M | v0.8 |
| MOB-088 | ConsentReceipt + trace binding | P3 | compliance | 085 | Receipt in trace | M | v0.8 |
| MOB-089 | Approval spoof/replay test suite | P3 | test | 085 | All fail closed | M | v0.8 |
| MOB-090 | Keychain/Keystore abstraction | P3 | security | — | Encrypted at rest | L | v0.8 |
| MOB-091 | Encrypted local memory capsule (SQLite) | P3 | security | 090 | No plaintext PII | L | v0.8 |
| MOB-092 | Privacy budget ledger | P3 | security | — | Over-budget blocked | M | v0.8 |
| MOB-093 | Data-egress guard | P3 | security | 092 | Egress gated | M | v0.8 |
| MOB-094 | Export/delete APIs + retention | P3 | compliance | 091 | Delete/export work | M | v1.0 |
| MOB-095 | RN TurboModule interface + Codegen | P3 | feature | 069 | Compiles | XL | v0.8 |
| MOB-096 | RN iOS+Android native modules | P3 | feature | 095 | Build passes | XL | v0.8 |
| MOB-097 | RN example app + tests | P3 | test | 095 | Runs | M | v0.8 |
| MOB-098 | Flutter Dart API + platform interface | P3 | feature | 028 | analyze clean | XL | v0.8 |
| MOB-099 | Flutter iOS+Android plugin impl | P3 | feature | 098 | Build passes | XL | v0.8 |
| MOB-100 | Flutter example + tests | P3 | test | 098 | Runs | M | v0.8 |
| MOB-101 | Device-lab CI (Maestro/XCTest/Espresso) | P3 | test | 078 | Opt-in green | L | v1.0 |
| MOB-102 | Native: real local notification (gated) | P3 | feature | Phase11 gate | Entry criteria met | L | v1.0 |
| MOB-103 | Native: system file/photo picker (gated) | P3 | feature | Phase11 gate | Entry criteria met | L | v1.0 |
| MOB-104 | Rollback flags + remote kill switch | P3 | security | 102 | Kill disables cap | M | v1.0 |

### Enterprise (P4, 6–12 months — Phase 12)

| ID | Title | P | Type | Deps | Acceptance | Est | Target |
|---|---|---|---|---|---|---|---|
| MOB-105 | Org/tenant policy engine | P4 | security | 038 | Org policy applied | XL | ent v1.x |
| MOB-106 | Signed admin policy bundles | P4 | security | 105 | Bad bundle rejected | L | ent v1.x |
| MOB-107 | RBAC | P4 | security | 105 | Role denies action | L | ent v1.x |
| MOB-108 | ABAC | P4 | security | 107 | Attribute gates | L | ent v1.x |
| MOB-109 | Tenant isolation | P4 | security | 105 | No cross-tenant leak | L | ent v1.x |
| MOB-110 | Device posture interface | P4 | security | — | Posture gate | M | ent v1.x |
| MOB-111 | MDM integration hooks | P4 | feature | 110 | Config applied | L | ent v1.x |
| MOB-112 | App attestation | P4 | security | — | Attestation verified | L | ent v1.x |
| MOB-113 | SIEM export (CEF/JSON) | P4 | security | 039 | Valid export | L | ent v1.x |
| MOB-114 | Audit retention + legal hold | P4 | compliance | 113 | Retention enforced | M | ent v1.x |
| MOB-115 | Admin dashboard/API | P4 | feature | 105 | CRUD policy | XL | ent v1.x |
| MOB-116 | Feature flags service | P4 | feature | — | Flags toggle | M | ent v1.x |
| MOB-117 | Compliance report generator | P4 | compliance | 113 | Report produced | L | ent v1.x |
| MOB-118 | SBOM generation | P4 | release | — | SBOM emitted | M | ent v1.x |
| MOB-119 | SLSA provenance + package signing | P4 | release | 118 | Provenance verified | L | ent v1.x |
| MOB-120 | Vulnerability scanning in CI | P4 | security | — | Scan gates release | M | ent v1.x |
| MOB-121 | Private enterprise package registry | P4 | release | 119 | Private install works | M | ent v1.x |
| MOB-122 | SSO/SAML/OIDC for admin | P4 | feature | 115 | Login works | L | ent v1.x |
| MOB-123 | SCIM provisioning | P4 | feature | 122 | Users synced | M | ent v1.x |
| MOB-124 | Customer-managed keys | P4 | security | 090 | CMK encrypts | L | ent v1.x |
| MOB-125 | SLA/SLO telemetry | P4 | feature | — | Metrics emitted | M | ent v1.x |

---

## 10. First 10 PRs (exact order)

### PR 1 — Truth-label docs and package warnings
- **Branch:** `mob/pr1-truth-labeling`
- **Goal:** Eliminate the highest-risk overclaims with zero behavior change.
- **Scope:** Docs titles + banners; `private:true` on Expo/RN; READMEs note "stub/no native bridge"; Flutter README "zero Dart, stub".
- **Files:** `docs/MOBILE_RUNTIME_SDK.md`, `docs/mobile/*`, `runtimes/mobile/**/package.json`, `runtimes/mobile/**/README.md`, `runtimes/mobile/flutter/.../pubspec.yaml` (description).
- **Implementation notes:** No code logic changes. Update `MOBILE_RUNTIME_SDK.md` line "records hash-linked traces" → "records per-event-hashed traces (previous-hash chain pending; see roadmap Phase 3)".
- **Tests:** `scripts/check-banned-claims.sh` passes; no test logic change.
- **Docs:** This is the docs PR.
- **Acceptance:** All package descriptions say "simulator stub"; no doc claims native access; banned-claims green.
- **Risk:** Low. **Rollback:** revert commit.

### PR 2 — Strict validation + duplicate ID checks
- **Branch:** `mob/pr2-strict-validation`
- **Goal:** Fail-closed on unknown fields and duplicate IDs.
- **Scope:** `extra="forbid"` strict loader path; dup capability ID; dup step ID; capability-ID regex; promote V4 write→error in strict; catalog unique-ID assertion.
- **Files:** `models.py`, `manifest.py`, `validation.py`, `capabilities.py`.
- **Implementation notes:** Keep default loader lenient with a `strict: bool=False` param; add `load_manifest(path, strict=True)`. Strict mode flips V4 to error.
- **Tests:** strict-reject-unknown, dup-cap-ID, dup-step-ID, bad-ID-regex, V4-error-in-strict, catalog-unique.
- **Docs:** Validation rules table updated.
- **Acceptance:** All negative fixtures rejected in strict; lenient default unchanged.
- **Risk:** Medium (strict could break existing manifests). **Rollback:** strict is opt-in, so revert is safe.

### PR 3 — SDK mapping loss fix
- **Branch:** `mob/pr3-sdk-mapping-loss`
- **Goal:** Stop misleading "no silent drop" claim; record dropped fields.
- **Scope:** Fix `mobile_sdk_mapping.py` docstring; add `_dropped_fields` list into SDK card metadata; round-trip test asserts dropped fields are recorded.
- **Files:** `mobile_sdk_mapping.py`, `tests/test_mobile_sdk_mapping.py`.
- **Implementation notes:** Forward direction adds `card["metadata"]={"arc_dropped_fields":[...]}` capturing platforms/permissions/background/network/reads/writes/requires_trust values so the inverse can reconstruct.
- **Tests:** forward records dropped fields; round-trip restores background/network/reads/writes.
- **Acceptance:** No field silently lost; round-trip preserves governance fields.
- **Risk:** Low. **Rollback:** revert.

### PR 4 — Hashing + trace chain fix
- **Branch:** `mob/pr4-trace-chain`
- **Goal:** Make traces tamper-evident and timestamps real.
- **Scope:** `prev_event_hash` field; real `datetime.now(timezone.utc)` default with `deterministic: bool` mode; embed `manifest_hash`/`plan_hash`/`policy_version`/`sdk_version`; fix `hashing.py` docstring + decide `schema_version` policy; `arc mobile trace verify`.
- **Files:** `recorder.py`, `hashing.py`, `cli/mobile.py`, `models.py` (event fields), `mobile-events.ts`, `mobile-events.schema.json`.
- **Implementation notes:** First event `prev_event_hash="0"*64`. `trace verify` recomputes chain and fails on mismatch.
- **Tests:** chain-verify, reorder-detected, delete-detected, mutate-detected, deterministic-stable, real-ts-differs.
- **Docs:** Trace format doc + "tamper-evident chain" now accurate.
- **Acceptance:** `trace verify` exits 1 on any mutation; deterministic mode reproducible.
- **Risk:** Medium (event schema change). **Rollback:** schema is additive; revert CLI.

### PR 5 — JSON Schemas for all mobile protocol objects
- **Branch:** `mob/pr5-json-schemas`
- **Goal:** Single source of truth for the protocol.
- **Scope:** Author/extend schemas: manifest, action plan, simulation report, event (exists), trace, policy decision; wire validation into `load_manifest`.
- **Files:** `runtimes/mobile/spec/*.schema.json`, `manifest.py`, tests.
- **Implementation notes:** Use `jsonschema` (already a transitive dep or add pinned). Validate on load when `strict=True`.
- **Tests:** every fixture validates; invalid manifest rejected; report/plan/trace validate.
- **Acceptance:** `arc mobile schema check` passes against all fixtures.
- **Risk:** Low. **Rollback:** validation gated behind strict.

### PR 6 — Generated TS validators and parity tests
- **Branch:** `mob/pr6-ts-validators`
- **Goal:** Runtime validation in TS; kill drift.
- **Scope:** Codegen tool (schema→TS types + Zod); replace hand mirror; Python↔TS parity test.
- **Files:** `tools/mobile/schema_codegen.py`, `packages/arc-protocol-ts/src/generated/*`, parity test.
- **Implementation notes:** Keep `mobile-runtime.ts` re-exporting generated types for back-compat.
- **Tests:** Zod rejects invalid; parity test (field names/types match Python); regen-diff clean in CI.
- **Acceptance:** Invalid object rejected at runtime; parity green.
- **Risk:** Medium (generated code review). **Rollback:** keep hand mirror as fallback export.

### PR 7 — Trace replay CLI
- **Branch:** `mob/pr7-replay`
- **Goal:** Prove determinism via golden replay.
- **Scope:** `mobile/replay.py`; `arc mobile replay`; golden fixtures.
- **Files:** `replay.py`, `cli/mobile.py`, `runtimes/mobile/fixtures/traces/*.golden.jsonl`.
- **Tests:** replay==golden; replay detects divergence.
- **Acceptance:** `arc mobile replay` matches golden in deterministic mode; diff on change.
- **Risk:** Low. **Rollback:** revert.

### PR 8 — Fixture-backed simulator skeleton
- **Branch:** `mob/pr8-fixture-simulator`
- **Goal:** Begin moving from static prediction to deterministic mock execution.
- **Scope:** `fixtures_registry.py`; per-capability input/output schema scaffolding; mock state store for `app.memory.*`.
- **Files:** `fixtures_registry.py`, `mock_store.py`, `simulator.py`, fixtures.
- **Tests:** memory write→read consistent; bad input blocked; output matches fixture.
- **Acceptance:** `app.memory.write.mock`/`retrieve.mock` produce consistent fixture-backed output.
- **Risk:** Medium. **Rollback:** keep static path as default.

### PR 9 — Compliance generator skeleton
- **Branch:** `mob/pr9-compliance-skeleton`
- **Goal:** Generate advisory iOS/Android artifacts (dry-run).
- **Scope:** `compliance/ios.py` (PrivacyInfo.xcprivacy), `compliance/android.py` (manifest); `arc mobile generate ios-privacy|android-manifest`; human-review banner.
- **Files:** `mobile/compliance/*`, `cli/mobile.py`, snapshot fixtures.
- **Tests:** snapshot for safe-demo manifest; advisory flag present.
- **Acceptance:** Valid artifacts generated; marked advisory/human-review.
- **Risk:** Low. **Rollback:** revert.

### PR 10 — Expo Module scaffold
- **Branch:** `mob/pr10-expo-scaffold`
- **Goal:** First buildable framework module (mock-native only).
- **Scope:** Expo Module structure; Swift+Kotlin mock scaffolds; config plugin; TS API; package build (tsc→dist); CI grep for forbidden native APIs.
- **Files:** `runtimes/mobile/expo/packages/arc-mobile-runtime/{ios,android,src,plugin,expo-module.config.json,tsconfig.json}`.
- **Implementation notes:** Native returns fixtures only; no `AVCapture`, `CLLocation`, `CNContact`, etc. CI fails if those symbols appear.
- **Tests:** Jest; `expo prebuild`; iOS/Android build; config-plugin snapshot; forbidden-API grep.
- **Acceptance:** Package builds; example prebuilds; no sensitive native symbol present.
- **Risk:** Medium (native toolchain in CI). **Rollback:** keep package `private:true`; revert if CI unstable.

---

## 11. File-Level Implementation Plan

### Existing Python files

**`mobile/models.py`**
- Add `model_config = ConfigDict(extra="forbid")` behind a strict flag; keep `_Base` lenient default + `_StrictBase` for production.
- Rename `MobileRuntimeManifest.privacy_manifest` → `privacy_manifest_intent`; add deprecated alias property.
- Add event-provenance fields to `MobileRuntimeEvent` (if centralized here): `prev_event_hash`, `manifest_hash`, `plan_hash`, `policy_version`, `sdk_version`, `app_build`.
- Add `schema_version` migration map and `migrate(data)` helper.
- Add `ApprovalGrant`, `ConsentReceipt`, `PrivacyBudget`, `DeviceContext`, `PolicyContext`, `RuntimeMode` models (Phase 7/8).

**`mobile/capabilities.py`**
- Add module-load assertion: unique IDs.
- Add per-capability `input_schema`/`output_schema` references (Phase 4).
- No new real capabilities until Phase 11 gates.

**`mobile/manifest.py`**
- Add `strict: bool=False` to `load_manifest`; when strict, run JSON Schema validation + `_StrictBase`.
- Add duplicate-ID check post-load.

**`mobile/validation.py`**
- Add: dup capability ID, dup step ID, capability-ID regex, platform cross-check, permission-registry check, metadata constraint.
- Promote `write_requires_hitl_or_trust` to error in strict mode.
- Return `policy_version` context.

**`mobile/simulator.py`**
- Add sensitivity guard: any `extra_capabilities` with `data_sensitivity>=HIGH` must end `.mock` else block.
- Add input/output schema validation when fixtures present (Phase 4).
- Consume `DeviceContext`/permission-state/approval-state when provided (Phases 4/7).

**`mobile/policy.py`**
- Add `policy_version` to `MobilePolicyDecision`.
- Add decision logging (append to `~/.arc/audit/mobile_decisions.jsonl`).
- Add `EnterprisePolicyHook` extension point + `PolicyContext` (org/user/device).
- Bind decision to approval evidence (Phase 7).

**`mobile/recorder.py`**
- Replace fixed timestamp with `datetime.now(timezone.utc)`; add `deterministic` mode.
- Add `prev_event_hash` chain; embed manifest/plan/policy/sdk/app_build.
- Add HMAC signing (Phase 3) → asymmetric (Phase 7).
- Add `verify_trace()` used by CLI.

**`mobile/hashing.py`**
- Fix docstring; decide `schema_version` policy (recommend add to `_VOLATILE` with documented migration rationale).
- Add domain separation prefixes (`cap:`, `manifest:`, `plan:`, `report:`, `event:`).

**`mobile/redaction.py`**
- In `redact_list`, apply `Redactor.is_safe()` to string items; recurse nested lists.
- Add metadata-specific redaction pass.

**`mobile/runtime_pack.py`**
- Emit `capabilities_detail` (full cards) alongside ID list.
- Preserve per-platform support detail.

**`cli/mobile.py`**
- Add: `replay`, `trace verify`, `trace diff`, `fixture generate/validate`, `schema export/check`, `generate ios-privacy/android-manifest/data-safety/review-notes`, `privacy-budget`, `policy compile/verify`, `plan sign/verify`, `approval issue/revoke`, `package doctor`, `expo/rn/flutter doctor`, `device-lab`, `mcp dev-bridge`.
- Add `--dry-run` to `pin`; standardize `simulate` to `--plan`.
- Add CLI tests (CliRunner) for all commands.

**`mobile_sdk_mapping.py`**
- Fix docstring (forward is lossy by design).
- Record dropped fields in `metadata.arc_dropped_fields`.

**`adapters/arc_runtime_sdk.py`**
- Document/surface `gate_policy` status in `CapabilityReport`.

**`adapters/arc_runtime_sdk_pack.py`**
- Honor `gate_policy` (reflect approved gates in permissions/metadata).

### Existing TS files
- `mobile-runtime.ts` → re-export generated types (back-compat).
- `mobile-capability.ts`, `mobile-action-plan.ts`, `mobile-events.ts`, `mobile-trace.ts` → align with generated; add Zod validators.
- `index.ts` → export validators + `validateMobile*` functions.

### Existing package areas
- `expo/packages/arc-mobile-runtime/` → full Expo Module (Phase 6).
- `expo/packages/arc-mobile-expo/` → thin wrapper; rename scope `@arc/mobile-runtime-expo`.
- `react-native/packages/arc-mobile-runtime/` → TurboModule (Phase 9); scope `@arc/mobile-runtime-rn`.
- `flutter/packages/arc_mobile_runtime/` → `lib/`, platform interface, plugins (Phase 10).

### New files to propose

| Path | Purpose |
|---|---|
| `runtimes/mobile/spec/mobile-action-plan.schema.json` | Plan schema |
| `runtimes/mobile/spec/mobile-simulation-report.schema.json` | Report schema |
| `runtimes/mobile/spec/mobile-trace.schema.json` | Trace schema |
| `runtimes/mobile/spec/mobile-policy-decision.schema.json` | Policy decision schema |
| `tools/mobile/schema_codegen.py` | Schema→TS/Dart/Swift/Kotlin codegen |
| `packages/arc-protocol-ts/src/generated/` | Generated TS types + Zod |
| `runtimes/mobile/dart/lib/models.dart` | Generated Dart models |
| `runtimes/mobile/swift/Sources/ARCMobileModels/` | Generated Swift models |
| `runtimes/mobile/kotlin/src/main/kotlin/` | Generated Kotlin models |
| `python/src/agent_runtime_cockpit/mobile/replay.py` | Replay engine |
| `python/src/agent_runtime_cockpit/mobile/fixtures_registry.py` | Fixture registry |
| `python/src/agent_runtime_cockpit/mobile/mock_store.py` | Mock state store |
| `python/src/agent_runtime_cockpit/mobile/signing.py` | Plan/trace signing |
| `python/src/agent_runtime_cockpit/mobile/approval.py` | Approval engine |
| `python/src/agent_runtime_cockpit/mobile/consent.py` | Consent receipts |
| `python/src/agent_runtime_cockpit/mobile/privacy_budget.py` | Privacy budget |
| `python/src/agent_runtime_cockpit/mobile/permission_registry.py` | OS permission allowlist |
| `python/src/agent_runtime_cockpit/mobile/policy_context.py` | Org/user/device context |
| `python/src/agent_runtime_cockpit/mobile/compliance/ios.py` | PrivacyInfo.xcprivacy generator |
| `python/src/agent_runtime_cockpit/mobile/compliance/android.py` | Android manifest/data-safety |
| `python/src/agent_runtime_cockpit/mobile/compliance/review_notes.py` | App-store review notes |
| `python/src/agent_runtime_cockpit/mobile/enterprise/policy.py` | Org policy engine |
| `python/src/agent_runtime_cockpit/mobile/enterprise/rbac.py` | RBAC/ABAC |
| `python/src/agent_runtime_cockpit/mobile/enterprise/siem.py` | SIEM export |
| `docs/mobile/QUICKSTART.md` … (see Section 18) | Docs |
| `docs/adr/00NN-mobile-signed-plans.md` | ADR: signed plans |
| `docs/adr/00NN-mobile-approval-engine.md` | ADR: approval |
| `.github/workflows/mobile-python.yml` | Python CI |
| `.github/workflows/mobile-ts.yml` | TS build/test |
| `.github/workflows/mobile-expo.yml` | Expo build |
| `.github/workflows/mobile-rn.yml` | RN build |
| `.github/workflows/mobile-flutter.yml` | Flutter build |

---

## 12. CLI Roadmap

> All commands: loopback-only, no network unless explicitly gated, JSON via `ok()`/`err()` envelopes, exit 0 success / 1 policy-deny or validation-fail / 2 usage error. CI-safe by default.

### Current commands (keep, harden)

| Command | Purpose | Inputs | Outputs | Exit | Safety | Tests |
|---|---|---|---|---|---|---|
| `doctor` | SDK health + catalog summary | `--json` | schema_version, counts, status | 0 | read-only | smoke |
| `capabilities` | List capabilities | `--manifest`, `--json` | capability list | 0/1 | read-only | smoke + manifest |
| `validate` | Validate manifest | `<path>`, `--json` | findings | 0/1 | read-only | ok+fail |
| `simulate` | Dry-run plan | `--plan`, `--manifest`, `--trace`, `--json` | report (+trace) | 0/1 | no exec | allow+block |
| `trace` | Inspect trace | `<file>`, `--json` | events + hash | 0/1 | read-only | smoke |
| `policy explain` | Explain decision | `--capability`\|`--plan`, `--json` | decision | 0/1 | read-only | cap+plan |
| `init-runtime-pack` | Scaffold pack | `<target>`, `--id`, `--name` | pack + manifest | 0 | writes dir | smoke |
| `export-runtime-pack` | Inspect pack | `<path>`, `--json` | summary | 0/1 | read-only | smoke |
| `pin` | Recompute manifest_hash | `<path>`, **`--dry-run`** | hash | 0/1 | mutates (add dry-run) | dry+write |

### Proposed commands

| Command | Purpose | Inputs | Outputs | Exit | Safety gates | Example |
|---|---|---|---|---|---|---|
| `replay` | Replay trace vs golden | `<trace>`, `--golden`, `--json` | match/diff | 0/1 | read-only | `arc mobile replay t.jsonl --golden g.jsonl` |
| `trace verify` | Verify hash chain + signature | `<trace>`, `--json` | ok/tamper detail | 0/1 | read-only | `arc mobile trace verify t.jsonl` |
| `trace diff` | Diff two traces | `<a> <b>`, `--json` | diff | 0/1 | read-only | `arc mobile trace diff a b` |
| `fixture generate` | Build fixture from sim | `--plan`, `--out` | fixture file | 0/1 | writes file | `... fixture generate --plan p.json --out f.json` |
| `fixture validate` | Validate fixture vs schema | `<fixture>` | findings | 0/1 | read-only | `... fixture validate f.json` |
| `schema export` | Emit JSON Schemas | `--out` | schema files | 0 | writes dir | `... schema export --out spec/` |
| `schema check` | Validate objects vs schema | `<file>`, `--kind` | findings | 0/1 | read-only | `... schema check m.json --kind manifest` |
| `generate ios-privacy` | PrivacyInfo.xcprivacy | `--manifest`, `--out` | advisory artifact | 0/1 | advisory, human-review | `... generate ios-privacy --manifest m.json` |
| `generate android-manifest` | AndroidManifest perms | `--manifest`, `--out` | advisory artifact | 0/1 | advisory | `... generate android-manifest` |
| `generate data-safety` | Play Data Safety notes | `--manifest`, `--out` | advisory notes | 0/1 | advisory | `... generate data-safety` |
| `generate review-notes` | App-store review notes | `--manifest`, `--out` | advisory notes | 0/1 | advisory | `... generate review-notes` |
| `privacy-budget` | Summarize egress/read budget | `--manifest`, `--json` | ledger | 0 | read-only | `... privacy-budget` |
| `policy compile` | Compile org policy bundle | `<policy>`, `--out` | compiled bundle | 0/1 | signed bundle | `... policy compile org.yaml` |
| `policy verify` | Verify policy bundle sig | `<bundle>` | ok/fail | 0/1 | sig check | `... policy verify b.bin` |
| `plan sign` | Sign action plan | `--plan`, `--key` | signed envelope | 0/1 | key handling | `... plan sign --plan p.json` |
| `plan verify` | Verify plan signature | `<envelope>` | ok/fail | 0/1 | sig check | `... plan verify e.json` |
| `approval issue` | Issue scoped grant | `--cap`, `--scope`, `--ttl` | grant | 0/1 | scoped/expiring | `... approval issue --cap x --ttl 300` |
| `approval revoke` | Revoke grant | `<grant-id>` | ok | 0/1 | revocation | `... approval revoke g1` |
| `package doctor` | Check package buildability | `--platform` | report | 0/1 | read-only | `... package doctor --platform expo` |
| `expo doctor` | Expo module health | — | report | 0/1 | read-only | `... expo doctor` |
| `rn doctor` | RN module health | — | report | 0/1 | read-only | `... rn doctor` |
| `flutter doctor` | Flutter plugin health | — | report | 0/1 | read-only | `... flutter doctor` |
| `device-lab` | Opt-in real-device tests | `--platform`, `--opt-in` | results | 0/1 | opt-in, no secrets | `... device-lab --platform ios --opt-in` |
| `mcp dev-bridge` | Dev-only loopback bridge | `--token`, `--ttl`, `--enable` | status | 0/1 | loopback+token+TTL, default-off, no sensitive caps | `... mcp dev-bridge --enable --ttl 600` |

**Example output (`trace verify`, tampered):**
```json
{"ok": false, "error": {"code": "INVALID_INPUT", "message": "trace chain broken at sequence 3"},
 "data": {"expected_prev": "abc…", "actual_prev": "def…", "first_bad_sequence": 3}}
```

---

## 13. SDK API Roadmap

### Shared concepts (canonical models)
| Model | Key fields | Notes |
|---|---|---|
| `MobileCapability` | id, name, category, platforms, required_permissions, approval_mode, data_sensitivity, reads/writes/network/paid/background, replayable, auditable, mcp_exposable, simulator_supported, requires_trust/hitl, metadata, capability_hash, **input_schema, output_schema** (new) | Add I/O schemas in Phase 4 |
| `MobileRuntimeManifest` | schema_version, id, name, version, platforms, capabilities, background_execution, network_by_default, simulator_mode, **privacy_manifest_intent**, manifest_hash | Rename bool field |
| `MobileActionPlan` | schema_version, plan_id, name, steps, requires_network/background, plan_hash, **signature, provenance** (new) | Envelope in Phase 7 |
| `MobileRuntimeEvent` | + **prev_event_hash, manifest_hash, plan_hash, policy_version, sdk_version, app_build, approval_ref** | Phase 3/7 |
| `MobileTrace` | plan_id, events, trace_hash, **signature, signed_root** | Phase 3/7 |
| `MobilePolicyDecision` | allowed, approval_required, reason, denied_rules, required_approvals, mcp_exposable, **policy_version, context_ref** | Phase 2 |
| `ApprovalGrant` (new) | grant_id, capability_id, scope, issued_at, expires_at, revoked, subject, plan_hash | Phase 7 |
| `ConsentReceipt` (new) | receipt_id, grant_id, user_visible_text, accepted_at, evidence_hash | Phase 7 |
| `PrivacyBudget` (new) | reads, writes, egress_bytes, sensitive_classes, limits | Phase 8 |
| `RuntimeMode` (new) | enum: simulator \| mock_native \| native_gated | Banner everywhere |
| `DeviceContext` (new) | platform, os_version, app_build, posture, attestation | Phases 7/12 |
| `PolicyContext` (new) | org_id, tenant_id, user_id, roles, device_posture | Phase 12 |

### TypeScript API
```ts
// Types (generated from JSON Schema)
export type { MobileCapability, MobileRuntimeManifest, MobileActionPlan,
  MobileRuntimeEvent, MobileTrace, MobilePolicyDecision, ApprovalGrant,
  ConsentReceipt, PrivacyBudget, RuntimeMode, DeviceContext, PolicyContext };

// Runtime validators (Zod)
export function validateMobileCapability(o: unknown): MobileCapability;   // throws ArcValidationError
export function validateMobileManifest(o: unknown): MobileRuntimeManifest;
export function validateActionPlan(o: unknown): MobileActionPlan;

// Simulator client (talks to ARC daemon/CLI; no native exec)
export interface SimulatorClient {
  simulate(plan: MobileActionPlan, manifest?: MobileRuntimeManifest): Promise<MobileActionSimulationReport>;
}
// Trace client
export interface TraceClient {
  read(path: string): Promise<MobileTrace>;
  verify(trace: MobileTrace): Promise<{ ok: boolean; firstBadSequence?: number }>;
  replay(trace: MobileTrace, golden: MobileTrace): Promise<{ match: boolean }>;
}
// Approval APIs (Phase 7)
export interface ApprovalClient {
  issue(capId: string, scope: string, ttlSec: number): Promise<ApprovalGrant>;
  revoke(grantId: string): Promise<void>;
}
// Errors + events
export class ArcValidationError extends Error {}
export type ArcEvent = MobileRuntimeEvent;
export interface EventSubscription { on(cb: (e: ArcEvent) => void): () => void; }
export function registerCapability(cap: MobileCapability): void; // dev registry
```

### Expo API
```ts
export function ArcMobileRuntimeProvider(props: { mode: RuntimeMode; children: React.ReactNode }): JSX.Element;
export function getCapabilities(): Promise<MobileCapability[]>;
export function simulateActionPlan(plan: MobileActionPlan): Promise<MobileActionSimulationReport>;
export function verifyActionPlan(envelope: SignedPlanEnvelope): Promise<{ ok: boolean }>;   // Phase 7
export function requestApproval(capId: string, scope: string, ttlSec: number): Promise<ApprovalGrant>; // Phase 7
export function executeApprovedAction(grant: ApprovalGrant, step: MobileActionStep): Promise<StepResult>; // Phase 11, gated
export function subscribeToEvents(cb: (e: MobileRuntimeEvent) => void): () => void;
export function readTrace(): Promise<MobileTrace>;
export function exportTrace(format: "jsonl" | "siem"): Promise<string>;
export function getPermissionState(capId: string): Promise<PermissionState>; // mock until Phase 11
export function generateComplianceReport(): Promise<{ ios: string; android: string; advisory: true }>;
```
> Until Phase 11, `executeApprovedAction` returns fixture results; `getPermissionState` returns mock state. Banner: `mode==="simulator"`.

### React Native API (TurboModule, Phase 9)
```ts
export interface Spec extends TurboModule {
  getCapabilities(): Promise<MobileCapability[]>;
  simulateActionPlan(planJson: string): Promise<string>; // report JSON
  verifyActionPlan(envelopeJson: string): Promise<boolean>;
  requestApproval(capId: string, scope: string, ttlSec: number): Promise<string>; // grant JSON
  getPermissionState(capId: string): Promise<string>;
  readTrace(): Promise<string>;
  addListener(eventName: string): void; removeListeners(count: number): void; // event emitter
}
```

### Flutter API (Phase 10)
```dart
class ArcMobileRuntime {
  Future<List<MobileCapability>> getCapabilities();
  Future<MobileActionSimulationReport> simulateActionPlan(MobileActionPlan plan);
  Future<bool> verifyActionPlan(SignedPlanEnvelope envelope);
  Future<ApprovalGrant> requestApproval(String capId, String scope, Duration ttl);
  Stream<MobileRuntimeEvent> get events;                  // EventChannel
  Future<MobileTrace> readTrace();
  Future<PermissionState> getPermissionState(String capId);
}
abstract class ArcMobileRuntimePlatform extends PlatformInterface { /* method channel */ }
```

### Native iOS API (Swift, Phases 6/11)
```swift
public enum RuntimeMode { case simulator, mockNative, nativeGated }
public struct ARCCapability: Codable { /* mirror */ }
public protocol ARCPermissionMapper { func usageStrings() -> [String:String] }   // NSCameraUsageDescription…
public final class ARCPrivacyManifestGenerator { public func generate() -> Data } // PrivacyInfo.xcprivacy
public protocol ARCSecureStore { func put(_:Data, key:String) throws; func get(key:String) throws -> Data } // Keychain
public final class ARCEventRecorder { public func record(_ e: ARCRuntimeEvent) } // prev-hash chain
```
> Native sensitive APIs (AVCapture, CLLocation, CNContact…) are **forbidden** until Phase 11 entry gates pass; CI greps for them.

### Native Android API (Kotlin, Phases 6/11)
```kotlin
enum class RuntimeMode { SIMULATOR, MOCK_NATIVE, NATIVE_GATED }
data class ARCCapability(/* mirror */)
interface ARCPermissionMapper { fun manifestPermissions(): List<String> }       // uses-permission
class ARCManifestGenerator { fun generate(): String }                            // AndroidManifest fragment
interface ARCSecureStore { fun put(key: String, value: ByteArray); fun get(key: String): ByteArray } // Keystore
class ARCEventRecorder { fun record(e: ARCRuntimeEvent) }
// WorkManager only ever for explicit offline-queue flush (Phase 11+, gated); never free-running.
```

---

## 14. Security Roadmap

### Threat model summary
- **Assets:** user device data (contacts/photos/location/etc), action plans, approval grants, traces, org policy, signing keys.
- **Trust boundaries:** SwarmGraph→plan; plan→policy; policy→approval; approval→native bridge; bridge→OS; device→SIEM.
- **Adversaries:** malicious/compromised plan source, malicious manifest author, on-device malware reading traces, network attacker, insider.

### STRIDE / abuse-case register

| Risk | Scenario | Current mitigation | Missing mitigation | Roadmap item | Acceptance |
|---|---|---|---|---|---|
| Spoofing (plan) | Forged action plan | none | signed envelope | MOB-083 | Bad sig rejected |
| Spoofing (approval) | Fake approval grant | none | signed grants + scope | MOB-085/86 | Spoof denied |
| Tampering (trace) | Reorder/delete events | per-event hash only | prev-hash chain + signing | MOB-002/041 | Tamper detected |
| Tampering (manifest) | Inject unknown fields | `extra="ignore"` (bad) | strict mode | MOB-010 | Unknown rejected |
| Repudiation | "Agent didn't do that" | trace exists | signed trace + approval ref | MOB-039/041/088 | Non-repudiable |
| Info disclosure (secrets) | Secret in manifest/metadata | redaction (partial) | list-string redaction, metadata schema | MOB-008/035 | Secret redacted |
| Info disclosure (payload) | Raw payload in trace | payload hashed | confirm no raw payload | MOB-039 | Hash-only verified |
| DoS (fuzz) | Malformed plan crashes | basic validation | fuzz/property tests | MOB-050 | No crash |
| Elevation (capability) | Non-mock sensitive via extras | sensitive-prefix block | extras sensitivity guard | MOB-015 | Blocked |
| Elevation (metadata smuggle) | Unsafe value in metadata | none | metadata schema constraint | MOB-035 | Constrained |
| Plan tampering (replay) | Re-use old signed plan | none | nonce/expiry in envelope | MOB-083/086 | Replay rejected |
| Native bridge abuse | Sensitive API w/o approval | no native yet | Phase 11 gates + CI grep | MOB-080/102+ | No bypass |
| Permission overreach | Request all perms | least-privilege catalog | permission registry | MOB-033 | Unknown perm denied |
| Background abuse | Hidden background work | hard-blocked | keep blocked; WorkManager gated | Phase 11 | Blocked |
| Network exfiltration | Egress sensitive data | network blocked | egress guard + budget | MOB-092/093 | Egress gated |
| MCP bridge risk | Remote tool surface | denied in policy | dev-only loopback/token/TTL | Section 20 | No remote |
| Supply chain | Malicious dep | none | SBOM + scanning + pinned deps | MOB-118/120 | Scan gates |
| Package signing | Tampered package | none | SLSA provenance + signing | MOB-119 | Verified |
| Secrets handling | Key leakage | redaction | secure key store, CMK | MOB-090/124 | Keys protected |
| Local storage | Plaintext at rest | none | Keychain/Keystore + encrypted SQLite | MOB-090/091 | Encrypted |
| Attestation | Tampered app/device | none | app attestation + posture | MOB-110/112 | Verified |
| Policy bypass (org) | Ignore org policy | local only | org policy engine + signed bundles | MOB-105/106 | Enforced |

### Security phases
- **S0 (Phase 0–2):** strict mode, dup-ID, regex, permission registry, extras guard, metadata constraint, redaction fix.
- **S1 (Phase 3):** prev-hash chain + HMAC trace signing + tamper tests.
- **S2 (Phase 7):** signed plan envelope, approval scopes/expiry/revocation, consent receipts, spoof/replay tests.
- **S3 (Phase 8):** secure local store, egress guard, privacy budget.
- **S4 (Phase 11):** native bridge CI grep, device-lab denial tests, kill switch.
- **S5 (Phase 12):** org policy, RBAC/ABAC, attestation, MDM, SIEM, SBOM, signing, vuln scanning.

---

## 15. Privacy & Compliance Roadmap

### Coverage map

| Area | Requirement | Deliverable | Phase | Acceptance |
|---|---|---|---|---|
| Apple App Review | No hidden features, explicit consent | Review-notes generator + human review | 5 | Notes generated |
| Apple privacy manifests | `PrivacyInfo.xcprivacy` | iOS generator | 5 | Valid artifact snapshot |
| iOS usage descriptions | `NS*UsageDescription` | Usage-string generator | 5 | Strings per permission |
| App Intents | User-visible only | Generate only for approved caps | 11 | No generic automation |
| BackgroundTasks | OS-scheduled, constrained | Keep background blocked; offline-queue only | 11 | No autonomous background |
| Android permissions | Least-privilege manifest | Android manifest generator | 5 | Minimal perms |
| Android Data Safety | Declared collection | Data Safety generator | 5 | Notes valid |
| Scoped storage | System picker only | File/photo picker via system UI | 11 | No broad storage perm |
| Contacts/location/photos/mic/camera | Explicit consent + rationale | Per-cap approval + usage string | 11 | Consent enforced |
| Health data | Separate review | Out of scope until dedicated review | post-12 | Not enabled |
| User consent | Per-action | ConsentReceipt | 7 | Receipt recorded |
| Data minimization | Only needed data | Capability declares reads/writes | 2 | Validated |
| Data retention | Bounded | Retention policy | 8/12 | Enforced |
| Deletion/export | User rights | Export/delete APIs | 8 | Works |
| GDPR-style | Lawful basis, DSAR | Consent + export/delete + audit | 8/12 | DSAR satisfiable |
| SOC2-style | Audit, access control | RBAC + audit export + retention | 12 | Controls evidenced |
| HIPAA-style | Only if PHI (avoid) | Not targeted; document exclusion | — | Explicit exclusion |
| Enterprise legal review | Sign-off workflow | Human-review flag + compliance diff | 5/12 | Review required |

### Compliance deliverables
- `compliance/ios.py` → `PrivacyInfo.xcprivacy` (NSPrivacyAccessedAPITypes, collected data types) — advisory.
- `compliance/android.py` → `AndroidManifest` permission fragment + Data Safety JSON — advisory.
- `compliance/review_notes.py` → human-readable review notes per capability.
- `consent.py` → `ConsentReceipt` model + trace binding.
- `arc mobile generate ...` CLI family + CI compliance diff (fails PR if permissions change without doc update).
- Human-review workflow: every generated artifact carries `"advisory": true, "requires_human_review": true`; never auto-submitted.

---

## 16. Testing Roadmap

### Python tests
- Model validation; strict mode rejection; dup capability/step IDs; capability-ID regex; permission registry; platform cross-check; hashing determinism + domain separation; redaction (dicts, lists, string items, metadata); simulator allow/block/extras-guard; policy decision + version; trace prev-hash chain; tamper (reorder/delete/mutate); replay vs golden; fixture-backed I/O; CLI JSON outputs + exit codes for all commands; malicious manifests; fuzz/property (Hypothesis) on manifest + plan.

### TypeScript tests
- Type parity (Python↔TS field/type); Zod validator accept/reject; schema snapshot; package export surface; build (tsc) test; regen-diff (generated == committed).

### Expo tests
- Jest unit; native module mock returns fixtures; config-plugin snapshot; example app smoke (Detox optional); iOS build (xcodebuild); Android build (gradle); forbidden-native-API grep.

### React Native tests
- TurboModule Codegen compile; iOS+Android native build; event bridge emit/receive; example app smoke; RN version matrix (0.76+ New Architecture).

### Flutter tests
- Dart unit; platform-interface contract; plugin build (iOS+Android); widget test; integration test; example app smoke; `flutter analyze` clean.

### Device tests (opt-in, gated)
- Simulator/emulator runs; real-device opt-in (device-lab); permission-prompt tests; background-constraint tests; app-store artifact snapshot tests.

### Security tests
- Trace tamper; plan/trace signature; approval spoof/expiry/revocation/replay; metadata secret leakage; egress exfiltration; native-bridge denial (no sensitive API without approval).

### Enterprise tests
- Org policy bundle apply; signed-bundle rejection; RBAC denial; ABAC attribute gate; tenant isolation (no cross-tenant); SIEM export format (CEF/JSON valid); audit retention; legal hold.

### Test matrix

| Layer | Unit | Integration | Snapshot | Security | Device | CI gate |
|---|---|---|---|---|---|---|
| Python core | ✓ | ✓ | ✓ (CLI JSON) | ✓ | — | required |
| TS protocol | ✓ | ✓ (fixtures) | ✓ (schema) | ✓ (validator) | — | required |
| Expo | ✓ | ✓ | ✓ (plugin) | ✓ (grep) | opt-in | required (build) |
| RN | ✓ | ✓ | ✓ (codegen) | ✓ | opt-in | required (build) |
| Flutter | ✓ | ✓ | — | ✓ | opt-in | required (build) |
| Compliance | ✓ | — | ✓ (artifacts) | — | — | required (diff) |
| Enterprise | ✓ | ✓ | — | ✓ | — | required |

---

## 17. CI/CD & Release Roadmap

### Pipelines (GitHub Actions)

| Workflow | Triggers | Steps | Gate |
|---|---|---|---|
| `mobile-python.yml` | PR touching `mobile/**`, `cli/mobile.py` | ruff, mypy, pytest (mobile), forbidden-primitive grep, banned-claims | block merge on fail |
| `mobile-ts.yml` | PR touching `arc-protocol-ts/**` | tsc build, jest, schema regen-diff, parity | block |
| `mobile-expo.yml` | PR touching `expo/**` | tsc→dist, jest, expo prebuild, xcodebuild, gradle, forbidden-native grep | block (build) |
| `mobile-rn.yml` | PR touching `react-native/**` | codegen, jest, native build | block |
| `mobile-flutter.yml` | PR touching `flutter/**` | flutter analyze, dart test, plugin build | block |
| `mobile-compliance.yml` | PR touching capabilities/manifests | generate artifacts, snapshot diff, compliance diff | warn→block |
| `mobile-security.yml` | PR + nightly | dependency scan, SBOM, secret scan, tamper tests | block |
| `mobile-release.yml` | tag | build all, sign, provenance, publish (channel-gated) | manual approve |

### Release engineering
- **Channels:** `alpha` (internal), `beta` (developer preview), `stable` (production), `enterprise` (private registry).
- **Versioning:** semver; framework packages independent (`@arc/mobile-runtime-expo`, `-rn`, `arc_mobile_runtime`).
- **Changelog:** generated; migration notes required for any schema change.
- **Signing:** packages signed; SLSA provenance attached (Phase 12).
- **SBOM:** generated per release (CycloneDX).
- **Rollback:** feature flags + remote kill switch (Phase 11/12); revert published version via deprecate + republish prior.
- **Deprecation policy:** additive-only protocol; deprecate with one minor of overlap + migration note.

---

## 18. Documentation Roadmap

| Doc | Path | Audience | Purpose | Required content | Acceptance |
|---|---|---|---|---|---|
| Current state | `docs/mobile/REAL_VS_MOCK.md` (exists) | all | Truth matrix | real/mock/stub per area | matches code |
| Real vs mock | same | reviewers | classification | updated each phase | banned-claims green |
| Quickstart | `docs/mobile/QUICKSTART.md` | devs | first sim run | install, doctor, simulate, trace verify | runs as written |
| CLI reference | `docs/mobile/CLI.md` | devs | all commands | inputs/outputs/exit/examples | matches `--help` |
| Capability manifest | `docs/mobile/CAPABILITY_MANIFEST.md` | devs | schema + fields | field semantics, enforcement | schema-linked |
| Action plan format | `docs/mobile/ACTION_PLAN.md` | devs | plan schema | fields, signing (Phase 7) | schema-linked |
| Trace format | `docs/mobile/TRACE_FORMAT.md` | devs/security | trace + chain | prev-hash, verify | tamper test ref |
| Policy model | `docs/mobile/POLICY.md` | security | decisions | rules, versioning, context | matches policy.py |
| Simulator | `docs/mobile/SIMULATOR.md` | devs | dry-run | static vs fixture-backed | examples |
| Fixtures | `docs/mobile/FIXTURES.md` | devs/QA | fixture registry | how to add | examples |
| Replay | `docs/mobile/REPLAY.md` | QA/security | golden replay | determinism | examples |
| Compliance generation | `docs/mobile/COMPLIANCE.md` | compliance | artifacts | advisory status, human review | non-legal disclaimer |
| Expo SDK | `docs/mobile/EXPO.md` | mobile devs | usage | API, config plugin, example | example builds |
| React Native SDK | `docs/mobile/REACT_NATIVE.md` | mobile devs | usage | TurboModule, New Arch | beta label |
| Flutter SDK | `docs/mobile/FLUTTER.md` | mobile devs | usage | plugin, channels | beta label |
| Native iOS | `docs/mobile/NATIVE_IOS.md` | native devs | Swift API | permission map, privacy gen | examples |
| Native Android | `docs/mobile/NATIVE_ANDROID.md` | native devs | Kotlin API | permission map, keystore | examples |
| Security model | `docs/mobile/SECURITY.md` | security | threat model | STRIDE, gates | matches roadmap |
| Privacy model | `docs/mobile/PRIVACY.md` | compliance | data handling | minimization, retention | matches code |
| Enterprise admin | `docs/mobile/ENTERPRISE.md` | admins | governance | org policy, RBAC, SIEM | Phase 12 |
| Troubleshooting | `docs/mobile/TROUBLESHOOTING.md` | all | common issues | doctor outputs | covers errors |
| Migration guide | `docs/mobile/MIGRATION.md` | devs | version moves | v1→v2, renames | per release |
| Release notes | `docs/mobile/CHANGELOG.md` | all | history | per version | generated |
| What not to build | `docs/mobile/DO_NOT_BUILD.md` | all | guardrails | banned features | matches Section "do not build" |
| App-store review guide | `docs/mobile/APP_STORE.md` | submitters | checklist | iOS+Android gates | matches Section 21 |
| MCP dev bridge warning | `docs/mobile/MCP_BRIDGE.md` | security | risk + rules | loopback/token/TTL | matches Section 20 |
| Production readiness | `docs/mobile/PRODUCTION_READINESS.md` (exists) | release | gate | checklist | drives go/no-go |
| No-overclaim policy | `docs/mobile/NO_OVERCLAIM_POLICY.md` (exists) | all | wording | allowed/forbidden | enforced |

---

## 19. Enterprise Roadmap

| Capability | Description | Deliverable | Phase | Acceptance |
|---|---|---|---|---|
| Org policy | Org-wide allow/deny + defaults | `enterprise/policy.py` | 12 | Org policy overrides local, tested |
| Tenant isolation | No cross-tenant data/policy | tenant-scoped stores | 12 | Cross-tenant access test fails closed |
| RBAC | Role→capability grants | `enterprise/rbac.py` | 12 | Role without grant denied |
| ABAC | Attribute-based (dept, posture) | `enterprise/abac.py` | 12 | Attribute gate enforced |
| Admin console/API | CRUD policy, view audit | `enterprise/admin/` | 12 | Policy CRUD + audit view |
| Policy bundles | Signed, versioned bundles | `policy compile/verify` | 12 | Bad signature rejected |
| Device posture | Require compliant device | `policy_context.device_posture` | 12 | Non-compliant blocked |
| MDM | Intune/Jamf config hooks | `enterprise/mdm.py` | 12 | Managed config applied |
| App attestation | App Attest / Play Integrity | `enterprise/attestation.py` | 12 | Tampered app blocked |
| SIEM | CEF/JSON export | `enterprise/siem.py` | 12 | Splunk/Sentinel ingest |
| Audit logs | Immutable, signed | trace v2 + retention | 12 | Tamper-evident |
| Retention | Configurable TTL | retention policy | 12 | Old logs purged per policy |
| Legal hold | Suspend deletion | hold flag | 12 | Held logs retained |
| Data export | DSAR export | export API | 8/12 | Export produced |
| Data deletion | Right to erasure | delete API | 8/12 | Verified deletion |
| Remote kill switch | Disable cap/SDK remotely | flag service | 11/12 | Kill disables in <X min |
| Feature flags | Gradual rollout | flag service | 11/12 | Flag toggles behavior |
| Private registry | Enterprise package install | registry | 12 | Private install works |
| SSO/SAML/OIDC | Admin auth | `enterprise/auth.py` | 12 | Login via IdP |
| SCIM | User provisioning | `enterprise/scim.py` | 12 | Users synced |
| Customer-managed keys | CMK for at-rest | KMS integration | 12 | CMK encrypts store |
| Compliance reports | SOC2/GDPR evidence | report generator | 12 | Report generated |
| Support tools | Diagnostics bundle | `support doctor` | 12 | Bundle redacted |
| SLA/SLO | Latency/availability | telemetry | 12 | Metrics emitted |
| Incident response | Runbooks + alerts | docs + alerts | 12 | Runbook exists |
| Vuln disclosure | Advisory process | SECURITY.md | 12 | Process documented |
| Security review | Pre-release gate | review checklist | 12 | Sign-off recorded |

### Enterprise readiness checklist (go/no-go)
- [ ] Tenant isolation tested (no cross-tenant leak).
- [ ] Org policy engine overrides local policy.
- [ ] RBAC + ABAC enforced and tested.
- [ ] Signed policy bundles; bad signature rejected.
- [ ] Device posture + attestation gates.
- [ ] MDM config hooks.
- [ ] SIEM export validated against ≥1 SIEM.
- [ ] Audit retention + legal hold.
- [ ] DSAR export + deletion.
- [ ] Remote kill switch + feature flags.
- [ ] SBOM + SLSA provenance + signed packages.
- [ ] Vulnerability scanning gates release.
- [ ] Private registry distribution.
- [ ] SSO + SCIM (if required by customer).
- [ ] CMK (if required).
- [ ] Compliance reports + security review sign-off.

---

## 20. MCP Roadmap (high-risk, deliberately constrained)

**Why production MCP gateway is NOT allowed yet:** A production MCP server on a personal mobile device is a remote-reachable tool surface over sensitive capabilities. It violates "no unauthenticated local server," risks app-store rejection, and expands attack surface dramatically. Current policy correctly **denies** `mcp_exposable` (see `policy.py::explain_capability_policy`).

**Dev-only bridge requirements (when introduced):** loopback-only (127.0.0.1); short-lived token; TTL-limited session; disabled by default; **no sensitive capabilities** exposed; explicit per-session user opt-in; audit log of every call; replayable; kill switch; enterprise disable policy; no remote exposure; no background daemon (foreground dev session only).

| Stage | Definition | Gate |
|---|---|---|
| **v0 — no MCP** | MCP exposure denied for all capabilities (current) | default |
| **v1 — dev-only simulator MCP bridge** | Loopback + token + TTL; exposes only `app.*.mock` simulator caps; foreground dev session; audited | written threat model + security review |
| **v2 — local trusted tooling bridge** | Adds local read-only inspection tools for trusted dev machines; still no sensitive caps | pen-test + tamper tests pass |
| **v3 — enterprise-approved controlled bridge** | Org-policy-gated, attested device, RBAC-scoped; sensitive caps only if org explicitly enables + approval engine enforces | full security review + enterprise sign-off |

**Threat model (bridge):** token theft → TTL + loopback bind; replay → nonce; privilege escalation → no sensitive caps in v1/v2; persistence → no background daemon; exfiltration → egress guard. **Tests:** token expiry, loopback-only bind, sensitive-cap rejection, kill switch, audit completeness.

---

## 21. App-Store Roadmap

### iOS — "no submission before" checklist
- [ ] `PrivacyInfo.xcprivacy` generated + human-reviewed (Phase 5).
- [ ] All `NS*UsageDescription` strings present and accurate for every requested permission.
- [ ] App Review notes generated explaining each agent capability and consent flow.
- [ ] App Intents (if any) cover only user-visible, approved, app-owned capabilities — no generic automation.
- [ ] BackgroundTasks: no autonomous background; only OS-scheduled, declared, constrained offline-queue flush.
- [ ] Camera/mic/location/contacts/photos accessed only via user-visible system pickers/prompts with explicit consent.
- [ ] Local network usage declared; no undeclared local server.
- [ ] Data collection disclosure matches actual reads/writes.
- [ ] Review evidence bundle (trace + consent receipts) available.

### Android — "no submission before" checklist
- [ ] `AndroidManifest` permissions generated, least-privilege (Phase 5).
- [ ] Runtime permission requests with rationale UI.
- [ ] Data Safety form generated + human-reviewed.
- [ ] Background work via WorkManager only for declared offline-queue flush; no free-running services.
- [ ] Foreground services (if any) typed + justified.
- [ ] Contacts/location/photos/mic/camera via system pickers + scoped storage.
- [ ] Play policy review for sensitive permissions completed.
- [ ] Data minimization documented.

**Process gate:** No store submission until Phases 5 (artifacts) + 6 (buildable module) + 11 entry criteria for the specific capabilities are met, plus human legal/product review sign-off.

---

## 22. Native Capability Rollout Plan

**Universal entry criteria (ALL must be true before ANY real native capability ships):**
1. Signed plan verification live (Phase 7).
2. Scoped, expiring approval engine live (Phase 7).
3. Tamper-evident signed traces live (Phase 3+7).
4. Compliance artifacts generated + human-reviewed (Phase 5).
5. Device-lab tests green (Phase 11).
6. Per-capability rollback flag + remote kill switch.
7. CI grep confirms no sensitive native symbol outside the approved, gated module path.

### Rollout order (safest first)

| # | Capability | Entry criteria (additional) | Permission map | Approval | Compliance artifact | Tests | UX | Rollback | Reasons to reject |
|---|---|---|---|---|---|---|---|---|---|
| 1 | App memory (mock→fixture-backed) | none beyond universal | none | none | none | fixture+replay | invisible | flag | n/a (no OS access) |
| 2 | Local notification (mock→real) | universal | iOS UN auth / Android POST_NOTIFICATIONS | recommended | usage string + Data Safety | device-lab notify | system prompt | flag | spammy/misleading content |
| 3 | File/photo picker (system UI only) | universal | none broad (system picker) | recommended | review note | device-lab pick | system picker | flag | requesting broad storage perm |
| 4 | Calendar read | universal + consent UX | ios.calendars / READ_CALENDAR | required | privacy + Data Safety | device-lab read | consent prompt | flag | no clear user benefit |
| 5 | Calendar write | universal + HITL | WRITE_CALENDAR | blocking + HITL | privacy + review | device-lab write | confirm each write | flag | silent writes |
| 6 | Location (current, foreground) | universal + purpose string | location.whenInUse / ACCESS_FINE_LOCATION | required | privacy + Data Safety | device-lab loc | foreground prompt | flag | background/continuous tracking |
| 7 | Camera capture (user-visible) | universal + visible capture UI | ios.camera / CAMERA | required | privacy + review | device-lab cam | visible camera UI | flag | hidden capture |
| 8 | Microphone (explicit foreground) | universal + explicit consent + recording indicator | ios.microphone / RECORD_AUDIO | blocking + HITL | privacy + review | device-lab mic | recording indicator | flag | always-on / background |
| 9 | Contacts search | universal + necessity review | ios.contacts / READ_CONTACTS | blocking + HITL | privacy + Data Safety + review | device-lab contacts | per-query consent | flag | bulk export / unnecessary |
| 10 | Health / biometric / background | **separate dedicated security review** | platform-specific | blocking + HITL + re-auth | full privacy + legal | dedicated suite | strict consent | flag + kill | most cases — default reject |

Each capability remains `.mock` until its row's criteria are individually met and evidence is cited. The default answer for rows 7–10 is "not yet."

---

## 23. Risk Register (50+)

| ID | Risk | Prob | Impact | Severity | Mitigation | Owner | Phase |
|---|---|---|---|---|---|---|---|
| R01 | Stub packages published as real SDKs | Med | High | High | `private:true`, build gate | Release | 0 |
| R02 | `extra="ignore"` hides malicious fields | Med | High | High | strict mode | Security | 0 |
| R03 | Fixed trace timestamp misleads forensics | High | Med | High | real clock | Backend | 0 |
| R04 | No prev-hash chain → undetected tamper | Med | High | High | chain + signing | Security | 3 |
| R05 | SDK mapping drops governance fields silently | Med | Med | Med | record dropped fields | Backend | 0 |
| R06 | `privacy_manifest:true` implies compliance | High | Med | High | rename + generator | Compliance | 0/5 |
| R07 | Duplicate IDs accepted | Low | Med | Med | dup checks | Backend | 0 |
| R08 | Schema drift across languages | Med | High | High | codegen + parity | Protocol | 1 |
| R09 | TS guards trivially fooled | Med | Med | Med | Zod validators | Frontend | 1 |
| R10 | JSON Schemas unused in loader | High | Med | Med | wire into load | Backend | 1 |
| R11 | Redaction misses list strings | Med | High | High | list redaction | Security | 0 |
| R12 | Metadata smuggling | Med | Med | Med | metadata schema | Security | 2 |
| R13 | Unknown permission IDs unchecked | Med | Med | Med | permission registry | Security | 2 |
| R14 | Extras bypass sensitive block | Low | High | Med | sensitivity guard | Security | 0 |
| R15 | No policy versioning → irreproducible | Med | Med | Med | policy_version | Security | 2 |
| R16 | Plan forgery | Med | High | High | signed envelope | Security | 7 |
| R17 | Approval spoofing | Med | High | High | signed grants | Security | 7 |
| R18 | Approval replay | Med | High | High | nonce + expiry | Security | 7 |
| R19 | Native bridge sensitive bypass | Low | Crit | High | Phase 11 gates + grep | Security | 11 |
| R20 | Background abuse | Low | High | Med | keep blocked | Security | 11 |
| R21 | Network exfiltration | Med | High | High | egress guard | Security | 8 |
| R22 | MCP remote exposure | Low | Crit | High | deny; dev-bridge only | Security | 20 |
| R23 | Plaintext local storage | Med | High | High | Keychain/Keystore | Security | 8 |
| R24 | Supply-chain compromise | Med | High | High | SBOM + scanning | Release | 12 |
| R25 | Unsigned packages | Med | Med | Med | signing + provenance | Release | 12 |
| R26 | App-store rejection (privacy) | High | High | High | artifact generators | Compliance | 5 |
| R27 | App-store rejection (background) | Med | High | High | no autonomous bg | Compliance | 11 |
| R28 | Data Safety mismatch | Med | High | High | generator + diff | Compliance | 5 |
| R29 | Missing consent | Med | High | High | consent receipts | Compliance | 7 |
| R30 | Over-broad permissions | Med | Med | Med | least-privilege | Compliance | 2 |
| R31 | No tenant isolation | Low | Crit | High | tenant scoping | Security | 12 |
| R32 | No RBAC | Low | High | Med | RBAC engine | Security | 12 |
| R33 | No SIEM export | Med | Med | Med | export module | Security | 12 |
| R34 | No retention/legal hold | Med | Med | Med | retention policy | Compliance | 12 |
| R35 | No kill switch | Med | High | High | flag service | Security | 11 |
| R36 | Expo native build flaky in CI | High | Med | Med | pinned toolchain | Release | 6 |
| R37 | RN New Arch churn | Med | Med | Med | version matrix | Mobile | 9 |
| R38 | Flutter plugin API changes | Med | Med | Med | platform interface | Mobile | 10 |
| R39 | Device-lab cost/instability | Med | Med | Med | opt-in, cached | QA | 11 |
| R40 | Codegen maintenance burden | Med | Med | Med | regen-diff CI | Protocol | 1 |
| R41 | Doc overclaim regressions | Med | Med | Med | banned-claims CI | Tech writer | all |
| R42 | Package name collision (npm) | Med | Med | Med | scoped names | Release | 0 |
| R43 | Breaking schema changes | Med | High | Med | migration map + additive | Protocol | 1 |
| R44 | Key management failure | Low | High | High | KMS/CMK + rotation | Security | 12 |
| R45 | Attestation false negatives | Med | Med | Med | tunable posture | Security | 12 |
| R46 | Fuzz finds parser crash | Med | Med | Med | fuzz suite + fixes | QA | 1 |
| R47 | Consent UX rejected by users | Med | Med | Med | clear rationale | Product | 11 |
| R48 | SwarmGraph handoff drift | Med | Med | Med | shared signed schema | Backend | 7 |
| R49 | Enterprise policy latency | Med | Med | Med | local cache + async | Security | 12 |
| R50 | Mock mistaken for real in demos | High | High | High | RuntimeMode banner | Product | 0 |
| R51 | Trace file deletion (whole file) | Med | Med | Med | external anchor / signed root | Security | 3 |
| R52 | Insider policy tamper | Low | High | Med | signed bundles + audit | Security | 12 |
| R53 | Health data scope creep | Low | Crit | High | dedicated review, default reject | Compliance | post-12 |
| R54 | Over-reliance on simulator == reality | Med | Med | Med | device-lab parity tests | QA | 11 |
| R55 | Abandoned stubs rot | Med | Low | Low | CI build gate or remove | Release | 0 |

---

## 24. Metrics & Success Criteria

### Engineering metrics
- Test coverage: ≥90% lines for `mobile/` Python core; ≥80% for TS protocol.
- Schema parity: 100% field parity Python↔TS↔generated (parity test green).
- Build success: 100% of enabled framework packages build in CI.
- Package publish readiness: `npm pack`/`flutter pub publish --dry-run` clean for non-stub packages.
- CI duration: mobile-python < 5 min; full mobile matrix < 25 min.
- Defect rate: < 1 escaped P0/P1 per release.
- Fuzz findings: 0 unfixed crashes/bypasses at release.

### Security metrics
- Policy denial coverage: 100% of negative fixtures denied.
- Tamper detection: 100% of reorder/delete/mutate cases detected.
- Secret leakage tests: 0 leaks across manifest/metadata/trace.
- Signed plan verification: 100% bad-signature rejection.
- Approval spoofing prevention: 100% spoof/expiry/revocation/replay denied.

### Product metrics
- Time to first simulator run: < 5 min from clone (quickstart).
- Time to first Expo integration: < 30 min (developer preview).
- CLI success rate: > 99% non-error exits on valid input in CI.
- Doc task completion: every command documented with example + acceptance.
- Developer feedback: tracked via issues; triage SLA.

### Enterprise metrics
- Audit export coverage: 100% of allow decisions exported to SIEM.
- Policy evaluation latency: p95 < 50 ms local.
- SIEM compatibility: validated against ≥1 (Splunk/Sentinel).
- Admin controls: 100% of policy fields manageable via API.
- Compliance artifact completeness: every requested permission has privacy + Data Safety entry.

### Release gates (go/no-go)
- **Preview:** Phase 0 done; banned-claims green; suite green; no overclaim.
- **Beta:** Phases 1–6; Expo builds; generated validators; replay + tamper tests; compliance generators (advisory).
- **Production:** Phase 7 + ≥1 framework production-ready; signed plans; scoped approvals; tamper-evident signed traces; app-store artifacts; security review sign-off.
- **Enterprise:** Phase 12; tenant isolation; RBAC/ABAC; SIEM; SBOM/provenance/signing; vuln scanning; enterprise checklist complete.

---

## 25. Final Deliverables

### One-page executive roadmap
ARC Mobile Runtime is a hardened simulator-first governance layer for mobile AI agents. **Now:** make it honest (Phase 0) — fix trace timestamps + hash chain, strict validation, dup-ID checks, rename `privacy_manifest`, mark stub packages private, correct misleading docstrings. **Next (v0.2→v0.5):** single-source JSON schemas + generated TS/Dart/Swift/Kotlin types, runtime validators, replay CLI, fixture-backed simulator, advisory compliance generators, and the first buildable Expo module (mock-native). **Then (v0.8→v1.0):** signed plans, scoped approvals, tamper-evident signed traces, secure local storage, RN + Flutter SDKs, and gated native capabilities in safest-first order. **Enterprise (v1.x):** org policy, tenant isolation, RBAC/ABAC, SIEM, MDM, attestation, SBOM, signing, kill switch. Every native capability requires permission mapping, scoped approval, compliance artifact, device-lab tests, rollback, and review. No production or enterprise claim is made without cited evidence.

### 12-month phased roadmap
- **Month 0–0.5:** Phase 0 (truth + safety). Ship `v0.2.0-preview`.
- **Month 0.5–2:** Phases 1–3 (schemas, validation/policy, trace/replay).
- **Month 2–3:** Phases 4–5 (fixture simulator, compliance generators).
- **Month 3–4:** Phase 6 (Expo preview). Ship `@arc/mobile-runtime-expo@0.5`.
- **Month 4–6:** Phases 7–8 (signed plans, approvals, secure storage). `v0.8` beta.
- **Month 6–9:** Phases 9–10 (RN, Flutter betas).
- **Month 9–11:** Phase 11 (gated native capabilities, safest-first). `v1.0`.
- **Month 11–12+:** Phase 12 (enterprise). Enterprise `v1.x`.

### First 30-day implementation plan
- **Week 1:** PR1 (truth labeling), PR2 (strict validation + dup IDs), MOB-001/002 (timestamp + prev-hash).
- **Week 2:** PR3 (mapping fix), PR4 (hashing + trace chain + `trace verify`), MOB-008 (redaction), MOB-013 (`pin --dry-run`), MOB-014 (CLI tests).
- **Week 3:** PR5 (JSON schemas + wire into loader), MOB-017 (negative fixtures), MOB-015/016 (extras guard, catalog assert).
- **Week 4:** PR6 (TS validators + parity), PR7 (replay CLI), docs sync (MOB-018/019), tag `v0.2.0-preview`.

### First 10 PRs
See Section 10 (PR1–PR10, in order, with branches/scope/tests/acceptance/rollback).

### 100-item backlog
See Section 9 (MOB-001 … MOB-125, grouped Immediate/Short/Mid/Long/Enterprise).

### Target architecture / Security / Privacy / Testing / Enterprise / App-store / Do-not-build
See Sections 6, 14, 15, 16, 19, 21, and below.

### "Do not build" list
1. Hidden/background autonomous agents.
2. Generic OS automation / accessibility-service control of other apps.
3. Always-on microphone or camera.
4. Remote/unauthenticated MCP server or any remote listener on device.
5. Blanket/install-time broad permissions.
6. Undeclared data collection or default cloud sync.
7. Cross-app spying or scraping.
8. Unreviewed App Intents exposing internal agent state.
9. Executing downloaded code on device.
10. Real native sensitive access before signed-plan + scoped-approval + tamper-evident-trace + compliance artifacts exist.

### Go/No-Go matrix

| Stage | Decision | Blocking condition to flip |
|---|---|---|
| Internal demo | **GO** | — |
| Public preview | **NO-GO → GO after Phase 0** | overclaims fixed, banned-claims green |
| Developer beta | **NO-GO** | Phases 1–6 complete, Expo builds |
| Production SDK | **NO-GO** | Phase 7 + ≥1 framework prod + app-store artifacts + security sign-off |
| Enterprise SDK | **NO-GO** | Phase 12 enterprise checklist complete |
| iOS App Store | **NO-GO** | Phases 5+6 + Phase 11 entry gates + legal review |
| Google Play | **NO-GO** | same |
| MCP mobile gateway | **NO-GO (intentional)** | v1 dev-bridge only after threat model + security review |

### Immediate next action
```bash
# On branch arcStudioMobileSDK, start PR1 (truth labeling), then PR2.
uv run --directory python arc mobile doctor --json          # confirm baseline
# Then implement MOB-001 (real timestamp) + MOB-002 (prev_event_hash) in recorder.py,
# and MOB-010 (strict mode) in models.py/manifest.py, with tests, per Section 10.
```

---

*End of roadmap. This document is planning only; it changes no product status. Status labels follow cited evidence per `AGENTS.md` and `scripts/check-banned-claims.sh`.*

---

## Implementation Status — 2026-06-07 (Batch 5 + roadmap completion)

All milestone phases are now **implemented in the simulator-preview posture** (deterministic,
offline, fixtures-only; no real device access). Recorded in `docs/phases.md` (Phases 187–192)
and `docs/roadmap.md` (R-MOBILE-*). Per-task evidence in `docs/mobile/NEXT-10-BACKLOG.md`.

| Phase | Status | Implementation |
|---|---|---|
| 0–5 | Implemented | truth-labeling, schemas + TS validators, validation/policy hardening, prev-hash trace + replay, fixture simulator, compliance generators (PR1–19) |
| 6 — Expo | Implemented (mock-native) | config plugin (advisory permissions), TS API over fixtures-only native bridge + events, example app, recursive forbidden-symbol CI gate |
| 7 — Signed plan + approval | Implemented | HMAC signed-plan envelope + scoped/expiring/revocable approval grants (PR18–19) |
| 8 — Secure storage + egress | Implemented | encrypted-at-rest `SecureLocalStore` (Fernet), deterministic `EgressGuard`, durable hash-only `OfflineQueue` |
| 9 — React Native | Implemented (mock-native) | New-Arch TurboModule Codegen spec + iOS/Android fixture stubs |
| 10 — Flutter | Implemented (mock-native) | federated platform interface + Dart models (`flutter analyze` clean, `flutter test` 5/5) |
| 11 — Native capability gate | Implemented as **entry-gate only** | `CapabilityEntryGate` enforces flag+kill-switch+signed-plan+approval+compliance; **always routes to fixtures, `executed_real_device=False`**. Enabling real device access remains human-gated and out of scope. |
| 12 — Enterprise | Implemented (deterministic slices) | SIEM export (CEF/JSON), signed org/tenant RBAC/ABAC, audit retention/rotation, aggregated compliance report, CycloneDX SBOM, feature flags + remote kill switch |
| 20 — MCP dev-bridge | Implemented (guard) | default-OFF, fail-closed loopback+token+TTL admission guard; opens no network connection/listener |

**Posture unchanged:** ARC Mobile Runtime stays a **Simulator Preview**. No real camera/mic/
contacts/calendar/photos/location/health access exists; the native layers return fixtures and
the entry-gate never routes to a real device in this build.
