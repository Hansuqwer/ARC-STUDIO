# ADR-007: Provider Routing Unification

## Status
Proposed

## Context

ARC Studio currently has **two separate provider routing layers**:

### Layer 1: ARC Python Daemon (`providers.py`)
- Location: `python/src/agent_runtime_cockpit/providers.py`
- Purpose: IDE daemon provider status, account management, routing metadata
- Storage: JSON files in `~/.arc/` (`providers.json`, `provider-routing.json`, `provider-quota.json`)
- Execution: **Dry-run proxy only** — blocks live calls unless `ARC_ALLOW_LIVE_PROVIDER_TESTS=true`
- Providers: 5 registered (openai, anthropic, openrouter, qwen, kimi)
- Features: Account store, routing policy, daily quota tracking

### Layer 2: SwarmGraph Gateway (`ai-provider-swarm-gateway`)
- Location: `runtimes/swarmgraph/packages/ai-provider-swarm-gateway/`
- Purpose: Actual LLM inference routing with consensus
- Storage: JSON files + SQLite semantic cache + encrypted vault
- Execution: **Real inference calls** to 12+ providers
- Providers: 12+ adapters (OpenAI, Anthropic, Qwen, Kimi, OpenRouter, Grok, Google, DeepSeek, GLM, Groq, 9Router, Mock)
- Features: 9-node LangGraph routing, consensus strategies, policy guardrails, semantic cache, encrypted vault, quota tracking, browser auth import

### Current Interaction
- ARC daemon spawns SwarmGraph gateway as subprocess
- Provider selection passed via env var: `AI_PROVIDER_SWARM_GATEWAY_DEFAULT_PROVIDER`
- No deep integration — ARC's provider system is metadata-only
- SwarmGraph gateway handles all actual inference

### Problem
- Duplicate provider definitions (5 in ARC, 12+ in gateway)
- Duplicate quota tracking (ARC daily counters, gateway quota pool)
- Duplicate secret management (ARC env refs, gateway encrypted vault)
- ARC provider system can't actually route calls — it's a dry-run shell
- Users configure providers in ARC but actual routing happens in gateway
- No unified view of provider status, usage, or costs

## Decision

### Unified Architecture

**Principle: ARC manages metadata and policy; SwarmGraph gateway manages execution.**

```
┌─────────────────────────────────────────────────┐
│                  ARC Studio IDE                  │
│                                                  │
│  Provider UI ──► ARC Provider Metadata           │
│    - Status (configured/missing)                 │
│    - Accounts (env refs)                         │
│    - Routing policy (mode, default)              │
│    - Quota display (read from gateway)           │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│               ARC Python Daemon                  │
│                                                  │
│  ProviderService (metadata + policy)             │
│    ├── accounts       → env var references       │
│    ├── routing_policy → mode, default, dry_run   │
│    └── quota_display  → reads from gateway API   │
│                                                  │
│  NO inference calls. NO provider adapters.       │
│  All execution delegated to runtime adapters.    │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              SwarmGraph Gateway                  │
│                                                  │
│  Provider Adapters (12+)                         │
│    ├── Inference routing                         │
│    ├── Consensus strategies                      │
│    ├── Semantic cache (SQLite)                   │
│    ├── Encrypted vault (Fernet)                  │
│    └── Quota tracking (multi-tenant)             │
└─────────────────────────────────────────────────┘
```

### ARC Provider System (Simplified)

ARC's provider system becomes a **metadata and policy layer only**:

```python
class ProviderService:
    """Manages provider metadata, accounts, and routing policy.
    Does NOT make inference calls — that's the gateway's job."""
    
    def __init__(self, config: Config):
        self.config = config
        self.accounts = ProviderAccountStore()  # ~/.arc/providers.json
        self.routing = ProviderRoutingStore()   # ~/.arc/provider-routing.json
    
    def get_provider_status(self, provider_id: str) -> ProviderStatus:
        """Check if a provider is configured (has env var or account)."""
        account = self.accounts.get_account(provider_id)
        if account:
            env_key = account.api_key_env
            return ProviderStatus(
                configured=bool(os.environ.get(env_key)),
                provider_id=provider_id,
                model=account.model,
            )
        return ProviderStatus(configured=False, provider_id=provider_id)
    
    def resolve_provider(self, request: RunRequest) -> ResolvedProvider:
        """Resolve which provider to use for a run request."""
        policy = self.routing.get_policy()
        
        if request.provider:
            return ResolvedProvider(
                provider_id=request.provider,
                model=request.model or policy.default_model,
                source="explicit_request",
            )
        
        return ResolvedProvider(
            provider_id=policy.default_provider,
            model=policy.default_model,
            source="routing_policy",
        )
    
    def list_providers(self) -> list[ProviderStatus]:
        """List all known providers and their configuration status."""
        return [
            self.get_provider_status(pid)
            for pid in KNOWN_PROVIDER_IDS
        ]
```

### Gateway Integration

ARC passes resolved provider info to the gateway via env vars:

```python
class SwarmGraphAdapter:
    def _build_env(self, resolved_provider: ResolvedProvider) -> dict[str, str]:
        env = filtered_env(SWARMGRAPH_ENV_ALLOWLIST)
        
        env["AI_PROVIDER_SWARM_GATEWAY_DEFAULT_PROVIDER"] = resolved_provider.provider_id
        env["AI_PROVIDER_GATEWAY_MODEL"] = resolved_provider.model
        
        # Pass API key env vars (gateway reads them directly)
        account = self.provider_service.accounts.get_account(resolved_provider.provider_id)
        if account:
            api_key = os.environ.get(account.api_key_env)
            if api_key:
                env[account.api_key_env] = api_key
        
        return env
```

### Quota Unification

ARC reads quota data from the gateway instead of maintaining its own counters:

```python
class ProviderService:
    async def get_quota(self, provider_id: str) -> QuotaInfo:
        """Read quota from gateway's quota tracker."""
        gateway_api = f"{self.config.swarmgraph.gateway_url}/api/quota"
        async with aiohttp.ClientSession() as session:
            resp = await session.get(gateway_api, params={"provider": provider_id})
            return QuotaInfo.model_validate(await resp.json())
```

If gateway is not running, ARC falls back to its own `~/.arc/provider-quota.json`.

### Secret Management Unification

- **ARC layer**: Stores env var references only (never actual keys)
- **Gateway layer**: Uses encrypted vault (Fernet) for stored secrets
- **Runtime**: API keys passed via env vars to subprocess (gateway reads them)
- **No duplicate secret storage**: ARC references, gateway stores encrypted

### CLI Commands

```bash
# ARC provider commands (metadata layer)
arc providers list                    # Show all providers + config status
arc providers accounts add ...        # Add account (env var reference)
arc providers accounts list           # List configured accounts
arc providers routing set ...         # Set routing policy
arc providers routing show            # Show current routing policy
arc providers status <provider>       # Check if provider is configured

# Gateway commands (execution layer)
arc gateway quota <provider>          # Show gateway quota usage
arc gateway cache stats               # Show semantic cache stats
arc gateway providers list            # List gateway provider adapters
```

### Migration Path

**Phase 1: Clarify separation**
- Document that ARC provider system is metadata-only
- Remove `dry_run_proxy()` from ARC (it's misleading — ARC never makes real calls)
- Add `can_route: false` to ARC provider capability flags

**Phase 2: Wire gateway integration**
- ARC passes resolved provider to gateway via env vars
- ARC reads quota from gateway API when available
- Gateway remains the single source of truth for inference

**Phase 3: Unify CLI**
- `arc providers` commands manage metadata
- `arc gateway` commands manage execution
- Clear separation in help text and documentation

**Phase 4: Deprecate duplicate features**
- Remove ARC's `provider-quota.json` (use gateway quota)
- Remove ARC's `ProviderDefinition` registry (gateway owns adapters)
- Keep ARC's `ProviderAccountStore` (env var references for IDE UX)

## Consequences

### Positive
- Clear separation of concerns (metadata vs execution)
- No duplicate provider definitions
- No duplicate quota tracking
- Gateway remains the single source of truth for inference
- ARC IDE gets provider status without making API calls
- Simpler ARC provider code (no dry-run proxy, no adapter registry)

### Negative
- Requires gateway to be running for full provider visibility
- Quota data unavailable when gateway is offline (fallback to local JSON)
- Two CLI namespaces (`arc providers` vs `arc gateway`)

### Neutral
- ARC still manages env var references (needed for IDE UX)
- Gateway still manages encrypted vault (needed for multi-tenant security)
- Both systems coexist during migration

## References
- ARC providers: `python/src/agent_runtime_cockpit/providers.py`
- Gateway providers: `runtimes/swarmgraph/packages/ai-provider-swarm-gateway/src/ai_provider_swarm_gateway/providers/`
- Gateway CLI: `runtimes/swarmgraph/packages/ai-provider-swarm-gateway/src/ai_provider_swarm_gateway/cli.py`
- Gateway quota: `runtimes/swarmgraph/packages/ai-provider-swarm-gateway/src/ai_provider_swarm_gateway/quota/`
- Gateway cache: `runtimes/swarmgraph/packages/ai-provider-swarm-gateway/src/ai_provider_swarm_gateway/cache/semantic.py`
