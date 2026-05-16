/** ARC Event Stream Widget — universal trace event renderer. */
import * as React from 'react';
import { inject, injectable, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcService, TraceData, TraceEvent, TraceFile } from '../common/arc-protocol';

const EVENT_COLORS: Record<string, string> = {
    RUN_STARTED: '#4caf50',
    RUN_COMPLETED: '#4caf50',
    RUN_FAILED: '#f44336',
    HITL_PROMPT: '#ff9800',
    HITL_RESPONSE: '#4caf50',
    HITL_TIMEOUT: '#f44336',
    MESSAGE: '#9c27b0',
    RAW: '#757575',
    CUSTOM: '#607d8b',
};

@injectable()
export class ArcEventStreamWidget extends ReactWidget {
    static readonly ID = 'arc:event-stream';
    static readonly LABEL = 'ARC Event Stream (Advanced Trace)';

    @inject(ArcService)
    protected readonly arcService!: ArcService;

    protected traces: TraceFile[] = [];
    protected selectedTrace: TraceData | null = null;
    protected selectedEvent: TraceEvent | null = null;
    protected filter = '';
    protected selectedEventTypes = new Set<string>();
    protected loading = false;
    protected error = '';

    @postConstruct()
    protected init(): void {
        this.id = ArcEventStreamWidget.ID;
        this.title.label = ArcEventStreamWidget.LABEL;
        this.title.closable = true;
        this.title.caption = 'ARC Event Stream (Advanced Trace)';
        this.loadTraces();
    }

    protected async loadTraces(): Promise<void> {
        this.loading = true;
        this.error = '';
        this.update();
        try {
            this.traces = await this.arcService.getTraces();
            if (this.traces[0]) {
                await this.selectTrace(this.traces[0]);
            }
        } catch (error) {
            this.error = error instanceof Error ? error.message : String(error);
        } finally {
            this.loading = false;
            this.update();
        }
    }

    protected async selectTrace(trace: TraceFile): Promise<void> {
        this.selectedEvent = null;
        this.selectedTrace = await this.arcService.readTrace(trace.id);
        this.update();
    }

    protected render(): React.ReactNode {
        if (this.loading && this.traces.length === 0) {
            return <div style={centerStyle}>Loading event stream...</div>;
        }
        const events = this.getFilteredEvents();
        return (
            <div style={{ display: 'flex', height: '100%', fontFamily: 'var(--theia-ui-font-family)', color: 'var(--theia-foreground)' }}>
                {this.renderTraceList()}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                    {this.renderToolbar(events)}
                    {this.error && <div style={errorStyle}>{this.error}</div>}
                    <div style={{ flex: 1, overflow: 'auto', padding: '12px' }}>
                        {events.map(event => this.renderEvent(event))}
                        {events.length === 0 && <div style={centerStyle}>No events match current filters</div>}
                    </div>
                </div>
                {this.selectedEvent && this.renderDetails(this.selectedEvent)}
            </div>
        );
    }

    protected renderTraceList(): React.ReactNode {
        return (
            <div style={{ width: '220px', borderRight: '1px solid var(--theia-widget-border)', overflow: 'auto', flexShrink: 0 }}>
                <div style={{ padding: '8px 12px', fontWeight: 600, borderBottom: '1px solid var(--theia-widget-border)', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Runs</span>
                    <button style={buttonStyle} onClick={() => this.loadTraces()}>Refresh</button>
                </div>
                {this.traces.map(trace => (
                    <div key={trace.id} style={{ padding: '8px 12px', borderBottom: '1px solid var(--theia-widget-border)', cursor: 'pointer', backgroundColor: this.selectedTrace?.id === trace.id ? 'var(--theia-list-activeSelectionBackground)' : 'transparent' }} onClick={() => this.selectTrace(trace)}>
                        <div style={{ fontSize: '11px', fontWeight: 600 }}>{trace.id.substring(0, 18)}</div>
                        <div style={{ fontSize: '10px', opacity: 0.75 }}>{trace.status} / {trace.eventCount ?? 0} events</div>
                    </div>
                ))}
            </div>
        );
    }

    protected renderToolbar(events: TraceEvent[]): React.ReactNode {
        const allTypes = Array.from(new Set(this.selectedTrace?.events.map(event => event.type) ?? [])).sort();
        return (
            <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--theia-widget-border)', display: 'grid', gap: '8px' }}>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <strong>Event Stream</strong>
                    <span>{events.length} visible</span>
                    <input style={inputStyle} value={this.filter} placeholder="Filter text or event type" onChange={event => { this.filter = event.currentTarget.value; this.update(); }} />
                    <button style={buttonStyle} onClick={() => { this.selectedEventTypes = new Set<string>(); this.filter = ''; this.update(); }}>Clear</button>
                </div>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {allTypes.map(type => (
                        <button key={type} style={{ ...chipStyle, backgroundColor: this.selectedEventTypes.has(type) ? this.eventColor(type) : 'transparent' }} onClick={() => this.toggleEventType(type)}>{type}</button>
                    ))}
                </div>
            </div>
        );
    }

    protected renderEvent(event: TraceEvent): React.ReactNode {
        return (
            <div key={`${event.sequence}-${event.type}`} style={{ borderLeft: `4px solid ${this.eventColor(event.type)}`, backgroundColor: 'var(--theia-editor-background)', borderRadius: '4px', marginBottom: '8px', padding: '8px', cursor: 'pointer' }} onClick={() => { this.selectedEvent = event; this.update(); }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                    <strong>{event.type}</strong>
                    <span style={{ color: 'var(--theia-descriptionForeground)', fontSize: '11px' }}>#{event.sequence}</span>
                </div>
                <div style={{ color: 'var(--theia-descriptionForeground)', fontSize: '11px' }}>{event.timestamp}</div>
                <pre style={compactPreStyle}>{JSON.stringify(event.data, null, 2)}</pre>
            </div>
        );
    }

    protected renderDetails(event: TraceEvent): React.ReactNode {
        return (
            <div style={{ width: '320px', borderLeft: '1px solid var(--theia-widget-border)', overflow: 'auto', padding: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                    <strong>{event.type}</strong>
                    <button style={buttonStyle} onClick={() => { this.selectedEvent = null; this.update(); }}>Close</button>
                </div>
                <pre style={preStyle}>{JSON.stringify(event, null, 2)}</pre>
            </div>
        );
    }

    protected getFilteredEvents(): TraceEvent[] {
        const source = this.selectedTrace?.events ?? [];
        return source.filter(event => {
            if (this.selectedEventTypes.size > 0 && !this.selectedEventTypes.has(event.type)) {
                return false;
            }
            if (!this.filter.trim()) {
                return true;
            }
            const needle = this.filter.toLowerCase();
            return event.type.toLowerCase().includes(needle) || JSON.stringify(event.data).toLowerCase().includes(needle);
        });
    }

    protected toggleEventType(type: string): void {
        if (this.selectedEventTypes.has(type)) {
            this.selectedEventTypes.delete(type);
        } else {
            this.selectedEventTypes.add(type);
        }
        this.update();
    }

    protected eventColor(type: string): string {
        return EVENT_COLORS[type] ?? (type.includes('ERROR') || type.includes('FAILED') ? '#f44336' : '#4fc3f7');
    }
}

const centerStyle: React.CSSProperties = { alignItems: 'center', color: 'var(--theia-descriptionForeground)', display: 'flex', flexDirection: 'column', gap: '8px', height: '100%', justifyContent: 'center', padding: '24px', textAlign: 'center' };
const buttonStyle: React.CSSProperties = { background: 'none', border: '1px solid var(--theia-widget-border)', borderRadius: '4px', color: 'var(--theia-foreground)', cursor: 'pointer', padding: '3px 8px' };
const inputStyle: React.CSSProperties = { backgroundColor: 'var(--theia-input-background)', border: '1px solid var(--theia-input-border)', color: 'var(--theia-input-foreground)', minWidth: '220px', padding: '4px 6px' };
const chipStyle: React.CSSProperties = { ...buttonStyle, fontSize: '10px' };
const errorStyle: React.CSSProperties = { backgroundColor: 'var(--theia-inputValidation-errorBackground)', border: '1px solid var(--theia-inputValidation-errorBorder)', color: 'var(--theia-errorForeground)', margin: '12px', padding: '8px' };
const preStyle: React.CSSProperties = { backgroundColor: 'var(--theia-textCodeBlock-background)', fontSize: '11px', overflow: 'auto', padding: '8px', whiteSpace: 'pre-wrap' };
const compactPreStyle: React.CSSProperties = { ...preStyle, maxHeight: '120px', margin: '6px 0 0 0' };
