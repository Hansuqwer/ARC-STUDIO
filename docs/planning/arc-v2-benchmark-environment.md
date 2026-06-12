# arc-v2 Benchmark Environment (pinned)

Decision 4 of the provisional-ranking memo (2026-06-12, owner-delegated):
the M4 is the pinned benchmark machine. This file is the §Environment record
the planning package's benchmark plan called for (the tarball's
arc-v2-benchmark-plan.md was never extracted into docs/planning/; this
additive file serves as that section until/unless the full plan lands).

## Pinned machine (primary — all binding numbers)

| Field | Value (from reports/sprint3-local-preflight.json) |
|---|---|
| Hostname | BLUETEAM.local |
| Model | MacBook Air Mac16,12 |
| CPU / GPU | Apple M4 / Apple M4 8-core, Metal 4 |
| Memory | 16 GB |
| Display | 2940x1912 physical, 1470x956 logical @ 60.00 Hz |
| OS | macOS (Darwin 25.x line) |
| Toolchain | rust 1.96.0 (Homebrew), Xcode 26.5 + Metal Toolchain |
| Power profile | mains preferred; record battery state in report notes |

Rules:
- Reports from this machine set `is_pinned_benchmark_machine: true` from now
  on; the three committed spike reports (floem/gpui/gpui-ce) predate the pin
  but are retroactively binding for macOS rows per the owner decision.
- Numbers from any other machine (incl. this sandbox, CI runners) remain
  indicative-only and say so.
- 60 Hz display ⇒ vsync period 16,667 µs; the G2/G4 bar on this machine is
  the R1 form: **p99 ≤ 1.1 frames AND frames>2vsync = 0%**.

## Secondary environment (Linux rows — pending physical session)

Owner's Linux machine; identity recorded here when the session happens.
Until then Linux rows carry compile/container evidence only.

## Windows

No hardware recorded. Windows rows stay EvidencePending; any selection memo
must state Windows support is unverified (os-sequencing doc governs).
