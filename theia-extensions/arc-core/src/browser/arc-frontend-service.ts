/**
 * ARC Frontend Service
 *
 * Wraps the ARC service proxy with error handling and workspace detection.
 * Called by all ARC widgets.
 */

import { injectable, inject } from '@theia/core/shared/inversify';
import { WorkspaceService } from '@theia/workspace/lib/browser/workspace-service';
import {
  ArcService,
  ArcServiceSymbol,
  ArcEnvelope,
  WorkspaceInfo,
  RuntimeInfo,
  WorkflowInfo,
  SchemaInfo,
  RunRecord,
  ContextPackEntry,
} from '../common/arc-protocol';

@injectable()
export class ArcFrontendService {

  @inject(ArcServiceSymbol)
  protected readonly arcService: ArcService;

  @inject(WorkspaceService)
  protected readonly workspaceService: WorkspaceService;

  /** Get the current workspace path */
  async getWorkspacePath(): Promise<string> {
    const roots = this.workspaceService.tryGetRoots();
    if (roots.length === 0) return '';
    return roots[0].resource.path.toString();
  }

  async inspectWorkspace(): Promise<ArcEnvelope<WorkspaceInfo>> {
    const path = await this.getWorkspacePath();
    return this.arcService.inspectWorkspace(path);
  }

  async listRuntimes(): Promise<ArcEnvelope<RuntimeInfo[]>> {
    const path = await this.getWorkspacePath();
    return this.arcService.listRuntimes(path);
  }

  async listWorkflows(runtimeId?: string): Promise<ArcEnvelope<WorkflowInfo[]>> {
    const path = await this.getWorkspacePath();
    return this.arcService.listWorkflows(path, runtimeId);
  }

  async listSchemas(runtimeId?: string): Promise<ArcEnvelope<SchemaInfo[]>> {
    const path = await this.getWorkspacePath();
    return this.arcService.listSchemas(path, runtimeId);
  }

  async startRun(workflowId: string, inputs?: Record<string, unknown>): Promise<ArcEnvelope<RunRecord>> {
    return this.arcService.startRun(workflowId, inputs);
  }

  async getRun(runId: string): Promise<ArcEnvelope<RunRecord>> {
    return this.arcService.getRun(runId);
  }

  async listRuns(): Promise<ArcEnvelope<RunRecord[]>> {
    const path = await this.getWorkspacePath();
    return this.arcService.listRuns(path);
  }

  async generateContextPack(task: string): Promise<ArcEnvelope<ContextPackEntry[]>> {
    const path = await this.getWorkspacePath();
    return this.arcService.generateContextPack(task, path);
  }

  async getDaemonStatus(): Promise<ArcEnvelope<{ running: boolean; version: string; pid?: number }>> {
    return this.arcService.getDaemonStatus();
  }
}
