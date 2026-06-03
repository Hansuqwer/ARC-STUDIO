# Runtime Pack SDK

> **Status:** MVP — local-first, static validation, no code execution.
> **Constraint:** This is an **inert** discovery layer. ARC never imports, executes, or starts a runtime from a pack manifest.

---

## What Is a Runtime Pack?

A **runtime pack** is a static, version-pinned JSON file (`arc-runtime-pack.json`) that fully describes a runtime adapter's identity, permissions, capabilities, entrypoints, MCP dependencies, model usage, SwarmGraph IR claims, and policy requirements — **without ARC having to hard-code any of that knowledge into its core repository**.

Think of it as a machine-readable bill-of-materials for a runtime: you read it like a product spec sheet, never by running the product.

```
arc-runtime-pack.json      ← The only required artifact
├── schema_version: 1
├── id: "acme.my-runtime"
├── permissions: [{kind: "network", reason: "…"}]
├── capabilities: [{name: "run_graph", network: false}]
├── entrypoints: {inspect: "acme.runtime:inspect"}   ← never executed in MVP
├── ir: {can_export_ir: true, supported_ir_version: 1}
└── manifest_hash: "sha256…"    ← content-addressed, tamper-evident
```

### What a pack is NOT

| Misconception | Reality |
|---|---|
| A Python package or wheel | No — a pack is pure JSON metadata |
| Something ARC downloads | No — local-first only in the MVP |
| Something ARC executes | No — `entrypoints` are recorded but never called |
| A container image manifest | No — language/framework-agnostic |
| A dynamic plugin | No — static, fail-closed, hash-pinned |

---

## Key Design Decisions

### Fail-closed defaults

Every risk flag defaults to `false`. A capability is assumed to be harmless unless the manifest explicitly declares otherwise. ARC's validation layer enforces that dangerous claims (network, paid models, secrets, shell, outside-workspace) must be backed by explicit permissions with reasons.

### Static validation only

Validation is fully static and deterministic. The validator never imports pack code, makes a network request, or starts a subprocess. It checks schema, id safety, semver, entrypoint safety, permission completeness, MCP hash pinning, IR version compatibility, secret leakage, and hash integrity — all from the JSON alone.

### Content-addressed manifests

Every manifest carries a `manifest_hash` (sha256 of canonical JSON, volatile keys excluded). The hash is computed over a normalized view:

- Keys sorted alphabetically
- No whitespace (compact encoding)
- Volatile fields excluded: `manifest_hash`, `created_at`, `compiled_at`, `imported_at`, `installed_at`
- Sensitive field names (e.g. `token`, `api_key`) redacted before hashing

This makes manifests tamper-evident and reproducible: the same content always produces the same hash.

### No secrets ever

Manifests are committed to version control and stored in ARC's local registry. The validator (R11) scans for known secret patterns and rejects any manifest that contains one. The redactor scrubs sensitive field names before writing to the registry.

---

## Schema Version

```python
RUNTIME_PACK_SCHEMA_VERSION = 1   # int, bumped on breaking changes
MANIFEST_FILENAME = "arc-runtime-pack.json"
```

When `schema_version` does not equal `RUNTIME_PACK_SCHEMA_VERSION`, `load_manifest` raises `ManifestLoadError` and `validate_manifest` emits an R1 error. Readers refuse manifests they do not understand.

---

## Manifest Structure

```json
{
  "schema_version": 1,
  "id": "acme.my-runtime",
  "name": "Acme My Runtime",
  "version": "0.1.0",
  "description": "...",

  "runtime": {
    "runtime_name": "AcmeRuntime",
    "runtime_kind": "agent",
    "language": "python",
    "framework": "langgraph",
    "license": "Apache-2.0"
  },

  "entrypoints": {
    "inspect":       "acme_runtime.adapter:inspect",
    "compile_to_ir": "acme_runtime.ir:compile",
    "run":           "acme_runtime.runner:run"
  },

  "permissions": [
    { "kind": "network", "required": true, "reason": "Fetches remote graph definitions.", "default_decision": "deny" }
  ],

  "capabilities": [
    { "name": "run_graph", "reads": true, "writes": true, "network": true }
  ],

  "ir": {
    "can_export_ir": true,
    "supported_ir_version": 1,
    "opaque_node_policy": "reject"
  },

  "mcp": [
    { "server_id": "my-tool-server", "required": true, "manifest_hash": "<64-char sha256>" }
  ],

  "manifest_hash": "<sha256 of canonical JSON>"
}
```

See `docs/schemas/runtime-pack.schema.json` for the full JSON Schema.

---

## Validation Rules (R1–R12)

| Rule | Severity | Description |
|---|---|---|
| R1 `schema_version` | error | Must equal `RUNTIME_PACK_SCHEMA_VERSION` |
| R2 `id` | error | Required, stable, safe (`[a-zA-Z0-9._-]`, no `..`/`/`/`\`) |
| R3 `version` | error | Must be semver-like (MAJOR.MINOR.PATCH) |
| R4 `entrypoints` | error | No absolute paths or shell invocations |
| R5 `unknown_permission` | error | Unknown `kind` fails closed |
| R6 `dangerous_permission_no_reason` | error | network/paid/secrets/shell/outside_workspace must have `reason` |
| R7 `capability_missing_permission` | error | Dangerous capability flag must have matching permission |
| R8 `dangerous_permission_default_allow` | warning | Dangerous permission with `default_decision=allow` |
| R9 `mcp_missing_hash` | error | Required MCP server must pin `manifest_hash` |
| R10 `ir_*` | error/warning | IR claims need `supported_ir_version` + `opaque_node_policy` |
| R11 `secret_in_manifest` | error | No secrets anywhere in the manifest |
| R12 `manifest_hash_*` | error/warning | Pinned hash must match content; absent hash is a warning |

---

## CLI Reference

All commands emit an `ArcEnvelope` (`ok(…)` or `err(…)`) with `--json`.

```bash
# Scaffold a new pack skeleton (hash-pinned, fail-closed by default)
arc runtime-pack init --id org.my-runtime --name "My Runtime" ./my-runtime/

# Validate all 12 rules
arc runtime-pack validate ./my-runtime/
arc runtime-pack validate ./my-runtime/ --json   # machine-readable envelope

# Structured inspection summary
arc runtime-pack inspect ./my-runtime/

# Install metadata into workspace registry (no code executed)
arc runtime-pack install ./my-runtime/
arc runtime-pack install ./my-runtime/ --force   # overwrite existing

# List all installed packs
arc runtime-pack list

# Remove a pack
arc runtime-pack uninstall org.my-runtime

# Full health check: validate + drift + integration availability
arc runtime-pack doctor ./my-runtime/
```

---

## Python SDK Reference

```python
from agent_runtime_cockpit.runtime_packs import (
    # Scaffold
    init_pack, build_scaffold_manifest,
    # Load
    load_manifest, find_manifest, inspect_manifest, load_manifest_dict,
    # Hash
    manifest_hash, verify_manifest_hash, canonical_json,
    # Validate
    validate_manifest, RuntimePackValidationReport, ValidationFinding,
    # Redact
    redact_manifest, redact_string, find_secrets, is_safe_manifest,
    # Registry
    create_registry, RuntimePackRegistry, RuntimePackRegistryEntry,
    RuntimePackInstallError,
    # Optional integrations
    to_capability_card, to_policy_findings, ir_compatibility,
    verify_mcp_against_registry,
)
```

### Quick workflow

```python
from pathlib import Path
from agent_runtime_cockpit.runtime_packs import (
    load_manifest, validate_manifest, create_registry
)

# 1. Scaffold
from agent_runtime_cockpit.runtime_packs import init_pack
init_pack(Path("my-runtime"), pack_id="org.my-runtime", name="My Runtime")

# 2. Load and validate
m = load_manifest(Path("my-runtime"))
report = validate_manifest(m)
if not report.ok:
    for f in report.errors:
        print(f"[{f.rule}] {f.message}")

# 3. Install metadata into registry (no code executed)
reg = create_registry(workspace=Path("."))
entry = reg.install(Path("my-runtime"))
print(f"Installed {entry.id} @ hash={entry.manifest_hash[:16]}…")

# 4. Drift detection
drift = reg.check_drift("org.my-runtime")
print("Drifted:", drift["drifted"])
```

---

## Permission System

### Known permission kinds

`network`, `filesystem`, `shell`, `mcp`, `secrets`, `memory`, `search`, `paid_models`, `outside_workspace`, `background`, `observability`

Unknown kinds are **errors** (fail-closed): ARC refuses to load a pack claiming a permission it doesn't recognise.

### Dangerous permissions

The five *dangerous* permission kinds — `network`, `paid_models`, `secrets`, `shell`, `outside_workspace` — must satisfy extra rules:

1. A pack claiming any of these must supply a non-empty `reason` (R6 error).
2. A capability flag that asserts one of these (e.g. `network: true`) must be backed by a matching declared permission (R7 error).
3. Setting `default_decision: allow` for a dangerous permission is a R8 warning, because capability expansion should require explicit operator trust.

---

## IR Integration

Packs that can produce SwarmGraph IR must declare:

```json
"ir": {
  "can_export_ir": true,
  "supported_ir_version": 1,
  "opaque_node_policy": "reject"
}
```

`opaque_node_policy` is required (R10): it tells ARC what to do when an exporter encounters a node it cannot classify (`reject`, `mark_opaque`, or `require_review`). A version mismatch with the locally installed IR reader is a warning.

---

## Capability Card Integration

`to_capability_card(manifest)` derives a `CapabilityCard` for the pack using `EntityType.RUNTIME_ADAPTER`. When the `capabilities` package is not importable (e.g. isolated tests), a structurally-compatible dict is returned.

---

## MCP Integration

`verify_mcp_against_registry(manifest)` compares the manifest's declared MCP `manifest_hash` values against the local `McpRegistryStore`. It never starts an MCP server. Required MCP dependencies that are missing from the registry are flagged.

---

## Security Surface Summary

`inspect_manifest(manifest)` returns a `security_surface` dict answering:

| Key | Meaning |
|---|---|
| `can_call_paid_models` | Declares `requires_paid_models` or has `paid` cap/tool |
| `can_access_network` | Has `network` cap or search.network or `network` permission |
| `can_access_filesystem` | Has `reads`/`writes` cap or storage.enabled |
| `can_run_shell` | Has `shell` cap |
| `can_call_mcp` | Has `mcp` cap or declared MCP dependencies |
| `can_access_secrets` | Has `secrets` cap |
| `can_access_memory` | memory.enabled |
| `can_search` | search.enabled |
| `can_run_background` | Has `background` cap |
| `can_run_outside_workspace` | Has `outside_workspace` cap or storage.outside_workspace |

---

## Known Limitations (MVP)

- **Local-first only.** No registry discovery, signed pack distribution, or remote fetch.
- **Entrypoints recorded, never executed.** `entrypoints` are static references; ARC doesn't call them in the MVP.
- **No UI trust flows.** Interactive capability-expansion approval is planned but not implemented.
- **No signed packs.** Manifests are hash-pinned but not cryptographically signed.
- **No automatic re-pinning.** After editing a manifest, you must re-run `arc runtime-pack validate` (it re-pins on success) or call `build_scaffold_manifest` / `manifest_hash()` directly.

---

## Future Work

- Signed manifest bundles (GPG / OIDC cosign)
- Remote pack registry with version resolution
- UI capability-expansion trust flows
- Automatic schema migration when `RUNTIME_PACK_SCHEMA_VERSION` is bumped
- `arc runtime-pack upgrade` command for in-place schema migration
- Integration with ARC Studio's runtime selector UI
