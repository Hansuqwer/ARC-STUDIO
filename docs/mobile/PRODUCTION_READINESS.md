# ARC Mobile Runtime — Production Readiness Checklist

Current status: **not production-ready** and **not enterprise-ready**.

This checklist is a release gate. A production or enterprise claim must not be made until the relevant boxes are complete and tested.

> **Reconciliation note (2026-06-08).** Individual capability boxes below are now ticked where the capability is shipped **and** covered by tests (evidence cited per section). Checking these sub-items does **not** change the top-line status: ARC Mobile Runtime stays a simulator preview — **not production-ready** and **not enterprise-ready**. The hard no-go conditions still hold: the Expo / React Native / Flutter packages are fixtures-only scaffolds, no real native device access exists, and the gated items (real framework builds, device posture / MDM, supply-chain provenance, native dependency vulnerability scanning) remain unchecked. Remaining work is tracked in `docs/roadmap.md` (R79.1–R79.5).

## Preview readiness

- [x] Mock-only status is documented.
- [x] No real native access is claimed.
- [x] Built-in capabilities are simulator capabilities.
- [x] Strict validation rejects duplicate IDs and malformed manifests.
- [x] Protocol schemas cover manifests, plans, reports, events, traces, and policy decisions.
- [x] Trace verification detects mutation and reordering.
- [x] Replay compares traces against deterministic simulator outputs.

_Evidence:_ `validation.py` (`duplicate_capability_id`, V12 duplicate-step-ID, strict-mode errors) + `test_mobile_schemas.py` (`test_list_schema_kinds_has_all_six` = manifest/action_plan/simulation_report/event/trace/policy_decision; `test_strict_load_runs_schema_validation`); `tests/mobile/test_mobile.py` (`test_verify_trace_detects_reorder`, `test_verify_trace_detects_mutation`, `prev_event_hash` chain); `test_mobile_replay.py` (`test_deterministic_traces_match`, `test_mutated_step_detected`).

## Production SDK readiness

- [ ] At least one real mobile framework package builds from generated distribution artifacts.
- [ ] Expo Module, React Native TurboModule, or Flutter plugin implementation exists and is tested.
- [ ] No sensitive native capability can run without a signed action plan.
- [ ] No sensitive native capability can run without a scoped, unexpired approval grant.
- [ ] Every real capability has input/output schemas.
- [ ] Every real capability has fixture-backed simulator coverage.
- [ ] Every real capability has tamper-evident trace coverage.
- [ ] Every real capability has app-store privacy artifacts.
- [ ] Every real capability has rollback or feature-flag control.
- [ ] Package build, typecheck, unit, integration, and example-app tests run in CI.

## App-store readiness

- [x] Apple privacy manifest generation exists.
- [x] iOS permission usage descriptions are generated or validated.
- [x] Android manifest generation exists.
- [x] Android Data Safety notes are generated.
- [x] App review notes are generated.
- [x] Generated artifacts are snapshot-tested.
- [x] Human review is required before submission.

_Evidence:_ `mobile/compliance/` — `ios.py` (`generate_privacy_manifest` PrivacyInfo.xcprivacy, `generate_usage_strings` NSUsageDescription), `android.py` (`generate_manifest_permissions`, `generate_data_safety_notes`), `review_notes.py` (`generate_review_notes`), all marked advisory with `requires_human_review: True`. Output is locked by deterministic tests in `test_mobile_compliance.py` (9 content-assertion tests, not golden-file snapshots). These are **advisory** generators for the safe-demo manifest; they do not imply readiness to submit, and no real permissions exist.

## Enterprise readiness

- [x] Tenant/org policy context exists.
- [x] RBAC/ABAC policy controls exist.
- [ ] Device posture or MDM hooks exist.
- [x] Audit export exists.
- [x] Audit retention policy exists.
- [x] Remote kill switch or enterprise disable policy exists.
- [ ] Signed package provenance exists.
- [x] SBOM is generated.
- [ ] Vulnerability scanning is part of release.
- [ ] Enterprise docs and support posture exist.

_Evidence (checked):_ `policy_context.py` signed `OrgPolicyBundle` + `TenantPolicyHook` (`test_tenant_mismatch_denied`, `test_rbac_role_denied`, `test_capability_and_abac_denials`); `siem_export.py` CEF/JSON (`test_cef_format_and_severity`, `test_cli_siem_export`); `audit_retention.py` TTL/rotation (`test_mobile_audit_retention.py`); `feature_flags.py` kill switch (`test_kill_switch_overrides_all_flags`); `sbom.py` CycloneDX (`test_sbom_is_valid_cyclonedx_shape`, `test_cli_sbom`).
_Unchecked (gated/not yet built):_ device posture / MDM hooks → `docs/roadmap.md` R79.3; signed package supply-chain provenance → R79.4; native dependency vulnerability scanning in release (Python deps are scanned via `pip-audit`, but the mobile JS/Dart trees are not) → R79.5; enterprise docs + support posture remain unchecked conservatively.

## Hard no-go conditions

Do not claim production or enterprise readiness if any of these are true:

- Expo, React Native, or Flutter package is still only a stub.
- Native sensitive capability exists without signed plan verification.
- Native sensitive capability exists without scoped approval.
- Traces cannot detect tampering.
- App-store artifacts are missing for real permissions.
- Enterprise policy controls are missing for enterprise claims.
