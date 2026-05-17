# 12 — Trust Diff and Policy

## Summary

TrustDiff is a structured diff shown to users before trust/policy/provider/runtime changes that weaken safety or enable new paid/runtime capabilities. The policy loader provides a configurable approval policy file that controls what requires confirmation.

## TrustDiff Schema

**Create file:** `python/src/agent_runtime_cockpit/protocol/trust_diff.py`

```python
from pydantic import BaseModel, Field

class TrustDiff(BaseModel):
    diff_id: str
    before: list[str] = Field(default_factory=list)
    after: list[str] = Field(default_factory=list)
    added_capabilities: list[str] = Field(default_factory=list)
    removed_restrictions: list[str] = Field(default_factory=list)
    affected_runtimes: list[str] = Field(default_factory=list)
    requires_confirmation: bool = True
```

### Where TrustDiff Is Generated

1. **First workspace trust** — UNTRUSTED → TRUSTED
2. **Runtime switch** (capabilities change, e.g., no-paid → paid) — v0.2
3. **Provider key addition** (new paid capability) — v0.2
4. **Policy file change** (relaxed restrictions) — v0.2

## Policy Loader

**Create file:** `python/src/agent_runtime_cockpit/config/policy.py`

```python
from pydantic import BaseModel, Field
from pathlib import Path
from enum import Enum

class ApprovalRule(str, Enum):
    ASK = "ask"        # Ask user before action
    AUTO = "auto"      # Auto-approve
    DENY = "deny"      # Block action

class ApprovalPolicy(BaseModel):
    paid_calls: ApprovalRule = ApprovalRule.ASK
    destructive_writes: ApprovalRule = ApprovalRule.ASK
    trust_changes: ApprovalRule = ApprovalRule.DENY
    shell_exec: ApprovalRule = ApprovalRule.DENY
    phase_advance: ApprovalRule = ApprovalRule.ASK  # v0.2 [RESERVED]

class PolicyConfig(BaseModel):
    version: int = 1
    approvals: ApprovalPolicy = Field(default_factory=ApprovalPolicy)
```

### Policy File Locations

| Scope | Path |
|-------|------|
| Project | `.arc/policy.yaml` |
| User | `~/.config/arc-studio/policy.yaml` |
| Built-in | Safe defaults (any change = ASK or DENY) |

### Precedence

Project policy > User policy > Built-in defaults

**Important:** Project policy cannot weaken user policy for `shell_exec` or `trust_changes`. User policy can impose stricter limits than project policy.

```python
def load_policy(
    workspace: Path | None = None,
) -> PolicyConfig:
    """
    Load and merge policy files with precedence.
    Project policy cannot weaken user policy for shell_exec or trust_changes.
    """
    user_policy = _load_user_policy()
    project_policy = _load_project_policy(workspace) if workspace else None

    merged = _merge_with_safety(user_policy, project_policy)
    return merged
```

## Workspace Trust UX

### First-Untrusted-Workspace Flow

Spec `ARC_STUDIO_UX_SPEC.md:809`:

```
┌ workspace trust ──────────────────────────────────────────────┐
│ This workspace is untrusted. ARC Studio can read files but     │
│ cannot write, run, or call paid providers.                     │
│                                                                │
│ [Trust this workspace] [Stay untrusted] [Learn more]           │
└───────────────────────────────────────────────────────────────┘
```

Chat input is disabled until user chooses. Trust requires explicit click/Enter.

### Trust Binding

Trust binds to: canonical path + machine ID + user ID.
- Symlinked paths resolve before trust check.
- Moving/cloning a workspace requires new trust decision.
- Trust can be revoked from `/config > Workspace Trust`.

### Trust Diff Rendering

Before `UNTRUSTED → TRUSTED`, show:

```
┌ trust change ─────────────────────────────────────────────────┐
│ This change enables:                                           │
│   + write files in workspace                                   │
│   + run arbitrary commands                                     │
│   + call paid providers (if keys set)                           │
│                                                                │
│ Previously restricted: read-only, no network, no paid calls    │
│                                                                │
│ [Confirm trust] [Stay untrusted]                               │
└────────────────────────────────────────────────────────────────┘
```

## Entry Points to Extend

| File | What to Change |
|------|----------------|
| `security/trust.py` | `ensure_trusted()` computes and returns TrustDiff |
| `security/profiles.py` | Profile switch computes TrustDiff |
| `config/policy.py` | NEW: policy loader |
| `orchestration/runtime_router.py` | Runtime switch computes capability TrustDiff |
| `cli/slash_commands.py` | `/config` shows trust diff |
| `cli/chat_repl.py` | Render TrustDiffBanner before trust changes |
| `web/routes.py` | Add `GET /api/trust/diff` and `POST /api/trust/accept` |
| `browser/` | `WorkspaceTrustBanner` component |

## Acceptance Criteria

- [ ] TrustDiff generated before first workspace trust
- [ ] v0.1 renders TrustDiff for first workspace trust only
- [ ] Policy loader reads `.arc/policy.yaml` and `~/.config/arc-studio/policy.yaml`
- [ ] Project policy cannot weaken user policy for `shell_exec` and `trust_changes`
- [ ] `ApprovalPolicy` controls paid calls, destructive writes, shell exec, trust changes
- [ ] Chat input disabled until trust decision is made
- [ ] Trust binds to canonical path + machine ID + user ID
- [ ] All tests pass

## Do Not Implement Yet

- TrustDiff for provider key addition — v0.2
- TrustDiff for runtime capability changes — v0.2
- Trust revocation user flow beyond `/config > Trust` — v0.2
- Parent folder trust inheritance — v0.2
- `.arc/` and `.git/` protected paths enforcement — v0.2
- Shell exec guard (not just policy) — v0.2
- Network policy enforcement (proxy) — v0.2
