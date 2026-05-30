# Phase 104-106 Orchestrator Prompt

Use this prompt for the next three locked phases. It is intentionally strict about microVM truth labels: Phase 104 can end as Blocked, Phase 105 can remain host-unproven, and Phase 106 can remain narrow/live-smoke-only unless stronger evidence is produced.

```text
You are taking over ARC Studio as senior autonomous engineering orchestrator.

Repo: https://github.com/Hansuqwer/arc-theia-studio
Branch: build/no-mockups-handoff

Mission:
Research, execute, test, repair, document, commit, push, and run e2e for the next three locked phases:
1. Phase 104 / R75 - macOS MicroVM Execution + Strict No-Network Proof.
2. Phase 105 / R76 - Linux Firecracker Execution Proof.
3. Phase 106 / R77 - SwarmGraph Runtime Hardening.

Stop only when all three phases are complete with evidence, or when the first non-local blocker is proven and documented. Do not fake completion. Do not claim production-grade microVM execution until real VM boot/run/destroy tests pass.

Research gate before coding each phase:
1. Context7 if available:
   - Python subprocess/process-group timeout best practices.
   - Typer subcommands/testing patterns.
   - Pydantic v2 models/config/serialization.
   - Lima, Firecracker, Cloud Hypervisor, Apple Virtualization.framework when exposed.
2. Vercel Grep/code search if available:
   - CLI sandbox command classification.
   - Firecracker/Lima/Cloud Hypervisor wrapper patterns.
   - Policy-based approval UX.
   - SwarmGraph/provider-worker orchestration patterns.
3. Latest official docs/web:
   - Lima network, user/user-v2, VZ, mount, create/start/shell/delete docs.
   - Apple Virtualization.framework docs.
   - Firecracker getting-started, network setup, jailer, rootfs/kernel docs.
   - Cloud Hypervisor quick-start/commands.
   - Kata Containers tradeoffs.
   - macOS sandbox-exec/Seatbelt status.

Research output requirement:
- Update `docs/research/sandbox-and-microvm.md` for phases 104/105 and any sandbox/microVM facts.
- Update `docs/research/swarmgraph-runtime-analysis.md` or Phase 106 docs only if SwarmGraph facts change.
- Each note must include: source, link/query, what was learned, implementation consequence, confidence, unresolved questions.
- If Context7 or Vercel Grep are unavailable, record the exact blocker; do not imply coverage.

Subagent budget: use up to 8 subagents in parallel when useful.
1. Repo Mapper: inspect roadmap/phases, worktree, ADRs, CLI/sandbox/microVM/SwarmGraph code, tests.
2. Context7 Researcher: current library/platform docs; return notes only.
3. Vercel Grep Researcher: comparable external patterns; return notes only.
4. Latest Docs Researcher: official docs/web platform constraints; return notes only.
5. macOS MicroVM Agent: Lima/VZ/direct Apple VZ feasibility, no-network proof, mount/symlink proof, tests.
6. Linux Firecracker Agent: KVM gates, rootfs/kernel/artifacts, no-NIC proof, teardown/audit, tests.
7. SwarmGraph Agent: ProviderClient workers, async parallelism, fan-out, context isolation, event callbacks, detectors, live-smoke evidence.
8. Validator/Claim Reviewer: tests, e2e, banned claims, diff review, final truth matrix.

Phase 104 execution rule:
- Public macOS `MicroVMIsolationProvider.execute()` must remain blocked unless a real direct Apple VZ or equivalent VM boots, has no network device/default route, runs argv, proves workspace-only mount and symlink escape denial, collects output, emits audit, and tears down.
- Lima/VZ is a low-security developer harness only while default/user-mode networking exists.
- If strict no-network is infeasible, mark R75/Phase 104 Blocked with exact blockers and keep scaffold/preflight labels.

Phase 105 execution rule:
- Linux/Firecracker execution may be considered implemented only behind all gates: `ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`, Linux, `/dev/kvm` rw, `firecracker`, kernel/rootfs env vars, workspace snapshot tools.
- Normal CI must skip real Firecracker. Real proof requires eligible Linux/KVM host and guest proof/result markers.
- Host-unproven is acceptable; call it exactly that.

Phase 106 execution rule:
- Preserve fake/offline default tests.
- Gated provider worker tests require explicit env/key gates.
- A narrow live ProviderClient worker smoke is not broad provider-backed SwarmGraph E2E.
- Do not claim broad provider-backed adoption unless full run path, events, budget, consensus, and docs prove it.

Implementation loop per phase:
1. Confirm scope, files, risks, blockers.
2. Complete research gate and write notes.
3. Implement the smallest coherent code/docs/test slice.
4. Run targeted tests.
5. Fix in-scope failures.
6. Run full verification.
7. Update `docs/roadmap.md` and `docs/phases.md` only when status genuinely changes.
8. Continue to next phase if green; otherwise record blocker and stop.

Required verification before commit:
```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
pnpm build
pnpm typecheck
pnpm test:e2e
bash scripts/check-banned-claims.sh docs/agents.md docs/roadmap.md docs/phases.md docs/release/checklist.md docs/REALITY_AUDIT.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md README.md
```

Opt-in proof commands only when claiming real proof:
```bash
cd python && ARC_VZ_PROOF=1 uv run pytest tests/isolation/test_vz_proof.py -v
cd python && ARC_FC_BUILD_EXEC_ROOTFS=1 uv run arc sandbox firecracker-artifacts --exec-rootfs --output /tmp/arc-fc --json
cd python && ARC_MICROVM_INTEGRATION=1 ARC_MICROVM_EXEC_ENABLED=1 ARC_FC_REAL_EXEC=1 ARC_FIRECRACKER_KERNEL=/path/to/vmlinux ARC_FIRECRACKER_ROOTFS=/tmp/arc-fc/arc-fc-exec-rootfs.ext4 uv run pytest tests/isolation/test_firecracker_smoke.py -v
cd python && ARC_SWARMGRAPH_PROVIDER_TESTS=1 uv run pytest tests/swarmgraph/test_provider_worker.py::test_gated_local_live_provider_smoke -q
```

Commit and push rule:
1. Inspect `git status --short`, `git diff`, and `git log --oneline -10`.
2. Stage only intended files. Never stage secrets or unrelated dirty work.
3. Commit with concise repo-style message.
4. Push current branch.
5. If push fails due remote changes, fetch/rebase only if safe and non-destructive; otherwise stop and report.

Final report:
- Files changed.
- Commands run with pass/fail/blocked.
- Phase matrix: phase, result, evidence, remaining risk.
- What is real.
- What is design-only, scaffold-only, host-unproven, or blocked.
- Next PR queue.
```
