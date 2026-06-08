/**
 * ARC hardcoded color-contrast guard (Tier-2 L-G2)
 *
 * Complements the layout-capable L-G1 Playwright scan. ARC's stylesheets mostly delegate color to
 * Theia/ARC theme tokens (the active theme manages contrast), but a few rules use **hardcoded**
 * fg/bg pairs (alerts, the primary button). Those are theme-independent, so their WCAG 2.1 contrast
 * ratio can be computed deterministically here — and asserted to meet AA. A guard also fails if a
 * NEW bare-hex `color:` value is introduced without being audited, so contrast can't silently regress.
 */

import * as fs from 'fs';
import * as path from 'path';

const STYLE_DIR = path.join(__dirname, '..', 'style');

function relLum(hex: string): number {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16) / 255);
  const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function wcagRatio(fg: string, bg: string): number {
  const a = relLum(fg) + 0.05;
  const b = relLum(bg) + 0.05;
  return Math.round((Math.max(a, b) / Math.min(a, b)) * 100) / 100;
}

// ARC's hardcoded fg/bg pairs (extracted from arc-widget.css / arc-studio-widget.css). These are
// theme-independent, so they must meet WCAG AA (4.5:1 normal text) on their own.
const AUDITED_PAIRS: Array<{ name: string; fg: string; bg: string }> = [
  { name: 'alert-warning', fg: '#856404', bg: '#fff3cd' },
  { name: 'alert-success', fg: '#155724', bg: '#d4edda' },
  { name: 'alert-error', fg: '#721c24', bg: '#f8d7da' },
  { name: 'alert-error-on-tint', fg: '#721c24', bg: '#fff5f5' },
  { name: 'primary-button', fg: '#ffffff', bg: '#0052a3' },
];

// Bare-hex `color:` values allowed in ARC CSS (each must appear in an AA-passing audited pair above,
// or be white used only on an audited dark background). Update deliberately when adding a color.
const ALLOWED_BARE_TEXT_COLORS = new Set(['#fff', '#ffffff', '#856404', '#155724', '#721c24']);

describe('ARC hardcoded color-contrast guard (L-G2)', () => {
  it('every hardcoded ARC fg/bg pair meets WCAG AA (4.5:1)', () => {
    for (const { name, fg, bg } of AUDITED_PAIRS) {
      expect({ name, ratio: wcagRatio(fg, bg) }).toEqual({
        name,
        ratio: expect.any(Number),
      });
      expect(wcagRatio(fg, bg)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it('no un-audited bare-hex text color is introduced in ARC CSS', () => {
    const cssFiles = fs.readdirSync(STYLE_DIR).filter((f) => f.endsWith('.css'));
    const found = new Set<string>();
    for (const f of cssFiles) {
      const src = fs.readFileSync(path.join(STYLE_DIR, f), 'utf-8');
      for (const m of src.matchAll(/(?:^|\s)color:\s*(#[0-9a-fA-F]{3,8})\s*;/g)) {
        found.add(m[1].toLowerCase());
      }
    }
    const unaudited = [...found].filter((c) => !ALLOWED_BARE_TEXT_COLORS.has(c));
    expect(unaudited).toEqual([]); // add to an AUDITED_PAIR (and verify AA) before allowing
  });
});
