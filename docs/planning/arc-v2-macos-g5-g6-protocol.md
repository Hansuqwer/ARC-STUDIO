# macOS G5/G6 Evidence Protocol (spike round 1 — execute per candidate)

Companion to `arc-v2-sprint-3-os-sequencing.md` (which holds the Linux/Windows
checklists). This is the detailed macOS script: follow it verbatim so all four
candidates produce comparable evidence. Evidence = screen recordings
(QuickTime, .mov, named as specified) or Accessibility-Inspector dumps; file
paths go into the report's G5/G6 `raw_data_path`/`notes`. An outcome without
paths stays EvidencePending — the matrix enforces this.

Setup once per machine:
- System Settings → Accessibility → VoiceOver off by default (toggle per test).
- Input Sources: add "Japanese — Romaji" (Hiragana), "Pinyin — Simplified",
  "2-Set Korean", and "ABC" (for dead-keys via Option-key combos).
- Recording: QuickTime → New Screen Recording → capture the spike window +
  enable "Show Mouse Clicks"; system audio not required (VO captions appear
  in the VO caption panel — enable VoiceOver → Utility → Caption Panel).

## G5 — VoiceOver (per candidate, ~10 min)

File: `reports/evidence/g5-<candidate>-macos-voiceover.mov`

| # | Step | Pass looks like |
|---|---|---|
| 1 | Launch spike binary in windowed mode; VO on (Cmd-F5) | VO announces window title containing the candidate name |
| 2 | VO-navigate (Ctrl-Opt-Arrow) across the four views: text, diff, event table, bidi sample | Each view announced with a role (text area/table/group) and a label — NOT "unknown" or silence |
| 3 | Focus the event table after ≥1 AppendRows | Row content readable via VO cursor; row count or position announced |
| 4 | Focus the type box; type "abc" with VO on | Characters echoed by VO as typed |
| 5 | Quit via keyboard only (Cmd-Q) | No VO crash, no orphaned VO focus |

Record per candidate in the report notes: which steps passed (1–5), VO
behaviors that were degraded-but-present vs absent. **A candidate with zero
accessibility tree (VO sees one opaque surface) is a G5 FAIL on macOS**, not
pending — note it explicitly. (Known risk: GPU-painted UIs without an
AccessKit/NSAccessibility bridge typically fail step 2; that is exactly what
this gate exists to surface. Do not soften the finding.)

## G6 — IME (per candidate, ~15 min)

File: `reports/evidence/g6-<candidate>-macos-ime.mov`

Target: the TypeBox view (the G4 single-line editor), spike binary idle
(script finished or paused) — IME testing is manual, not scripted.

### JA (Hiragana → Kanji)
1. Switch to Japanese input (Ctrl-Space / Fn-E as configured).
2. Type `nihongo` → expect inline composition `にほんご` WITH underline,
   composition text rendered IN the type box at the cursor (not in a
   floating fallback window).
3. Space → candidate window appears anchored at/near the composition.
4. Return → commits `日本語`; composition underline gone; committed text
   present in the box.
5. Type `kyou` then Escape → composition CANCELLED, box returns to
   pre-composition content (cancel path is the one frameworks get wrong).

### ZH (Pinyin)
1. Type `nihao` → inline composition; digit selection `1` commits `你好`.
2. Half-committed state: type `zhongwen`, commit only the first candidate
   syllable if the IME segments — note whether segmentation display works.

### KO (2-Set)
1. Type `gksrnrdj` (한국어) — Hangul composes syllable-by-syllable; each
   jamo updates the current syllable IN PLACE (no append-then-fix flicker).
2. Backspace mid-syllable → decomposes jamo-wise, not whole-syllable.

### Dead keys (ABC layout)
1. Option-e then `e` → `é`; Option-u then `o` → `ö`; Option-n then `n` → `ñ`.
2. Option-e then Space → standalone `´`.

Per script, record: inline composition yes/no, candidate window anchoring
sane yes/no, commit correct yes/no, cancel correct yes/no. Any "composition
appears in a separate floating input window" = degraded, report it as such
(it usually means the framework lacks NSTextInputClient integration — a
material finding, G8-adjacent).

## Filing the evidence

```
reports/evidence/
  g5-gpui-macos-voiceover.mov
  g6-gpui-macos-ime.mov
  …per candidate
```

Then in `reports/spike-<candidate>.json`: G5/G6 rows get `raw_data_path` =
the .mov path(s) and `notes` = the per-step pass/degraded/fail table in one
line each. Leave outcome mechanics to the matrix rules: paths present + all
steps passed → operator flips to Pass; any step failed → Fail with the step
number; recordings missing → stays EvidencePending.
