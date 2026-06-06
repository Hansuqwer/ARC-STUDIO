# Release Readiness Checklist

**Project:** ARC Studio
**Version:** v0.8-r-ux2 (internal track) / v0.1.0a0 (published)
**Target release date:** internal track only — no external tag set
**Last Updated:** 2026-06-07
**Current evidence anchor:** `aa788f3` | Phase 131 complete (ApprovalCard Gate Hook in TurnManager); Phases 132-156 stubs present.

**Evidence refresh:** Docs refreshed against pushed `main` commit `aa788f3` on 2026-06-07.
Python test suite: **5609 collected**; recent CI baseline reports **5537 passed, 42 skipped, 7 xfailed, 0 failed** (collected count includes xfail markers).
Highest complete phase: **131**.

> ⚠️ **Alpha software.** ARC Studio is a **single-user local workstation tool**. Not production-grade, not multi-tenant, not safe on shared hosts. No tenant isolation.

---

## Shipped feature groups (with phase refs)

| Group | Phases | Status |
|---|---|---|
| 20 runtime adapters (SwarmGraph, LangGraph, CrewAI, AG2, LlamaIndex, pydantic-ai, letta, browser-use, agno, strands, …) | 112-122 | Shipped (gated/offline defaults) |
| Retry + graceful degradation (_call_with_retry, _stream_with_retry, turn.failed, ProviderError.retryable) | 123-125 | Shipped |
| Sandbox P0 hardening (env-filter, secret-strip, path confinement, shell=True removal) | 60-65 range | Shipped |
| MCP control plane (11 tools, 3 resources, per-call risk gate, stdio-only) | 50-59 range | Shipped |
| HMAC audit chain (tamper-evident for single-session local runs; does not protect against a local attacker with write access to ~/.arc/audit/) | 80-90 range | Shipped |
| Token-saving suite (wallet, budget enforcement, compaction, model picker, Chinese-labs support) | 90-115 | Shipped |
| TUI 6 themes (dark/light/mocha/latte/high-contrast/mono) | 126-128 | Shipped |
| 109 providers bundled (OpenAI-compatible, live catalog opt-in) | 100-115 | Shipped |
| SwarmGraph native runtime (queen/worker/consensus lifecycle) | 80-100 | Shipped |
| microVM preflight (gated, default-off, macOS arm64 only) | 104-106 | Shipped (gated/not production-grade) |
| R-UX3 TurnManager gate hook + ApprovalCard hint | 129-131 | Shipped |

---

## Open items

- **R-OPEN-HARDEN router**: Multi-provider router abstraction (R-AUDIT25 / Phase 156) — default-off
- **R79 Theia surfacing**: CLI budget panel in TUI (R-AUDIT17 / Phase 148); IDE panels deferred
- **R-TS1 sdk_version**: Adapter version sweep (R-AUDIT24 / Phase 155) — not yet done
- **R-AUDIT1 through R-AUDIT25**: Full audit synthesis backlog (Phases 132-156) — active sprint

---

## Required to release

Items in this section are gating. If any are unchecked, the release is blocked.

### 1. `pnpm install --frozen-lockfile` passes

**Status:** ✅ Green on `aa788f3`

**Check:**
```bash
pnpm install --frozen-lockfile
# Expect: exit 0, no lockfile changes
```

---

### 2. All build targets succeed

**Status:** ✅ Green on `aa788f3`

**Check:**
```bash
pnpm build
cd python && uv build
# Expect: both exit 0
```

---

### 3. `arc --help` prints and exits 0

**Status:** ✅ Verified on `aa788f3`

**Check:**
```bash
cd python && uv run arc --help
# Expect: help text, exit 0
```

---

### 4. `arc runtimes --capabilities --json` prints honest capability report

**Status:** ✅ Verified on `aa788f3`

Capability wording keeps fake/offline deterministic defaults separate from any opt-in local-real smoke path and does not imply provider-backed execution.

**Check:**
```bash
cd python && uv run arc runtimes --capabilities --json | python -m json.tool
# Expect: JSON with runtimes array. No runtime falsely claims live provider execution.
```

---

### 5. Banned claims checker passes on key docs

**Status:** ✅ Passing on `aa788f3`

**Check:**
```bash
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md AGENTS.md README.md docs/release/checklist.md
# Expect: "OK: No banned claims found."
```

---

### 6. Python test suite passes

**Status:** ✅ Baseline: 5537 passed, 42 skipped, 7 xfailed, 0 failed (collected 5609 on `aa788f3`)

All real-runtime smoke paths are opt-in only (`ARC_REAL_RUNTIME_SMOKE=1`). No provider/paid calls in default suite. microVM execution is gated and default-off. Container sandbox gated behind `ARC_ENABLE_CONTAINER_SANDBOX=1`.

**Check:**
```bash
cd python && uv run pytest -q -p no:cacheprovider
# Expect: 0 failed; xfails and skips documented
```

---

### 7. Canonical extension test suite passes

**Status:** ✅ Passing on `aa788f3`

**Check:**
```bash
pnpm --filter arc-extension test
# Expect: all tests pass
```

---

### 8. Public release docs do not imply implemented SwarmGraph adoption

**Status:** ✅ Passing on `aa788f3`

All adapter adoption paths are fake/offline/gated unless explicitly gated with env vars. `langgraph+swarmgraph` local-real path requires `ARC_REAL_RUNTIME_SMOKE=1 ARC_LANGGRAPH_SWARMGRAPH_REAL=1`.

**Check:**
```bash
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md AGENTS.md README.md
# Exit 0 means no banned claims.
```

---

### 8a. Daemon/doctor parity docs are honest

**Status:** ✅ Baseline documented; deferred surfaces listed in docs/phases.md

Open deferred daemon surfaces: `GET /api/runs/start` (being removed — R-AUDIT14 Phase 145), arena stubs.

**Check:**
```bash
cd python && uv run pytest tests/test_cli_doctor.py -q
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md AGENTS.md README.md
```

---

### 9. `.env` history scrubbed

**Status:** ✅ Complete — scrub executed 2026-05-18 via `ffc1fd1`

---

### 9a. Alpha/single-user/gated labels present

**Status:** ✅ All alpha/single-user/gated/default-off labels preserved

No microVM execution claims beyond proven gated `pwd` proof (macOS arm64 only). Container is gated fallback only. No production-grade claims.

---

## Should be done before release

### 10. Browser app starts and loads ARC widget

**Status:** ✅ Reachability smoke passing on `aa788f3`

**Check:**
```bash
pnpm start:browser:arc 2>&1 &
sleep 30 && curl -s http://127.0.0.1:3000 | grep -q 'arc'
```

---

### 11. All CI workflows green

**Status:** ⏳ Monitor on main; 3-day green-window required before any external tag

Required workflows: `python`, `node`, `ARC Roadmap Gate`. `real-runtime-smoke` is opt-in/non-gating.

---

### 12. No P0/P1 security issues open

**Status:** ✅ Passing on `aa788f3`

**Check:**
```bash
gh issue list --state open --label security
```

---

### 13. README advertises only honest claims

**Status:** ✅ Passing on `aa788f3`

README reviewed: all adapter adoption is described as fake-tested/gated, LM Arena is stub-default, microVM is gated/default-off, all alpha labels preserved.

---

## Appendix: Checklist dry-run procedure

```bash
# Automated subset
echo "=== Banned claims ==="
bash scripts/check-banned-claims.sh docs/roadmap.md docs/phases.md AGENTS.md README.md docs/release/checklist.md

echo "=== Python tests ==="
cd python && uv run pytest -q -p no:cacheprovider 2>&1 | tail -3

echo "=== Extension tests ==="
pnpm --filter arc-extension test 2>&1 | tail -3
```
