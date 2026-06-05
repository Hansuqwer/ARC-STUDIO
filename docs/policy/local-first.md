# Policy: Local-First (ARC Studio Default Posture)

> **Status:** Authoritative for ARC Studio default behavior.
> **Owner:** Sprint planning + spec authors.
> **Last updated:** 2026-06-04
> **Companion to:** `docs/policy/cosai-llm-in-path.md`
> **Origin:** Lock the definition that has been operating implicitly through
> the token-saving spec series (v0.3.0-alpha → v0.5.0-alpha) so future spec
> authors don't re-litigate it per sprint.

---

## The rule (short form)

**ARC Studio is local-first by default.** All state lives on the user's
machine; ARC depends on no central server; ARC makes no network call the
user hasn't explicitly configured; ARC exports no telemetry without explicit
per-session consent.

LLM API calls to vendors the user has configured (Anthropic, OpenAI,
Google, OpenRouter, DeepSeek, Qwen, Kimi, GLM, MiMo, MiniMax, etc.) are
**permitted** — the user owns the conversation; the vendor sees only
prompts; nothing else.

---

## What "local-first" means here (long form)

The phrase "local-first" has multiple plausible readings. ARC uses
**L2 + L3 + L4** combined (defined below). It does NOT mean "no network."

### L1 — Strict local-only (NOT ARC's posture)

Would mean: only local-runnable LLMs (Ollama, llama.cpp). No Anthropic.
No OpenAI. **ARC does not adopt this** because the value proposition is
"frontier-quality conversation, user owns the trace."

### L2 — Local data sovereignty (ARC default)

- All conversation history persisted to local disk
- All budget state on local disk (per `budget/storage.py` SQLite WAL)
- All handles (per QW-4) on local disk in the same SQLite file
- Anthropic / OpenAI / Google / openai-compatible vendors are permitted
  destinations for LLM calls; user explicitly configures keys
- Vendor sees prompts; vendor does not see anything else

### L3 — Single-user, single-machine, no central broker (ARC default)

- ARC does not depend on a central license server
- ARC does not depend on a remote auth gate
- ARC does not depend on a remote budget broker
- ARC does not require any third-party service to function
- Multi-instance ARC across machines does not coordinate by default

### L4 — No surprise exfiltration (ARC default)

- No background telemetry to ARC's own servers
- No "phone home" version-check pings (unless user opts in)
- No default-enabled analytics
- Network calls happen only to user-configured vendors
- OTel exports go to user-configured local collectors only

### What L2+L3+L4 forbids

| Forbidden by default | Why |
|---|---|
| Telemetry to ARC project servers | L4 |
| Cloud-hosted budget aggregation | L3 (no central broker) |
| Mandatory hosted observability | L2 + L3 |
| Required auth via remote OAuth gate | L3 |
| Background auto-updates | L4 |
| Crash reports to third party | L4 |
| Remote model registry / pricing feed | L4 (no surprise network call) |
| LLMLingua-as-a-Service for compression | L2 + L3 (user data to third party) |

### What L2+L3+L4 permits

| Permitted | Why |
|---|---|
| Anthropic / OpenAI / Google / OpenRouter direct API | User-configured vendor; user owns the prompt |
| Local OTel collector | User-configured destination on user's machine |
| Local SQLite for budget + handles | L2 |
| Multiple ARC instances on the same machine sharing budget DB | L2 + L3 (shared *file*, not shared *broker*) |
| Reading public docs (when user clicks "open in browser") | User-initiated; not ARC-initiated |
| Vendor's own caching (Anthropic prompt cache, OpenAI auto-cache) | Vendor is the configured destination |

---

## What's the difference between this and CoSAI?

`cosai-llm-in-path.md` is about *decisions*: no LLM may decide whether to
spend, evict, or compact. It applies even to *local* LLMs.

`local-first.md` (this document) is about *deployment topology*: no central
server, no mandatory cloud, no surprise network. It applies to all of ARC's
own architecture choices, regardless of whether LLMs are involved.

The two policies are **independent**:

| Scenario | CoSAI? | Local-first? |
|---|---|---|
| Compaction triggered by a local Ollama model's perplexity scoring | ✗ Forbidden (LLM in decision path) | ✓ Permitted (all local) |
| Hosted Anthropic call for a chat turn | ✓ Permitted (informing the user, not deciding) | ✓ Permitted (user-configured vendor) |
| ARC ships traces to ARC project's cloud for analytics | ✓ Permitted (no decision involved) | ✗ Forbidden (telemetry to third party without opt-in) |
| ARC asks GPT-5 whether to evict a message | ✗ Forbidden (LLM deciding) | ✓ Permitted (would be a vendor call) |

Most enforcement code paths must pass both. Both policies have
**import-guard tests** that future code must satisfy.

---

## Opt-in escape hatches (queued for future sprints)

Three categories of feature would be **useful** but **violate L4 if enabled
by default**. They are queued as opt-in (off by default) features in
`docs/spec/v0.7-alpha-opt-in-cloud-features.md`:

1. **Remote pricing-table feed.** Signed JSON file on a CDN. ARC checks
   once per week IF user opts in. No usage data leaves the box; only a
   public document is fetched. Closes the manual pricing-refresh loop.

2. **Shared budget broker (team mode).** Optional remote endpoint that
   multiple ARC instances can check for a shared cap. Useful for "this
   engagement has $500 across 3 developers." Off by default. When
   configured, ARC documents in `/wallet` that the broker is in use.

3. **Hosted observability bridge.** Export local OTel traces to
   user-chosen destination (Langfuse / Helicone / SigNoz / etc) with
   explicit per-session consent. ARC does not depend on the destination;
   it just integrates.

**None of these change the default posture.** A user who never opts in
sees ARC behave exactly as L2+L3+L4 today. Each escape hatch:

- Defaults OFF
- Requires explicit user configuration to enable
- Shows visible indicator in `/wallet` or status bar when active
- Is logged in the CHANGELOG as opt-in
- Has its own threat-model + privacy review in its spec

---

## How to check compliance

### Code review checklist

For any PR touching network code, persistence, or analytics:

- [ ] Does this make a network request? → To which destination? Is it user-configured?
- [ ] Does this default to ON for any kind of cloud or remote service? → Refactor to default OFF.
- [ ] Does this write user data outside the user's data dir? → Justify or refactor.
- [ ] Does this introduce a new server-side dependency? → Refactor or write a `docs/policy/` exception.
- [ ] Does this read user data from a remote source ARC didn't ask for? → Same.

### Import-guard test pattern

Modules covered by this policy SHOULD have an automated test that asserts
no telemetry / analytics / phone-home library is imported:

```python
# tests/<module>/test_no_telemetry_imports.py
import ast
from pathlib import Path

FORBIDDEN_IMPORTS = {
    "datadog", "sentry_sdk", "newrelic", "rollbar", "bugsnag",
    "mixpanel", "amplitude", "segment", "posthog",
    "honeycomb",  # ARC users may opt-in via OTel exporter; never default
    # If telemetry-adjacent libs ever land in deps, audit them here
}

def test_arc_studio_imports_no_telemetry_libs():
    root = Path(__file__).parent.parent.parent / "src" / "agent_runtime_cockpit"
    found = set()
    for py_file in root.rglob("*.py"):
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                        found.add(f"{py_file.relative_to(root)}: {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in FORBIDDEN_IMPORTS:
                    found.add(f"{py_file.relative_to(root)}: {node.module}")
    assert not found, f"Forbidden telemetry imports: {found}"
```

### Runtime network-call audit

For paths that explicitly are NOT supposed to make network calls (compaction,
handle store, budget, wallet):

```python
def test_compaction_makes_no_network_calls(monkeypatch):
    """Compaction is local-only — no urllib, requests, httpx, aiohttp."""
    call_count = 0
    def fail(*a, **kw):
        nonlocal call_count
        call_count += 1
        raise AssertionError("Network call from local-first path")
    for mod in ["urllib.request.urlopen", "requests.request",
                "httpx.Client.request", "aiohttp.ClientSession._request"]:
        monkeypatch.setattr(mod, fail)
    result = compact(sample_messages, context_limit=100, context_used=95)
    assert call_count == 0
```

---

## Resolution procedure for new ambiguous cases

When a proposed feature has plausible cloud / remote integration:

1. **Author proposes** in a sprint spec with one of: LOCAL_ONLY, OPT_IN_REMOTE, FORBIDDEN.
2. If OPT_IN_REMOTE, the spec MUST include:
   - Why local-only is insufficient
   - Default value (must be OFF)
   - Configuration path (env var, config file)
   - User-visible indicator when active
   - Threat model (what data leaves the box? to whom? under what auth?)
3. Sprint review either ratifies (adds an entry to this document's §"Opt-in escape hatches") or rejects.
4. Once ruled, the result is recorded here. Future sprints inherit.

---

## Cross-references

- Companion policy: `docs/policy/cosai-llm-in-path.md`
- Implementation: `python/src/agent_runtime_cockpit/budget/storage.py` (local SQLite WAL)
- Implementation: `python/src/agent_runtime_cockpit/context/handles.py` (planned v0.5.0; local blob store)
- Opt-in escape hatches spec: `docs/spec/v0.7-alpha-opt-in-cloud-features.md`
- Project rules: `AGENTS.md`
- Origin: token-saving sprint preamble (v0.3.0-alpha through v0.5.0-alpha)
