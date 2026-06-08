import * as fs from 'fs';
import * as path from 'path';
import { RISK_VARIANT, riskBadgeVariant } from '../tabs/mcp-risk';

describe('MCP Workbench risk badge a11y (R-AUDIT26)', () => {
    it('maps every risk level to a distinct badge variant', () => {
        const variants = Object.values(RISK_VARIANT);
        expect(new Set(variants).size).toBe(variants.length);
    });

    it('renders critical distinctly from high (not the same variant)', () => {
        expect(RISK_VARIANT.critical).not.toEqual(RISK_VARIANT.high);
    });

    it('falls back to a neutral variant for an unknown score', () => {
        expect(riskBadgeVariant('bogus')).toBe('ok');
        expect(riskBadgeVariant('critical')).toBe('risk-critical');
    });

    it('has a CSS rule for every risk variant', () => {
        const css = fs.readFileSync(
            path.join(__dirname, '../style/arc-studio-widget.css'),
            'utf8',
        );
        for (const variant of Object.values(RISK_VARIANT)) {
            expect(css).toContain(`.arc-mcp-workbench__badge--${variant}`);
        }
    });

    it('labels the risk badge for screen readers (not color-only)', () => {
        const tsx = fs.readFileSync(
            path.join(__dirname, '../tabs/McpWorkbenchTab.tsx'),
            'utf8',
        );
        expect(tsx).toMatch(/aria-label=\{`risk level \$\{d\.riskScore\}`\}/);
    });
});
