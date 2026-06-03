/**
 * Workflow Detector Service
 *
 * Detects SwarmGraph CLI installations and LangGraph workflows
 * by scanning the workspace for Python files with langgraph imports.
 */

import * as fs from 'fs-extra';
import * as path from 'path';
import { spawn } from 'child_process';
import { injectable } from '@theia/core/shared/inversify';
import { WorkflowInfo } from '../../common/arc-protocol';

@injectable()
export class WorkflowDetector {
    /**
     * Detect all workflows in workspace.
     */
    async detectWorkflows(workspaceRoot: string): Promise<WorkflowInfo[]> {
        const workflows: WorkflowInfo[] = [];

        // Detect SwarmGraph CLI
        const swarmgraphWorkflows = await this.detectSwarmGraph(workspaceRoot);
        workflows.push(...swarmgraphWorkflows);

        // Detect LangGraph workflows
        const langgraphWorkflows = await this.detectLangGraphWorkflows(workspaceRoot);
        workflows.push(...langgraphWorkflows);

        return workflows;
    }

    // ========== SwarmGraph Detection ==========

    /**
     * Detect SwarmGraph CLI installations.
     */
    private async detectSwarmGraph(workspaceRoot: string): Promise<WorkflowInfo[]> {
        const workflows: WorkflowInfo[] = [];

        // 1. Check workspace-local swarmgraph executable
        const localPath = path.join(workspaceRoot, 'swarmgraph');
        if (await fs.pathExists(localPath)) {
            workflows.push({
                type: 'swarmgraph',
                path: localPath,
                name: 'SwarmGraph (local)',
                description: 'SwarmGraph workflow execution engine (workspace-local)'
            });
        }

        // 2. Check for swarmgraph package
        const pkgPath = path.join(workspaceRoot, 'node_modules', 'swarmgraph');
        if (await fs.pathExists(pkgPath)) {
            workflows.push({
                type: 'swarmgraph',
                path: pkgPath,
                name: 'SwarmGraph (npm package)',
                description: 'SwarmGraph as npm dependency'
            });
        }

        // 3. Check venv paths for Python-based SwarmGraph
        const venvPaths = [
            path.join(workspaceRoot, '.venv', 'Scripts', 'swarmgraph'),
            path.join(workspaceRoot, '.venv', 'bin', 'swarmgraph'),
            path.join(workspaceRoot, 'venv', 'Scripts', 'swarmgraph'),
            path.join(workspaceRoot, 'venv', 'bin', 'swarmgraph')
        ];
        for (const venvPath of venvPaths) {
            if (await fs.pathExists(venvPath)) {
                workflows.push({
                    type: 'swarmgraph',
                    path: venvPath,
                    name: 'SwarmGraph (Python venv)',
                    description: 'SwarmGraph in Python virtual environment'
                });
                break;
            }
        }

        // 4. Check PATH via `which`
        if (workflows.length === 0) {
            const whichPath = await this.whichExecutable('swarmgraph');
            if (whichPath) {
                workflows.push({
                    type: 'swarmgraph',
                    path: whichPath,
                    name: 'SwarmGraph (PATH)',
                    description: 'SwarmGraph CLI in system PATH'
                });
            }
        }

        return workflows;
    }

    // ========== LangGraph Detection ==========

    /**
     * Detect LangGraph StateGraph workflows by scanning Python files.
     */
    private async detectLangGraphWorkflows(workspaceRoot: string): Promise<WorkflowInfo[]> {
        const workflows: WorkflowInfo[] = [];

        try {
            const pyFiles = await this.findPythonFiles(workspaceRoot);

            for (const pyFile of pyFiles) {
                const workflowInfo = await this.analyzePythonWorkflow(pyFile);
                if (workflowInfo) {
                    workflows.push(workflowInfo);
                }
            }
        } catch (error) {
            console.warn('Failed to scan for LangGraph workflows:', error);
        }

        return workflows;
    }

    /**
     * Find all Python files in the workspace (recursive, excluding common ignore dirs).
     */
    private async findPythonFiles(dir: string): Promise<string[]> {
        const ignoreDirs = new Set([
            'node_modules', '.git', '__pycache__', '.venv', 'venv',
            '.arc', 'docs', 'scripts',
            'env', '.env', 'virtualenv', 'site-packages',
            'build', 'dist', '.tox', '.pytest_cache', '.mypy_cache',
            '.ruff_cache', '.next', 'coverage',
        ]);
        const results: string[] = [];

        const entries = await fs.readdir(dir, { withFileTypes: true });

        for (const entry of entries) {
            if (!entry.isDirectory()) {
                if (entry.name.endsWith('.py')) {
                    results.push(path.join(dir, entry.name));
                }
                continue;
            }

            if (ignoreDirs.has(entry.name)) continue;

            const subResults = await this.findPythonFiles(path.join(dir, entry.name));
            results.push(...subResults);
        }

        return results;
    }

    /**
     * Analyze a Python file to detect if it's a LangGraph workflow.
     */
    private async analyzePythonWorkflow(filePath: string): Promise<WorkflowInfo | null> {
        try {
            const content = await fs.readFile(filePath, 'utf-8');

            if (!content.includes('langgraph')) {
                return null;
            }

            const hasStateGraphImport = this.matchPattern(content, [
                /^\s*from\s+langgraph\.graph\s+import\s+[^\n]*\bStateGraph\b/m,
                /^\s*from\s+langgraph\s+import\s+[^\n]*\bStateGraph\b/m,
                /^\s*import\s+langgraph\.graph\b/m,
            ]);

            if (!hasStateGraphImport) {
                return null;
            }

            const name = this.extractWorkflowName(filePath, content);

            const isCompiled = this.matchPattern(content, [
                /\.compile\s*\(/,
            ]);

            const hasPersistence = this.matchPattern(content, [
                /checkpointer/i,
                /MemorySaver/i,
                /SqliteSaver/i,
                /PostgresSaver/i,
            ]);

            const hasMultiAgent = this.matchPattern(content, [
                /agent.*node/i,
                /swarm.*node/i,
                /multi.*agent/i,
            ]);

            return {
                type: 'langgraph',
                path: filePath,
                name,
                description: this.buildWorkflowDescription(isCompiled, hasPersistence, hasMultiAgent)
            };
        } catch {
            return null;
        }
    }

    /**
     * Check if any pattern matches in content.
     */
    private matchPattern(content: string, patterns: RegExp[]): boolean {
        return patterns.some(pattern => pattern.test(content));
    }

    /**
     * Extract a human-readable workflow name from file path and content.
     */
    private extractWorkflowName(filePath: string, content: string): string {
        const classMatch = content.match(/(\w+)\s*=\s*StateGraph\s*\(/);
        if (classMatch) {
            return classMatch[1];
        }

        const nameMatch = content.match(/__name__\s*=\s*['"]([^'"]+)['"]/);
        if (nameMatch) {
            return nameMatch[1];
        }

        return path.basename(filePath, '.py');
    }

    /**
     * Build a description string based on detected workflow features.
     */
    private buildWorkflowDescription(isCompiled: boolean, hasPersistence: boolean, hasMultiAgent: boolean): string {
        const parts: string[] = [];
        parts.push('LangGraph StateGraph workflow');

        if (!isCompiled) {
            parts.push('(not compiled)');
        }
        if (hasPersistence) {
            parts.push('with persistence');
        }
        if (hasMultiAgent) {
            parts.push('multi-agent');
        }

        return parts.join(' ');
    }

    // ========== Utilities ==========

    /**
     * Find an executable in PATH.
     */
    private async whichExecutable(name: string): Promise<string | null> {
        return new Promise(resolve => {
            const child = spawn('which', [name], {
                shell: false,
                stdio: ['ignore', 'pipe', 'ignore']
            });

            let stdout = '';
            const timeout = setTimeout(() => {
                child.kill('SIGTERM');
                resolve(null);
            }, 5000);

            child.stdout.on('data', data => {
                stdout += data.toString();
            });

            child.on('error', () => {
                clearTimeout(timeout);
                resolve(null);
            });

            child.on('close', async code => {
                clearTimeout(timeout);
                if (code !== 0) {
                    resolve(null);
                    return;
                }

            const execPath = stdout.trim();
            if (execPath && await fs.pathExists(execPath)) {
                    resolve(execPath);
                    return;
            }

                resolve(null);
            });
        });
    }
}
