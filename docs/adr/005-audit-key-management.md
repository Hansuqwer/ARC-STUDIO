# ADR-005: Audit HMAC Key Management and Rotation

## Status
Proposed

## Context

ARC Studio's audit situation:
- **SwarmGraph runtime** has production-grade HMAC-SHA256 audit chain (`runtimes/swarmgraph/packages/swarm-shared/swarm_shared/audit.py`, 474 lines, tested)
- **ARC Studio frontend** has an empty audit widget (`theia-extensions/arc-audit/`) — hardcoded empty array, "Not implemented" badge
- **ARC adapter** declares `can_audit=False` — does not wire into SwarmGraph's audit system
- **HMAC secrets** come from environment variables only (`HIVE_SWARM_AUDIT_SECRET`) — no key management, no rotation, no encrypted storage
- **Protocol** has `can_audit: boolean` field but it's always `false`

The audit chain implementation in SwarmGraph is solid. The gap is entirely in:
1. Wiring ARC to use SwarmGraph's audit system
2. Managing HMAC secrets (generation, storage, rotation)
3. Exposing audit verification in the IDE

## Decision

### Audit Architecture

ARC Studio will wire into SwarmGraph's existing HMAC audit chain system:

```
┌─────────────────────────────────────────────────┐
│                  ARC Studio IDE                  │
│                                                  │
│  Audit Widget ──► GET /api/audit/{run_id}       │
│  Verify Button ─► POST /api/audit/{run_id}/verify│
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│               ARC Python Daemon                  │
│                                                  │
│  AuditService                                    │
│    ├── load_chain(run_id)    → .arc/audit/      │
│    ├── verify_chain(run_id)  → HMAC check       │
│    └── get_head_hash(run_id) → current head     │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              SwarmGraph Runtime                  │
│                                                  │
│  AuditChain (swarm_shared/audit.py)             │
│    ├── sign_record()     → HMAC-SHA256          │
│    ├── verify_record()   → timing-safe check    │
│    ├── verify_chain()    → full chain verify    │
│    └── JSONLBackend      → .arc/audit/{run_id}  │
└─────────────────────────────────────────────────┘
```

### HMAC Secret Management

#### Secret Generation

```python
def generate_audit_secret() -> str:
    """Generate a cryptographically secure HMAC secret."""
    return secrets.token_hex(32)  # 64 hex chars, 256 bits
```

#### Secret Storage

Preferred local-desktop storage is **system keychain**. Headless/CI deployments may use an explicitly named environment variable. A plaintext file fallback is not approved.

| Platform | Storage | API |
|----------|---------|-----|
| macOS | Keychain | `security add-generic-password` |
| Linux | Secret Service / GNOME Keyring | `secret-tool` or `dbus` |
| Windows | Credential Manager | `cmdkey` or Windows Credential API |

Potential Python implementation uses `keyring` library, gated behind dependency and platform-behavior review:
```python
import keyring

SERVICE_NAME = "arc-studio-audit"
SECRET_KEY = "hmac-signing-key"

def store_audit_secret(secret: str) -> None:
    keyring.set_password(SERVICE_NAME, SECRET_KEY, secret)

def load_audit_secret() -> Optional[str]:
    return keyring.get_password(SERVICE_NAME, SECRET_KEY)

def delete_audit_secret() -> None:
    keyring.delete_password(SERVICE_NAME, SECRET_KEY)
```

Fallback: If keyring is unavailable (headless server/CI), use an explicit env var and report degraded key-management status:
```python
def resolve_audit_secret() -> Optional[str]:
    secret = load_audit_secret()
    if secret is None:
        secret = os.environ.get("ARC_AUDIT_SECRET")
    return secret
```

#### Secret Rotation

Rotation procedure:

1. **Generate new secret** → store as `hmac-signing-key-next`
2. **Grace period** → both old and new secrets accepted for verification (configurable, default 24h)
3. **Cutover** → new runs use new secret, old secret marked for expiry
4. **Expire** → old secret deleted after grace period

```python
class AuditKeyManager:
    def __init__(self, grace_period_hours: int = 24):
        self.grace_period = timedelta(hours=grace_period_hours)
    
    def rotate(self) -> str:
        """Start rotation. Returns new secret ID."""
        new_secret = generate_audit_secret()
        keyring.set_password(SERVICE_NAME, "hmac-signing-key-next", new_secret)
        keyring.set_password(SERVICE_NAME, "hmac-signing-key-rotated-at", now())
        return new_secret
    
    def resolve(self) -> tuple[str, Optional[str]]:
        """Return (current_secret, previous_secret) for signing/verification."""
        current = load_audit_secret()
        if current is None:
            raise AuditKeyMissing("No audit secret configured")
        
        rotated_at_str = keyring.get_password(SERVICE_NAME, "hmac-signing-key-rotated-at")
        if rotated_at_str is None:
            return (current, None)
        
        rotated_at = parse_iso(rotated_at_str)
        next_secret = keyring.get_password(SERVICE_NAME, "hmac-signing-key-next")
        
        if now() - rotated_at > self.grace_period:
            # Grace period expired — cutover
            keyring.set_password(SERVICE_NAME, "hmac-signing-key", next_secret)
            keyring.delete_password(SERVICE_NAME, "hmac-signing-key-next")
            keyring.delete_password(SERVICE_NAME, "hmac-signing-key-rotated-at")
            return (next_secret, None)
        
        # In grace period — sign with next, verify with both
        return (next_secret, current)
    
    def verify_with_rotation(self, record: AuditRecord) -> bool:
        """Verify record, accepting both current and previous secrets."""
        current, previous = self.resolve()
        if verify_record(record, current):
            return True
        if previous and verify_record(record, previous):
            return True
        return False
```

### CLI Commands

```bash
# Initialize audit (generate and store secret)
arc audit init

# Show current audit status (secret configured? rotation pending?)
arc audit status

# Rotate HMAC secret (starts grace period)
arc audit rotate

# Complete rotation immediately (skip remaining grace period)
arc audit rotate --force

# Verify a run's audit chain
arc audit verify <run_id> [--expected-head-hash <hash>] [--expected-count <n>]

# Export audit chain for external verification
arc audit export <run_id> [--format jsonl|json]
```

### Daemon Endpoints

```
GET  /api/audit/{run_id}           # Get audit chain metadata and head hash
POST /api/audit/{run_id}/verify    # Verify chain, return result
GET  /api/audit/{run_id}/chain     # Full audit chain (JSONL format)
POST /api/audit/init               # Generate and store audit secret
POST /api/audit/rotate             # Start key rotation
GET  /api/audit/status             # Audit configuration status
```

### IDE Integration

1. **Audit widget** (`theia-extensions/arc-audit/`) wired to daemon endpoints
2. **Run detail view** shows audit status badge (verified/unverified/not-audited)
3. **Verify button** triggers `POST /api/audit/{run_id}/verify` and shows result
4. **Audit chain visualization** shows chain links with hash verification

### Wiring SwarmGraph Audit to ARC

The SwarmGraph adapter will enable audit when configured:

```python
class SwarmGraphAdapter:
    def __init__(self, config: Config):
        self.audit_enabled = config.security.audit_enabled
        self.audit_secret = resolve_audit_secret() if self.audit_enabled else None
    
    def run_workflow(self, workflow_id: str, inputs: dict) -> RunRecord:
        env = self._build_env()
        if self.audit_enabled and self.audit_secret:
            env["HIVE_SWARM_AUDIT_SECRET"] = self.audit_secret
            env["ARC_AUDIT_DIR"] = str(self.workspace / ".arc" / "audit")
        
        # ... spawn subprocess ...
        
        # After completion, verify audit chain
        if self.audit_enabled:
            chain_path = self.workspace / ".arc" / "audit" / f"{run_id}.jsonl"
            if chain_path.exists():
                # Verify chain integrity
                chain = AuditChain.from_file(chain_path)
                if not chain.verify(self.audit_secret):
                    # Log warning but don't fail the run
                    logger.warning(f"Audit chain verification failed for {run_id}")
```

## Consequences

### Positive
- Leverages SwarmGraph's battle-tested HMAC audit implementation
- Keychain storage is more secure than env vars or files
- Key rotation supports compliance requirements
- Grace period prevents verification gaps during rotation
- IDE integration makes audit visible and actionable

### Negative
- `keyring` library adds a dependency and may not work in all environments
- Fallback to env var needed for headless/CI environments
- Rotation adds complexity (dual-secret verification window)

### Neutral
- Audit is opt-in (disabled by default, no performance impact when off)
- Audit chain files are separate from trace files (`.arc/audit/` vs `.arc/traces/`)
- Verification is read-only and can be done offline

## References
- SwarmGraph audit: `runtimes/swarmgraph/packages/swarm-shared/swarm_shared/audit.py`
- SwarmGraph audit ADR: `runtimes/swarmgraph/docs/adr/0004-audit-signing-hmac-chain.md`
- Audit tests: `runtimes/swarmgraph/packages/swarm-shared/tests/test_audit.py`
- ARC audit widget (stub): `theia-extensions/arc-audit/src/browser/arc-audit-widget.tsx`
- Audit verify CLI: `runtimes/swarmgraph/packages/ai-provider-swarm-gateway/src/ai_provider_swarm_gateway/cli.py:1006-1079`
