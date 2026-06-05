# AGENTS.md — ARC Studio Agent Charter

🔒 **LOCKED CHARTER.** This is the single source of governance for agents working on ARC Studio.

## Single sources of truth

There is exactly **one** of each. Do not create competing or replacement copies.

| Concern | Canonical file |
|---|---|
| Roadmap | `docs/roadmap.md` |
| Phase list / execution plan | `docs/phases.md` |
| Agent charter | `AGENTS.md` (this file) |

Both `docs/roadmap.md` and `docs/phases.md` are CI-protected (`scripts/release_check.sh`). Update them **in place**. Never add a new roadmap/phase/status markdown — everything else is archived under `docs/archive/`.

## Working discipline

1. **Finish 1 → 100% before broadening.** Complete the active phase end to end — with tests and evidence — before starting any new phase, feature, or roadmap item. No new top-level scope while the active phase is incomplete.
2. **Single source.** All roadmap/phase/status updates go into the two canonical docs above.
3. **Evidence over claims.** State what was actually run/verified. Do not claim tests pass unless they were run.
4. **Additive protocol only.** Do not remove or rename existing events, CLI commands, or public API surfaces unless explicitly proposing a breaking change for a future major.
5. **Deterministic security.** Sandbox, trust, policy, budget, audit, and capability decisions are deterministic. No LLM-based security judgement.
6. **Immutable `EnforcementContext`.** Route new runtime state through immutable copies / `ContextVar`, never by mutating the frozen context.
7. **No commits unless asked.** Leave changes in the working tree for review unless the owner explicitly requests a commit.

## Active track (2026-06-05, `spec/v0.8-r-ux2` @ `ffa1e1f`)

P0 hardening sprint from the five-way audit, in order:

1. SQLite `database is locked` in budget storage (confirmed failing test).
2. TUI shell-escape completion (remove `shell=True`, fail-closed gate, audit on allow).
3. Quarantine orphan `python/src/routes.py` (`0.0.0.0` FastAPI).
4. `/api/runs/start` POST-only (deprecate mutating GET).
5. Refresh `docs/security/enforcement-surfaces.md` (stale paths).
6. Reconcile `security/profiles.py` schema version (1 vs 2).

Then resume the v0.8 R-UX2 track. See `docs/phases.md` for full status.

## Sandbox / microVM truth constraints (still in force)

- **No microVM execution claims** beyond what is proven. macOS direct VZ is a gated public CLI proof passed once for guest-available `pwd` (default-off, not production-grade). Linux/Firecracker is preflight/baseline only, host-unproven (Linux/KVM only). Windows is out of scope.
- **Container is a gated fallback only** — disabled unless `ARC_ENABLE_CONTAINER_SANDBOX=1`.
- **Do not remove** existing alpha/mock/fallback labeling.
- Allowed wording: "production-ready foundation", "microVM preflight/doctor support", "container fallback (gated)". Forbidden until proven: "production-grade microVM execution", "production-ready sandbox", broad "VZ command runner".

## Verification commands

```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
pnpm typecheck && pnpm build
```

Document failures honestly; do not hide them.
