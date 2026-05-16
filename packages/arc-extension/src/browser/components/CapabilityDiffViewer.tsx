/**
 * CapabilityDiffViewer — shows added/removed capabilities on runtime switch.
 *
 * Renders a diff view when the user is considering switching runtimes.
 * If trust boundary widens, requires explicit confirmation.
 * Unknown/degraded capabilities are rendered honestly.
 */
import * as React from 'react';
import { CapabilityDiffResponse } from '../../common/arc-protocol';

export interface CapabilityDiffViewerProps {
    diffResponse: CapabilityDiffResponse | null;
    loading?: boolean;
    error?: string;
    onConfirm?: () => void;
    onCancel?: () => void;
    onCompare?: (from: string, to: string) => void;
    availableRuntimes: string[];
}

export const CapabilityDiffViewer: React.FC<CapabilityDiffViewerProps> = ({
    diffResponse,
    loading = false,
    error,
    onConfirm,
    onCancel,
    onCompare,
    availableRuntimes,
}) => {
    const [fromRuntime, setFromRuntime] = React.useState('');
    const [toRuntime, setToRuntime] = React.useState('');
    const [confirmed, setConfirmed] = React.useState(false);

    React.useEffect(() => {
        setConfirmed(false);
    }, [diffResponse]);

    if (loading) {
        return (
            <div style={sectionStyle}>
                <div style={{ padding: 12, color: 'var(--theia-descriptionForeground)', fontSize: 12 }}>
                    Computing capability diff...
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div style={sectionStyle}>
                <div style={{ padding: 12, color: 'var(--theia-errorForeground)', fontSize: 12 }}>
                    Diff error: {error}
                </div>
            </div>
        );
    }

    const handleCompare = () => {
        if (fromRuntime && toRuntime && fromRuntime !== toRuntime && onCompare) {
            onCompare(fromRuntime, toRuntime);
        }
    };

    const handleConfirm = () => {
        setConfirmed(true);
        if (onConfirm) {
            onConfirm();
        }
    };

    const handleCancel = () => {
        setConfirmed(false);
        if (onCancel) {
            onCancel();
        }
    };

    const renderSelector = () => (
        <div style={{ marginBottom: 10, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 11, color: 'var(--theia-descriptionForeground)' }}>Compare:</span>
            <select
                value={fromRuntime}
                onChange={e => setFromRuntime(e.target.value)}
                style={selectStyle}
                aria-label="Source runtime"
            >
                <option value="">-- from --</option>
                {availableRuntimes.map(rt => (
                    <option key={rt} value={rt}>{rt}</option>
                ))}
            </select>
            <span style={{ fontSize: 11, color: 'var(--theia-descriptionForeground)' }}>&rarr;</span>
            <select
                value={toRuntime}
                onChange={e => setToRuntime(e.target.value)}
                style={selectStyle}
                aria-label="Target runtime"
            >
                <option value="">-- to --</option>
                {availableRuntimes.map(rt => (
                    <option key={rt} value={rt}>{rt}</option>
                ))}
            </select>
            <button
                style={buttonStyle}
                onClick={handleCompare}
                disabled={!fromRuntime || !toRuntime || fromRuntime === toRuntime}
            >
                Compare
            </button>
        </div>
    );

    if (!diffResponse) {
        return (
            <div style={sectionStyle}>
                <h3 style={{ margin: '0 0 8px 0', fontSize: 13 }}>Runtime Capability Diff</h3>
                {renderSelector()}
                <div style={{ fontSize: 11, color: 'var(--theia-descriptionForeground)', padding: '8px 0' }}>
                    Select two runtimes to compare their capabilities.
                </div>
            </div>
        );
    }

    const { diff, fromRuntime: from, toRuntime: to, trustBoundaryWidened, trustSensitiveChanges } = diffResponse;
    const hasAdded = diff.addedCapabilities.length > 0;
    const hasRemoved = diff.removedCapabilities.length > 0;
    const hasChanges = hasAdded || hasRemoved || Object.keys(diff.changedFlags).length > 0;

    const renderCapabilityList = (items: string[], label: string, icon: string, color: string) => {
        if (items.length === 0) return null;
        return (
            <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4, color }}>
                    {icon} {label} ({items.length})
                </div>
                <ul style={{ margin: 0, paddingLeft: 20, fontSize: 11 }}>
                    {items.map(cap => (
                        <li key={cap} style={{ marginBottom: 2 }}>
                            <code style={{ fontSize: 10 }}>{cap}</code>
                        </li>
                    ))}
                </ul>
            </div>
        );
    };

    const renderChangedFlags = () => {
        const entries = Object.entries(diff.changedFlags);
        if (entries.length === 0) return null;
        return (
            <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4, color: 'var(--theia-foreground)' }}>
                    Changed Flags ({entries.length})
                </div>
                <div style={{ fontSize: 11 }}>
                    {entries.map(([key, val]) => {
                        const isTrustSensitive = trustSensitiveChanges.includes(key);
                        const isUnknown = val.before === null || val.after === null || val.before === undefined || val.after === undefined;
                        return (
                            <div key={key} style={{
                                marginBottom: 3,
                                padding: '3px 6px',
                                borderRadius: 3,
                                backgroundColor: isTrustSensitive
                                    ? 'var(--theia-editorWarning-background, rgba(255,200,0,0.1))'
                                    : 'var(--theia-editor-background)',
                                border: isTrustSensitive
                                    ? '1px solid var(--theia-editorWarning-foreground, #c90)'
                                    : '1px solid transparent',
                            }}>
                                <code style={{ fontSize: 10 }}>{key}</code>
                                {' : '}
                                <span style={{ color: 'var(--theia-editorError-foreground, #f44)' }}>
                                    {isUnknown ? 'unknown' : String(val.before)}
                                </span>
                                {' → '}
                                <span style={{ color: 'var(--theia-charts-green, #4c4)' }}>
                                    {isUnknown ? 'degraded' : String(val.after)}
                                </span>
                                {isTrustSensitive && (
                                    <span style={{ marginLeft: 6, fontSize: 9, color: 'var(--theia-editorWarning-foreground)' }}>
                                        [trust-sensitive]
                                    </span>
                                )}
                                {isUnknown && (
                                    <span style={{ marginLeft: 6, fontSize: 9, color: 'var(--theia-descriptionForeground)' }}>
                                        [unknown/degraded]
                                    </span>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    };

    const renderTrustWarning = () => {
        if (!trustBoundaryWidened) return null;
        return (
            <div style={{
                marginTop: 10,
                padding: 10,
                borderRadius: 6,
                backgroundColor: 'var(--theia-editorWarning-background, rgba(255,200,0,0.08))',
                border: '1px solid var(--theia-editorWarning-foreground, #c90)',
                fontSize: 12,
            }} role="alert" aria-live="assertive">
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                    Trust Boundary Widens
                </div>
                <div style={{ marginBottom: 6, lineHeight: 1.5 }}>
                    Switching from <strong>{from}</strong> to <strong>{to}</strong> grants
                    additional trust-sensitive capabilities:
                </div>
                <ul style={{ margin: '0 0 8px 0', paddingLeft: 20, fontSize: 11 }}>
                    {trustSensitiveChanges.map(cap => (
                        <li key={cap}><code style={{ fontSize: 10 }}>{cap}</code></li>
                    ))}
                </ul>
                <div style={{ fontSize: 11, color: 'var(--theia-editorWarning-foreground)' }}>
                    Explicit confirmation is required to proceed.
                </div>
            </div>
        );
    };

    const renderConfirmationButtons = () => {
        if (!trustBoundaryWidened) return null;
        if (confirmed) {
            return (
                <div style={{ marginTop: 10, fontSize: 11, color: 'var(--theia-charts-green)' }}>
                    Confirmed.
                </div>
            );
        }
        return (
            <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
                <button
                    style={{ ...buttonStyle, backgroundColor: 'var(--theia-errorForeground, #f44)' }}
                    onClick={handleConfirm}
                    aria-label="Confirm runtime switch"
                >
                    Confirm Switch
                </button>
                <button
                    style={buttonStyle}
                    onClick={handleCancel}
                    aria-label="Cancel runtime switch"
                >
                    Cancel
                </button>
            </div>
        );
    };

    return (
        <div style={sectionStyle}>
            <h3 style={{ margin: '0 0 8px 0', fontSize: 13 }}>
                Capability Diff: {from} &rarr; {to}
            </h3>
            {renderSelector()}
            {!hasChanges && (
                <div style={{ fontSize: 11, color: 'var(--theia-descriptionForeground)', padding: '8px 0' }}>
                    No capability differences detected.
                </div>
            )}
            {renderCapabilityList(diff.addedCapabilities, 'Added Capabilities', '+', 'var(--theia-charts-green, #4c4)')}
            {renderCapabilityList(diff.removedCapabilities, 'Removed Capabilities', '-', 'var(--theia-editorError-foreground, #f44)')}
            {renderChangedFlags()}
            {renderTrustWarning()}
            {renderConfirmationButtons()}
        </div>
    );
};

const sectionStyle: React.CSSProperties = {
    marginBottom: 12,
    padding: '10px 14px',
    backgroundColor: 'var(--theia-editor-background)',
    border: '1px solid var(--theia-widget-border)',
    borderRadius: 6,
};

const selectStyle: React.CSSProperties = {
    backgroundColor: 'var(--theia-dropdown-background)',
    color: 'var(--theia-dropdown-foreground)',
    border: '1px solid var(--theia-dropdown-border)',
    borderRadius: 4,
    padding: '3px 6px',
    fontSize: 11,
    outline: 'none',
};

const buttonStyle: React.CSSProperties = {
    backgroundColor: 'var(--theia-button-background)',
    color: 'var(--theia-button-foreground)',
    border: 'none',
    borderRadius: 4,
    padding: '4px 10px',
    cursor: 'pointer',
    fontSize: 11,
};

export default CapabilityDiffViewer;
