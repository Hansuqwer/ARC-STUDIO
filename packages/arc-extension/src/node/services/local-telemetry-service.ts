import { execFileSync } from 'child_process';
import {
    ArcError, ArcErrorCode, CiCheckStatus, McpWorkbenchStatus, TestbenchDetection, WorkspaceInventory,
} from '../../common/arc-protocol';
import { buildArcCliEnv } from './arc-cli-utils';

interface ArcEnvelope {
    ok: boolean;
    data?: Record<string, unknown>;
    error?: { code?: string; message?: string };
}

export class LocalTelemetryService {
    constructor(private readonly workspaceRoot: string) {}

    getMcpWorkbenchStatus(): McpWorkbenchStatus {
        const data = this.runArcJson(['mcp', 'workbench', 'status', '--workspace', this.workspaceRoot, '--json'], 10000);
        return {
            workspace: String((data.workspace as string) || this.workspaceRoot),
            serverCreatable: Boolean(data.server_creatable ?? data.serverCreatable),
            serverBlocker: (data.server_blocker as string) ?? (data.serverBlocker as string) ?? null,
            tools: Array.isArray(data.tools) ? (data.tools as string[]).map(String) : [],
            resources: Array.isArray(data.resources) ? (data.resources as string[]).map(String) : [],
            trust: {
                level: String(((data.trust as Record<string, unknown>)?.level as string) || 'unknown'),
                reason: ((data.trust as Record<string, unknown>)?.reason as string) ?? null,
                markerPath: ((data.trust as Record<string, unknown>)?.marker_path as string) ?? ((data.trust as Record<string, unknown>)?.markerPath as string) ?? null,
                warning: ((data.trust as Record<string, unknown>)?.warning as string) ?? null,
            },
            diagnostic: String((data.diagnostic as string) || 'read-only'),
        };
    }

    getWorkspaceInventory(options?: { suffix?: string; maxEntries?: number }): WorkspaceInventory {
        const args = ['workspace', 'inventory', '--workspace', this.workspaceRoot, '--json'];
        if (options?.suffix) args.push('--suffix', options.suffix);
        const data = this.runArcJson(args, 15000);
        const maxEntries = Math.max(0, Math.min(options?.maxEntries ?? 200, 1000));
        const filesData = data.files as Record<string, unknown> | undefined;
        const allEntries = (Array.isArray(filesData?.entries) ? filesData.entries : []) as Array<Record<string, unknown>>;
        const entries = allEntries.slice(0, maxEntries);
        return {
            workspace: String((data.workspace as string) || this.workspaceRoot),
            files: {
                count: Number(filesData?.count || 0),
                totalSize: Number((filesData?.total_size as number) ?? (filesData?.totalSize as number) ?? 0),
                entries: entries.map((f: Record<string, unknown>) => ({
                    path: String(f.path),
                    size: f.size == null ? null : Number(f.size),
                    suffix: String(f.suffix || ''),
                    provenance: String(f.provenance || 'workspace_file'),
                    error: f.error as string | undefined,
                })),
                truncated: allEntries.length > maxEntries,
            },
            git: this.extractGit(data.git as Record<string, unknown> | undefined),
            traces: {
                count: Number(((data.traces as Record<string, unknown>)?.count as number) || 0),
                entries: Array.isArray((data.traces as Record<string, unknown>)?.entries) ? ((data.traces as Record<string, unknown>).entries as Array<Record<string, unknown>>).map((e: Record<string, unknown>) => ({ name: String(e.name), size: Number(e.size), provenance: String(e.provenance || 'trace_store') })) : [],
            },
            mcpResources: Array.isArray(data.mcp_resources) ? (data.mcp_resources as Array<Record<string, unknown>>).map((r: Record<string, unknown>) => ({ name: r.name as string | undefined, provenance: String(r.provenance || 'mcp_resource'), present: r.present as boolean | undefined, reason: r.reason as string | undefined })) : [],
            symbols: data.symbols ? this.extractSymbols(data.symbols as Record<string, unknown>, maxEntries) : undefined,
        };
    }

    detectTestbench(commandOverride?: string): TestbenchDetection {
        const args = ['testbench', 'detect', '--workspace', this.workspaceRoot, '--json'];
        if (commandOverride?.trim()) args.push('--command', commandOverride.trim());
        const data = this.runArcJson(args, 10000);
        return {
            workspace: String((data.workspace as string) || this.workspaceRoot),
            detected: Array.isArray(data.detected) ? (data.detected as Array<Record<string, unknown>>).map((d: Record<string, unknown>) => ({
                command: d.command as string | undefined,
                source: String(d.source || ''),
                cwd: d.cwd as string | undefined,
                confidence: String(d.confidence || 'unknown'),
                runner: d.runner as string | undefined,
                reason: d.reason as string | undefined,
                script: d.script as string | undefined,
            })) : [],
            count: Number((data.count as number) || 0),
        };
    }

    getCiCheckStatus(): CiCheckStatus {
        const data = this.runArcJson(['ci', 'check', '--json', '--workspace', this.workspaceRoot], 15000, true);
        return {
            private: Boolean(data.private),
            workspace: String((data.workspace as string) || this.workspaceRoot),
            checks: (data.checks || {}) as Record<string, Record<string, unknown>>,
            overall: String((data.overall as string) || 'skip'),
            checkedAt: (data.checked_at as string) || (data.checkedAt as string),
        };
    }

    private runArcJson(args: string[], timeout: number, useWorkspaceCwd = false): Record<string, unknown> {
        try {
            const output = execFileSync('arc', args, {
                cwd: useWorkspaceCwd ? this.workspaceRoot : undefined,
                timeout,
                encoding: 'utf-8',
                windowsHide: true,
                env: buildArcCliEnv(),
                maxBuffer: 1024 * 1024,
            });
            const parsed: ArcEnvelope = JSON.parse(output);
            if (!parsed.ok || !parsed.data) {
                throw new ArcError(ArcErrorCode.RUN_FAILED, parsed?.error?.message || 'ARC CLI returned no data');
            }
            return parsed.data;
        } catch (error) {
            if (error instanceof ArcError) throw error;
            throw new ArcError(
                ArcErrorCode.RUN_FAILED,
                `Local telemetry unavailable: ${error instanceof Error ? error.message : 'Unknown error'}`
            );
        }
    }

    private extractGit(git: Record<string, unknown> | undefined): WorkspaceInventory['git'] {
        if (!git) return { provenance: 'git', present: false, reason: 'no_git_data' };
        return {
            provenance: 'git',
            present: git.present as boolean | undefined,
            branch: git.branch as string | null | undefined,
            commit: git.commit as string | null | undefined,
            commitCount: (git.commit_count as number) ?? (git.commitCount as number) ?? null,
            dirty: git.dirty as boolean | undefined,
            gitDir: (git.git_dir as string) ?? (git.gitDir as string) ?? undefined,
            degraded: git.degraded as boolean | undefined,
            reason: git.reason as string | undefined,
        };
    }

    private extractSymbols(symbols: Record<string, unknown>, maxEntries: number): WorkspaceInventory['symbols'] {
        const entries = (Array.isArray(symbols.entries) ? symbols.entries : []).slice(0, maxEntries) as Array<Record<string, unknown>>;
        return {
            count: Number(symbols.count || 0),
            entries: entries.map((s: Record<string, unknown>) => ({
                path: String(s.path),
                language: String(s.language),
                kind: String(s.kind),
                name: String(s.name),
                qualname: String(s.qualname),
                line: Number(s.line),
                provenance: String(s.provenance || 'local_static_symbol'),
            })),
            errors: Array.isArray(symbols.errors) ? (symbols.errors as Array<Record<string, unknown>>).map((e: Record<string, unknown>) => ({ path: String(e.path || ''), error: String(e.error || '') })) : [],
            truncated: Boolean(symbols.truncated),
            provenance: String(symbols.provenance || 'local_static_symbol_inventory'),
        };
    }
}
