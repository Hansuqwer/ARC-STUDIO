# Prompt — Recommend and Execute Next Phase

## Method

1. Read `docs/roadmap.md` (open R-items) and `docs/phases.md` (highest phase number).
2. Read `git log --oneline -10` to see what just landed.
3. For the top candidate, do **grounded research** before committing to it:
   - **context7**: resolve library ID → query docs for verified API signatures.
   - **vercel grep / searchGitHub**: find real usage patterns in production codebases.
   - Confirm the API is stable and the adapter/feature is implementable offline (no live API calls in tests).
4. Write a one-page `docs/research/<feature>-plan.md` with verified facts.
5. Implement — follow the established adapter pattern or feature slice pattern.
6. Add roadmap row + phase entry. Banned-claims gate. Commit/push on green CI.

## Selection criteria (in order)

1. **Highest leverage** — closes a real gap, not just adds another "nice to have".
2. **Verifiable offline** — all tests must run without real API keys.
3. **Bounded** — completable in one session slice, not a multi-week track.
4. **Grounded** — do NOT start implementing until the API is verified (context7 / grep).

## Current open backlog (as of Phase 117)

- **AG-UI gap sweep** — 18 adapters, verify which ones are missing AG-UI mapping
  registration; fix the real gaps. Bounded verification sweep.
- **Browser Use adapter** — 97K stars, `from browser_use import Agent; await agent.run(task)`.
  Requires research first (async API, sandbox implications).
- **Agno (ex-Phidata) adapter** — `agent.run(prompt)` pattern, growing fast.
- **R-OPEN-HARDEN** — provider failure-injection, retry/backoff durability tests.
- **CLI parity (R68-R76)** — large track, needs a research sprint first to scope gaps.

## Honest constraint

Do not claim "production-grade", "multi-user", "tenant-isolated", or fabricate
benchmark numbers. Keep gated/default-off/mock labeling. Evidence over claims.
