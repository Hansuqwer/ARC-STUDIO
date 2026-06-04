# QW-4 — MCP Output Handle Virtualization Design

> **Date:** 2026-06-04
> **Question:** What handle URI scheme should QW-4 use to virtualize large
> MCP tool outputs, and how does it interop with the MCP spec?

---

## §1 — Executive verdict

1. **MCP spec already has a handle pattern.** It's called `resource_link` (returned from tools) and `embedded resource` (inlined). URI scheme is open per MCP — vendors use `file://`, `note://`, `stock://`, `network:///`, `resource://`, etc.
2. **Recommended scheme:** Use **`arc://output/sha256/<hex>`** for ARC-managed output handles. The `arc://` prefix is owned, the `sha256/` segment is interop-friendly with future spec changes, and it's structurally compatible with MCP's `resource_link` type returned from `tools/call`. Round-trip via `resources/read`.
3. **Biggest risk:** MCP `resource_link` is *not* explicitly designed for "I generated this output and stored it on the host" — it's designed for server-exposed resources. ARC is creating a *new* resource type ("agent-side output cache"). Get a written posture: are these MCP resources (and should be advertised in `resources/list`) or are they ARC-internal with MCP-compatible URIs (and *not* in `resources/list`)?

---

## §2 — MCP spec audit (accessed 2026-06-04)

Sources: [modelcontextprotocol.io/specification/2025-11-25/server/tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools), [modelcontextprotocol.io/specification/2025-06-18/server/resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources), [speakeasy.com/mcp/core-concepts/resources](https://www.speakeasy.com/mcp/core-concepts/resources).

### A. Resources are URI-addressed read-only data

```jsonrpc
{ "method": "resources/read", "params": { "uri": "file:///project/src/main.rs" } }
```

Response shape:
```json
{
  "contents": [{
    "uri": "file:///project/src/main.rs",
    "mimeType": "text/x-rust",
    "text": "fn main() { ... }"
  }]
}
```

Binary content uses `blob` (base64) instead of `text`. (Spec section: Resources → Reading Resources.)

### B. Tools can return resource references in two forms

From `tools/` spec, accessed 2026-06-04:

**`embedded resource` (inline content) —** for small things, returns the actual data:

```json
{
  "type": "resource",
  "resource": {
    "uri": "file:///project/src/main.rs",
    "mimeType": "text/x-rust",
    "text": "fn main() { ... }",
    "annotations": { "audience": ["user", "assistant"], "priority": 0.7 }
  }
}
```

**`resource_link` (reference only) —** for big things, returns just the pointer:

```json
{
  "type": "resource_link",
  "uri": "file:///project/src/main.rs",
  "name": "main.rs",
  "description": "Primary application entry point",
  "mimeType": "text/x-rust"
}
```

**This is exactly the handle pattern QW-4 wants.** The client (in our case, ARC) calls `resources/read` later to expand.

### C. URI scheme is open

Spec doesn't prescribe a single scheme. Documented in-the-wild:
- `file:///` (canonical for filesystems)
- `resource://` (Speakeasy examples)
- `note://`, `stock://`, `media://` (custom per-server)
- `network:///` (IETF draft for network-equipment MCP)

Servers may use any scheme; clients must round-trip the exact string in `resources/read`.

### D. Lifecycle

- `notifications/resources/list_changed` — server tells client "my resource list changed, re-list"
- `notifications/resources/updated` — server tells client "this specific URI changed, re-read"
- `resources/subscribe` — client opts into update notifications

For QW-4, ARC is acting as a *server-to-itself* (the handle creator). Spec doesn't prohibit this but it's slightly out of pattern.

---

## §3 — Recommended scheme for ARC

### URI

```
arc://output/sha256/<64-hex-chars>
```

Examples:
- `arc://output/sha256/3a7f9e2b1c4d8a6f5e0b7c8d9e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f`
- `arc://output/sha256/3a7f9e2b...` (display-truncated to first 8 chars in UI)

Rationale:
- **`arc://` namespace** is ARC-owned; no collision with `file://`, `mcp://`, etc.
- **`output/`** path segment leaves room for `arc://prompt/`, `arc://snapshot/`, future internal URIs.
- **`sha256/`** is the algorithm choice; if ARC ever needs to migrate to blake3, new URIs become `arc://output/blake3/...` while old URIs remain readable.
- **Stable across process restarts** — the SHA derived from content, not from a random ID, so the same tool output produces the same handle. Free deduplication.
- **Compatible with MCP** — `arc://...` is a valid MCP URI; an MCP-aware client could in principle `resources/read` it if ARC exposed a resource server. Not a current requirement but no obstacles later.

### Payload shape (what the model sees in the tool result)

```json
{
  "type": "resource_link",
  "uri": "arc://output/sha256/3a7f9e2b...",
  "name": "fs.read_file: /repo/CHANGELOG.md",
  "description": "2,097,152 bytes (~525K tokens) — too large to inline",
  "mimeType": "text/markdown",
  "annotations": {
    "audience": ["assistant"],
    "priority": 0.5,
    "arc.size_bytes": 2097152,
    "arc.estimated_tokens": 524288,
    "arc.preview_head": "# Changelog\n\n## [Unreleased]\n...",
    "arc.preview_tail": "...\n## [v0.1.0-alpha]\nInitial release.",
    "arc.expand_command": "/expand 3a7f9e2b"
  }
}
```

Notes:
- Uses spec-standard `resource_link` type, so any MCP-aware tool sees a familiar shape.
- ARC-specific extensions are in `annotations` under `arc.*` prefix per spec recommendation (custom annotations are allowed).
- `arc.preview_head` and `arc.preview_tail` give the model enough context to decide whether to expand without burning the full budget.
- `arc.expand_command` is user-facing only (the model shouldn't fabricate slash commands).

### Expansion contract

| Trigger | Behavior |
|---|---|
| User types `/expand <handle-prefix>` | ARC retrieves full content from local store, injects as next-turn user message |
| User types `/expand <handle> --filter <regex>` | (for structured outputs like dir listings) expand only matching entries |
| Model returns the handle URI in its output | **Do NOT auto-expand.** That would be an LLM-driven decision (CoSAI: prohibited). Surface as a clickable in TUI; require user keypress. |
| Cache eviction | Handles are *append-only* on disk (content-addressed); evict when storage budget exceeds N GB, oldest-first by *last access* not creation |

### Redaction interaction (verified against `arc-protocol-ts/src/run-diff.ts:redactDict`)

- Redaction runs at **handle-write time**, not handle-expand time.
- A redacted byte never enters the SHA computation as cleartext — hash is over post-redaction bytes.
- This means: redacting the same secret across two tool outputs produces *different* handles (good — no info leak via hash collision).

### Cache (R-04) interaction

- The *handle URI string* enters the model's context, not the full content.
- Anthropic's prompt cache will cache the handle URI (which is short and stable) — high cache hit rate.
- If expanded via `/expand`, the full content is *not* re-injected into earlier turns; it's appended as a new user message. So R-04 cache for prior turns stays valid.

---

## §4 — Two worked examples

### Example 1: Large file read

```
Tool call:  fs.read_file({ "path": "/repo/CHANGELOG.md" })
Raw output: 2,097,152 bytes (~525K tokens)

ARC intercepts in providers layer:
  1. SHA256 of post-redaction bytes → 3a7f9e2b1c4d...
  2. Store at ~/.local/share/arc-theia-studio/handles/3a/7f/9e2b1c4d.bin
  3. Emit resource_link to model (see §3 payload shape, ~150 tokens total)
  4. Cache hit: ~99.7% saving (525K → 0.15K tokens)

Model sees:
  [tool_result: resource_link uri=arc://output/sha256/3a7f9e2b...
    name="fs.read_file: /repo/CHANGELOG.md"
    description="2,097,152 bytes (~525K tokens) — too large to inline"
    preview_head="# Changelog\n## [Unreleased]\n..."
    preview_tail="...## [v0.1.0-alpha]\nInitial release."]

If user runs /expand 3a7f9e2b:
  → ARC injects full content as next user message, capped at remaining
    context budget per R-02 compaction strategy
```

### Example 2: Large directory listing

```
Tool call:  fs.list_directory({ "path": "/repo/python/tests" })
Raw output: 500 entries × ~80 chars = 40KB (~10K tokens)

Annotations:
  arc.entry_count = 500
  arc.preview_head = [first 50 entries as JSON array]
  arc.preview_tail = [last 50 entries as JSON array]
  arc.expand_command = "/expand def4ab56 [--filter REGEX]"

If user runs /expand def4ab56 --filter "test_token_*":
  → ARC reads full content, filters by regex, injects matching entries only
  → Typical filter saves 80-95% of tokens vs raw expansion
```

---

## §5 — Migration plan if MCP standardizes a different scheme

Scenarios:

| Future spec change | ARC migration |
|---|---|
| Spec adds canonical `mcp://output/...` scheme | Add `mcp://output/...` aliases; emit both during overlap; deprecate `arc://` in following release |
| Spec adds dedicated "handle" type beyond `resource_link` | Adopt new type in payload; keep URI scheme |
| Spec adds expiration metadata on resources | Add `arc.expires_at` annotation, mirror once spec stable |
| Spec deprecates `resource_link` for tool returns | Update payload type; URI scheme unaffected |
| Spec mandates a specific hash algorithm for content URIs | Already use SHA256; add `arc://output/<algo>/<hash>` aliasing if needed |

The chosen scheme is forward-compatible because it's:
- URI-shaped (always a string-comparable URI)
- Algorithm-tagged (can add other hashes)
- Vendor-prefixed (can be ignored or aliased by any client)

---

## §6 — Sources

| Source | URL | Accessed |
|---|---|---|
| MCP Resources spec | [modelcontextprotocol.io/specification/2025-06-18/server/resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources) | 2026-06-04 |
| MCP Tools spec (resource_link + embedded resource) | [modelcontextprotocol.io/specification/2025-11-25/server/tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) | 2026-06-04 |
| MCP Prompts (embedded resource shape) | [modelcontextprotocol.io/specification/2025-06-18/server/prompts](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts) | 2026-06-04 |
| MCP Resources concept guide | [modelcontextprotocol.info/docs/concepts/resources](https://modelcontextprotocol.info/docs/concepts/resources/) | 2026-06-04 |
| Resources URI scheme examples (note://, stock://) | [speakeasy.com/mcp/core-concepts/resources](https://www.speakeasy.com/mcp/core-concepts/resources) | 2026-06-04 |
| IETF MCP network-mgmt draft (network:/// scheme) | [ietf.org/archive/id/draft-zw-opsawg-mcp-network-mgmt-00.html](https://www.ietf.org/archive/id/draft-zw-opsawg-mcp-network-mgmt-00.html) | 2026-06-04 |
| MCP client SDK examples (read/list pattern) | [github.com/cyanheads/model-context-protocol-resources](https://github.com/cyanheads/model-context-protocol-resources/blob/main/guides/mcp-client-development-guide.md) | 2026-06-04 |
| MCP Cheat Sheet 2026 (resource summary) | [webfuse.com/mcp-cheat-sheet](https://www.webfuse.com/mcp-cheat-sheet) | 2026-06-04 |

---

## §7 — Open questions

| Q | Resolution path |
|---|---|
| Should ARC's handles be `resources/list`-able? (i.e., advertise to other MCP clients) | Probably no for v0.5.0-alpha P0; ARC's handles are an internal optimization, not a contract. Revisit if a third-party MCP client wants to deduplicate against ARC's cache. |
| Disk persistence: SQLite blob store or filesystem? | Recommend filesystem under `~/.local/share/arc-theia-studio/handles/<aa>/<bb>/<rest>.bin` (sharded prefix to avoid huge dirs). SQLite if we need transactional eviction. |
| Eviction policy: LRU by last access, or FIFO by creation, or budget-driven? | Start LRU with N GB cap (configurable). Same shape as browser cache. |
| Should the model be allowed to *create* handles? | No. Handles are ARC-side ingestion-time only. Models can only *reference* via the URI it received. |
| What does `/expand` do when handle is evicted? | Return `[handle expired or evicted; rerun the originating tool call]` — deterministic, model-friendly fallback. |
| Multi-process ARC sharing the same handle store? | Same race-condition concerns as budget persistence. Use SQLite or file locking. Defer to `budget-persistence-audit.md` outcome. |

---

## §8 — Cross-references

- Sibling brief: `docs/research/briefs/R-02-compaction-options.md` — handle virtualization is the overlapping strategy with compaction
- Sibling brief: `docs/research/briefs/budget-persistence-audit.md` — same persistence design questions
- Existing ARC: `packages/arc-protocol-ts/src/run-diff.ts:redactDict` (must compose)
- R-04 cache: `python/src/agent_runtime_cockpit/providers/anthropic.py:237-366`
- Headroom prior art: `chopratejas/headroom@8006293`
