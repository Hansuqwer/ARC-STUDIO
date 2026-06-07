/**
 * Trace Parser Service
 *
 * Parses JSONL trace files, streams large trace files,
 * validates trace events, and extracts trace metadata.
 */

import * as fs from 'fs-extra';
import { injectable } from '@theia/core/shared/inversify';
import {
    TraceData,
    TraceEvent,
    ArcError,
    ArcErrorCode
} from '../../common/arc-protocol';
import {
    sanitizeErrorMessage as strictSanitizeErrorMessage,
} from '../security-utils';

export interface ParseOptions {
    maxEvents?: number;
    skipInvalid?: boolean;
}

/** Reject a full in-memory parse above this size; callers should stream instead. */
const MAX_TRACE_FILE_BYTES = 64 * 1024 * 1024; // 64 MB
/** Drop a single delimiter-less line larger than this so the stream buffer
 *  cannot grow unbounded (a valid JSONL event line is far smaller). */
const MAX_LINE_BYTES = 4 * 1024 * 1024; // 4 MB

@injectable()
export class TraceParser {
    /**
     * Parse a JSONL trace file and return trace data.
     * Returns null if the content cannot be parsed.
     */
    async parseTrace(
        tracePath: string,
        traceId?: string
    ): Promise<TraceData | null> {
        const startTime = Date.now();

        try {
            if (!await fs.pathExists(tracePath)) {
                throw new ArcError(
                    ArcErrorCode.RUN_NOT_FOUND,
                    `Trace file not found: ${tracePath}`,
                    { tracePath }
                );
            }

            const stat = await fs.stat(tracePath);
            if (stat.size > MAX_TRACE_FILE_BYTES) {
                throw new ArcError(
                    ArcErrorCode.INVALID_INPUT,
                    `Trace file too large to parse fully (${stat.size} bytes > ${MAX_TRACE_FILE_BYTES} cap); stream it instead.`,
                    { tracePath, size: stat.size, cap: MAX_TRACE_FILE_BYTES }
                );
            }

            const content = await fs.readFile(tracePath, 'utf-8');
            const result = this.parseJsonlContent(content, traceId);

            const duration = Date.now() - startTime;
            const eventCount = result?.events?.length || 0;
            // [ARC Performance] Parsed trace in ${duration}ms
            // (${eventCount} events, ${content.split('\n').length} lines)

            return result;
        } catch (error) {
            if (error instanceof ArcError) {
                throw error;
            }
            throw new ArcError(
                ArcErrorCode.INVALID_INPUT,
                `Failed to parse trace: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
        }
    }

    /**
     * Parse JSONL content into trace data.
     */
    parseJsonlContent(content: string, fallbackId?: string): TraceData | null {
        const lines = this.splitJsonlLines(content);

        if (lines.length === 0) {
            return null;
        }

        let result: TraceData | null = null;

        // Single-line JSON: entire trace is one JSON object
        if (lines.length === 1) {
            result = this.parseJsonObject(lines[0], fallbackId);
        } else {
            // Multi-line JSONL
            const firstLine = lines[0];

            try {
                const first = JSON.parse(firstLine);
                if (first.id || first.workflow_id || first.workflowId) {
                    result = this.normalizeTraceData(first, fallbackId);
                }
            } catch {
                // First line is not JSON — treat every line as an event
            }

            if (!result) {
                result = this.parseLangGraphStyleJsonl(lines, fallbackId);
            }
        }

        return result;
    }

    /**
     * Stream trace events from a file as an async iterable.
     */
    async *streamTrace(tracePath: string): AsyncIterable<TraceEvent> {
        const readStream = fs.createReadStream(tracePath, { encoding: 'utf-8' });
        let lineBuffer = '';
        let lineIndex = 0;

        for await (const chunk of readStream) {
            lineBuffer += chunk;
            // Bound the buffer: a single line with no newline must not grow
            // without limit. Drop the pathological oversized line and resync.
            if (lineBuffer.length > MAX_LINE_BYTES && !lineBuffer.includes('\n')) {
                lineBuffer = '';
                continue;
            }
            const lines = lineBuffer.split('\n');
            lineBuffer = lines.pop() || '';

            for (const rawLine of lines) {
                const line = rawLine.trim();
                if (!line) continue;

                try {
                    const obj = JSON.parse(line);
                    yield this.normalizeTraceEvent(obj, lineIndex++);
                } catch {
                    // Skip invalid lines
                }
            }
        }

        if (lineBuffer.trim()) {
            try {
                const obj = JSON.parse(lineBuffer.trim());
                yield this.normalizeTraceEvent(obj, lineIndex);
            } catch {
                // Skip invalid final line
            }
        }
    }

    /**
     * Validate JSONL structure without full parsing.
     */
    validateJsonlStructure(lines: string[]): { errors: string[]; warnings: string[] } {
        const errors: string[] = [];
        const warnings: string[] = [];

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            try {
                JSON.parse(line);
            } catch (error) {
                errors.push(`Line ${i + 1}: Invalid JSON - ${strictSanitizeErrorMessage(error)}`);
            }
        }

        return { errors, warnings };
    }

    // ========== Private Parsing Helpers ==========

    /**
     * Split content into JSONL lines, skipping empty ones.
     */
    private splitJsonlLines(content: string): string[] {
        return content
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0);
    }

    /**
     * Parse a single JSON object with error handling.
     */
    private parseJsonObject(line: string, fallbackId?: string): TraceData | null {
        try {
            return this.normalizeTraceData(JSON.parse(line), fallbackId);
        } catch {
            console.warn('Failed to parse JSON line:', line.substring(0, 100));
            return null;
        }
    }

    /**
     * Normalize trace data from various formats to TraceData interface.
     */
    private normalizeTraceData(obj: any, fallbackId?: string): TraceData {
        const id = obj.id || obj.runId || obj.run_id || fallbackId || `unknown-${Date.now().toString(16)}`;

        let events: TraceEvent[] = [];
        if (Array.isArray(obj.events)) {
            events = obj.events.map((e: any, idx: number) => this.normalizeTraceEvent(e, idx));
        } else if (Array.isArray(obj.traces)) {
            events = obj.traces.map((e: any, idx: number) => this.normalizeTraceEvent(e, idx));
        }

        return {
            id,
            workflowId: obj.workflow_id || obj.workflowId || '',
            runtime: obj.runtime || 'swarmgraph',
            status: obj.status || 'unknown',
            startedAt: obj.started_at || obj.startedAt || new Date().toISOString(),
            endedAt: obj.ended_at || obj.endedAt || undefined,
            events,
            metadata: obj.metadata || this.extractMetadata(obj)
        };
    }

    /**
     * Normalize a single trace event.
     */
    private normalizeTraceEvent(obj: any, fallbackIndex: number): TraceEvent {
        return {
            type: obj.type || 'MESSAGE',
            timestamp: obj.timestamp || new Date().toISOString(),
            runId: obj.run_id || obj.runId || '',
            sequence: obj.sequence ?? fallbackIndex,
            data: obj.data || this.extractEventData(obj)
        };
    }

    /**
     * Extract metadata from a trace object, excluding standard fields.
     */
    private extractMetadata(obj: any): Record<string, any> {
        const standardFields = [
            'id', 'run_id', 'runId', 'workflow_id', 'workflowId', 'runtime',
            'status', 'started_at', 'startedAt', 'ended_at', 'endedAt',
            'events', 'traces', 'metadata'
        ];
        const metadata: Record<string, any> = {};
        for (const [key, value] of Object.entries(obj)) {
            if (!standardFields.includes(key)) {
                metadata[key] = value;
            }
        }
        return metadata;
    }

    /**
     * Extract event data from a raw event object.
     */
    private extractEventData(obj: any): Record<string, any> {
        const standardFields = ['type', 'timestamp', 'run_id', 'runId', 'sequence', 'data'];
        const data: Record<string, any> = {};
        for (const [key, value] of Object.entries(obj)) {
            if (!standardFields.includes(key)) {
                data[key] = value;
            }
        }
        return data;
    }

    /**
     * Parse LangGraph-style JSONL where each line is a separate event.
     */
    private parseLangGraphStyleJsonl(lines: string[], fallbackId?: string): TraceData {
        const events: TraceEvent[] = [];
        let runId = fallbackId || '';

        for (let i = 0; i < lines.length; i++) {
            try {
                const obj = JSON.parse(lines[i]);
                const event = this.normalizeTraceEvent(obj, i);
                events.push(event);

                if (i === 0 && !runId) {
                    runId = event.runId || obj.run_id || obj.runId || fallbackId || `run-${Date.now().toString(16)}`;
                }
            } catch {
                console.warn(`Skipping malformed JSONL line ${i + 1}`);
            }
        }

        if (!runId) {
            runId = fallbackId || `run-${Date.now().toString(16)}`;
        }

        const status = this.deriveStatusFromEvents(events);

        return {
            id: runId,
            workflowId: '',
            runtime: 'langgraph',
            status,
            startedAt: events[0]?.timestamp || new Date().toISOString(),
            endedAt: events[events.length - 1]?.timestamp || undefined,
            events,
            metadata: {}
        };
    }

    /**
     * Derive trace status from event types.
     */
    private deriveStatusFromEvents(events: TraceEvent[]): string {
        for (const event of events) {
            if (event.type === 'RUN_COMPLETED') return 'completed';
            if (event.type === 'RUN_FAILED' || event.type === 'ERROR') return 'failed';
        }
        return events.length > 0 ? 'running' : 'unknown';
    }

    /**
     * Check if an event has valid structure.
     */
    isValidEvent(event: any): event is TraceEvent {
        return (
            event &&
            typeof event === 'object' &&
            typeof event.type === 'string' &&
            typeof event.timestamp === 'string'
        );
    }

    /**
     * Normalize status string to expected enum values.
     */
    normalizeStatus(status: string): 'completed' | 'failed' | 'unknown' {
        if (!status) return 'unknown';
        const s = status.toLowerCase();
        if (s === 'completed' || s === 'success' || s === 'ok') return 'completed';
        if (s === 'failed' || s === 'error' || s === 'failure') return 'failed';
        return 'unknown';
    }
}
