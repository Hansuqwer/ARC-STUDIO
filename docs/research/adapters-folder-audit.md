# Audit — `WorkSpace/ARC/adapters/` Research Folder

> **Status:** Executed 2026-06-06. Read-only audit of an out-of-tree research
> folder, reconciled against the live `arc-theia-studio` repo.
> **Prompt:** `docs/prompts/adapters-folder-audit.md`
> **Method:** verify-don't-trust — every load-bearing claim checked with a
> command against the live repo. The external folder was not modified.

---

## §1 — Folder inventory

`/Users/hansvilund/HansuQWER/WorkSpace/ARC/adapters/` contains three distinct
kinds of content:

| Kind | Item | Note |
|---|---|---|
| **Duplicate checkout** | `adapters/arc-theia-studio/` | A full second checkout. Its `docs/roadmap.md` (≈153 KB) and `docs/phases.md` (≈313 KB) are **stale** vs the canonical repo — treat as historical only. |
| **Research docs** | `arc-studio-adapter-deep-analysis.md` (34 KB) | Adapter-by-adapter audit + a 5-sprint "make all adapters fully working" plan. |
| | `arc-studio-next-steps-research.md` (12 KB) | New-runtime candidates (Strands, Letta, Browser Use) + duplication/AG-UI/audit-gap claims. |
| | `sprint1/2/3-research-findings.md` | SDK API specs (sprint3 = Pydantic AI / Google ADK / LlamaIndex signatures). |
| | `sprint1/2/sprint-next-research-prompt.md` | The prompts that generated the findings. |
| | `cross-platform-mobile-alternatives-2026.md` (50 KB) | KMP / Flutter / RN / Skip research — informs **R79 Mobile Runtime SDK**, NOT the adapter system. |
| **Tool caches** | `.dspy_cache/`, `.haystack/`, `.local/share/crewai` | Disposable; ignore. |

---

## §2 — Verified-claims reconciliation (adapter system)

Each claim from the research docs, checked against the live repo:

| Claim (research) | Status | Evidence |
|---|---|---|
| "14/17 adapters" registered | **STALE (now 15)** | `grep -c "self.register(" adapters/registry.py` → 15 (14 original + `arc-runtime-sdk` added 2026-06-06). |
| Pydantic AI is a 🔴 stub with a placeholder runner | **VERIFIED** | `adapters/pydantic_ai/` exists (detect/export/runner) but is **not** in `build_default()`; `runner.py:173` still reads `# In production, this would use agent.run() …`. |
| No `adapters/_shared.py` (Sprint 6 consolidation still open) | **VERIFIED** | `ls adapters/_shared.py` → absent. The shared-helper recommendation is still actionable. |
| "20+ `_workspace_import_path`, 22 `_make_event`, 16 `_load_export_target`" (60+ duplicated helpers) | **OVERSTATED ~7×** | `grep -rhoE "def _(workspace_import_path\|make_event\|load_export_target\|event\|redact)"` across `adapters/` → **4 `_event` + 2 `_workspace_import_path` + 2 `_redact` = ~8 copies**. Duplication is real but far smaller; the research likely counted the duplicate checkout and the bundled SDK packages too. |
| Adapter maturity tiers (swarmgraph full; langgraph/crewai/openai-agents partial; langchain/dspy/haystack/smolagents/google_adk/mcp_sdk/semantic_kernel scaffold/detect-only; ag2/llamaindex/lmarena stub) | **BROADLY VERIFIED** | Matches the package layout under `adapters/` and `build_default()` registration. |
| sprint3 SDK API specs (Pydantic AI `agent.run_sync`/`TestModel`; Google ADK 2.0 `Runner.run_async`; LlamaIndex `Workflow.run`) | **EXTERNAL-SOURCED, plausible** | Not re-verified against installed SDKs (not present in the env). Useful as an implementation reference; label "unverified against installed SDK" until exercised. |

---

## §3 — Still actionable (survived verification)

1. **`adapters/_shared.py` consolidation** — real, but scoped to ~8 helper
   copies (`_event` ×4, `_workspace_import_path` ×2, `_redact` ×2), not the
   60+ the research implied. A focused extraction is a clean, bounded slice.
2. **Pydantic AI runner is still a placeholder** — `runner.py:173` does not call
   `agent.run()`. Either implement the real call (sprint3 has the v1.106 API:
   `agent.run_sync(prompt, deps=…)` + `TestModel` for offline tests) or mark the
   adapter honestly and leave it unregistered. It is currently **not** in
   `build_default()`, so it is not falsely advertised.
3. **New-runtime candidates** — Strands Agents (AWS), Letta (MemGPT),
   Browser Use are reasonable Tier-1/2 additions; each is its own adapter sprint.
4. **AG-UI / audit-chain gaps** — the research lists adapters missing AG-UI
   mappings and audit-chain wiring; these are individually verifiable before any
   sprint and should be re-checked per-adapter at implementation time (not taken
   on faith from the doc).

## §4 — Discard / down-weight

- The **60+ duplicated-helper** figure — overstated ~7×; do not size a sprint
  around it.
- The **duplicate `adapters/arc-theia-studio/` checkout** — stale; its roadmap/
  phases must not be merged into the canonical docs.
- **"17 adapters"** framing — the registry wires 15; pydantic_ai is intentionally
  unregistered. Use the registry count, not the package count.

## §5 — Relationship to existing roadmap

- Adapter-system findings extend the existing adapter work (the
  `ArcRuntimeSDKAdapter` slices, R79/Phase 111) but are **not** a new product
  track — they are a backlog of per-adapter completion + one consolidation slice.
- The mobile cross-platform doc informs **R79 Mobile Runtime SDK** (KMP/Flutter/
  RN comparison), already tracked; it is not adapter-system work.

## §6 — Deliverables from this audit

- This findings doc.
- Reusable prompt: `docs/prompts/adapters-folder-audit.md`.
- Roadmap item + phase entry (see `docs/roadmap.md` / `docs/phases.md`).
- No change to the external folder; no new competing roadmap.
