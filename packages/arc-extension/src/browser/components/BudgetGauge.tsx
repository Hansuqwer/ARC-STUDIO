import * as React from '@theia/core/shared/react';
import { BudgetVector } from '../../common/arc-protocol';

export interface BudgetGaugeProps {
    usage?: BudgetVector;
    limit?: BudgetVector;
}

export const BudgetGauge: React.FC<BudgetGaugeProps> = ({ usage, limit }) => {
    const renderGauge = (label: string, used?: number | null, max?: number | null, format?: (v: number) => string) => {
        if (used === undefined || used === null || max === undefined || max === null) {
            return (
                <div className="arc-budget-item">
                    <span className="arc-budget-label"><strong>{label}:</strong></span>
                    <span className="arc-budget-value degraded" style={{ marginLeft: '8px', color: '#888' }}>Degraded/Absent</span>
                </div>
            );
        }
        
        const pct = max > 0 ? Math.min(100, Math.max(0, (used / max) * 100)) : 0;
        const formattedUsed = format ? format(used) : used.toString();
        const formattedMax = format ? format(max) : max.toString();
        
        return (
            <div className="arc-budget-item" style={{ marginBottom: '8px' }}>
                <div className="arc-budget-item-header" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span className="arc-budget-label"><strong>{label}</strong></span>
                    <span className="arc-budget-value">{formattedUsed} / {formattedMax}</span>
                </div>
                <div className="arc-budget-track" style={{ width: '100%', backgroundColor: 'var(--theia-editorWidget-background, #333)', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                    <div className="arc-budget-fill" style={{ width: `${pct}%`, backgroundColor: pct > 90 ? 'var(--theia-errorForeground, red)' : pct > 75 ? 'var(--theia-list-warningForeground, orange)' : 'var(--theia-testing-iconPassed, green)', height: '100%' }} />
                </div>
            </div>
        );
    };

    const formatCost = (v: number) => `$${v.toFixed(2)}`;
    const formatLatency = (v: number) => `${v}ms`;

    return (
        <div className="arc-budget-gauges" role="region" aria-label="Budget Gauges">
            {renderGauge('Tokens', usage?.tokens, limit?.tokens)}
            {renderGauge('Cost', usage?.cost_usd, limit?.cost_usd, formatCost)}
            {renderGauge('Latency', usage?.latency_ms, limit?.latency_ms, formatLatency)}
        </div>
    );
};
