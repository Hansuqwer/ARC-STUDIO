/**
 * Trace Viewer Section Component
 * 
 * UI section for viewing execution traces.
 */

import * as React from '@theia/core/shared/react';
import { TraceFile } from '../../common/arc-protocol';
import { ProgressBar } from './ProgressBar';

export interface TraceViewerSectionProps {
    isCollapsed: boolean;
    onToggle: () => void;
    isLoadingTraces: boolean;
    traceProgress: number;
    traces: TraceFile[];
    selectedTrace?: TraceFile;
    traceFilter: string;
    onTraceFilterChange: (value: string) => void;
    onClearFilter: () => void;
    onLoadTraces: () => void;
    onSelectTrace: (trace: TraceFile) => void;
}

export const TraceViewerSection: React.FC<TraceViewerSectionProps> = ({
    isCollapsed,
    onToggle,
    isLoadingTraces,
    traceProgress,
    traces,
    selectedTrace,
    traceFilter,
    onTraceFilterChange,
    onClearFilter,
    onLoadTraces,
    onSelectTrace
}) => {
    const filteredTraces = traces.filter((t: TraceFile) => 
        t.id.toLowerCase().includes(traceFilter.toLowerCase())
    );

    return (
        <section className={`arc-section ${isCollapsed ? 'arc-section-collapsed' : ''}`} aria-labelledby='trace-viewer-heading'>
            <button 
                className='arc-section-header'
                onClick={onToggle}
                aria-expanded={!isCollapsed}
                aria-controls='trace-viewer-content'
            >
                <h3 id='trace-viewer-heading'>Trace Viewer</h3>
                <div className='arc-section-header-right'>
                    {isCollapsed && filteredTraces.length > 0 && (
                        <span className='arc-section-badge' aria-label={`${filteredTraces.length} trace(s)`}>
                            {filteredTraces.length}
                        </span>
                    )}
                    <span className='arc-section-toggle' aria-hidden='true'>
                        {isCollapsed ? '▸' : '▾'}
                    </span>
                </div>
            </button>
            
            <div id='trace-viewer-content' className='arc-section-content'>
                {!isCollapsed && (
                    <>
                        <p className='arc-section-description'>View execution traces from .arc/traces/</p>
                        
                        <div className='arc-input-group'>
                            <label htmlFor='trace-filter'>Filter traces:</label>
                            <div className='arc-filter-input-wrapper'>
                                <input
                                    id='trace-filter'
                                    type='text'
                                    className='theia-input'
                                    placeholder='Filter by ID...'
                                    value={traceFilter}
                                    onChange={(e) => onTraceFilterChange(e.target.value)}
                                    aria-label='Filter traces by ID'
                                />
                                {traceFilter && (
                                    <button
                                        className='arc-filter-clear'
                                        onClick={onClearFilter}
                                        aria-label='Clear filter'
                                        title='Clear filter'
                                    >
                                        ×
                                    </button>
                                )}
                            </div>
                        </div>

                        <button 
                            className={`theia-button ${isLoadingTraces ? 'arc-button-loading' : ''}`}
                            onClick={onLoadTraces}
                            disabled={isLoadingTraces}
                            aria-busy={isLoadingTraces}
                            aria-label='Load traces'
                        >
                            {isLoadingTraces ? (
                                <>
                                    <span className='arc-spinner' aria-hidden='true'></span>
                                    <span className='arc-button-text'>Loading...</span>
                                </>
                            ) : (
                                'Load Traces'
                            )}
                        </button>

                        {isLoadingTraces && <ProgressBar value={traceProgress} label='Loading traces...' />}

                        {traces.length > 0 && (
                            <div className='arc-trace-list' role='listbox' aria-label='Trace files'>
                                <div className='arc-trace-list-header'>
                                    <span>Status</span>
                                    <span>Run ID</span>
                                    <span>Timestamp</span>
                                </div>
                                {filteredTraces.map((trace: TraceFile) => (
                                    <div 
                                        key={trace.id} 
                                        className={`arc-trace-item ${selectedTrace?.id === trace.id ? 'arc-trace-item-selected' : ''}`}
                                        role='option'
                                        onClick={() => onSelectTrace(trace)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' || e.key === ' ') {
                                                onSelectTrace(trace);
                                            }
                                        }}
                                        tabIndex={0}
                                        aria-selected={selectedTrace?.id === trace.id}
                                    >
                                        <span className={`arc-trace-status arc-trace-status-${trace.status}`} aria-label={`Status: ${trace.status}`}>
                                            {trace.status === 'completed' ? '✓' : '✗'}
                                        </span>
                                        <span className='arc-trace-id'>{trace.id}</span>
                                        <span className='arc-trace-time'>{new Date(trace.timestamp).toLocaleString()}</span>
                                    </div>
                                ))}
                                {filteredTraces.length === 0 && (
                                    <p className='arc-empty-state'>No traces match the filter</p>
                                )}
                            </div>
                        )}

                        {traces.length === 0 && !isLoadingTraces && (
                            <p className='arc-empty-state'>No traces loaded. Click "Load Traces" to view traces.</p>
                        )}
                    </>
                )}
            </div>
        </section>
    );
};
