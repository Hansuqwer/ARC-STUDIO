# ADR-022: Deprecation Policy

**Status:** Proposed (draft 2026-05-21)  
**Context:** Path to 1.0 planning, Phase 1 (Polish)  
**Related:** ADR-004 (event schema versioning), ADR-020 (desktop-first), ADR-021 (audit chain)

## Context

ARC Studio has grown from a single Python CLI to a multi-adapter Python backend with a TypeScript protocol layer and an Eclipse Theia IDE. During this growth, APIs, schemas, CLI commands, and configuration keys have been added, changed, and occasionally removed — but without a documented policy governing how those changes are communicated to users.

The lack of a deprecation policy creates several problems:

1. **Breaking changes surprise users.** A user upgrading from v0.1.0-alpha to v0.2 may find that a CLI flag, config key, or schema version they relied on has been removed without warning.

2. **Schema migration debt accumulates.** The project has explicit v1→v2→v3 migration functions (CostRecord, EventEnvelope, ChatSession) but no policy for when a version becomes unsupported and what notice users can expect.

3. **CLI command drift is undocumented.** The `arc studio sessions-migrate` alias exists as a "compatibility alias and prints a deprecation warning" (per CHANGELOG) but the policy on how long aliases live is implicit.

4. **Contributor uncertainty.** Engineers working on Phase 2 (Provider Expansion) need to know: can they rename a CLI flag? Can they reorder a JSON-RPC response field? How much notice do they need to give?

ADR-020 (desktop-first) established that pre-1.0 versions follow SemVer pre-release conventions, but that is a versioning policy, not a deprecation policy. This ADR fills that gap.

## Decision

ARC Studio adopts the following deprecation policy, effective immediately for all v0.x releases and locked at 1.0.

### 1. Semver Versioning

ARC Studio follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html):

- **Major version (1.0, 2.0, etc.):** Breaking changes require a major version bump. A "breaking change" is any change that requires a user to modify their existing ARC Studio configuration, CLI invocation, or integration code to restore previously-working behavior.

- **Minor version (0.1, 0.2, ... 0.x):** Before 1.0, breaking changes are allowed at any minor version, but must follow the notice period below. This is consistent with the SemVer spec: "Major version zero (0.y.z) is for initial development. Anything may change at any time. The public API should not be considered stable."

- **Patch version (0.x.y):** Bug fixes and performance improvements only. No breaking changes, no new features.

**Pre-1.0 exceptions:** Schema migrations (CostRecord v1→v2→v3, EventEnvelope v1→v2, ChatSession v1→v2→v3→v4) are explicitly exempt from the minor-version notice requirement. These are internal data formats, not user-facing APIs, and must support forward/backward migration for at least one version cycle regardless of the minor version.

### 2. Deprecation Notice Period

When a feature, API, CLI command, flag, or configuration key is deprecated:

| Severity | Notice Period | Example |
|----------|---------------|---------|
| Breaking | One minor version + one patch cycle | A CLI flag renamed in v0.4.0 was deprecated in v0.3.0 with a warning, and removed in v0.4.0. |
| Non-breaking additive | No notice required | Adding a new CLI flag, new endpoint, new config key. |
| Internal schema migration | One version cycle (must support read of previous version) | CostRecord v3 can read v2. v2 readers must handle v3 by ignoring unknown fields. |

**Breaking** means:
- Renaming or removing a CLI command, subcommand, or flag
- Changing the semantics of a CLI flag (e.g., `--mode` now accepts different values)
- Renaming or removing a configuration key in `arc config` or `.env`
- Changing the shape of a JSON-RPC response field in `arc-protocol.ts`
- Removing or renaming a public Python function, class, or module
- Changing the default behavior of a command in a way that breaks existing workflows

**Non-breaking additive** means:
- Adding a new CLI command, flag, or config key
- Adding a new field to a JSON-RPC response (existing fields unchanged)
- Adding a new public function or class
- Adding a new adapter or provider

**Schema versioning** means:
- Schema versions are immutable once released. A v1 event envelope always means the same thing.
- New schema versions are created by adding migration functions. Old versions are supported for at least one major version after the new version is introduced.
- Schema readers must handle at least the current and previous version. Writers must always write the latest version.
- Schema migration tests are required for every version transition (per ADR-021 Phase 1 checks).

### 3. Deprecation Announcement Requirements

When a deprecation is announced (at the start of the notice period):

1. **CHANGELOG entry:** The "Deprecated" section of CHANGELOG.md must list the deprecated item, its planned removal version, and the recommended migration path.

2. **In-code warning:** The deprecated code path must emit a runtime warning. For CLI commands: a deprecation warning printed to stderr. For Python functions: a `DeprecationWarning` or `warnings.warn()` call. For configuration keys: a warning logged at startup.

3. **Release notes:** The GitHub release for the version that introduces the deprecation must include the same information as the CHANGELOG entry.

### 4. Shims and Aliases

Deprecated features may be supported via backward-compatibility shims:

- **CLI aliases:** A deprecated command name may be preserved as a hidden alias that prints a deprecation warning. Example: `arc studio sessions-migrate` → `arc studio sessions migrate`.

- **Function wrappers:** A deprecated function may be preserved as a wrapper that calls the new function and emits a `DeprecationWarning`.

- **Config backward-compatibility:** A deprecated config key may be read and mapped to the new key with a warning.

**Shim lifetime:** Shims live for one minor version + one patch cycle (matching the notice period). They are then removed. This is documented at the time of deprecation.

### 5. Documentation Requirements

When a deprecation is announced:

1. The CHANGELOG's "Deprecated" section must include: the deprecated item, its replacement (if any), its planned removal version, and a migration example.

2. The relevant CLI `--help` text must include a deprecation note.

3. The relevant configuration documentation must include a deprecation note.

4. Schema migration functions must include JSDoc/docstrings documenting their version lifespan.

### 6. Deprecation During Pre-1.0

During v0.x (pre-1.0):

- The notice period is still one minor version + one patch cycle. This is shorter than a post-1.0 cycle would be, but provides predictability during rapid development.

- Deprecation warnings are printed to stderr for CLI, logged for daemon, and included in CHANGELOG.

- Users running with `-W error` in Python (as the project's own CI does) will see deprecation warnings as errors. This is intentional: it surfaces deprecation impact early.

- The project's CI must not itself trigger deprecation warnings (all in-code deprecations must have corresponding CI-visible tests or CI must run without `-W error` for affected commands).

### 7. Post-1.0 Commitment

At 1.0:

- The notice period extends to **one major version** for breaking changes. A feature deprecated in 1.x is removed in 2.0 at the earliest.

- Semantic versioning becomes strict. Breaking changes require a major version bump.

- Schema versions are supported for at least two major versions.

- A formal API surface will be documented (a "Public API" declaration) to make it unambiguous which interfaces are covered by the deprecation policy. Until then, the public API is defined as: all CLI commands, all configuration keys, all Python modules exported from `agent_runtime_cockpit`, and all TypeScript types exported from `arc-protocol-ts`.

## Consequences

### Positive

- **Predictability for users:** Users know what to expect when upgrading. Breaking changes are announced, documented, and have a migration path.

- **Predictability for contributors:** Engineers working on Phase 2-5 know the rules about renaming, removing, or changing APIs.

- **CHANGELOG discipline:** The "Deprecated" section becomes meaningful rather than incidental.

- **Schema cleanup:** Migration shims have defined expiration dates, preventing indefinite accumulation of backward-compatibility code.

### Negative

- **Complexity for rapid development:** During v0.x, the one-minor+one-patch cycle means some breaking changes take two releases to complete. This is accepted as the cost of predictability.

- **Documentation burden:** Every deprecation requires CHANGELOG, help text, and doc updates. This is accepted as the cost of professional software.

### Open Questions

1. **API surface definition:** Should the public API be explicitly annotated (e.g., `@public` decorator, `__all__` enforcement, dedicated public module)? Lean: document the public API surface in `docs/reference/api-surface.md` for v0.5, enforce with tooling at 1.0.

2. **Config backward-compatibility:** How long should old config keys be readable? Lean: same as shim lifetime (one minor + one patch). After that, the old key is ignored (not errored) to avoid breaking user config files.

3. **Pre-1.0 notice period reduction:** Should the notice period be shorter during v0.x (e.g., one minor version only, not + one patch)? Lean: keep one minor + one patch for consistency. The cycle is already short during rapid development.

## Implementation Plan

**Phase 1 (v0.2-v0.5):**
1. Adopt this ADR. Update CHANGELOG to use the "Deprecated" section consistently.
2. Audit current deprecated features (sessions-migrate alias, legacy runtime-mode values) and ensure they have removal timelines.
3. Add deprecation warnings to shims that lack them.
4. Document the public API surface in `docs/reference/api-surface.md` (target: v0.5).

**Phase 3 (v0.9):**
1. Enforce deprecation policy in code review: every change that deprecates something must include CHANGELOG entry, warning, and migration path.
2. Remove shims whose notice period has expired.
3. Prepare for 1.0 policy escalation (longer notice periods, strict semver).
