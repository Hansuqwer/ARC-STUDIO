# ADR-006: Workspace Trust, Filesystem, and Network Isolation Policies

## Status
Proposed

## Context

ARC Studio's current security model:
- **Path validation** prevents directory traversal (workspace boundary enforcement via `resolve()` + `relative_to()`)
- **Environment allowlisting** prevents secret leakage to subprocesses
- **Secret redaction** scrubs API keys from output
- **Run profiles** define permission flags (`allow_paid_calls`, `allow_network`, `allow_shell`, `allow_secrets`) but don't enforce actual isolation
- **No sandbox** — subprocesses run with full user privileges
- **No filesystem isolation** — no chroot, no mount restrictions, no allowed_paths
- **No network isolation** — no iptables, no network namespace, no egress filtering (except `allowed_hosts` on one adapter)
- **No workspace trust model** — no signing, no verification, no multi-workspace hierarchy

This is acceptable for local development but insufficient for:
- Multi-tenant environments
- Untrusted workflow execution
- Production deployments
- Compliance requirements

## Decision

### Workspace Trust Model

#### Trust Levels

```python
class TrustLevel(str, Enum):
    UNTRUSTED = "untrusted"    # No trust — maximum isolation
    PARTIAL = "partial"        # Partial trust — limited capabilities
    TRUSTED = "trusted"        # Full trust — all capabilities allowed
```

#### Trust Resolution

Workspace trust is resolved at run time:

1. **Explicit config**: `.arc/config.yaml` → `workspace.trust_level`
2. **Workspace marker**: `.arc/trusted` file exists → `TRUSTED`
3. **Default**: `UNTRUSTED`

`PARTIAL` trust requires explicit user approval or future Theia trust integration. A path under the user's home directory is not trust evidence.

```python
def resolve_trust(workspace: Path, config: Optional[Config] = None) -> TrustLevel:
    if config and config.workspace.trust_level != "auto":
        return TrustLevel(config.workspace.trust_level)
    
    if (workspace / ".arc" / "trusted").exists():
        return TrustLevel.TRUSTED
    
    return TrustLevel.UNTRUSTED
```

#### Trust CLI Commands

```bash
# Mark workspace as trusted
arc workspace trust

# Mark workspace as untrusted
arc workspace untrust

# Show current trust level
arc workspace trust-status

# List all known workspaces and their trust levels
arc workspace list
```

### Filesystem Isolation Policy

#### Allowed Paths

Each run gets a filesystem access policy based on trust level:

| Trust Level | Allowed Read Paths | Allowed Write Paths | Blocked |
|-------------|-------------------|---------------------|---------|
| `UNTRUSTED` | `{workspace}/` | `{workspace}/.arc/`, `{workspace}/output/` | Everything else |
| `PARTIAL` | `{workspace}/`, `{home}/.arc/` | `{workspace}/` | System dirs, other users' homes |
| `TRUSTED` | All user-accessible | All user-writable | None (user discretion) |

#### Enforcement Strategy

**Phase 1 (P1): Policy-only enforcement**
- Document allowed paths in run metadata
- Log violations but don't block
- Used for audit and visibility

**Phase 2 (P2): Subprocess wrapper enforcement**
- Wrap subprocess execution with pre-exec validation
- Check file access patterns against policy
- Block obvious violations (e.g., writing to `/etc/`)

**Phase 3 (P3): Container-based enforcement**
- Use Docker/OrbStack bind mounts to restrict filesystem
- Only mount allowed paths into container
- True filesystem isolation

**Phase 4 (P4): Firecracker microVM (Linux only)**
- Full VM isolation for high-assurance environments
- No shared filesystem with host

#### Implementation (Phase 2)

```python
class FilesystemPolicy:
    def __init__(self, workspace: Path, trust: TrustLevel):
        self.workspace = workspace
        self.trust = trust
        self.allowed_read = self._compute_read_paths()
        self.allowed_write = self._compute_write_paths()
    
    def validate_path(self, path: Path, write: bool = False) -> bool:
        """Check if path is within allowed paths."""
        resolved = path.resolve()
        allowed = self.allowed_write if write else self.allowed_read
        return any(
            resolved == allowed_path.resolve() or resolved.is_relative_to(allowed_path.resolve())
            for allowed_path in allowed
        )
    
    def _compute_read_paths(self) -> list[Path]:
        if self.trust == TrustLevel.TRUSTED:
            return [Path.home()]
        elif self.trust == TrustLevel.PARTIAL:
            return [self.workspace, Path.home() / ".arc"]
        else:
            return [self.workspace]
    
    def _compute_write_paths(self) -> list[Path]:
        if self.trust == TrustLevel.TRUSTED:
            return [Path.home()]
        elif self.trust == TrustLevel.PARTIAL:
            return [self.workspace]
        else:
            return [self.workspace / ".arc", self.workspace / "output"]
```

### Network Isolation Policy

#### Network Modes

```python
class NetworkMode(str, Enum):
    NONE = "none"          # No network access
    RESTRICTED = "restricted"  # Only allowed hosts
    FULL = "full"          # Unrestricted network access
```

#### Network Policy by Trust Level

| Trust Level | Default Network Mode | Allowed Hosts |
|-------------|---------------------|---------------|
| `UNTRUSTED` | `NONE` | None |
| `PARTIAL` | `RESTRICTED` | LLM provider APIs, configured allowed_hosts |
| `TRUSTED` | `FULL` | All |

#### Allowed Hosts Configuration

```yaml
# .arc/config.yaml
security:
  allowed_hosts:
    - api.openai.com
    - api.anthropic.com
    - api.openrouter.ai
    - dashscope.aliyuncs.com
```

#### Enforcement Strategy

**Phase 1 (P1): Policy-only**
- Document network policy in run metadata
- Log network calls (via subprocess wrapper)
- No actual blocking

**Phase 2 (P2): HTTP proxy enforcement**
- Route subprocess HTTP traffic through ARC-controlled proxy
- Proxy enforces allowed_hosts list
- Blocks non-HTTP traffic at the process level (no raw socket access)

**Phase 3 (P3): Container network isolation**
- Docker network policies
- Egress filtering via iptables in container
- Network namespace isolation

**Phase 4 (P4): Firecracker network isolation**
- MicroVM network configuration
- Complete network stack isolation

### Resource Limits

#### Per-Run Resource Caps

```yaml
# .arc/config.yaml
execution:
  limits:
    max_memory_mb: 2048      # Max RAM per run
    max_cpu_percent: 100     # Max CPU (100 = 1 core)
    max_duration_seconds: 600 # Max run duration
    max_disk_mb: 512         # Max workspace write
```

#### Enforcement (Phase 2+)

```python
class ResourceLimits:
    def __init__(self, config: Config):
        self.max_memory = config.execution.limits.max_memory_mb * 1024 * 1024
        self.max_cpu = config.execution.limits.max_cpu_percent
        self.max_duration = config.execution.limits.max_duration_seconds
    
    def apply_to_subprocess(self, proc: asyncio.subprocess.Process):
        """Apply resource limits to subprocess (Unix only)."""
        import resource
        
        # Memory limit
        resource.setrlimit(resource.RLIMIT_AS, (self.max_memory, self.max_memory))
        
        # CPU time limit
        resource.setrlimit(resource.RLIMIT_CPU, (self.max_duration, self.max_duration))
```

### Isolation Provider Interface

Define an abstraction for isolation providers:

```python
class IsolationProvider(Protocol):
    """Interface for execution isolation providers."""
    
    async def run(
        self,
        command: list[str],
        env: dict[str, str],
        cwd: Path,
        filesystem_policy: FilesystemPolicy,
        network_policy: NetworkPolicy,
        resource_limits: ResourceLimits,
    ) -> SubprocessResult:
        """Execute command with isolation constraints."""
        ...
    
    async def health_check(self) -> bool:
        """Check if provider is available and functional."""
        ...
    
    @property
    def name(self) -> str:
        """Provider name (none, subprocess, docker, orbstack, firecracker)."""
        ...
```

Provider implementations:
- `NoIsolationProvider` — direct subprocess, no isolation (current behavior)
- `SubprocessIsolationProvider` — subprocess with env allowlist + resource limits
- `DockerIsolationProvider` — Docker container with bind mounts + network policy
- `OrbStackIsolationProvider` — OrbStack VM (macOS, Docker-compatible API)
- `FirecrackerIsolationProvider` — Firecracker microVM (Linux only, P4)

### Run Profile Enhancement

Extend run profiles to include isolation settings:

```python
@dataclass
class RunProfile:
    id: str
    allow_paid_calls: bool
    allow_network: bool
    allow_shell: bool
    allow_secrets: bool
    env_allowlist: tuple[str, ...] = ()
    isolation: str = "none"           # NEW: isolation provider
    network_mode: str = "restricted"  # NEW: network mode
    trust_required: TrustLevel = TrustLevel.UNTRUSTED  # NEW: minimum trust
```

Updated built-in profiles:

| Profile | Isolation | Network | Trust Required |
|---------|-----------|---------|----------------|
| `stub` | `none` | `none` | `untrusted` |
| `local-safe` | `subprocess` | `restricted` | `partial` |
| `local-paid` | `subprocess` | `restricted` | `partial` |
| `gateway` | `docker` | `restricted` | `trusted` |

## Consequences

### Positive
- Clear trust model with explicit levels
- Graduated isolation (policy → subprocess → container → microVM)
- Filesystem and network policies are documented and auditable
- Resource limits prevent runaway executions
- Isolation provider interface enables pluggable backends

### Negative
- Container-based isolation requires Docker/OrbStack installed
- Network proxy enforcement adds latency
- Resource limits are platform-dependent (rlimit on Unix, different on Windows)
- Trust model adds cognitive overhead for users

### Neutral
- Default trust is `UNTRUSTED` (safe by default)
- `TRUSTED` workspaces get full access (user discretion)
- Phase 1 is policy-only (no enforcement overhead)
- Firecracker is Linux-only and deferred to P4

## References
- Path validation: `packages/arc-extension/src/node/security-utils.ts:70-90`
- Python validation: `python/src/agent_runtime_cockpit/security/validation.py`
- Run profiles: `python/src/agent_runtime_cockpit/security/profiles.py`
- Env allowlist: `python/src/agent_runtime_cockpit/adapters/swarmgraph.py:46-56`
- Secret redaction: `python/src/agent_runtime_cockpit/security/redaction.py`
