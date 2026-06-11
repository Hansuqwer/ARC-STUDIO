# G7 golden reference — bidi + ligature shaping sample

Every candidate's `Action::TakeScreenshot` renders exactly this content
(`sample.txt`, UTF-8, byte-for-byte) in a 800x600 logical-pixel view,
14px monospace-preferred font stack, LTR paragraph context, no soft wrap.

Compare rule: the FIRST screenshot taken per OS becomes that OS's reference;
other candidates diff against it. Cross-candidate font-fallback differences
are FINDINGS (recorded in the report notes), not automatic failures — the
gate checks shaping correctness, specifically:

1. Line B renders RTL runs right-to-left with correct bracket mirroring.
2. Line C mixes LTR identifiers inside an RTL sentence without reordering
   the identifier's characters.
3. Line D: programming ligatures (=> != >= ->) either shape as ligatures or
   render as plain pairs — but NEVER as tofu/missing glyphs; whichever the
   candidate does must be consistent across the whole line.
4. Line E: combining marks stack on the base (no detached diacritics).
5. No tofu (U+FFFD / empty boxes) anywhere except line F's intentional
   PUA probe, which MAY be tofu — it tests fallback honesty, and a candidate
   silently substituting a wrong glyph there is a failure.

Pass = screenshot satisfies 1-5 under eyeball + zoom; the comparison note
and image path go into the report's G7 row. Automated pixel-diff is NOT
required at spike stage (font stacks differ per OS by design).
