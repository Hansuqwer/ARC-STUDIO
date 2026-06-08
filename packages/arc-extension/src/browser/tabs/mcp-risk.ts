/**
 * MCP risk-level → badge variant mapping (R-AUDIT26).
 *
 * Each risk level maps to a VISUALLY DISTINCT badge variant so `critical` is never
 * indistinguishable from `high` (WCAG 1.4.1 — do not convey meaning by color alone;
 * the badge also carries a text label + aria-label). Pure module (no React) so it is
 * unit-testable without a render harness.
 */
export const RISK_VARIANT: Record<string, string> = {
    low: 'risk-low',
    medium: 'risk-medium',
    high: 'risk-high',
    critical: 'risk-critical',
};

/** Resolve a risk score to its badge variant, falling back to a neutral `ok`. */
export function riskBadgeVariant(score: string): string {
    return RISK_VARIANT[score] ?? 'ok';
}
