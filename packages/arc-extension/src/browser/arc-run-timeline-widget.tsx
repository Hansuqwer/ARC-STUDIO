/** ARC Run Timeline Widget — trace-backed run timeline shell. */
import * as React from 'react';
import { inject, injectable, postConstruct } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { ArcService, TraceData, TraceEvent, TraceFile } from '../common/arc-protocol';

const EVENT_ICONS: Record<string, string> = {
    RUN_STARTED: '>',
    RUN_COMPLETED: 'OK',
    RUN_FAILED: 'ERR',
    HITL_PROMPT: 'HITL',
    HITL_RESPONSE: 'DECISION',
    HITL_TIMEOUT: 'TIMEOUT',
    MESSAGE: 'MSG',
    TOOL_CALL: 'TOOL',
};

@injectable()
export class ArcRunTimelineWidget extends ReactWidget {
    static readonly ID = 'arc:run-timeline';
    static readonly LABEL = 'ARC Run Timeline';

    @inject(ArcService)
    protected readonly arcService!: ArcService;

    protected traces: TraceFile[] = [];
    protected selectedTrace: TraceData | null = null;
    protected selectedEvent: TraceEvent | null = null;
    protected eventFilter = '';
    protected loading = false;
    protected error = '';

    @postConstruct()
    protected init(): void {
        this.id = ArcRunTimelineWidget.ID;
        this.title.label = ArcRunTimelineWidget.LABEL;
        this.title.caption = 'ARC Run Timeline';
        this.title.closable = true;
        this.loadTraces();
    }

    protected async loadTraces(): Promise<void> {
        this.loading = true;
        this.error = '';
        this.update();
        try {
            this.traces = await this.arcService.getTraces();
            if (this.traces[0]) {
                this.selectedTrace = await this.arcService.readTrace(this.traces[0].id);
            }
        } catch (error) {
            this.error = error instanceof Error ? error.message : String(error);
        } finally {
            this.loading = false;
            this.update();
        }
    }

    protected async selectTrace(trace: TraceFile): Promise<void> {
        this.loading = true;
        this.selectedEvent = null;
        this.update();
        try {
            this.selectedTrace = await this.arcService.readTrace(trace.id);
        } catch (error) {
            this.error = error instanceof Error ? error.message : String(error);
        } finally {
            this.loading = false;
            this.update();
        }
    }

    protected render(): React.ReactNode {
        if (this.loading && this.traces.length === 0) {
            return <div style={centerStyle}>Loading traces...</div>;
        }
        return (
            <div style={{ display: 'flex', height: '100%', fontFamily: 'var(--theia-ui-font-family)', color: 'var(--theia-foreground)' }}>
                {this.renderTraceList()}
                <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
                    {this.error && <div style={errorStyle}>{this.error}</div>}
                    {this.selectedTrace ? this.renderTimeline(this.selectedTrace) : <div style={centerStyle}>No trace selected</div>}
                </div>
            </div>
        );
    }

    protected renderTraceList(): React.ReactNode {
        return (
            <div style={{ width: '220px', borderRight: '1px solid var(--theia-widget-border)', overflow: 'auto', flexShrink: 0 }}>
                <div style={{ padding: '8px 12px', fontWeight: 600, borderBottom: '1px solid var(--theia-widget-border)', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Traces ({this.traces.length})</span>
                    <button style={buttonStyle} onClick={() => this.loadTraces()}>Refresh</button>
                </div>
                {this.traces.map(trace => (
                    <div key={trace.id} style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--theia-widget-border)', backgroundColor: this.selectedTrace?.id === trace.id ? 'var(--theia-list-activeSelectionBackground)' : 'transparent' }} onClick={() => this.selectTrace(trace)}>
                        <div style={{ fontSize: '11px', fontWeight: 600 }}>{trace.id.substring(0, 18)}</div>
                        <div style={{ fontSize: '10px', color: this.statusColor(trace.status) }}>{trace.status}</div>
                        <div style={{ fontSize: '10px', opacity: 0.7 }}>{trace.eventCount ?? 0} events</div>
                    </div>
                ))}
            </div>
        );
    }

    protected renderTimeline(trace: TraceData): React.ReactNode {
        const events = this.filteredEvents(trace.events);
        const types = Array.from(new Set(trace.events.map(event => event.type))).sort();
        return (
            <div>
                <div style={{ marginBottom: '16px' }}>
                    <h2 style={{ margin: '0 0 6px 0', fontSize: '15px' }}>Run: {trace.id}</h2>
                    <div style={{ fontSize: '12px', color: 'var(--theia-descriptionForeground)' }}>
                        Workflow: <strong>{trace.workflowId}</strong> / Runtime: <strong>{trace.runtime}</strong> / Status: <strong>{trace.status}</strong>
                    </div>
                    <div style={{ marginTop: '10px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <span>{events.length}/{trace.events.length} events</span>
                        <select style={selectStyle} value={this.eventFilter} onChange={event => { this.eventFilter = event.currentTarget.value; this.update(); }}>
                            <option value="">All events</option>
                            {types.map(type => <option key={type} value={type}>{type}</option>)}
                        </select>
                    </div>
                </div>
                <div style={{ position: 'relative', paddingLeft: '32px' }}>
                    <div style={{ position: 'absolute', left: '14px', top: '12px', bottom: '12px', width: '2px', backgroundColor: 'var(--theia-widget-border)' }} />
                    {events.map((event, index) => this.renderEvent(event, index, trace.startedAt))}
                </div>
                {this.selectedEvent && <pre style={preStyle}>{JSON.stringify(this.selectedEvent, null, 2)}</pre>}
            </div>
        );
    }

    protected renderEvent(event: TraceEvent, index: number, startedAt: string): React.ReactNode {
        const offset = Math.max(0, new Date(event.timestamp).getTime() - new Date(startedAt).getTime());
        return (
            <div key={`${event.sequence}-${index}`} style={{ position: 'relative', marginBottom: '12px', cursor: 'pointer' }} onClick={() => { this.selectedEvent = event; this.update(); }}>
                <div style={{ position: 'absolute', left: '-26px', top: '2px', width: '28px', height: '18px', borderRadius: '9px', backgroundColor: this.eventColor(event.type), color: '#fff', fontSize: '9px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{EVENT_ICONS[event.type] ?? 'EV'}</div>
                <div style={{ border: '1px solid var(--theia-widget-border)', borderRadius: '4px', padding: '8px', backgroundColor: 'var(--theia-editor-background)' }}>
                    <div style={{ fontWeight: 600, fontSize: '12px' }}>{event.type} <span style={{ opacity: 0.6 }}>+{offset}ms</span></div>
                    <pre style={{ ...preStyle, margin: '6px 0 0 0' }}>{JSON.stringify(event.data, null, 2)}</pre>
                </div>
            </div>
        );
    }

    protected filteredEvents(events: TraceEvent[]): TraceEvent[] {
        return this.eventFilter ? events.filter(event => event.type === this.eventFilter) : events;
    }

    protected statusColor(status: string): string {
        if (status === 'completed') return '#4caf50';
        if (status === 'failed') return '#f44336';
        return 'var(--theia-descriptionForeground)';
    }

    protected eventColor(type: string): string {
        if (type.includes('FAILED') || type.includes('TIMEOUT')) return '#f44336';
        if (type.includes('COMPLETED') || type.includes('RESPONSE')) return '#4caf50';
        if (type.includes('HITL')) return '#ff9800';
        return '#4fc3f7';
    }
}

const centerStyle: React.CSSProperties = { alignItems: 'center', color: 'var(--theia-descriptionForeground)', display: 'flex', flexDirection: 'column', gap: '8px', height: '100%', justifyContent: 'center', padding: '24px', textAlign: 'center' };
const buttonStyle: React.CSSProperties = { background: 'none', border: '1px solid var(--theia-widget-border)', borderRadius: '4px', color: 'var(--theia-foreground)', cursor: 'pointer', padding: '2px 6px' };
const selectStyle: React.CSSProperties = { backgroundColor: 'var(--theia-input-background)', border: '1px solid var(--theia-input-border)', color: 'var(--theia-input-foreground)', padding: '4px' };
const errorStyle: React.CSSProperties = { backgroundColor: 'var(--theia-inputValidation-errorBackground)', border: '1px solid var(--theia-inputValidation-errorBorder)', color: 'var(--theia-errorForeground)', marginBottom: '12px', padding: '8px' };
const preStyle: React.CSSProperties = { backgroundColor: 'var(--theia-textCodeBlock-background)', fontSize: '11px', maxHeight: '240px', overflow: 'auto', padding: '8px', whiteSpace: 'pre-wrap' };
