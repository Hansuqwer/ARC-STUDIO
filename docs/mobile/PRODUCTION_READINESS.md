# ARC Mobile Runtime — Production Readiness Checklist

Current status: **not production-ready** and **not enterprise-ready**.

This checklist is a release gate. A production or enterprise claim must not be made until the relevant boxes are complete and tested.

## Preview readiness

- [x] Mock-only status is documented.
- [x] No real native access is claimed.
- [x] Built-in capabilities are simulator capabilities.
- [ ] Strict validation rejects duplicate IDs and malformed manifests.
- [ ] Protocol schemas cover manifests, plans, reports, events, traces, and policy decisions.
- [ ] Trace verification detects mutation and reordering.
- [ ] Replay compares traces against deterministic simulator outputs.

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

- [ ] Apple privacy manifest generation exists.
- [ ] iOS permission usage descriptions are generated or validated.
- [ ] Android manifest generation exists.
- [ ] Android Data Safety notes are generated.
- [ ] App review notes are generated.
- [ ] Generated artifacts are snapshot-tested.
- [ ] Human review is required before submission.

## Enterprise readiness

- [ ] Tenant/org policy context exists.
- [ ] RBAC/ABAC policy controls exist.
- [ ] Device posture or MDM hooks exist.
- [ ] Audit export exists.
- [ ] Audit retention policy exists.
- [ ] Remote kill switch or enterprise disable policy exists.
- [ ] Signed package provenance exists.
- [ ] SBOM is generated.
- [ ] Vulnerability scanning is part of release.
- [ ] Enterprise docs and support posture exist.

## Hard no-go conditions

Do not claim production or enterprise readiness if any of these are true:

- Expo, React Native, or Flutter package is still only a stub.
- Native sensitive capability exists without signed plan verification.
- Native sensitive capability exists without scoped approval.
- Traces cannot detect tampering.
- App-store artifacts are missing for real permissions.
- Enterprise policy controls are missing for enterprise claims.
