# G8 Sustainability Evidence — desk research (hardware-free)

Prepared 2026-06-11 by Arena agent. Sources: deep-research review §4
(web-checked 2026-06-11, citations there) + local-CLI preflight pins.
G8 is a scored evidence row feeding the ADR-0002 addendum decision rule
(tie-break #2 after facade cost). It never auto-passes/fails; a candidate
with "unbounded" vendoring cost cannot win a tie.

Operator action: paste each block into the candidate's
`reports/spike-<candidate>.json` G8 row (`notes` + flip EvidencePending →
Pass with this file's path in `raw_data_path`). Re-verify cadence numbers
the week of the decision — this table ages.

## gpui @ 0.2.2 (crates.io)

| Criterion | Evidence | Score (1-5, 5 best) |
|---|---|---|
| (a) Cadence trailing 12mo | Published to crates.io ~Oct 2025; upstream (Zed) publicly deprioritized non-Zed GPUI work for 2026 (Dec 2025 statement). Releases driven by Zed's internal needs. | 2 |
| (b) Bus factor / governance | Zed Industries; single-vendor; roadmap explicitly not outsider-driven. Docs thin ("read the source" per community). | 2 |
| (c) Breaking-change rate vs pin | Pre-1.0; API tracks Zed internals; no stability commitment to external users. | 2 |
| (d) Vendoring cost if stalled | High but bounded: large surface (platform layers for Metal/DX/Vulkan via blade), but gpui-ce exists as the de-facto vendor path — cost ≈ adopting gpui-ce. | 3 |

## gpui-ce @ c237d57d (github fork)

| Criterion | Evidence | Score |
|---|---|---|
| (a) Cadence | Fork created Dec 2025 by former Zed employee #1; one current Zed engineer co-maintains off-hours ("not sure how much I'll be able to commit"). <6mo of independent history at pin time. | 2 |
| (b) Bus factor | 2 named maintainers, both part-time; community interest measured in stars, not merged PRs yet. Governance unformed. | 2 |
| (c) Breakage vs pin | Inherits gpui pre-1.0 churn PLUS fork divergence risk from upstream Zed. | 2 |
| (d) Vendoring cost | This IS the vendor path — adopting it = accepting maintenance exposure directly. Bounded only if ARC is willing to become a co-maintainer. | 2 |

## floem @ 0.2.0 (crates.io)

| Criterion | Evidence | Score |
|---|---|---|
| (a) Cadence | Active: repo updated Feb 2026; steady release history on crates.io; drives Lapce (shipping editor). | 4 |
| (b) Bus factor | Lapce team; >1 maintainer; MIT; ~4k stars; self-declared "occasional breaking changes on the way to v1". | 3 |
| (c) Breakage vs pin | Pre-1.0, honest about it; changes documented; smaller API surface than gpui. | 3 |
| (d) Vendoring cost | Moderate: pure-Rust, wgpu+tiny-skia fallback renderer, no platform-blade layer to maintain. One-sprint vendor estimate plausible. | 4 |

## bespoke (winit 0.31.0-beta.2 + vello 0.9.0 + parley 0.10.0 + accesskit_winit 0.33.0 [+ masonry 0.4.0])

| Criterion | Evidence | Score |
|---|---|---|
| (a) Cadence | Linebender stack: monthly public updates; Vello 0.8→0.9 and Parley releases through Q1-2026; winit on a 0.31 beta (note: beta pin must move to stable before any non-spike use). | 4 |
| (b) Bus factor | Multi-org governance (Linebender: Google Fonts collaboration, Canva engineers on Vello hybrid); broadest contributor base of the four. | 4 |
| (c) Breakage vs pin | Each crate evolves independently — integration churn is OURS to absorb; Masonry layout/IME APIs moved substantially in Q1-2026. | 2 |
| (d) Vendoring cost | Lowest per-crate (each is small and replaceable), but ARC owns the integration glue forever — the "vendor cost" is permanent first-party code, not a fork. | 3 |

## Summary row (paste into decision matrix §G8)

| | gpui | gpui-ce | floem | bespoke |
|---|---|---|---|---|
| G8 total (max 20) | 9 | 8 | **14** | 13 |
| One-line risk | upstream attention withdrawn | youngest fork, part-time maintainers | healthiest single dependency | healthiest ecosystem, integration is ours |

**Not a selection.** G8 is tie-break #2; facade cost (measured during the
macOS spike by porting the Sprint-2 ShellModel render) ranks first. A gpui
variant that wins decisively on facade cost + G1-G4 + a11y/IME can still win
overall — G8 then mandates the mitigation plan (vendoring budget reserved,
kill criterion R1 armed) in the selection memo.
