/**
 * File Manager Service
 *
 * Manages trace files: listing, path resolution, directory creation,
 * deletion, and metadata reading.
 */

import * as fs from 'fs-extra';
import * as path from 'path';
import { injectable } from '@theia/core/shared/inversify';
import {
    TraceFile,
    ArcError,
    ArcErrorCode,
    TraceData
} from '../../common/arc-protocol';
import { validateTraceId } from '../security-utils';
import { TraceParser } from './trace-parser';

@injectable()
export class FileManager {
    constructor(private readonly parser: TraceParser = new TraceParser()) {}

    /**
     * Get all trace files from .arc/traces/ directory.
     */
    async getTraceFiles(workspaceRoot: string): Promise<TraceFile[]> {
        const tracesDir = path.join(workspaceRoot, '.arc', 'traces');

        if (!await fs.pathExists(tracesDir)) {
            return [];
        }

        const files = await fs.readdir(tracesDir);
        const traces: TraceFile[] = [];

        for (const file of files) {
            if (!file.endsWith('.jsonl')) {
                continue;
            }

            const filePath = path.join(tracesDir, file);
            const traceFile = await this.readTraceFileMetadata(file, filePath);
            if (traceFile) {
                traces.push(traceFile);
            }
        }

        return traces.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
    }

    /**
     * Get the absolute path for a trace file by ID.
     */
    getTracePath(workspaceRoot: string, traceId: string): string {
        validateTraceId(traceId);
        return path.join(workspaceRoot, '.arc', 'traces', `${traceId}.jsonl`);
    }

    /**
     * Ensure traces directory exists.
     */
    async ensureTracesDir(workspaceRoot: string): Promise<void> {
        const tracesDir = path.join(workspaceRoot, '.arc', 'traces');
        await fs.ensureDir(tracesDir);
    }

    /**
     * Delete a trace file by ID.
     */
    async deleteTrace(workspaceRoot: string, traceId: string): Promise<void> {
        const tracePath = this.getTracePath(workspaceRoot, traceId);

        if (!await fs.pathExists(tracePath)) {
            throw new ArcError(
                ArcErrorCode.RUN_NOT_FOUND,
                `Trace not found: ${traceId}`,
                { traceId }
            );
        }

        await fs.remove(tracePath);
    }

    /**
     * Read trace file metadata from file path.
     */
    async readTraceFileMetadata(file: string, filePath: string): Promise<TraceFile | null> {
        try {
            const stats = await fs.stat(filePath);
            // Parse the file to extract metadata
            const content = await fs.readFile(filePath, 'utf-8');
            const traceData = this.parser.parseJsonlContent(content, file.replace('.jsonl', ''));

            if (traceData) {
                return {
                    id: traceData.id || file.replace('.jsonl', ''),
                    path: filePath,
                    timestamp: traceData.startedAt || stats.mtime.toISOString(),
                    status: this.normalizeStatus(traceData.status),
                    size: stats.size,
                    eventCount: traceData.events?.length || 0
                };
            }
        } catch {
            // Fall through to fallback
        }

        // Fallback: include file with minimal info
        try {
            const stats = await fs.stat(filePath);
            return {
                id: file.replace('.jsonl', ''),
                path: filePath,
                timestamp: stats.mtime.toISOString(),
                status: 'unknown',
                size: stats.size
            };
        } catch {
            return null;
        }
    }

    /**
     * Normalize status string to expected enum values.
     */
    private normalizeStatus(status: TraceData['status']): 'completed' | 'failed' | 'unknown' {
        if (!status) return 'unknown';
        const s = status.toLowerCase();
        if (s === 'completed' || s === 'success' || s === 'ok') return 'completed';
        if (s === 'failed' || s === 'error' || s === 'failure') return 'failed';
        return 'unknown';
    }
}
