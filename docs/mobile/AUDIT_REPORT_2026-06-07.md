# ARC Mobile Runtime SDK — Comprehensive Audit Report

**Date:** 2026-06-07  
**Branch:** arcStudioMobileSDK  
**Auditor role:** Principal mobile platform architect, security auditor, SDK product lead, enterprise readiness reviewer, mobile compliance engineer  
**Method:** Line-by-line source read of all mobile SDK files, CLI, adapters, TS mirror, framework stubs, tests, fixtures, schemas, and docs.

---

## 1. Executive Verdict

**Current maturity level:** Simulator-preview MVP. Well-structured Python governance foundation with zero native mobile execution.

| Question | Answer |
|---|---|
| Production-ready? | **No.** No real native bridge, no distributable package, no signed plans. |
| Enterprise-ready? | **No.** No tenant policy, no RBAC, no audit export, no MDM, no SBOM. |
| Safe to demo? | **Yes**, with accurate "simulator-only" framing. CLI, simulator, and Theia widget all work and are honest. |
| Safe to ship? | **No**, as a native mobile SDK. Safe to ship as a simulator/governance tooling library. |
| Honest in docs/names? | **Mostly yes.** Docs are unusually honest. Two misleading items: `privacy_manifest: true` boolean and "flight recorder" framing in `MOBILE_RUNTIME_SDK.md`. |

**Starting hypothesis verdict:** Confirmed in full. The implementation is exactly as hypothesized — strong Python-side mock-only governance layer, zero native mobile SDK.

---

## 2. Top 10 Blocking Issues

| # | Issue | Severity | File |
|---|---|---|---|
| 1 | `extra="ignore"` on `_Base` silently swallows unknown fields in all models | High | `models.py:11` |
| 2 | Timestamp hard-coded to `2026-01-01T00:00:00Z` — every production trace is wrong | High | `recorder.py:44` |
| 3 | No previous-event hash chain — events hash themselves only, not `prev_hash` | High | `recorder.py` |
| 4 | `mobile_capability_to_sdk_card` silently drops 7 fields: `platforms`, `required_permissions`, `background`, `network`, `reads`, `writes`, `requires_trust` | High | `mobile_sdk_mapping.py:88` |
| 5 | Expo/RN `package.json` has `"main": "src/index.ts"` — not publishable as npm package | High | `expo/.../package.json`, `react-native/.../package.json` |
| 6 | Flutter: `pubspec.yaml` only, zero Dart source files, no `lib/`, no plugin structure | High | `runtimes/mobile/flutter/` |
| 7 | `privacy_manifest: true` is a misleading boolean — no `PrivacyInfo.xcprivacy` is generated | Medium | `models.py`, all manifests |
| 8 | `write_requires_hitl_or_trust` fires as WARNING not ERROR — write capabilities can exist without HITL/trust | Medium | `validation.py:106` |
| 9 | `schema_version` not in `_VOLATILE` despite docstring saying it is excluded from hashing | Medium | `hashing.py:10` |
| 10 | No duplicate capability ID validation in `validate_manifest` or `validate_action_plan` | Medium | `validation.py` |

---

## 3. Reality Matrix

| Area | Claimed capability | Actual implementation | Classification | Risk |
|---|---|---|---|---|
| Python models | Typed models for all SDK surfaces | Full Pydantic v2 models, `extra="ignore"` | Real (with `extra="ignore"` risk) | Medium |
| Python validation | Fail-closed rules, 11 rules | 11 rules implemented, V4 write rule is WARNING | Real MVP | Medium |
| Python simulator | Static plan prediction | Pure static analysis, no execution | Real simulator | Low |
| Python policy | Allow/deny with reasons | Wraps validation + simulation, MCP denied | Real MVP | Low |
| Python trace recorder | Append-only JSONL flight recorder | JSONL works, timestamp fixed, no prev-hash chain | Partial — not tamper-evident | High |
| Python CLI | 9 mobile commands | All implemented, CI-safe | Real | Low |
| Capability catalog | 13 mock capabilities | All `.mock`, no native access | Real mock catalog | Low |
| Runtime pack bridge | Mobile manifest → runtime pack | Works but loses capability detail in metadata | Lossy bridge | Medium |
| SDK mapping | Bidirectional MobileCapability ↔ SDK card | Forward drops 7 fields; documented but lossy | Partial | High |
| TS protocol mirror | Type mirror of Python models | Hand-written interfaces, full field parity | Real (no runtime validation) | Low |
| TS type guards | Runtime type checking | Checks only 2 fields each — trivially fooled | Stub | Medium |
| Expo SDK | Native Expo module | JS-only stub, `main: src/index.ts`, no Swift/Kotlin | Stub only | High |
| React Native SDK | TurboModule/JSI bridge | JS-only stub, same as Expo | Stub only | High |
| Flutter SDK | Dart plugin | `pubspec.yaml` only, zero Dart code | Empty stub | High |
| iOS native bridge | Real camera/mic/contacts/etc | Does not exist | Missing | Critical |
| Android native bridge | Same | Does not exist | Missing | Critical |
| Camera | Real access | No — fixture only | Mock | N/A |
| Microphone | Real access | No — fixture only | Mock | N/A |
| Location | Real access | No — fixture only | Mock | N/A |
| Contacts | Real access | No — fixture only | Mock | N/A |
| Photos | Real access | No — fixture only | Mock | N/A |
| Calendar | Real access | No — fixture only | Mock | N/A |
| Notifications | Real access | No — fixture only | Mock | N/A |
| Background execution | Blocked | Hard-blocked in validation + simulator | Real block | Low |
| Network | Blocked for non-mock | Hard-blocked in validation + simulator | Real block | Low |
| MCP gateway | Production MCP | Denied in policy engine | Intentionally absent | Low |
| Privacy manifest gen | `PrivacyInfo.xcprivacy` | Boolean field only, no file generated | Misleading boolean | High |
| Android manifest gen | Manifest XML | Not implemented | Missing | High |
| Theia inspector | Capability table + doctor | Read-only widget, works | Real MVP UI | Low |
| SwarmGraph signed handoff | Signed plan from SwarmGraph | Not implemented — research only | Roadmap | Medium |
| Enterprise policy | Tenant/org/RBAC | Not implemented | Missing | Critical |
| Device management | MDM/posture | Not implemented | Missing | Critical |
| Audit export | SIEM/export | Not implemented | Missing | Critical |
| CI/release | Package build CI | No build step for Expo/RN/Flutter | Missing | High |

---

## 4. Architecture Map

### Intended architecture (from docs/research)
```
SwarmGraph (verified intent) → signed MobileActionPlan
  → capability policy engine (org/device/user context)
  → approval engine (scoped, time-bound)
  → permission engine (OS mapping + user explanation)
  → native bridge (Expo Module / TurboModule / Flutter plugin)
  → trace recorder (tamper-evident, prev-hash chain)
  → compliance generator (PrivacyInfo.xcprivacy, Android manifest)
  → enterprise controls (RBAC, audit export, MDM)
```

### Actual current architecture
```
MobileActionPlan (JSON)
  → simulate_action_plan() [pure Python, static analysis]
  → MobileActionSimulationReport
  → build_trace() [JSONL with fixed timestamp, no prev-hash]
  → validate_manifest() / explain_plan_policy() [Python rules]
  → CLI commands [Typer, JSON output]
  → Theia widget [read-only table]
```

**The chain stops at: static Python prediction.** Nothing crosses into native mobile execution.

---

## 5. File-by-File Audit

### `mobile/models.py`
- **Does:** Defines all Pydantic v2 data models. Full field coverage.
- **Does not do:** Validate unknown fields (`extra="ignore"` on `_Base`). No `schema_version` migration.
- **Issue:** `extra="ignore"` means a malicious or drifted manifest silently discards unknown fields rather than rejecting them. Only `MobilePolicyDecision` uses `extra="forbid"`.
- **Production readiness:** MVP. Change `_Base` to `extra="forbid"` or `extra="allow"` with explicit handling before production.
- **Recommendation:** Add `model_config = ConfigDict(extra="forbid")` to `_Base` for strict mode. Offer a `strict=False` loader path for migration.

### `mobile/capabilities.py`
- **Does:** Defines 13 mock capabilities, seals each with SHA-256 hash.
- **Does not do:** Validate against JSON Schema at load time. No duplicate ID check.
- **All 13 capabilities confirmed:** `background=False`, `network=False`, all IDs end in `.mock`. Safe.
- **Issue:** No runtime check that catalog has no duplicate IDs. If `_seal()` is called twice with drift, old hash remains unchecked.
- **Recommendation:** Add `assert len({c.id for c in MOCK_CAPABILITIES}) == len(MOCK_CAPABILITIES)` at module load.

### `mobile/manifest.py`
- **Does:** Loads `arc-mobile-capabilities.json` via `json.loads` + `model_validate`. Builds default manifest.
- **Does not do:** Run JSON Schema validation (schema files exist but are never invoked from Python). No duplicate ID check.
- **Issue:** Schema files in `runtimes/mobile/spec/` and `docs/schemas/` are never called from `load_manifest()`. They are documentation artifacts only.
- **Recommendation:** Add optional jsonschema validation pass in `load_manifest()`, or at minimum in `validate_manifest()`.

### `mobile/validation.py`
- **Does:** 11 rules (V1-V11), structured `ValidationFinding` with severity/remediation. Good fail-closed stance.
- **Issue 1:** V4 `write_requires_hitl_or_trust` is severity `"warning"` — write capabilities without HITL/trust pass validation with `ok=True`. This is a governance gap.
- **Issue 2:** No duplicate capability ID check in `validate_manifest`.
- **Issue 3:** No cross-check between `manifest.platforms` list and per-capability `platforms`.
- **Issue 4:** Permission IDs (e.g., `ios.camera`, `android.CAMERA`) are not validated against any known registry.
- **Recommendation:** Promote V4 to `"error"`. Add duplicate ID check. Add platform cross-check.

### `mobile/simulator.py`
- **Does:** Pure static prediction. Correctly blocks background, non-mock-network, sensitive non-mock, and unknown capabilities. Computes risk score.
- **Does not do:** Validate input/output payload shapes. Does not consume `plan_hash`. Does not model OS permission state or user approval state.
- **Issue:** `extra_capabilities` path allows injecting non-mock sensitive capabilities that bypass the catalog safety net if the ID doesn't start with a `_SENSITIVE_PREFIXES` prefix. Example: `app.sensitive_custom` would pass through unblocked.
- **Recommendation:** Add a check that all `extra_capabilities` with `data_sensitivity >= HIGH` must end in `.mock`.

### `mobile/hashing.py`
- **Does:** Deterministic SHA-256, sorted-key JSON, `_VOLATILE` exclusion.
- **Issue 1:** `schema_version` is NOT in `_VOLATILE` (`_VOLATILE = frozenset({"capability_hash", "manifest_hash", "plan_hash", "report_hash"}`). The docstring says "Excludes volatile fields (*_hash, schema_version)" — this is wrong. `schema_version` IS included in hashes.
- **Issue 2:** No domain separation between `capability_hash`, `manifest_hash`, `plan_hash`, `report_hash`. A capability hash value could theoretically be used as a manifest hash.
- **Issue 3:** No hash algorithm label in output (could be confused with other SHA-256 hashes).
- **Recommendation:** Either add `"schema_version"` to `_VOLATILE` (and update all pinned hashes) or fix the docstring. Add domain prefix: `"cap:" + sha256(...)`.

### `mobile/recorder.py`
- **Does:** Appends JSONL events, computes `event_hash` and `trace_hash`.
- **Critical issue 1:** Timestamp is hard-coded: `datetime(2026, 1, 1, tzinfo=timezone.utc)`. Every event in production would have this timestamp, making traces forensically useless.
- **Critical issue 2:** No previous-event hash chain. `event_hash` hashes the event itself; there is no `prev_event_hash` field. Deleting or reordering events is undetectable.
- **Issue 3:** `trace_hash` is `_hash([event.event_hash for event in events])` — this is a hash of a list of hashes. Order-sensitive, but deletion of the trace file itself is not detectable.
- **Recommendation:** Replace fixed timestamp with `datetime.now(timezone.utc).isoformat()`. Add `prev_event_hash: str` field to `MobileRuntimeEvent`. Add `--deterministic-timestamp` flag for CI use.

### `mobile/redaction.py`
- **Does:** Key-based and value-based redaction, recursive dicts.
- **Issue:** `redact_list` only recurses into `dict` items. Non-dict list items (strings, numbers) are passed through unredacted. A manifest with `metadata: {"api_keys": ["sk-abc123"]}` would leak `"sk-abc123"`.
- **Recommendation:** In `redact_list`, apply `Redactor.is_safe()` to string items too.

### `mobile/policy.py`
- **Does:** Wraps validation + simulation. MCP exposure denied. Clean `MobilePolicyDecision` model with `extra="forbid"`.
- **Does not do:** No policy versioning. No org/tenant/device context. No approval scope/expiry. Policy decisions are not logged.
- **Issue:** `explain_plan_policy` returns `allowed=True` for plans where some steps are blocked but `validation.ok=True` and `simulation.overall_allowed=True`. The combination logic is correct, but there is no policy version pin in the output, so two identical decisions at different times cannot be distinguished.
- **Recommendation:** Add `policy_version: str` field to `MobilePolicyDecision`. Add logging of decisions to a local audit file.

### `mobile/runtime_pack.py`
- **Does:** Converts `MobileRuntimeManifest` to `RuntimePackManifest`. Writes `arc-runtime-pack.json`.
- **Issue:** Capability detail is reduced to a flat list of ID strings in `metadata["mobile_capabilities"]`. Per-capability `data_sensitivity`, `approval_mode`, `permissions`, `background`, `network`, `reads`, `writes` are all lost. The runtime pack consumer has no governance information.
- **Recommendation:** Write a `capabilities_detail` key containing the full capability card list (or reference the mobile manifest file).

### `mobile_sdk_mapping.py`
- **Does:** Bidirectional `MobileCapability ↔ SDK CapabilityCard`. SDK-only fields preserved in `metadata`.
- **Forward direction drops:** `platforms`, `required_permissions`, `background`, `network`, `reads`, `writes`, `requires_trust` — 7 fields. These fields have no equivalent in the SDK card schema.
- **Comment in code says "no lossy silent discards"** — this is contradicted by the 7 dropped fields. The comment refers to SDK→Mobile direction only; the forward direction is explicitly lossy.
- **Recommendation:** Fix the module docstring to accurately say the forward direction is lossy. Consider adding a `_dropped_fields` key in the SDK card's metadata for traceability.

### `cli/mobile.py`
- **Does:** 9 Typer commands, JSON output, structured error envelopes, proper exit codes.
- **UX issue 1:** `simulate` accepts both a positional `plan_file` and `--plan` option. Both are `None`-checked after the fact, but `--help` shows both. Confusing.
- **Issue 2:** `pin` mutates the manifest file in-place with no `--dry-run` flag and no confirmation prompt.
- **Issue 3:** `export-runtime-pack` calls `runtime_packs.loader.load_manifest` / `inspect_manifest`, not the mobile module. This is correct behavior but the command name implies mobile-specific export.
- **Issue 4:** No CLI tests. Zero test coverage for all 9 commands.
- **Recommendation:** Add `--dry-run` to `pin`. Standardize plan arg to `--plan` only. Add at minimum 1 happy-path + 1 error-path CLI test per command via `typer.testing.CliRunner`.

### `adapters/arc_runtime_sdk.py`
- **Honest:** `can_run=False` always. Detection confidence gated on `arc-sdk.json` presence.
- **Issue:** `gate_policy` in `arc-sdk.json` is parsed for count but never honored in any policy decision.
- **Recommendation:** Document that `gate_policy` is deferred, or surface it in the `CapabilityReport`.

### TypeScript: `mobile-runtime.ts`, `mobile-capability.ts`, `mobile-events.ts`, `mobile-action-plan.ts`
- **Good:** Full field parity with Python models. All interface fields present.
- **Issue 1:** Type guards check only 2 fields each (`isMobileCapability` checks `"id" in obj && "simulator_supported" in obj`). Any object with those two keys passes.
- **Issue 2:** No Zod validators, no io-ts, no generated types from schema. Runtime validation is entirely absent.
- **Issue 3:** `mobile-events.ts` defines `event_type` as the literal `'mobile.step.simulated'` only — correct for MVP but will need union type expansion.
- **Recommendation:** Add a `validateMobileCapability(obj): MobileCapability` function using Zod or manual field-by-field checking. Or generate types from JSON Schema.

### `arc-mobile-widget.tsx`
- **Good:** Read-only, explicit loading/error/empty/success states, ARIA labels, uses CSS variables for theming.
- **Shows "simulator/mock only" inline.** Honest.

### Expo `arc-mobile-runtime` package
- **`package.json`:** `"main": "src/index.ts"` — TypeScript source as `main` entry. Not publishable without a build step. No `dist/`, no `tsconfig.json`, no build script, no `exports` map.
- **`src/index.ts`:** 25 lines. Exports `simulateAction()` which always returns `{ simulated: true, mock: true }`. No Expo Modules API, no Swift, no Kotlin, no config plugin, no permission mapping.
- **Verdict:** JavaScript stub. Not usable in a real Expo app beyond importing the type.

### Expo `arc-mobile-expo` package
- **`package.json`:** `private: true`, `"main": "src/index.ts"`.
- **`src/index.ts`:** 1 line re-export from `arc-mobile-runtime/src`.
- **Verdict:** Re-export shim with no own code.

### React Native `arc-mobile-runtime` package
- **Same pattern as Expo.** No TurboModule, no JSI, no Codegen, no Podspec, no `build.gradle`.
- **Verdict:** JS stub identical to Expo stub.

### Flutter `arc_mobile_runtime` package
- **`pubspec.yaml`:** Valid YAML, correct SDK constraints `>=3.0.0 <4.0.0`, Flutter `>=3.10.0`.
- **No `lib/` directory.** No Dart files. No `android/`, no `ios/` platform directories. No example app.
- **Verdict:** Empty package shell. Cannot be imported in any Flutter app.

---

## 6. Capability and Permission Audit

| ID | Platforms | Sensitivity | Approval | HITL | Trust | Permissions | Real/Mock | App-store risk |
|---|---|---|---|---|---|---|---|---|
| device.camera.capture.mock | ios, android, flutter, expo | high | required | no | yes | ios.camera, android.CAMERA | Mock | None (mock only) |
| device.microphone.transcribe.mock | ios, android | critical | blocking | yes | yes | ios.microphone, android.RECORD_AUDIO | Mock | None |
| device.location.current.mock | ios, android | high | required | no | yes | ios.location.whenInUse, android.ACCESS_FINE_LOCATION | Mock | None |
| device.calendar.read.mock | ios, android | high | required | no | yes | ios.calendars, android.READ_CALENDAR | Mock | None |
| device.calendar.write.mock | ios, android | high | blocking | yes | yes | ios.calendars, android.WRITE_CALENDAR | Mock | None |
| device.contacts.search.mock | ios, android | critical | blocking | yes | yes | ios.contacts, android.READ_CONTACTS | Mock | None |
| device.files.pick.mock | all | medium | recommended | no | no | none | Mock | None |
| device.photos.pick.mock | ios, android | high | required | no | yes | ios.photoLibrary, android.READ_MEDIA_IMAGES | Mock | None |
| device.notifications.schedule.mock | ios, android | low | recommended | no | no | none | Mock | None |
| app.memory.write.mock | all | low | none | no | no | none | Mock | None |
| app.memory.retrieve.mock | all | low | none | no | no | none | Mock | None |
| app.local_search.query.mock | all | low | none | no | no | none | Mock | None |
| app.ui.action_plan.mock | all | none | recommended | no | no | none | Mock | None |

**Confirmed:** No capability touches real camera, microphone, location, contacts, photos, calendar, files, notifications, app storage, network, background execution, or OS permissions. Catalog is entirely mock-safe.

**Gaps:**
- `device.files.pick.mock` has no `required_permissions` despite being a storage capability. Correct for mock but would need permissions for real implementation.
- `device.notifications.schedule.mock` similarly has no permissions. Real iOS requires `UNUserNotificationCenter.requestAuthorization`.
- No `app.memory.write.mock` HITL requirement despite `writes=True` — fires V4 warning. Low risk at `data_sensitivity: low` but inconsistent with stated policy.

---

## 7. Security Audit

| Surface | Status | Risk | Recommendation |
|---|---|---|---|
| Fail-closed for unknown capabilities | Yes — simulator blocks unknown IDs | Low | Good |
| Fail-closed for sensitive non-mock | Yes — V5 blocks non-.mock sensitive | Low | Good |
| Background execution | Hard-blocked at validation + simulator | Low | Good |
| Network (non-mock) | Hard-blocked at validation + simulator | Low | Good |
| MCP exposure | Always denied in `explain_capability_policy` | Low | Good |
| `extra="ignore"` | Silent field discard | High | Change to `extra="forbid"` |
| Metadata can carry arbitrary values | Yes — `metadata: dict[str, Any]` unrestricted | Medium | Add metadata schema |
| Secret redaction in manifest | Implemented via `Redactor` | Medium | Fix list item redaction gap |
| Trace tamper detection | Hash per-event but no prev-hash chain | High | Add `prev_event_hash` |
| `extra_capabilities` bypass | Non-catalog caps with non-sensitive prefix bypass blocks | Medium | Add sensitivity check for extras |
| Hash domain separation | None | Low | Add domain prefix |
| `pin` command mutates in-place | No dry-run | Low | Add `--dry-run` |
| Package supply chain | No SBOM, no signing | High | Add for production |
| Framework packages not publishable | `main: src/index.ts` | High | Add build step before any publish |

---

## 8. Privacy and Compliance Audit

| Claim/field | Actual status | Risk |
|---|---|---|
| `privacy_manifest: true` | Boolean field only. No `PrivacyInfo.xcprivacy` file generated. | High — misleading |
| iOS permission usage strings | Declared in `required_permissions` as IDs only. No `NSCameraUsageDescription` strings generated. | Medium |
| Android Data Safety | Not generated. No `uses-permission` XML. | Medium |
| App Review notes | Not generated. Research doc describes planned generator. | Low (honest) |
| GDPR/data minimization | No data retention policy, no export/deletion. | Low (mock only, no real data) |
| Consent state | Not modeled in capability or plan. | Medium (future gap) |

**Rename required:** `privacy_manifest` field should be renamed to `privacy_manifest_declared: bool` with a clear docstring: "Developer declares intent to generate privacy manifest; no file is generated by this field."

---

## 9. Product and DX Audit

- **Onboarding:** `arc mobile doctor --json` works. `arc mobile capabilities --json` works. Quick-start is correct.
- **Package naming:** `arc-mobile-runtime` used in both Expo and RN paths — potential npm collision if both are published. Should be `@arc/mobile-runtime-expo` and `@arc/mobile-runtime-rn`.
- **Package buildability:** Neither Expo nor RN package has a `tsconfig.json` or build script. `npm publish` would publish TypeScript source, not compiled JS. Will not work with most bundlers.
- **CLI UX:** `simulate` has positional + `--plan` ambiguity. Error messages use `ArcErrorCode` envelopes — consistent with rest of CLI.
- **Examples:** Demo README in `runtimes/mobile/expo/examples/arc-mobile-demo/` is a single sentence placeholder.
- **Versioning:** All packages at `0.1.0` or `0.1.0-alpha`. No semver enforcement. No changelog.

---

## 10. Enterprise Readiness Audit

| Control | Status |
|---|---|
| Tenant isolation | Not implemented |
| Org policy | Not implemented |
| RBAC / ABAC | Not implemented |
| MDM / device posture | Not implemented |
| App attestation | Not implemented |
| Audit log export | Not implemented — JSONL traces are local only |
| SIEM integration | Not implemented |
| Data retention policy | Not implemented |
| Encryption at rest | Not implemented (traces are plaintext JSONL) |
| Keychain / Keystore | Not implemented |
| Remote kill switch | Not implemented |
| SBOM | Not implemented |
| SLSA / provenance | Not implemented |
| Code signing | Not implemented |
| Vulnerability scanning | Not implemented in mobile CI |
| Feature flags | Not implemented |
| Version pinning (SDK → policy) | Not implemented — no `policy_version` in decisions |
| Compliance reports | Not implemented |
| Admin controls | Not implemented |

**Verdict:** Zero enterprise controls implemented. Every row is "Not implemented." This is expected and honest for a simulator preview, but means the "enterprise-ready" label is a hard no-go.

---

## 11. Critical Contradictions

### C1: "No lossy silent discards" vs. 7 dropped fields
- **Claim:** `mobile_sdk_mapping.py` docstring line 17: "No field is silently dropped: SDK-only fields land in `metadata`"
- **Reality:** The sentence refers to the *inverse* (SDK→Mobile) direction. The *forward* (Mobile→SDK) direction explicitly drops `platforms`, `required_permissions`, `background`, `network`, `reads`, `writes`, `requires_trust`.
- **Risk:** Consumers of the SDK card have no visibility into whether a capability requires background, network, or real permissions.
- **Fix:** Change docstring to: "Forward direction (Mobile→SDK) is lossy by design — see dropped fields list. Inverse direction preserves all SDK-only fields in metadata."

### C2: `privacy_manifest: true` implies a generated artifact
- **Claim:** Field name `privacy_manifest` + `True` value suggests the manifest has been submitted or generated.
- **Reality:** It is a boolean intent flag. No `PrivacyInfo.xcprivacy` file is generated anywhere.
- **Risk:** A developer shipping a real iOS app based on this manifest could assume privacy declarations are handled.
- **Fix:** Rename to `privacy_manifest_intent: bool` or add a validator that emits a warning: "privacy_manifest=True requires manual generation of PrivacyInfo.xcprivacy."

### C3: "Flight recorder" framing with no tamper-evident chain
- **Claim:** `docs/MOBILE_RUNTIME_SDK.md` says "records hash-linked traces."
- **Reality:** Traces hash each event independently. There is no `prev_event_hash` link. Deleting, reordering, or inserting events is undetectable by the verifier.
- **Fix:** Add `prev_event_hash` to `MobileRuntimeEvent`. The first event uses `"0" * 64` as sentinel.

### C4: `schema_version` exclusion claim in `hashing.py` docstring
- **Claim:** Docstring says "Excludes volatile fields (*_hash, schema_version)."
- **Reality:** `_VOLATILE = frozenset({"capability_hash", "manifest_hash", "plan_hash", "report_hash"})` — `schema_version` is NOT excluded.
- **Risk:** If schema version changes, all existing hashes break, which is a migration hazard.
- **Fix:** Either add `"schema_version"` to `_VOLATILE` (and document this policy) or remove it from the docstring.

### C5: Package names imply published SDKs
- **Claim:** Package names `arc-mobile-runtime`, `@arc/mobile-expo`, `arc_mobile_runtime` imply installable, usable SDK packages.
- **Reality:** All three are stubs. The Expo/RN packages have `"main": "src/index.ts"` — not distributable. The Flutter package has no Dart source.
- **Fix:** Add `"private": true` to Expo's `arc-mobile-runtime/package.json` (currently missing). Add `status: "stub"` to all `package.json` descriptions.

---

## 12. Production Readiness Gap List

### P0 — Honesty and Safety (do immediately)

| # | Work item | Why | Files | Acceptance criteria |
|---|---|---|---|---|
| P0-1 | Fix `hashing.py` docstring re `schema_version` | Misleading docs | `hashing.py:5` | Docstring matches `_VOLATILE` exactly |
| P0-2 | Rename `privacy_manifest` → `privacy_manifest_intent` or add validator warning | Misleading field | `models.py`, all manifests, fixtures | No field named `privacy_manifest` that implies generated artifact |
| P0-3 | Add `"private": true` to Expo `arc-mobile-runtime/package.json` | Prevent accidental publish | `expo/.../package.json` | `npm publish` is blocked |
| P0-4 | Fix `recorder.py` timestamp to use `datetime.now(timezone.utc)` with `--deterministic` CI flag | Every production trace wrong | `recorder.py:44` | Traces have real timestamps in prod; deterministic mode available for tests |
| P0-5 | Fix `mobile_sdk_mapping.py` docstring re lossy forward direction | Misleading claim | `mobile_sdk_mapping.py:17` | Docstring accurately describes both directions |
| P0-6 | Add duplicate capability ID check in `validate_manifest` | Silent governance gap | `validation.py` | Test: duplicate IDs → validation error |
| P0-7 | Promote V4 `write_requires_hitl_or_trust` to `"error"` | Write without oversight | `validation.py:106` | Test: write cap without HITL/trust → `ok=False` |
| P0-8 | Fix `redact_list` to redact string items | Potential secret leak | `redaction.py:47` | Test: list of strings with secret-like values → redacted |

### P1 — Protocol and Schema

| # | Work item | Why | Files |
|---|---|---|---|
| P1-1 | Run JSON Schema validation in `load_manifest()` | Schema files are unused | `manifest.py`, `runtimes/mobile/spec/` |
| P1-2 | Add `prev_event_hash` to `MobileRuntimeEvent` for tamper-evident chain | Chain integrity | `recorder.py`, `models.py` if moved |
| P1-3 | Add `policy_version` field to `MobilePolicyDecision` | Auditable decisions | `policy.py` |
| P1-4 | Add Zod validators for TS interfaces or generate from JSON Schema | TS has no runtime validation | `packages/arc-protocol-ts/` |
| P1-5 | Add `@arc/mobile-runtime-expo` / `@arc/mobile-runtime-rn` scoped names | Prevent npm collision | `package.json` files |
| P1-6 | Add `tsconfig.json` and build scripts to Expo/RN packages | Not publishable without build | Framework package dirs |

### P2 — Simulator and Trace

| # | Work item | Why | Files |
|---|---|---|---|
| P2-1 | Add CLI tests via `CliRunner` for all 9 commands | Zero CLI test coverage | `tests/` |
| P2-2 | Add `--dry-run` to `pin` command | Mutates in place | `cli/mobile.py` |
| P2-3 | Add golden trace fixtures for replay comparison | No replay test | `runtimes/mobile/fixtures/traces/` |
| P2-4 | Add test: recorder timestamp changes between calls in prod mode | Hard-coded timestamp | `tests/mobile/test_mobile.py` |
| P2-5 | Add test: trace with deleted event fails verification | Chain integrity | `tests/mobile/test_mobile.py` |
| P2-6 | Add fuzz test: malicious metadata in capability | Security | `tests/mobile/` |
| P2-7 | Add test: duplicate capability IDs rejected | Governance | `tests/mobile/` |

### P3 — Expo First Real SDK

| # | Work item | Why | Files |
|---|---|---|---|
| P3-1 | Add `tsconfig.json` + build to `arc-mobile-runtime` Expo package | Not buildable | `runtimes/mobile/expo/packages/arc-mobile-runtime/` |
| P3-2 | Add Expo Module API skeleton (Swift + Kotlin) | Zero native code | Same dir |
| P3-3 | Add Expo config plugin for permission/privacy mapping | App-store requirement | Same dir |
| P3-4 | Add `PrivacyInfo.xcprivacy` generator CLI command | Privacy manifest gap | `cli/mobile.py` |
| P3-5 | Add Android `uses-permission` manifest generator | Privacy manifest gap | `cli/mobile.py` |
| P3-6 | Add example Expo app | No demo | `runtimes/mobile/expo/examples/` |

### P4 — React Native and Flutter

| # | Work item | Why | Files |
|---|---|---|---|
| P4-1 | Add TurboModule interface + Codegen spec for RN | Zero native code | `runtimes/mobile/react-native/` |
| P4-2 | Add Podspec + `build.gradle` for RN package | Not installable | Same dir |
| P4-3 | Add `lib/arc_mobile_runtime.dart` with API surface | Flutter has zero Dart | `runtimes/mobile/flutter/packages/arc_mobile_runtime/lib/` |
| P4-4 | Add Flutter platform interface + method channel | Flutter is empty stub | Same dir |

### P5 — Enterprise Platform

| # | Work item | Why | Files |
|---|---|---|---|
| P5-1 | Add org/tenant policy context to `MobilePolicyDecision` | Enterprise blocker | `policy.py` |
| P5-2 | Add signed plan envelope (from SwarmGraph) | Trust boundary | `models.py` |
| P5-3 | Add approval scopes with expiry | HITL gap | `models.py`, `policy.py` |
| P5-4 | Add audit export (JSONL → SIEM format) | Enterprise blocker | New module |
| P5-5 | Add SBOM generation for mobile packages | Supply chain | CI pipeline |

---

## 13. Next Engineering Tasks (5 / 10 / 25 / 50)

### Next 5
1. Fix `recorder.py` timestamp (real clock + deterministic CI flag)
2. Add `prev_event_hash` chain to `MobileRuntimeEvent`
3. Promote V4 write rule to error; add duplicate ID check to `validate_manifest`
4. Fix `hashing.py` docstring; add `schema_version` to `_VOLATILE` or document why not
5. Add 9 CLI command smoke tests via `typer.testing.CliRunner`

### Next 10 (after 5 above)
6. Fix `redact_list` to handle string items
7. Add JSON Schema validation in `load_manifest()`
8. Add `policy_version` to `MobilePolicyDecision`
9. Mark Expo/RN packages `private: true`; rename to scoped names
10. Add `tsconfig.json` + build step to Expo package

### Next 25 (after 10 above)
11. Add Zod validators for TS interfaces
12. Add `PrivacyInfo.xcprivacy` CLI generator
13. Add Android `uses-permission` manifest generator
14. Add golden trace replay test
15. Add fuzz tests for malicious capability metadata
16. Add approval scope + expiry fields to `MobileCapability` and `MobilePolicyDecision`
17. Add Expo Module API skeleton (Swift + Kotlin stubs)
18. Add Expo config plugin
19. Add `lib/arc_mobile_runtime.dart` API surface to Flutter package
20. Fix SDK mapping docstring; add `_dropped_fields` metadata key
21. Rename `privacy_manifest` field to `privacy_manifest_intent`
22. Add `--dry-run` to `pin` command
23. Add example Expo demo app
24. Add Flutter platform interface (method channel)
25. Generate all capability types from JSON Schema (single source of truth)

### Next 50 (after 25 above)
26-30. RN TurboModule interface + Codegen + Podspec + `build.gradle` + RN tests  
31-35. Signed plan envelope (SwarmGraph → Mobile), plan signature verification, signature test, key management plan, CLI `handoff verify` command  
36-40. Tenant/org policy layer, RBAC capability gates, device posture hook, MDM integration stub, policy version pinning  
41-45. Audit export (JSONL → SIEM), audit retention policy, encrypted local traces, trace CLI verifier with prev-hash check, mutation/reorder detection tests  
46-50. SBOM generation, supply chain signing, vulnerability scanning CI gate, compliance report generator, enterprise admin kill-switch flag

---

## 14. v1.0 Target Architecture

```
┌─────────────────────────────────────────────┐
│           SwarmGraph / LLM Agent            │
│   Produces signed MobileActionPlan          │
│   (plan_hash, org_id, user_id, issued_at)   │
└──────────────┬──────────────────────────────┘
               │  Signed plan envelope
               ▼
┌─────────────────────────────────────────────┐
│           Policy Engine v2                  │
│   org_policy + device_posture + user_role   │
│   approval_scope + expiry                   │
│   MCP exposure gate                         │
│   policy_version pin                        │
└──────────────┬──────────────────────────────┘
               │  Approved steps only
               ▼
┌─────────────────────────────────────────────┐
│         Permission Engine                   │
│   OS permission → user explanation          │
│   Biometric re-auth for BLOCKING caps       │
│   Scoped grants with expiry                 │
└──────────────┬──────────────────────────────┘
               │  Granted permissions
               ▼
┌─────────────────────────────────────────────┐
│         Native Bridge Abstraction           │
│   ┌──────────┐ ┌───────────┐ ┌──────────┐ │
│   │Expo Mod. │ │TurboModule│ │Flutter   │ │
│   │Swift/KT  │ │JSI/Codegen│ │Plugin    │ │
│   └──────────┘ └───────────┘ └──────────┘ │
└──────────────┬──────────────────────────────┘
               │  Execution result
               ▼
┌─────────────────────────────────────────────┐
│         Trace Recorder v2                   │
│   prev_event_hash chain                     │
│   real timestamps                           │
│   payload hashing + redaction               │
│   signed trace root                         │
└──────────────┬──────────────────────────────┘
               │  Evidence
               ▼
┌─────────────────────────────────────────────┐
│   Compliance Generator + Enterprise Admin   │
│   PrivacyInfo.xcprivacy + Android manifest  │
│   SIEM export + audit retention             │
│   Admin kill-switch + SBOM                  │
└─────────────────────────────────────────────┘
```

---

## 15. "Do Not Build" List

1. Hidden background agents that run without user knowledge
2. Always-on microphone or camera without explicit per-session approval
3. Cross-app spying via accessibility APIs
4. Remote unauthenticated MCP server on mobile
5. Blanket permissions ("request all at install")
6. Undeclared data collection or cloud sync by default
7. Real native access before signed policy/approval/trace chain exists
8. Generic OS automation (Accessibility service / UIAutomation abuse)
9. Downloading and executing remote code on device
10. Unreviewed App Intents that expose internal agent state to Siri/Shortcuts

---

## 16. Final Recommendations

**Market positioning:** ARC Mobile Runtime is today a well-engineered, honest simulator-preview governance layer for mobile AI agents. It provides the only capability-card-driven, policy-gated, hash-pinned, fail-closed foundation in the open agent tooling space. It is not a native mobile SDK yet, but the Python foundation is strong enough to build one on.

**Recommended rename:** "ARC Mobile Runtime" → **"ARC Mobile Runtime Simulator Preview"** in all package descriptions and README titles until at least one real Expo Module with native Swift/Kotlin code ships.

**Safest next milestone:** Fix the 8 P0 honesty/safety items (trace timestamp, prev-hash chain, write rule severity, duplicate ID check, docstring corrections). These are all single-file changes with no breaking API surface.

**Best first real SDK target:** Expo Module (dev-client adapter). Best DX, best config plugin support, fastest path to PrivacyInfo.xcprivacy generation.

**First 5 PRs:**
1. `fix(mobile): real timestamp in recorder + deterministic CI flag + prev_event_hash chain`
2. `fix(mobile): promote V4 write rule to error + add duplicate ID check in validate_manifest`
3. `fix(mobile): correct hashing.py docstring; fix redact_list string items`
4. `fix(mobile): rename privacy_manifest to privacy_manifest_intent; fix SDK mapping docstring`
5. `test(mobile): add CLI command tests for all 9 commands via CliRunner`

**First 10 tests to add:**
1. `test_recorder_timestamp_is_real_clock_in_prod_mode`
2. `test_trace_reorder_detection` (with prev_event_hash)
3. `test_write_capability_without_hitl_is_error`
4. `test_duplicate_capability_ids_rejected`
5. `test_cli_doctor_json_output`
6. `test_cli_simulate_plan_allowed`
7. `test_cli_simulate_plan_blocked_exits_1`
8. `test_cli_validate_manifest_ok`
9. `test_cli_policy_explain_capability`
10. `test_redact_list_redacts_secret_strings`

**First 10 doc changes:**
1. Fix `hashing.py` docstring re `schema_version`
2. Fix `mobile_sdk_mapping.py` docstring re lossy forward direction
3. Add `privacy_manifest_intent` docstring: "Boolean intent only; no file is generated"
4. Add "Previous-hash chain not yet implemented" warning to `recorder.py`
5. Add "Not publishable without build step" to Expo/RN package READMEs
6. Add "Zero Dart source; stub only" to Flutter package README
7. Update `MOBILE_RUNTIME_SDK.md` to say "hash-linked traces (single-event hashes; prev-hash chain not yet implemented)"
8. Add "CLI tests: not yet implemented" to `PRODUCTION_READINESS.md`
9. Add "gate_policy ignored" note to `arc_runtime_sdk_pack.py` docstring
10. Add "schema_version included in hashes" to `hashing.py` `_VOLATILE` comment

**Go/no-go decision:**
- **Demo:** ✅ Go — simulator is safe, honest, functional.
- **Beta (simulator library):** ✅ Go after P0 fixes — honest, tested, no native access.
- **Production (native mobile SDK):** ❌ No-go — zero native code, no signed plans, no compliance artifacts.
- **Enterprise:** ❌ Hard no-go — zero enterprise controls.
