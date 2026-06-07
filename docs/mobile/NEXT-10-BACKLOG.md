# ARC Mobile SDK — Next 10 (Batch 5) Execution Prompt

You are continuing ARC Mobile Runtime SDK development **in this session, on `main`**.
Execute the 10 tasks below in order. They continue the granular, one-commit-per-task
cadence of PR1–19 (MOB-001…092) and pick up exactly where PR19 (approval engine) left off.

## Where we are (do not redo)
Delivered on `main` (`docs/mobile/ROADMAP_TO_PRODUCTION.md` phases): **Phase 0** truth-labeling,
**Phase 1** schemas + TS validators, **Phase 2** validation/policy hardening + versioning +
`EnterprisePolicyHook`, **Phase 3** prev-hash trace chain + `trace verify` + `replay`,
**Phase 4** fixture-backed simulator (`fixtures_registry`, `mock_store`), **Phase 5** compliance
generators (ios-privacy / android-manifest / data-safety / review-notes), **Phase 7** signed plan
envelope + approval engine (issue/revoke). **Started:** Phase 6 (Expo scaffold — Swift/Kotlin mock
stubs + config.json + forbidden-native CI grep) and Phase 8 (privacy-budget ledger).

Modules: `mobile/{capabilities,manifest,models,hashing,fixtures_registry,mock_store,approval,policy,privacy_budget,recorder,redaction,replay,runtime_pack,schema_validator,signing,simulator,validation}.py`.
CLI (22 cmds incl. `mobile trace <path>` leaf + `mobile trace-verify`). TS: `@arc-studio/protocol` `mobile-*.ts`.

## Operating rules (read `docs/handover/SINGLE-BRANCH-WORKFLOW.md`)
- **One trunk: `main`.** No PRs, no `mob/pr*` or per-task branches. `git pull --ff-only` → work → commit → `git pull --rebase` → push.
- **One commit per task.** Conventional message `type(mobile): summary (T<n> / MOB-xxx)`. Stage explicit files only; never `git add -A` (arena/vendor noise).
- **Gates before every push:** `cd python && uv run ruff check src tests && uv run pytest tests/ -q` · `pnpm --filter @arc-studio/protocol test` (coverage-gated) · `pnpm typecheck`. New `.ts` modules MUST ship tests in the same commit or the protocol coverage gate fails.
- **Record each task** in `docs/phases.md` + `docs/roadmap.md` (CI-protected, update in place); run `bash scripts/check-banned-claims.sh`.
- **Discipline:** research-first → verify against real code before editing → smallest safe additive change → tests green → commit → push. Findings are often wrong; confirm before implementing.

## Non-negotiable safety constraints (every task must hold)
Simulator/mock-only posture. No real camera/mic/contacts/calendar/photos/location/health. No background
agents, no on-device network listener, no executing downloaded code. **Native code returns fixtures only**
and CI greps native dirs for sensitive symbols (`AVCapture`, `CLLocation`, `CNContact`, `EKEvent`, `PHPhoto`,
`CMMotion`, Android `Camera`/`LocationManager`/`ContactsContract`) and fails if present. Security decisions
stay deterministic (no LLM allow/deny). Secrets redacted; traces are hash-only. Do not relabel anything as a
"production SDK" or claim native access — it stays **"ARC Mobile Runtime — Simulator Preview"**.

## Mobile gotchas
- `runtimes/` is **gitignored** → new files there need `git add -f` (verify from a clean clone, not just locally).
- Types: `MobileRuntimeEvent`/`MobilePolicyDecision` live in `mobile-events.ts`; manifest/capability/action-plan in `mobile-runtime.ts`.
- Reuse existing modules: `signing.py` (HMAC envelope) for any new signature need; `privacy_budget.py` for egress accounting; `redaction.py` for any payload surface.

---

## The 10 tasks

### Phase 6 — make the Expo module buildable (mock-native)

**T1 / Expo config plugin (advisory permission injection).** Generate iOS usage strings + Android
manifest permissions from a `MobileRuntimeManifest`, marked advisory/human-review; no auto-submit.
Files: `runtimes/mobile/expo/packages/arc-mobile-runtime/plugin/`. Tests: config-plugin snapshot from
the safe-demo manifest; permission-change diff. Acceptance: plugin output valid + advisory-labeled.

**T2 / Expo TS API + mock-native bridge contract.** Typed JS API (`getCapabilities()`, `simulate(plan)`,
event emitter) over a native module interface whose Swift/Kotlin impls **return fixtures only**. Files:
`.../src/*.ts`, native bridge signatures. Tests: Jest against the mock bridge (events emit, simulate maps
to fixture report). Acceptance: API typed; bridge returns fixtures; no sensitive symbol referenced.

**T3 / Expo example app + native-build CI gate.** Minimal example app; `expo prebuild` check; xcodebuild/
gradle build (or, if CI lacks toolchains, a documented skip + the forbidden-sensitive-symbol grep hardened
to fail the build). Files: example app, `.github/workflows/*` (mobile build job), Jest smoke. Acceptance:
`expo prebuild` succeeds; example builds in simulator; CI grep fails on any sensitive native symbol.

### Phase 8 — secure local storage + egress control

**T4 / Secure local store abstraction (mock).** Keychain/Keystore + encrypted-capsule interface with a
deterministic mock impl; data-classification tags; export/delete APIs. Files: new `mobile/secure_store.py`
(+ TS interface). Tests: round-trip, no-plaintext-at-rest assertion, export/delete. Acceptance: no plaintext
sensitive data in the mock store; classification enforced.

**T5 / Data-egress guard (budget-bound).** Extend `privacy_budget.py` so simulated egress over budget is
**denied deterministically**; egress events carry classification + byte cost. Files: `privacy_budget.py`,
`policy.py`. Tests: under-budget allowed, over-budget blocked, classification recorded. Acceptance: egress
respects budget; decision deterministic + audited.

**T6 / Offline queue + retention controls.** Durable mock queue with TTL/retention + flush; redacted entries.
Files: new `mobile/offline_queue.py`. Tests: enqueue/flush/retention-expiry; entries hash-only. Acceptance:
queue durable + bounded; expired entries dropped; no raw payloads stored.

### Phase 9 / 10 — additional framework scaffolds (mock-native, parallel to Expo)

**T7 / React Native TurboModule spec + Codegen scaffold (mock).** TurboModule interface + Codegen spec +
mock iOS/Android stubs (fixtures only). Files: `runtimes/mobile/react-native/...`. Tests: codegen spec
compiles; Jest mock-bridge; forbidden-symbol grep. Acceptance: spec compiles; example wiring; no sensitive API.

**T8 / Flutter platform interface + Dart models (mock).** Dart API + platform interface + Method/EventChannel
stubs (mock); generated Dart models matching the schemas. Files: `runtimes/mobile/flutter/...`. Tests:
`flutter analyze` clean; Dart model round-trip vs a schema fixture. Acceptance: analyze clean; channels stubbed; mock-only.

### Phase 12 — enterprise governance (lowest-risk slices first)

**T9 / SIEM export (CEF + JSON) from traces.** Deterministic exporter from the prev-hash trace + `arc mobile
siem-export --format cef|json`; redaction preserved (hash-only payloads). Files: new `mobile/siem_export.py`,
`cli/mobile.py`. Tests: CEF + JSON snapshot from a golden trace; redaction holds; deterministic. Acceptance:
valid CEF/JSON; no raw payloads; stable output.

**T10 / Org/tenant policy context + RBAC/ABAC denial.** Add role/tenant context to `MobilePolicyDecision`
via `EnterprisePolicyHook`; deterministic RBAC denial; verify a **signed** org policy bundle (reuse
`signing.py`); reject bad signatures. Files: `policy.py`, new `mobile/policy_context.py`. Tests: RBAC denial,
tenant isolation, bad-bundle-signature rejected, `policy_version` carried. Acceptance: role denies action;
unsigned/forged bundle rejected; decisions deterministic + versioned.

---

## Batch acceptance
All 10 committed to `main`, each with tests; full Python suite + `@arc-studio/protocol` (coverage gate) +
`pnpm typecheck` green; `check-banned-claims.sh` green; `docs/phases.md` + `docs/roadmap.md` updated per task.
Posture unchanged: **Simulator Preview**, mock-native only, no production/native claims. Phase 11 (real
native capabilities) stays **out of scope** until its per-capability entry gates are met.

---

## Progress log (Batch 5)

- **T1 ✅ (Phase 6)** Expo config plugin — `app.plugin.js` + `plugin/arc-permission-map.json` (advisory iOS usage strings + Android permissions from capability permission IDs; allowlist-only, simulator-preview labeled, no real device APIs). Test: `python/tests/test_mobile_expo_config_plugin.py` (6 passed incl. node behavioral injection; map-completeness drift guard vs `capabilities.py`). ruff clean.
- **T2 ✅ (Phase 6)** Expo TS API + fixtures-only native bridge — `src/index.ts` rewritten to route through `requireNativeModule("ArcMobileRuntime")` with an identical deterministic JS fixture fallback; added `getCapabilities()` (13-cap catalog, drift-guarded vs `capabilities.py`), `simulate(plan)`, `addSimulationListener` + Expo `EventEmitter`; Swift/Kotlin declare `Events("onSimulate")` + emit (fixtures only). Test: `test_mobile_expo_api.py` (6) — bridge+fallback, TS↔Swift↔Kotlin contract parity, event wiring, catalog drift-guard, no real device APIs. 22 expo tests pass.
- **T3 ✅ (Phase 6 COMPLETE)** Expo example app (`example/App.tsx` + `app.json` wiring the config plugin) + dedicated CI gate `.github/workflows/mobile-expo.yml` (authoritative = recursive forbidden-symbol scan of all Swift/Kotlin/TS/JS; `expo prebuild` best-effort). Test: `test_mobile_expo_example.py` (6). Phase 6 recorded as main Phase 187.
- **T4 ✅ (Phase 8)** Secure local store — `mobile/secure_store.py`: REAL encryption-at-rest via Fernet (AES-128-CBC + HMAC); `SecureLocalStore` with `KeyProvider` abstraction (Keychain/Keystore seam, `InMemoryKeyProvider` preview), classification tags (MobileDataSensitivity), data-subject `export(include_values)`/`delete`/`wipe`. At-rest file holds ciphertext only; tamper + wrong-key fail closed (SecureStoreError). Test `test_mobile_secure_store.py` (8) incl. no-plaintext-at-rest + tamper.
- **T5 ✅ (Phase 8)** Data-egress guard — `privacy_budget.py` `EgressGuard`/`EgressDecision`: deterministic deny when egress exceeds overall byte budget or a per-classification limit; critical class blocked by default; negative cost denied; `check` pure, `record` applies only on allow; byte-cost + classification on every decision. Test `test_mobile_egress_guard.py` (7).
- **T6 ✅ (Phase 8 COMPLETE)** Offline queue — `mobile/offline_queue.py` `OfflineQueue`/`QueueEntry`: durable, bounded (FIFO eviction), TTL retention; entries hash-only (SHA-256 + redacted metadata, no raw payload at rest); `flush`/`gc`/`verify`. Test `test_mobile_offline_queue.py` (7). Phase 8 recorded as main Phase 188.
