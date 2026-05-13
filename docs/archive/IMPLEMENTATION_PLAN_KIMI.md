# ARC Studio - Comprehensive Implementation Plan for Kimi 2.6

**Date:** 2026-05-13  
**Purpose:** Detailed implementation guide with code examples and sources  
**Target:** Kimi 2.6 AI for efficient patching  
**Based on:** CRITICAL_REVIEW_GENSPARK.md

---

## Table of Contents

1. [P0 Tasks - Critical (Must Fix)](#p0-tasks---critical-must-fix)
2. [P1 Tasks - High Priority](#p1-tasks---high-priority)
3. [P2 Tasks - Medium Priority](#p2-tasks---medium-priority)
4. [Implementation Order](#implementation-order)
5. [Testing Strategy](#testing-strategy)
6. [Verification Checklist](#verification-checklist)

---

## P0 Tasks - Critical (Must Fix)

### Task 1: Fix Python Build Configuration (1 hour)

**Issue:** Python package build fails with hatchling error
**File:** `python/pyproject.toml`
**Priority:** P0 - CRITICAL

#### Current State
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

#### Problem
Missing `[tool.hatch.build.targets.wheel]` configuration causes:
```
ValueError: Unable to determine which files to ship inside the wheel
The most likely cause is that there is no directory that matches
the name of your project (arc_studio_backend).
```

#### Solution
Add the following to `python/pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/agent_runtime_cockpit"]
```

#### Complete Fixed Configuration
```toml
[project]
name = "arc-studio-backend"
version = "0.1.0"
description = "ARC Studio Python Backend"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.2.0",
    "mypy>=1.8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# ADD THIS SECTION
[tool.hatch.build.targets.wheel]
packages = ["src/agent_runtime_cockpit"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

#### Verification
```bash
cd python
uv run pytest -q
# Should pass without build errors
```

#### References
- Hatchling docs: https://hatch.pypa.io/latest/config/build/
- Python packaging guide: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/

---

### Task 2: Refactor arc-backend-service.ts (3-4 days)

**Issue:** Monolithic file with 1,330 lines
**File:** `packages/arc-extension/src/node/arc-backend-service.ts`
**Priority:** P0 - CRITICAL

#### Current Structure Analysis
```
arc-backend-service.ts (1,330 lines)
├── Workflow execution (lines 81-179)
├── Trace management (lines 189-250)
├── JSONL parsing (lines 468-738)
├── Workflow detection (lines 800-950)
├── File operations (lines 566-631)
└── Validation helpers (scattered)
```

#### Refactoring Plan

**New Structure:**
```
packages/arc-extension/src/node/
├── arc-backend-service.ts (200 lines) - Orchestration only
├── services/
│   ├── workflow-executor.ts (300 lines)
│   ├── trace-parser.ts (400 lines)
│   ├── workflow-detector.ts (300 lines)
│   └── file-manager.ts (200 lines)
└── utils/
    └── validation.ts (100 lines)
```

#### Step-by-Step Implementation

**Step 1: Create workflow-executor.ts**

```typescript
// packages/arc-extension/src/node/services/workflow-executor.ts

import { spawn, ChildProcess } from 'child_process';
import { injectable } from '@theia/core/shared/inversify';
import {
    ExecutionOptions,
    ExecutionResult,
    ArcError,
    ArcErrorCode
} from '../../common/arc-protocol';
import {
    sanitizePrompt,
    validateBackend,
    sanitizeErrorMessage
} from '../security-utils';

export interface CommandResult {
    stdout: string;
    stderr: string;
    exitCode: number;
}

@injectable()
export class WorkflowExecutor {
    private runningProcesses: Map<string, ChildProcess> = new Map();

    /**
     * Execute SwarmGraph workflow
     */
    async executeWorkflow(
        prompt: string,
        options?: ExecutionOptions
    ): Promise<ExecutionResult> {
        const startTime = Date.now();

        try {
            // Validate inputs
            const sanitizedPrompt = sanitizePrompt(prompt);
            const backend = validateBackend(options?.backend || 'gateway');
            const timeout = options?.timeout || 300000;

            // Check CLI availability
            const cliPath = await this.findExecutable('swarmgraph');
            if (!cliPath) {
                throw new ArcError(
                    ArcErrorCode.EXECUTION_FAILED,
                    'SwarmGraph CLI not found'
                );
            }

            // Build command
            const args = this.buildSwarmArgs(sanitizedPrompt, backend);
            const runId = `run-sg-${Date.now().toString(16)}`;

            // Execute
            const result = await this.executeCommand(
                'swarmgraph',
                args,
                timeout,
                runId
            );

            // Build result
            const duration = Date.now() - startTime;
            return {
                runId,
                status: this.determineStatus(result),
                output: this.extractOutput(result.stdout),
                tracePath: `.arc/traces/${runId}.jsonl`,
                duration
            };
        } catch (error: any) {
            const duration = Date.now() - startTime;
            return {
                runId: 'failed',
                status: 'failed',
                error: sanitizeErrorMessage(error),
                tracePath: '',
                duration
            };
        }
    }

    /**
     * Cancel running workflow
     */
    async cancelWorkflow(runId: string): Promise<boolean> {
        const process = this.runningProcesses.get(runId);
        if (!process) {
            return false;
        }

        process.kill('SIGTERM');
        this.runningProcesses.delete(runId);
        return true;
    }

    private async findExecutable(name: string): Promise<string | null> {
        // Implementation from original file
        return null;
    }

    private buildSwarmArgs(prompt: string, backend: string): string[] {
        return ['swarm', '--json', prompt, '--backend', backend];
    }

    private async executeCommand(
        command: string,
        args: string[],
        timeout: number,
        runId: string
    ): Promise<CommandResult> {
        // Implementation from original file
        return { stdout: '', stderr: '', exitCode: 0 };
    }

    private determineStatus(result: CommandResult): 'completed' | 'failed' {
        return result.exitCode === 0 ? 'completed' : 'failed';
    }

    private extractOutput(stdout: string): string {
        // Implementation from original file
        return stdout;
    }
}
```

**Step 2: Create trace-parser.ts**

```typescript
// packages/arc-extension/src/node/services/trace-parser.ts

import * as fs from 'fs-extra';
import * as path from 'path';
import { injectable } from '@theia/core/shared/inversify';
import {
    TraceData,
    TraceEvent,
    ArcError,
    ArcErrorCode
} from '../../common/arc-protocol';

export interface ParseOptions {
    maxEvents?: number;
    skipInvalid?: boolean;
}

@injectable()
export class TraceParser {
    /**
     * Parse JSONL trace file
     */
    async parseTrace(
        tracePath: string,
        options?: ParseOptions
    ): Promise<TraceData> {
        const startTime = Date.now();

        try {
            if (!await fs.pathExists(tracePath)) {
                throw new ArcError(
                    ArcErrorCode.NOT_FOUND,
                    `Trace file not found: ${tracePath}`
                );
            }

            const content = await fs.readFile(tracePath, 'utf-8');
            const events = this.parseJsonl(content, options);

            const duration = Date.now() - startTime;
            console.log(
                `[ARC Performance] Parsed trace in ${duration}ms ` +
                `(${events.length} events, ${content.split('\n').length} lines)`
            );

            return {
                runId: this.extractRunId(events),
                events,
                startedAt: this.extractStartTime(events),
                endedAt: this.extractEndTime(events),
                status: this.determineStatus(events)
            };
        } catch (error: any) {
            throw new ArcError(
                ArcErrorCode.PARSE_ERROR,
                `Failed to parse trace: ${error.message}`
            );
        }
    }

    /**
     * Parse JSONL content line by line
     */
    private parseJsonl(
        content: string,
        options?: ParseOptions
    ): TraceEvent[] {
        const lines = content.split('\n');
        const events: TraceEvent[] = [];
        const maxEvents = options?.maxEvents || Infinity;
        const skipInvalid = options?.skipInvalid !== false;

        for (let i = 0; i < lines.length && events.length < maxEvents; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            try {
                const event = JSON.parse(line);
                if (this.isValidEvent(event)) {
                    events.push(event);
                }
            } catch (error) {
                if (!skipInvalid) {
                    throw new Error(`Invalid JSON at line ${i + 1}: ${line}`);
                }
                // Skip invalid lines in lenient mode
            }
        }

        return events;
    }

    /**
     * Stream trace events (for large files)
     */
    async *streamTrace(tracePath: string): AsyncIterable<TraceEvent> {
        const stream = fs.createReadStream(tracePath, { encoding: 'utf-8' });
        let buffer = '';

        for await (const chunk of stream) {
            buffer += chunk;
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.trim()) continue;

                try {
                    const event = JSON.parse(line);
                    if (this.isValidEvent(event)) {
                        yield event;
                    }
                } catch (error) {
                    // Skip invalid lines
                }
            }
        }

        // Process remaining buffer
        if (buffer.trim()) {
            try {
                const event = JSON.parse(buffer);
                if (this.isValidEvent(event)) {
                    yield event;
                }
            } catch (error) {
                // Skip invalid final line
            }
        }
    }

    private isValidEvent(event: any): event is TraceEvent {
        return (
            event &&
            typeof event === 'object' &&
            typeof event.type === 'string' &&
            typeof event.timestamp === 'string'
        );
    }

    private extractRunId(events: TraceEvent[]): string {
        return events[0]?.runId || 'unknown';
    }

    private extractStartTime(events: TraceEvent[]): string {
        return events[0]?.timestamp || new Date().toISOString();
    }

    private extractEndTime(events: TraceEvent[]): string | undefined {
        return events[events.length - 1]?.timestamp;
    }

    private determineStatus(events: TraceEvent[]): 'completed' | 'failed' | 'running' {
        if (events.length === 0) return 'running';

        const lastEvent = events[events.length - 1];
        if (lastEvent.type === 'RUN_COMPLETED') return 'completed';
        if (lastEvent.type === 'RUN_FAILED') return 'failed';

        return 'running';
    }
}
```

**Step 3: Create workflow-detector.ts**

```typescript
// packages/arc-extension/src/node/services/workflow-detector.ts

import * as fs from 'fs-extra';
import * as path from 'path';
import { injectable } from '@theia/core/shared/inversify';
import { WorkflowInfo } from '../../common/arc-protocol';

@injectable()
export class WorkflowDetector {
    /**
     * Detect all workflows in workspace
     */
    async detectWorkflows(workspaceRoot: string): Promise<WorkflowInfo[]> {
        const workflows: WorkflowInfo[] = [];

        // Detect SwarmGraph CLI
        const swarmgraphCli = await this.detectSwarmGraphCli();
        if (swarmgraphCli) {
            workflows.push(swarmgraphCli);
        }

        // Detect LangGraph workflows
        const langgraphWorkflows = await this.detectLangGraphWorkflows(workspaceRoot);
        workflows.push(...langgraphWorkflows);

        return workflows;
    }

    private async detectSwarmGraphCli(): Promise<WorkflowInfo | null> {
        const cliPath = await this.findExecutable('swarmgraph');
        if (!cliPath) {
            return null;
        }

        return {
            type: 'swarmgraph',
            path: cliPath,
            name: 'SwarmGraph CLI',
            description: 'SwarmGraph command-line interface'
        };
    }

    private async detectLangGraphWorkflows(
        workspaceRoot: string
    ): Promise<WorkflowInfo[]> {
        const workflows: WorkflowInfo[] = [];

        // Search for Python files with LangGraph imports
        const pythonFiles = await this.findPythonFiles(workspaceRoot);

        for (const file of pythonFiles) {
            if (await this.isLangGraphFile(file)) {
                workflows.push({
                    type: 'langgraph',
                    path: file,
                    name: path.basename(file, '.py'),
                    description: 'LangGraph workflow'
                });
            }
        }

        return workflows;
    }

    private async findExecutable(name: string): Promise<string | null> {
        // Check PATH
        const pathEnv = process.env.PATH || '';
        const paths = pathEnv.split(path.delimiter);

        for (const dir of paths) {
            const fullPath = path.join(dir, name);
            if (await fs.pathExists(fullPath)) {
                return fullPath;
            }
        }

        return null;
    }

    private async findPythonFiles(dir: string): Promise<string[]> {
        const files: string[] = [];
        const entries = await fs.readdir(dir, { withFileTypes: true });

        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);

            // Skip common directories
            if (entry.isDirectory()) {
                if (this.shouldSkipDirectory(entry.name)) {
                    continue;
                }
                const subFiles = await this.findPythonFiles(fullPath);
                files.push(...subFiles);
            } else if (entry.name.endsWith('.py')) {
                files.push(fullPath);
            }
        }

        return files;
    }

    private shouldSkipDirectory(name: string): boolean {
        const skipDirs = [
            'node_modules',
            '.venv',
            'venv',
            '__pycache__',
            '.git',
            'dist',
            'build'
        ];
        return skipDirs.includes(name);
    }

    private async isLangGraphFile(filePath: string): Promise<boolean> {
        try {
            const content = await fs.readFile(filePath, 'utf-8');
            return (
                content.includes('from langgraph') ||
                content.includes('import langgraph')
            );
        } catch (error) {
            return false;
        }
    }
}
```

**Step 4: Create file-manager.ts**

```typescript
// packages/arc-extension/src/node/services/file-manager.ts

import * as fs from 'fs-extra';
import * as path from 'path';
import { injectable } from '@theia/core/shared/inversify';
import {
    TraceFile,
    ArcError,
    ArcErrorCode
} from '../../common/arc-protocol';
import { validateTraceId } from '../security-utils';

@injectable()
export class FileManager {
    /**
     * Get all trace files
     */
    async getTraceFiles(workspaceRoot: string): Promise<TraceFile[]> {
        const tracesDir = path.join(workspaceRoot, '.arc', 'traces');

        if (!await fs.pathExists(tracesDir)) {
            return [];
        }

        const files = await fs.readdir(tracesDir);
        const traces: TraceFile[] = [];

        for (const file of files) {
            if (!file.endsWith('.jsonl')) continue;

            const filePath = path.join(tracesDir, file);
            const stats = await fs.stat(filePath);

            traces.push({
                runId: path.basename(file, '.jsonl'),
                path: filePath,
                size: stats.size,
                createdAt: stats.birthtime.toISOString(),
                status: 'unknown'
            });
        }

        // Sort by creation time (newest first)
        traces.sort((a, b) => 
            new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        );

        return traces;
    }

    /**
     * Get trace file path
     */
    getTracePath(workspaceRoot: string, traceId: string): string {
        // Validate trace ID to prevent path traversal
        validateTraceId(traceId);

        return path.join(workspaceRoot, '.arc', 'traces', `${traceId}.jsonl`);
    }

    /**
     * Ensure traces directory exists
     */
    async ensureTracesDir(workspaceRoot: string): Promise<void> {
        const tracesDir = path.join(workspaceRoot, '.arc', 'traces');
        await fs.ensureDir(tracesDir);
    }

    /**
     * Delete trace file
     */
    async deleteTrace(workspaceRoot: string, traceId: string): Promise<void> {
        const tracePath = this.getTracePath(workspaceRoot, traceId);

        if (!await fs.pathExists(tracePath)) {
            throw new ArcError(
                ArcErrorCode.NOT_FOUND,
                `Trace not found: ${traceId}`
            );
        }

        await fs.remove(tracePath);
    }
}
```

**Step 5: Refactor arc-backend-service.ts (Orchestration)**

```typescript
// packages/arc-extension/src/node/arc-backend-service.ts (REFACTORED)

import { injectable, inject } from '@theia/core/shared/inversify';
import {
    ArcService,
    ExecutionOptions,
    ExecutionResult,
    TraceFile,
    TraceData,
    WorkflowInfo,
    ValidationResult,
    CancelResult
} from '../common/arc-protocol';
import { WorkflowExecutor } from './services/workflow-executor';
import { TraceParser } from './services/trace-parser';
import { WorkflowDetector } from './services/workflow-detector';
import { FileManager } from './services/file-manager';
import { validateWorkspaceRoot } from './security-utils';

/**
 * ARC Backend Service - Orchestration Layer
 * 
 * Delegates to specialized services for:
 * - Workflow execution
 * - Trace parsing
 * - Workflow detection
 * - File management
 */
@injectable()
export class ArcBackendService implements ArcService {
    private workspaceRoot: string;

    constructor(
        @inject(WorkflowExecutor) private executor: WorkflowExecutor,
        @inject(TraceParser) private parser: TraceParser,
        @inject(WorkflowDetector) private detector: WorkflowDetector,
        @inject(FileManager) private fileManager: FileManager
    ) {
        this.workspaceRoot = validateWorkspaceRoot(process.cwd());
    }

    async executeWorkflow(
        prompt: string,
        options?: ExecutionOptions
    ): Promise<ExecutionResult> {
        await this.fileManager.ensureTracesDir(this.workspaceRoot);
        return this.executor.executeWorkflow(prompt, {
            ...options,
            workspaceRoot: this.workspaceRoot
        });
    }

    async getTraces(): Promise<TraceFile[]> {
        return this.fileManager.getTraceFiles(this.workspaceRoot);
    }

    async getTrace(traceId: string): Promise<TraceData> {
        const tracePath = this.fileManager.getTracePath(
            this.workspaceRoot,
            traceId
        );
        return this.parser.parseTrace(tracePath);
    }

    async detectWorkflows(): Promise<WorkflowInfo[]> {
        return this.detector.detectWorkflows(this.workspaceRoot);
    }

    async cancelWorkflow(runId: string): Promise<CancelResult> {
        const cancelled = await this.executor.cancelWorkflow(runId);
        return {
            runId,
            cancelled,
            message: cancelled ? 'Workflow cancelled' : 'Workflow not found'
        };
    }

    async validateTrace(traceId: string): Promise<ValidationResult> {
        try {
            const tracePath = this.fileManager.getTracePath(
                this.workspaceRoot,
                traceId
            );
            await this.parser.parseTrace(tracePath);
            return {
                valid: true,
                traceId
            };
        } catch (error: any) {
            return {
                valid: false,
                traceId,
                error: error.message
            };
        }
    }

    async streamTrace(traceId: string): Promise<AsyncIterable<any>> {
        const tracePath = this.fileManager.getTracePath(
            this.workspaceRoot,
            traceId
        );
        return this.parser.streamTrace(tracePath);
    }
}
```

**Step 6: Update Dependency Injection**

```typescript
// packages/arc-extension/src/node/arc-extension-backend-module.ts

import { ContainerModule } from '@theia/core/shared/inversify';
import { ConnectionHandler, JsonRpcConnectionHandler } from '@theia/core';
import { ArcService } from '../common/arc-protocol';
import { ArcBackendService } from './arc-backend-service';
import { WorkflowExecutor } from './services/workflow-executor';
import { TraceParser } from './services/trace-parser';
import { WorkflowDetector } from './services/workflow-detector';
import { FileManager } from './services/file-manager';

export default new ContainerModule(bind => {
    // Bind services
    bind(WorkflowExecutor).toSelf().inSingletonScope();
    bind(TraceParser).toSelf().inSingletonScope();
    bind(WorkflowDetector).toSelf().inSingletonScope();
    bind(FileManager).toSelf().inSingletonScope();
    
    // Bind main service
    bind(ArcBackendService).toSelf().inSingletonScope();
    
    // Bind RPC connection
    bind(ConnectionHandler).toDynamicValue(ctx =>
        new JsonRpcConnectionHandler(ArcService, () => {
            return ctx.container.get(ArcBackendService);
        })
    ).inSingletonScope();
});
```

#### Verification

```bash
# Build
cd packages/arc-extension
pnpm build

# Run tests
pnpm test

# Check for errors
pnpm lint
```

#### References
- TypeScript dependency injection: https://github.com/inversify/InversifyJS
- Theia architecture: https://theia-ide.org/docs/architecture/
- SOLID principles: Single Responsibility Principle

---


### Task 3: Refactor arc-widget.tsx (3-4 days)

**Issue:** Monolithic React component with 974 lines
**File:** `packages/arc-extension/src/browser/arc-widget.tsx`
**Priority:** P0 - CRITICAL

#### Current Structure Analysis
```
arc-widget.tsx (974 lines)
├── State management (lines 27-92)
├── Workflow execution UI (lines 200-400)
├── Trace viewer UI (lines 400-600)
├── Workflow detection UI (lines 600-750)
├── Toast notifications (lines 750-850)
└── Keyboard shortcuts (lines 126-170)
```

#### Refactoring Plan

**New Structure:**
```
packages/arc-extension/src/browser/
├── arc-widget.tsx (150 lines) - Container only
├── components/
│   ├── WorkflowExecutionPanel.tsx (200 lines)
│   ├── TraceViewerPanel.tsx (250 lines)
│   ├── WorkflowDetectionPanel.tsx (150 lines)
│   ├── ToastNotifications.tsx (100 lines)
│   └── KeyboardShortcutsHelp.tsx (100 lines)
└── hooks/
    ├── useWorkflowExecution.ts (100 lines)
    ├── useTraceViewer.ts (100 lines)
    └── useToastNotifications.ts (50 lines)
```

#### Step-by-Step Implementation

**Step 1: Create Custom Hooks**

```typescript
// packages/arc-extension/src/browser/hooks/useWorkflowExecution.ts

import { useState, useCallback } from '@theia/core/shared/react';
import { ArcService, ExecutionResult } from '../../common/arc-protocol';

export interface WorkflowExecutionState {
    isExecuting: boolean;
    status: 'idle' | 'running' | 'completed' | 'failed';
    result?: ExecutionResult;
    error?: string;
}

export function useWorkflowExecution(arcService: ArcService) {
    const [state, setState] = useState<WorkflowExecutionState>({
        isExecuting: false,
        status: 'idle'
    });

    const executeWorkflow = useCallback(async (prompt: string) => {
        setState({
            isExecuting: true,
            status: 'running'
        });

        try {
            const result = await arcService.executeWorkflow(prompt);
            
            setState({
                isExecuting: false,
                status: result.status === 'failed' ? 'failed' : 'completed',
                result,
                error: result.error
            });

            return result;
        } catch (error: any) {
            setState({
                isExecuting: false,
                status: 'failed',
                error: error.message
            });
            throw error;
        }
    }, [arcService]);

    const reset = useCallback(() => {
        setState({
            isExecuting: false,
            status: 'idle'
        });
    }, []);

    return {
        ...state,
        executeWorkflow,
        reset
    };
}
```

```typescript
// packages/arc-extension/src/browser/hooks/useTraceViewer.ts

import { useState, useCallback, useEffect } from '@theia/core/shared/react';
import { ArcService, TraceFile, TraceData } from '../../common/arc-protocol';

export interface TraceViewerState {
    traces: TraceFile[];
    selectedTrace?: TraceFile;
    traceData?: TraceData;
    isLoading: boolean;
    filter: string;
}

export function useTraceViewer(arcService: ArcService) {
    const [state, setState] = useState<TraceViewerState>({
        traces: [],
        isLoading: false,
        filter: ''
    });

    const loadTraces = useCallback(async () => {
        setState(prev => ({ ...prev, isLoading: true }));

        try {
            const traces = await arcService.getTraces();
            setState(prev => ({
                ...prev,
                traces,
                isLoading: false
            }));
        } catch (error) {
            setState(prev => ({ ...prev, isLoading: false }));
            throw error;
        }
    }, [arcService]);

    const selectTrace = useCallback(async (trace: TraceFile) => {
        setState(prev => ({ ...prev, selectedTrace: trace, isLoading: true }));

        try {
            const traceData = await arcService.getTrace(trace.runId);
            setState(prev => ({
                ...prev,
                traceData,
                isLoading: false
            }));
        } catch (error) {
            setState(prev => ({ ...prev, isLoading: false }));
            throw error;
        }
    }, [arcService]);

    const setFilter = useCallback((filter: string) => {
        setState(prev => ({ ...prev, filter }));
    }, []);

    const filteredTraces = state.traces.filter(trace =>
        trace.runId.toLowerCase().includes(state.filter.toLowerCase())
    );

    return {
        ...state,
        filteredTraces,
        loadTraces,
        selectTrace,
        setFilter
    };
}
```

```typescript
// packages/arc-extension/src/browser/hooks/useToastNotifications.ts

import { useState, useCallback, useRef, useEffect } from '@theia/core/shared/react';

export interface Toast {
    id: string;
    type: 'success' | 'error' | 'info' | 'warning';
    message: string;
    timestamp: number;
}

export function useToastNotifications(autoHideDuration = 5000) {
    const [toasts, setToasts] = useState<Toast[]>([]);
    const timeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

    const addToast = useCallback((
        type: Toast['type'],
        message: string
    ) => {
        const id = `toast-${Date.now()}-${Math.random()}`;
        const toast: Toast = {
            id,
            type,
            message,
            timestamp: Date.now()
        };

        setToasts(prev => [...prev, toast]);

        // Auto-hide after duration
        const timeout = setTimeout(() => {
            removeToast(id);
        }, autoHideDuration);

        timeoutsRef.current.set(id, timeout);

        return id;
    }, [autoHideDuration]);

    const removeToast = useCallback((id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
        
        const timeout = timeoutsRef.current.get(id);
        if (timeout) {
            clearTimeout(timeout);
            timeoutsRef.current.delete(id);
        }
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            timeoutsRef.current.forEach(timeout => clearTimeout(timeout));
            timeoutsRef.current.clear();
        };
    }, []);

    return {
        toasts,
        addToast,
        removeToast
    };
}
```

**Step 2: Create WorkflowExecutionPanel Component**

```typescript
// packages/arc-extension/src/browser/components/WorkflowExecutionPanel.tsx

import * as React from '@theia/core/shared/react';
import { ExecutionResult } from '../../common/arc-protocol';

export interface WorkflowExecutionPanelProps {
    prompt: string;
    isExecuting: boolean;
    status: 'idle' | 'running' | 'completed' | 'failed';
    result?: ExecutionResult;
    error?: string;
    onPromptChange: (prompt: string) => void;
    onExecute: () => void;
}

export const WorkflowExecutionPanel: React.FC<WorkflowExecutionPanelProps> = ({
    prompt,
    isExecuting,
    status,
    result,
    error,
    onPromptChange,
    onExecute
}) => {
    return (
        <div className="arc-execution-panel">
            <h3>Workflow Execution</h3>
            
            <div className="arc-prompt-input">
                <label htmlFor="workflow-prompt">Prompt:</label>
                <textarea
                    id="workflow-prompt"
                    value={prompt}
                    onChange={(e) => onPromptChange(e.target.value)}
                    placeholder="Enter your workflow prompt..."
                    disabled={isExecuting}
                    rows={4}
                    aria-label="Workflow prompt input"
                />
            </div>

            <button
                onClick={onExecute}
                disabled={isExecuting || !prompt.trim()}
                className="arc-execute-button"
                aria-label="Execute workflow"
            >
                {isExecuting ? 'Executing...' : 'Execute Workflow'}
            </button>

            {status === 'running' && (
                <div className="arc-progress" role="status" aria-live="polite">
                    <div className="arc-progress-bar" />
                    <span>Executing workflow...</span>
                </div>
            )}

            {status === 'completed' && result && (
                <div className="arc-result arc-result-success" role="alert">
                    <h4>✓ Execution Completed</h4>
                    <div className="arc-result-details">
                        <p><strong>Run ID:</strong> {result.runId}</p>
                        <p><strong>Duration:</strong> {result.duration}ms</p>
                        {result.tracePath && (
                            <p><strong>Trace:</strong> {result.tracePath}</p>
                        )}
                        {result.output && (
                            <pre className="arc-output">{result.output}</pre>
                        )}
                    </div>
                </div>
            )}

            {status === 'failed' && (
                <div className="arc-result arc-result-error" role="alert">
                    <h4>✗ Execution Failed</h4>
                    <p className="arc-error-message">{error || 'Unknown error'}</p>
                    {result?.tracePath && (
                        <p><strong>Partial trace:</strong> {result.tracePath}</p>
                    )}
                </div>
            )}
        </div>
    );
};
```

**Step 3: Create TraceViewerPanel Component**

```typescript
// packages/arc-extension/src/browser/components/TraceViewerPanel.tsx

import * as React from '@theia/core/shared/react';
import { TraceFile, TraceData } from '../../common/arc-protocol';

export interface TraceViewerPanelProps {
    traces: TraceFile[];
    selectedTrace?: TraceFile;
    traceData?: TraceData;
    filter: string;
    isLoading: boolean;
    onFilterChange: (filter: string) => void;
    onSelectTrace: (trace: TraceFile) => void;
    onLoadTraces: () => void;
}

export const TraceViewerPanel: React.FC<TraceViewerPanelProps> = ({
    traces,
    selectedTrace,
    traceData,
    filter,
    isLoading,
    onFilterChange,
    onSelectTrace,
    onLoadTraces
}) => {
    return (
        <div className="arc-trace-panel">
            <div className="arc-trace-header">
                <h3>Trace Viewer</h3>
                <button
                    onClick={onLoadTraces}
                    disabled={isLoading}
                    className="arc-load-button"
                    aria-label="Load traces"
                >
                    {isLoading ? 'Loading...' : 'Load Traces'}
                </button>
            </div>

            <div className="arc-trace-filter">
                <input
                    type="text"
                    value={filter}
                    onChange={(e) => onFilterChange(e.target.value)}
                    placeholder="Filter traces..."
                    aria-label="Filter traces"
                />
            </div>

            <div className="arc-trace-list">
                {traces.length === 0 ? (
                    <p className="arc-empty-state">No traces found</p>
                ) : (
                    traces.map(trace => (
                        <div
                            key={trace.runId}
                            className={`arc-trace-item ${
                                selectedTrace?.runId === trace.runId ? 'selected' : ''
                            }`}
                            onClick={() => onSelectTrace(trace)}
                            role="button"
                            tabIndex={0}
                            aria-label={`Trace ${trace.runId}`}
                            onKeyPress={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                    onSelectTrace(trace);
                                }
                            }}
                        >
                            <div className="arc-trace-id">{trace.runId}</div>
                            <div className="arc-trace-meta">
                                <span className={`arc-status arc-status-${trace.status}`}>
                                    {trace.status}
                                </span>
                                <span className="arc-trace-time">
                                    {new Date(trace.createdAt).toLocaleString()}
                                </span>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {traceData && (
                <div className="arc-trace-details">
                    <h4>Trace Details</h4>
                    <div className="arc-trace-info">
                        <p><strong>Run ID:</strong> {traceData.runId}</p>
                        <p><strong>Status:</strong> {traceData.status}</p>
                        <p><strong>Events:</strong> {traceData.events.length}</p>
                        <p><strong>Started:</strong> {traceData.startedAt}</p>
                        {traceData.endedAt && (
                            <p><strong>Ended:</strong> {traceData.endedAt}</p>
                        )}
                    </div>

                    <div className="arc-trace-events">
                        <h5>Events</h5>
                        <div className="arc-events-list">
                            {traceData.events.map((event, index) => (
                                <div key={index} className="arc-event">
                                    <span className="arc-event-type">{event.type}</span>
                                    <span className="arc-event-time">
                                        {new Date(event.timestamp).toLocaleTimeString()}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
```

**Step 4: Create ToastNotifications Component**

```typescript
// packages/arc-extension/src/browser/components/ToastNotifications.tsx

import * as React from '@theia/core/shared/react';
import { Toast } from '../hooks/useToastNotifications';

export interface ToastNotificationsProps {
    toasts: Toast[];
    onDismiss: (id: string) => void;
}

export const ToastNotifications: React.FC<ToastNotificationsProps> = ({
    toasts,
    onDismiss
}) => {
    if (toasts.length === 0) {
        return null;
    }

    return (
        <div className="arc-toast-container" aria-live="polite" aria-atomic="true">
            {toasts.map(toast => (
                <div
                    key={toast.id}
                    className={`arc-toast arc-toast-${toast.type}`}
                    role="alert"
                >
                    <div className="arc-toast-content">
                        <span className="arc-toast-icon">
                            {toast.type === 'success' && '✓'}
                            {toast.type === 'error' && '✗'}
                            {toast.type === 'info' && 'ℹ'}
                            {toast.type === 'warning' && '⚠'}
                        </span>
                        <span className="arc-toast-message">{toast.message}</span>
                    </div>
                    <button
                        className="arc-toast-close"
                        onClick={() => onDismiss(toast.id)}
                        aria-label="Dismiss notification"
                    >
                        ×
                    </button>
                </div>
            ))}
        </div>
    );
};
```

**Step 5: Refactor arc-widget.tsx (Container)**

```typescript
// packages/arc-extension/src/browser/arc-widget.tsx (REFACTORED)

import { injectable, postConstruct, inject } from '@theia/core/shared/inversify';
import { ReactWidget } from '@theia/core/lib/browser/widgets/react-widget';
import { MessageService } from '@theia/core/lib/common/message-service';
import * as React from '@theia/core/shared/react';
import { ArcService } from '../common/arc-protocol';
import { WorkflowExecutionPanel } from './components/WorkflowExecutionPanel';
import { TraceViewerPanel } from './components/TraceViewerPanel';
import { ToastNotifications } from './components/ToastNotifications';
import { useWorkflowExecution } from './hooks/useWorkflowExecution';
import { useTraceViewer } from './hooks/useTraceViewer';
import { useToastNotifications } from './hooks/useToastNotifications';

/**
 * ARC Widget - Container Component
 * 
 * Orchestrates child components and manages global state.
 * Delegates UI rendering to specialized components.
 */
@injectable()
export class ArcWidget extends ReactWidget {
    static readonly ID = 'arc-widget';
    static readonly LABEL = 'ARC Studio';

    @inject(MessageService)
    protected readonly messageService!: MessageService;

    @inject(ArcService)
    protected readonly arcService!: ArcService;

    @postConstruct()
    protected init(): void {
        this.id = ArcWidget.ID;
        this.title.label = ArcWidget.LABEL;
        this.title.caption = ArcWidget.LABEL;
        this.title.closable = true;
        this.title.iconClass = 'fa fa-project-diagram';
        
        this.update();
    }

    protected render(): React.ReactNode {
        return <ArcWidgetContent arcService={this.arcService} />;
    }
}

/**
 * ARC Widget Content - Functional Component
 */
const ArcWidgetContent: React.FC<{ arcService: ArcService }> = ({ arcService }) => {
    const [prompt, setPrompt] = React.useState('');
    
    const workflowExecution = useWorkflowExecution(arcService);
    const traceViewer = useTraceViewer(arcService);
    const toasts = useToastNotifications();

    const handleExecute = React.useCallback(async () => {
        try {
            await workflowExecution.executeWorkflow(prompt);
            toasts.addToast('success', 'Workflow executed successfully');
            setPrompt('');
        } catch (error: any) {
            toasts.addToast('error', `Execution failed: ${error.message}`);
        }
    }, [prompt, workflowExecution, toasts]);

    const handleSelectTrace = React.useCallback(async (trace: any) => {
        try {
            await traceViewer.selectTrace(trace);
        } catch (error: any) {
            toasts.addToast('error', `Failed to load trace: ${error.message}`);
        }
    }, [traceViewer, toasts]);

    return (
        <div className="arc-widget-container">
            <WorkflowExecutionPanel
                prompt={prompt}
                isExecuting={workflowExecution.isExecuting}
                status={workflowExecution.status}
                result={workflowExecution.result}
                error={workflowExecution.error}
                onPromptChange={setPrompt}
                onExecute={handleExecute}
            />

            <TraceViewerPanel
                traces={traceViewer.filteredTraces}
                selectedTrace={traceViewer.selectedTrace}
                traceData={traceViewer.traceData}
                filter={traceViewer.filter}
                isLoading={traceViewer.isLoading}
                onFilterChange={traceViewer.setFilter}
                onSelectTrace={handleSelectTrace}
                onLoadTraces={traceViewer.loadTraces}
            />

            <ToastNotifications
                toasts={toasts.toasts}
                onDismiss={toasts.removeToast}
            />
        </div>
    );
};
```

#### Verification

```bash
# Build
cd packages/arc-extension
pnpm build

# Run tests
pnpm test

# Start application
cd ../..
pnpm start:browser
```

#### References
- React hooks: https://react.dev/reference/react
- Component composition: https://react.dev/learn/passing-props-to-a-component
- Lifting state up: https://react.dev/learn/sharing-state-between-components

---

### Task 4: Clean Up Build Artifacts (2 hours)

**Issue:** Multiple backup files and fix scripts
**Priority:** P0 - CRITICAL

#### Files to Delete

```bash
# Delete backup files
rm packages/arc-extension/src/node/arc-backend-service.ts.backup
rm packages/arc-browser-app/gen-webpack.config.js.bak2
rm packages/arc-browser-app/gen-webpack.config.js.bak
rm packages/arc-browser-app/gen-webpack.config.js.backup
```

#### Update .gitignore

```bash
# Add to .gitignore
echo "*.backup" >> .gitignore
echo "*.bak" >> .gitignore
echo "*.bak2" >> .gitignore
```

#### Document Build Issues

Create `docs/BUILD_ISSUES.md`:

```markdown
# Build Issues and Solutions

## Webpack Configuration Issues

### Issue 1: Monaco Editor ESM Build
**Problem:** Monaco editor fails to build with webpack due to ESM module resolution.

**Solution:** Added direct dependency in package.json:
\`\`\`json
"@theia/monaco-editor-core": "^1.45.0"
\`\`\`

### Issue 2: Missing Theia Dependencies
**Problem:** Generated server.js requires missing dependencies.

**Solution:** Added required dependencies:
\`\`\`json
"@theia/markers": "^1.45.0",
"@theia/process": "^1.45.0",
"@theia/variable-resolver": "^1.45.0",
"@theia/outline-view": "^1.45.0"
\`\`\`

### Issue 3: File Search Unavailable
**Problem:** @theia/file-search incompatible with Node.js v25 (ripgrep issue).

**Status:** Known limitation - file search feature unavailable.

**Workaround:** Accept missing feature or downgrade Node.js to v18.
```

#### Consolidate Fix Scripts

Create single `scripts/post-build-fix.sh`:

```bash
#!/bin/bash
# Post-build fixes for ARC Studio

set -e

echo "Applying post-build fixes..."

# Fix 1: Patch server.js for file-search
if [ -f "packages/arc-browser-app/src-gen/backend/server.js" ]; then
    echo "Patching server.js for file-search..."
    sed -i.bak "s/require('@theia\/file-search')/try { require('@theia\/file-search') } catch(e) { console.warn('file-search unavailable') }/g" \
        packages/arc-browser-app/src-gen/backend/server.js
    rm packages/arc-browser-app/src-gen/backend/server.js.bak
fi

echo "Post-build fixes complete!"
```

Make executable:
```bash
chmod +x scripts/post-build-fix.sh
```

Update `package.json`:
```json
{
  "scripts": {
    "build": "pnpm -r run build && bash scripts/post-build-fix.sh"
  }
}
```

#### Verification

```bash
# Clean build
pnpm clean
pnpm build

# Verify no backup files
find . -name "*.backup" -o -name "*.bak" -o -name "*.bak2" | grep -v node_modules

# Should return nothing
```

---

### Task 5: Enable TypeScript Strict Mode (2-3 days)

**Issue:** Base tsconfig has strict mode disabled
**Files:** `tsconfig.base.json`, all package tsconfigs
**Priority:** P0 - CRITICAL

#### Current Configuration

```json
// tsconfig.base.json
{
  "compilerOptions": {
    "strict": false,
    "noImplicitAny": false
  }
}
```

#### Migration Strategy

**Phase 1: Enable per-package (Incremental)**

Start with smallest packages first:

```json
// packages/arc-protocol-ts/tsconfig.json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true
  }
}
```

**Phase 2: Fix Type Errors**

Common patterns to fix:

1. **Implicit any parameters:**
```typescript
// Before
function handleEvent(event) {
    console.log(event.type);
}

// After
function handleEvent(event: Event) {
    console.log(event.type);
}
```

2. **Null/undefined checks:**
```typescript
// Before
function getName(user) {
    return user.name;
}

// After
function getName(user: User | null): string {
    return user?.name ?? 'Unknown';
}
```

3. **Property initialization:**
```typescript
// Before
class MyClass {
    private value: string;
}

// After
class MyClass {
    private value: string = '';
    // or
    private value!: string; // definite assignment assertion
}
```

4. **Replace any types:**
```typescript
// Before
const data: any = JSON.parse(response);

// After
interface ResponseData {
    id: string;
    name: string;
}
const data: ResponseData = JSON.parse(response);
```

**Phase 3: Enable in Base Config**

After all packages are fixed:

```json
// tsconfig.base.json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "declaration": true,
    "sourceMap": true,
    "experimentalDecorators": true,
    "jsx": "react"
  }
}
```

#### Implementation Order

1. `arc-protocol-ts` (smallest, 2 files)
2. `arc-test-fixtures` (minimal)
3. `arc-ag-ui` (medium)
4. `arc-extension` (largest, most work)
5. `arc-browser-app` (configuration only)

#### Verification

```bash
# Check each package
cd packages/arc-protocol-ts
pnpm build
# Fix any errors

cd ../arc-extension
pnpm build
# Fix any errors

# Run all tests
cd ../..
pnpm test
```

#### References
- TypeScript strict mode: https://www.typescriptlang.org/tsconfig#strict
- Migration guide: https://www.typescriptlang.org/docs/handbook/migrating-from-javascript.html

---


## P1 Tasks - High Priority

### Task 6: Add ESLint and Prettier (1-2 days)

**Issue:** No code quality tools configured
**Priority:** P1 - HIGH

#### Install Dependencies

```bash
# Root level
pnpm add -D -w eslint prettier
pnpm add -D -w @typescript-eslint/parser @typescript-eslint/eslint-plugin
pnpm add -D -w eslint-plugin-react eslint-plugin-react-hooks
pnpm add -D -w eslint-config-prettier
```

#### ESLint Configuration

Create `.eslintrc.json`:

```json
{
  "root": true,
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "ecmaVersion": 2020,
    "sourceType": "module",
    "ecmaFeatures": {
      "jsx": true
    },
    "project": "./tsconfig.json"
  },
  "plugins": [
    "@typescript-eslint",
    "react",
    "react-hooks"
  ],
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:@typescript-eslint/recommended-type-checked",
    "plugin:react/recommended",
    "plugin:react-hooks/recommended",
    "prettier"
  ],
  "rules": {
    "@typescript-eslint/no-explicit-any": "warn",
    "@typescript-eslint/no-unused-vars": ["error", {
      "argsIgnorePattern": "^_",
      "varsIgnorePattern": "^_"
    }],
    "@typescript-eslint/explicit-function-return-type": "off",
    "@typescript-eslint/explicit-module-boundary-types": "off",
    "@typescript-eslint/no-non-null-assertion": "warn",
    "react/react-in-jsx-scope": "off",
    "react/prop-types": "off",
    "no-console": ["warn", { "allow": ["warn", "error"] }]
  },
  "settings": {
    "react": {
      "version": "detect"
    }
  },
  "overrides": [
    {
      "files": ["**/*.test.ts", "**/*.test.tsx"],
      "rules": {
        "@typescript-eslint/no-explicit-any": "off"
      }
    }
  ]
}
```

#### Prettier Configuration

Create `.prettierrc.json`:

```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 4,
  "useTabs": false,
  "arrowParens": "avoid",
  "endOfLine": "lf"
}
```

Create `.prettierignore`:

```
node_modules
dist
lib
build
coverage
*.min.js
*.bundle.js
src-gen
.venv
__pycache__
```

#### Update package.json Scripts

```json
{
  "scripts": {
    "lint": "eslint . --ext .ts,.tsx",
    "lint:fix": "eslint . --ext .ts,.tsx --fix",
    "format": "prettier --write \"**/*.{ts,tsx,json,md}\"",
    "format:check": "prettier --check \"**/*.{ts,tsx,json,md}\""
  }
}
```

#### Pre-commit Hook (Optional)

Install husky:

```bash
pnpm add -D -w husky lint-staged
```

Create `.husky/pre-commit`:

```bash
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

pnpm lint-staged
```

Create `.lintstagedrc.json`:

```json
{
  "*.{ts,tsx}": [
    "eslint --fix",
    "prettier --write"
  ],
  "*.{json,md}": [
    "prettier --write"
  ]
}
```

#### Fix Existing Issues

Run and fix:

```bash
# Check issues
pnpm lint

# Auto-fix what can be fixed
pnpm lint:fix

# Format all files
pnpm format

# Manually fix remaining issues
```

Common fixes needed:

1. **Remove console.log:**
```typescript
// Before
console.log('[ARC Performance] Widget initialization');

// After
// Use proper logging or remove
```

2. **Fix any types:**
```typescript
// Before
const data: any = result;

// After
const data: ExecutionResult = result;
```

3. **Add missing return types:**
```typescript
// Before
async function loadTraces() {
    return await arcService.getTraces();
}

// After
async function loadTraces(): Promise<TraceFile[]> {
    return await arcService.getTraces();
}
```

#### Verification

```bash
# Run linting
pnpm lint

# Should pass with no errors

# Check formatting
pnpm format:check

# Should pass
```

#### References
- ESLint TypeScript: https://typescript-eslint.io/
- Prettier: https://prettier.io/docs/en/configuration.html
- React ESLint: https://github.com/jsx-eslint/eslint-plugin-react

---

### Task 7: Improve Test Coverage (3-4 days)

**Issue:** Test coverage at 63.86%, target is 70%
**Priority:** P1 - HIGH

#### Current Coverage

```
Statements:   63.86% (387/606)
Branches:     63.69% (186/292)
Functions:    56.97% (49/86)  ⚠️ BELOW TARGET
Lines:        64.92% (372/573)
```

#### Gap Analysis

Need to add:
- 37 more statements (6.14%)
- 37 more functions (13.03%)

#### Strategy

**1. Add jsdom for Widget Tests**

Install jsdom:

```bash
cd packages/arc-extension
pnpm add -D jsdom @types/jsdom
```

Update `jest.config.js`:

```javascript
module.exports = {
    preset: 'ts-jest',
    testEnvironment: 'jsdom', // Changed from 'node'
    testMatch: ['**/__tests__/**/*.test.ts', '**/__tests__/**/*.test.tsx'],
    collectCoverageFrom: [
        'src/**/*.{ts,tsx}',
        '!src/**/*.d.ts',
        '!src/**/index.ts'
    ],
    coverageDirectory: 'coverage',
    coverageThreshold: {
        global: {
            statements: 70,
            branches: 65,
            functions: 70,
            lines: 70
        }
    },
    setupFilesAfterEnv: ['<rootDir>/jest.setup.js']
};
```

Create `jest.setup.js`:

```javascript
// Mock Theia dependencies
global.ResizeObserver = jest.fn().mockImplementation(() => ({
    observe: jest.fn(),
    unobserve: jest.fn(),
    disconnect: jest.fn(),
}));

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
    })),
});
```

**2. Add Widget Component Tests**

Create `src/browser/components/__tests__/WorkflowExecutionPanel.test.tsx`:

```typescript
import * as React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { WorkflowExecutionPanel } from '../WorkflowExecutionPanel';

describe('WorkflowExecutionPanel', () => {
    const defaultProps = {
        prompt: '',
        isExecuting: false,
        status: 'idle' as const,
        onPromptChange: jest.fn(),
        onExecute: jest.fn()
    };

    it('renders prompt input', () => {
        render(<WorkflowExecutionPanel {...defaultProps} />);
        expect(screen.getByLabelText('Workflow prompt input')).toBeInTheDocument();
    });

    it('calls onPromptChange when typing', () => {
        const onPromptChange = jest.fn();
        render(<WorkflowExecutionPanel {...defaultProps} onPromptChange={onPromptChange} />);
        
        const input = screen.getByLabelText('Workflow prompt input');
        fireEvent.change(input, { target: { value: 'test prompt' } });
        
        expect(onPromptChange).toHaveBeenCalledWith('test prompt');
    });

    it('disables execute button when prompt is empty', () => {
        render(<WorkflowExecutionPanel {...defaultProps} prompt="" />);
        expect(screen.getByLabelText('Execute workflow')).toBeDisabled();
    });

    it('enables execute button when prompt is provided', () => {
        render(<WorkflowExecutionPanel {...defaultProps} prompt="test" />);
        expect(screen.getByLabelText('Execute workflow')).not.toBeDisabled();
    });

    it('calls onExecute when button clicked', () => {
        const onExecute = jest.fn();
        render(<WorkflowExecutionPanel {...defaultProps} prompt="test" onExecute={onExecute} />);
        
        fireEvent.click(screen.getByLabelText('Execute workflow'));
        
        expect(onExecute).toHaveBeenCalled();
    });

    it('shows progress when executing', () => {
        render(<WorkflowExecutionPanel {...defaultProps} status="running" isExecuting={true} />);
        expect(screen.getByText('Executing workflow...')).toBeInTheDocument();
    });

    it('shows success result', () => {
        const result = {
            runId: 'run-123',
            status: 'completed' as const,
            duration: 1000,
            tracePath: '.arc/traces/run-123.jsonl'
        };
        
        render(<WorkflowExecutionPanel {...defaultProps} status="completed" result={result} />);
        
        expect(screen.getByText('✓ Execution Completed')).toBeInTheDocument();
        expect(screen.getByText(/run-123/)).toBeInTheDocument();
    });

    it('shows error result', () => {
        render(<WorkflowExecutionPanel {...defaultProps} status="failed" error="Test error" />);
        
        expect(screen.getByText('✗ Execution Failed')).toBeInTheDocument();
        expect(screen.getByText('Test error')).toBeInTheDocument();
    });
});
```

**3. Add Hook Tests**

Create `src/browser/hooks/__tests__/useWorkflowExecution.test.ts`:

```typescript
import { renderHook, act } from '@testing-library/react';
import { useWorkflowExecution } from '../useWorkflowExecution';

describe('useWorkflowExecution', () => {
    const mockArcService = {
        executeWorkflow: jest.fn()
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('initializes with idle state', () => {
        const { result } = renderHook(() => useWorkflowExecution(mockArcService as any));
        
        expect(result.current.isExecuting).toBe(false);
        expect(result.current.status).toBe('idle');
    });

    it('executes workflow successfully', async () => {
        const mockResult = {
            runId: 'run-123',
            status: 'completed',
            duration: 1000
        };
        mockArcService.executeWorkflow.mockResolvedValue(mockResult);

        const { result } = renderHook(() => useWorkflowExecution(mockArcService as any));

        await act(async () => {
            await result.current.executeWorkflow('test prompt');
        });

        expect(result.current.status).toBe('completed');
        expect(result.current.result).toEqual(mockResult);
    });

    it('handles execution failure', async () => {
        mockArcService.executeWorkflow.mockRejectedValue(new Error('Test error'));

        const { result } = renderHook(() => useWorkflowExecution(mockArcService as any));

        await act(async () => {
            try {
                await result.current.executeWorkflow('test prompt');
            } catch (error) {
                // Expected
            }
        });

        expect(result.current.status).toBe('failed');
        expect(result.current.error).toBe('Test error');
    });

    it('resets state', async () => {
        const { result } = renderHook(() => useWorkflowExecution(mockArcService as any));

        act(() => {
            result.current.reset();
        });

        expect(result.current.status).toBe('idle');
        expect(result.current.result).toBeUndefined();
    });
});
```

**4. Add Service Tests**

Create `src/node/services/__tests__/workflow-executor.test.ts`:

```typescript
import { WorkflowExecutor } from '../workflow-executor';

describe('WorkflowExecutor', () => {
    let executor: WorkflowExecutor;

    beforeEach(() => {
        executor = new WorkflowExecutor();
    });

    describe('executeWorkflow', () => {
        it('validates prompt', async () => {
            await expect(
                executor.executeWorkflow('')
            ).rejects.toThrow('Invalid prompt');
        });

        it('sanitizes prompt', async () => {
            // Test that dangerous characters are removed
            const result = await executor.executeWorkflow('test; rm -rf /');
            expect(result.status).toBe('failed');
        });

        it('returns execution result', async () => {
            const result = await executor.executeWorkflow('test prompt');
            
            expect(result).toHaveProperty('runId');
            expect(result).toHaveProperty('status');
            expect(result).toHaveProperty('duration');
        });
    });

    describe('cancelWorkflow', () => {
        it('returns false for non-existent workflow', async () => {
            const cancelled = await executor.cancelWorkflow('non-existent');
            expect(cancelled).toBe(false);
        });
    });
});
```

**5. Install Testing Dependencies**

```bash
cd packages/arc-extension
pnpm add -D @testing-library/react @testing-library/react-hooks
pnpm add -D @testing-library/jest-dom
```

#### Run Tests and Check Coverage

```bash
# Run tests with coverage
pnpm test --coverage

# Check coverage report
open coverage/lcov-report/index.html
```

#### Verification

```bash
# Coverage should be >= 70%
pnpm test --coverage

# All tests should pass
pnpm test
```

#### References
- Jest with jsdom: https://jestjs.io/docs/configuration#testenvironment-string
- Testing Library: https://testing-library.com/docs/react-testing-library/intro/
- React hooks testing: https://react-hooks-testing-library.com/

---

### Task 8: Optimize Dev Build Size (2-3 days)

**Issue:** Dev build is 520MB vs 38MB production
**Priority:** P1 - HIGH

#### Current State

```
Development: 520 MB
Production:   38 MB
Ratio:       13.7x
```

#### Analysis

Install webpack-bundle-analyzer:

```bash
cd packages/arc-browser-app
pnpm add -D webpack-bundle-analyzer
```

Update `webpack.config.js`:

```javascript
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

module.exports = {
    // ... existing config
    
    plugins: [
        // Add analyzer in development
        process.env.ANALYZE && new BundleAnalyzerPlugin({
            analyzerMode: 'static',
            reportFilename: 'bundle-report.html',
            openAnalyzer: false
        })
    ].filter(Boolean)
};
```

Run analysis:

```bash
ANALYZE=true pnpm build
open lib/bundle-report.html
```

#### Optimization Strategies

**1. Enable Incremental Builds**

Update `tsconfig.json`:

```json
{
  "compilerOptions": {
    "incremental": true,
    "tsBuildInfoFile": ".tsbuildinfo"
  }
}
```

Add to `.gitignore`:
```
.tsbuildinfo
```

**2. Optimize Source Maps**

Update `webpack.config.js`:

```javascript
module.exports = {
    mode: process.env.NODE_ENV === 'production' ? 'production' : 'development',
    
    devtool: process.env.NODE_ENV === 'production' 
        ? false 
        : 'eval-cheap-module-source-map', // Faster than 'source-map'
    
    // ... rest of config
};
```

**3. Split Chunks**

```javascript
module.exports = {
    optimization: {
        splitChunks: {
            chunks: 'all',
            cacheGroups: {
                vendor: {
                    test: /[\\/]node_modules[\\/]/,
                    name: 'vendors',
                    priority: 10
                },
                monaco: {
                    test: /[\\/]node_modules[\\/]monaco-editor[\\/]/,
                    name: 'monaco',
                    priority: 20
                },
                theia: {
                    test: /[\\/]node_modules[\\/]@theia[\\/]/,
                    name: 'theia',
                    priority: 15
                }
            }
        }
    }
};
```

**4. Enable Caching**

```javascript
module.exports = {
    cache: {
        type: 'filesystem',
        cacheDirectory: path.resolve(__dirname, '.webpack-cache'),
        buildDependencies: {
            config: [__filename]
        }
    }
};
```

Add to `.gitignore`:
```
.webpack-cache
```

**5. Lazy Load Monaco**

```typescript
// Instead of direct import
import * as monaco from 'monaco-editor';

// Use dynamic import
const loadMonaco = async () => {
    const monaco = await import('monaco-editor');
    return monaco;
};
```

**6. Remove Duplicate Dependencies**

Check for duplicates:

```bash
pnpm list --depth=0 | grep -E "iconv-lite|other-package"
```

Use pnpm overrides in root `package.json`:

```json
{
  "pnpm": {
    "overrides": {
      "iconv-lite": "0.6.3"
    }
  }
}
```

#### Expected Results

After optimizations:

```
Development: ~200 MB (60% reduction)
Production:   38 MB (unchanged)
Build time:  -40% (with caching)
```

#### Verification

```bash
# Clean build
pnpm clean
pnpm build

# Check sizes
du -sh packages/arc-browser-app/lib

# Should be significantly smaller
```

#### References
- Webpack optimization: https://webpack.js.org/guides/build-performance/
- Bundle analyzer: https://github.com/webpack-contrib/webpack-bundle-analyzer
- Code splitting: https://webpack.js.org/guides/code-splitting/

---


## P2 Tasks - Medium Priority

### Task 9: Consolidate Documentation (2 days)

**Issue:** 83 markdown files, some outdated
**Priority:** P2 - MEDIUM

#### Create Documentation Index

Create `docs/INDEX.md`:

```markdown
# ARC Studio Documentation Index

**Last Updated:** 2026-05-13

## Getting Started

- [README](../README.md) - Project overview and quick start
- [Installation Guide](INSTALLATION.md) - Detailed installation instructions
- [Development Guide](DEVELOPMENT.md) - Development workflow and setup

## Architecture

- [Architecture Overview](ARCHITECTURE.md) - System architecture and components
- [API Reference](API.md) - REST API and JSON-RPC protocol
- [Implementation Decisions](IMPLEMENTATION_DECISIONS.md) - Architectural decisions

## Security

- [Security Guide](SECURITY.md) - Security implementation and best practices
- [Security Audit Report](../SECURITY_AUDIT_REPORT.md) - Vulnerability assessment
- [Security Quick Reference](SECURITY_QUICK_REFERENCE.md) - Quick security checklist

## Development

- [Contributing Guide](../CONTRIBUTING.md) - How to contribute
- [Testing Guide](TESTING.md) - Test setup and execution
- [Build Issues](BUILD_ISSUES.md) - Known build issues and solutions
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

## Features

- [Runtimes](RUNTIMES.md) - Supported agent runtimes
- [Extensions](EXTENSIONS.md) - Theia extension development
- [Roadmap](ROADMAP.md) - Future development plans

## Phase Documentation (Archive)

Historical phase documents have been moved to `docs/archive/`:

- [Phase 1: Bootstrap](archive/PHASE_1_BOOTSTRAP.md)
- [Phase 2: Research](archive/PHASE_2_RESEARCH.md)
- [Phase 3: Discovery](archive/PHASE_3_DISCOVERY.md)
- [Phase 4: Implementation](archive/PHASE_4_COMPLETE.md)
- [Phase 5: Integration](archive/PHASE_5_COMPLETE.md)
- [Phase 6: Alpha](archive/PHASE_6_ALPHA.md)
- [Phase 7: Handover](archive/PHASE_7_HANDOVER.md)

## Reports

- [Implementation Summary](../IMPLEMENTATION_SUMMARY.md)
- [Critical Review](../CRITICAL_REVIEW_GENSPARK.md)
- [GenSpark Handover](../GENSPARK_HANDOVER.md)
- [Performance Report](../PHASE_5_PERFORMANCE_REPORT.md)

## Status

- [Current Status](../STATUS.md) - What's working, what's not
- [Changelog](../CHANGELOG.md) - Version history
```

#### Archive Old Phase Documents

```bash
# Create archive directory
mkdir -p docs/archive

# Move phase documents
mv PHASE_*.md docs/archive/
mv PROMPT_PHASE_*.md docs/archive/
mv README_PHASE_*.md docs/archive/

# Keep only current status documents in root
```

#### Update Documentation Dates

Add to each doc:

```markdown
---
**Last Updated:** 2026-05-13  
**Status:** Current | Archived | Deprecated
---
```

#### Remove Duplicate Content

Identify and merge:
- Multiple "getting started" sections
- Duplicate API documentation
- Overlapping architecture descriptions

#### Verification

```bash
# Check all docs have dates
grep -L "Last Updated" docs/*.md

# Check for broken links
find docs -name "*.md" -exec grep -H "\[.*\](.*)" {} \; | grep -v "http"
```

---

### Task 10: Implement Missing Features (2-3 weeks)

**Issue:** LangGraph streaming, rate limiting, authentication not implemented
**Priority:** P2 - MEDIUM

#### Feature 1: LangGraph Streaming

**Current:** One-shot `.invoke()` only  
**Target:** Streaming events support

```python
# python/src/agent_runtime_cockpit/adapters/langgraph.py

async def stream_workflow(self, workflow_path: str, input_data: dict):
    """Stream LangGraph workflow events"""
    
    # Load workflow
    workflow = self._load_workflow(workflow_path)
    
    # Stream events
    async for event in workflow.astream_events(input_data):
        yield {
            "type": self._map_event_type(event["event"]),
            "timestamp": datetime.utcnow().isoformat(),
            "data": event["data"]
        }

def _map_event_type(self, event_type: str) -> str:
    """Map LangGraph event types to ARC event types"""
    mapping = {
        "on_chain_start": "NODE_STARTED",
        "on_chain_end": "NODE_COMPLETED",
        "on_chain_error": "NODE_FAILED",
        "on_llm_start": "LLM_STARTED",
        "on_llm_end": "LLM_COMPLETED"
    }
    return mapping.get(event_type, "UNKNOWN")
```

#### Feature 2: Rate Limiting

**Implementation:** Use FastAPI middleware

```python
# python/src/agent_runtime_cockpit/web/middleware.py

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host
        
        # Clean old requests
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=1)
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > cutoff
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later."
            )
        
        # Record request
        self.requests[client_ip].append(now)
        
        # Process request
        response = await call_next(request)
        return response

# Add to server.py
from .middleware import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
```

#### Feature 3: Authentication

**Implementation:** API key authentication

```python
# python/src/agent_runtime_cockpit/web/auth.py

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import os

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Validate API key"""
    expected_key = os.getenv("ARC_API_KEY")
    
    if not expected_key:
        # API key not configured, allow all
        return "anonymous"
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    if api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    return api_key

# Use in routes
from .auth import get_api_key

@app.post("/api/execute")
async def execute_workflow(
    request: ExecuteRequest,
    api_key: str = Depends(get_api_key)
):
    # Protected endpoint
    pass
```

#### Verification

```bash
# Test LangGraph streaming
cd python
uv run pytest tests/adapters/test_langgraph_streaming.py

# Test rate limiting
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}' \
  --repeat 100

# Should get 429 after 60 requests

# Test authentication
export ARC_API_KEY="test-key-123"
curl -X POST http://localhost:8000/api/execute \
  -H "X-API-Key: test-key-123" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}'

# Should succeed

curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test"}'

# Should fail with 401
```

---

## Implementation Order

### Week 1: Critical Fixes (P0)

**Day 1:**
- [ ] Task 1: Fix Python build (1 hour)
- [ ] Task 4: Clean up build artifacts (2 hours)
- [ ] Start Task 2: Create service modules (4 hours)

**Day 2-3:**
- [ ] Task 2: Complete backend refactoring (2 days)

**Day 4-5:**
- [ ] Task 3: Complete widget refactoring (2 days)

### Week 2: Type Safety & Quality (P0-P1)

**Day 1-2:**
- [ ] Task 5: Enable TypeScript strict mode (2 days)

**Day 3:**
- [ ] Task 6: Add ESLint and Prettier (1 day)

**Day 4-5:**
- [ ] Task 7: Improve test coverage (2 days)

### Week 3: Optimization (P1)

**Day 1-2:**
- [ ] Task 8: Optimize dev build size (2 days)

**Day 3-4:**
- [ ] Task 9: Consolidate documentation (2 days)

**Day 5:**
- [ ] Buffer for issues and testing

### Week 4+: Features (P2)

**Optional - Can be deferred:**
- [ ] Task 10: Implement missing features (2-3 weeks)

---

## Testing Strategy

### Unit Tests

Run after each task:

```bash
# TypeScript tests
cd packages/arc-extension
pnpm test

# Python tests
cd python
uv run pytest -q
```

### Integration Tests

Run after completing related tasks:

```bash
# Full test suite
pnpm test

# E2E tests
pnpm test:e2e
```

### Manual Testing

After major refactoring:

1. **Start application:**
   ```bash
   pnpm start:browser
   ```

2. **Test workflow execution:**
   - Open ARC widget
   - Enter prompt: "hello world"
   - Click "Execute Workflow"
   - Verify execution completes

3. **Test trace viewing:**
   - Click "Load Traces"
   - Select a trace
   - Verify trace details display

4. **Test keyboard shortcuts:**
   - Press Ctrl+E (execute)
   - Press Ctrl+L (load traces)
   - Press Ctrl+S (scan workspace)
   - Press Ctrl+H (help)

### Performance Testing

After optimization tasks:

```bash
# Measure build time
time pnpm build

# Measure bundle size
du -sh packages/arc-browser-app/lib

# Measure startup time
time pnpm start:browser
```

---

## Verification Checklist

### P0 Tasks

- [ ] Python build succeeds: `cd python && uv run pytest`
- [ ] No backup files: `find . -name "*.backup" -o -name "*.bak"`
- [ ] Backend service < 500 lines: `wc -l packages/arc-extension/src/node/arc-backend-service.ts`
- [ ] Widget < 500 lines: `wc -l packages/arc-extension/src/browser/arc-widget.tsx`
- [ ] TypeScript strict mode enabled: `grep "strict" tsconfig.base.json`
- [ ] All tests pass: `pnpm test`
- [ ] Build succeeds: `pnpm build`

### P1 Tasks

- [ ] ESLint configured: `pnpm lint`
- [ ] Prettier configured: `pnpm format:check`
- [ ] Test coverage >= 70%: `pnpm test --coverage`
- [ ] Dev build < 300MB: `du -sh packages/arc-browser-app/lib`
- [ ] Build time < 2 minutes: `time pnpm build`

### P2 Tasks

- [ ] Documentation index exists: `cat docs/INDEX.md`
- [ ] Phase docs archived: `ls docs/archive/`
- [ ] All docs have dates: `grep "Last Updated" docs/*.md`
- [ ] Features implemented (optional)

### Application Testing

- [ ] Application starts: `pnpm start:browser`
- [ ] Workflow execution works
- [ ] Trace viewing works
- [ ] Workspace scanning works
- [ ] Keyboard shortcuts work
- [ ] No console errors
- [ ] No memory leaks

---

## Code Examples Reference

### TypeScript Patterns

**Dependency Injection:**
```typescript
@injectable()
export class MyService {
    constructor(
        @inject(DependencyService) private dep: DependencyService
    ) {}
}
```

**React Hooks:**
```typescript
const [state, setState] = useState<StateType>(initialState);

const callback = useCallback(() => {
    // Logic
}, [dependencies]);

useEffect(() => {
    // Side effect
    return () => {
        // Cleanup
    };
}, [dependencies]);
```

**Error Handling:**
```typescript
try {
    const result = await operation();
    return result;
} catch (error: any) {
    throw new ArcError(
        ArcErrorCode.OPERATION_FAILED,
        sanitizeErrorMessage(error)
    );
}
```

### Python Patterns

**Async Generators:**
```python
async def stream_events(self) -> AsyncIterator[Event]:
    async for event in source:
        yield self.transform(event)
```

**Context Managers:**
```python
async with self.get_session() as session:
    result = await session.execute(query)
    return result
```

**Type Hints:**
```python
def process_data(
    input_data: dict[str, Any],
    options: Optional[ProcessOptions] = None
) -> ProcessResult:
    pass
```

---

## Resources and References

### Official Documentation

- **TypeScript:** https://www.typescriptlang.org/docs/
- **React:** https://react.dev/learn
- **Theia:** https://theia-ide.org/docs/
- **FastAPI:** https://fastapi.tiangolo.com/
- **Python Packaging:** https://packaging.python.org/

### Tools

- **ESLint TypeScript:** https://typescript-eslint.io/
- **Prettier:** https://prettier.io/
- **Jest:** https://jestjs.io/
- **pytest:** https://docs.pytest.org/
- **Webpack:** https://webpack.js.org/

### Best Practices

- **SOLID Principles:** https://en.wikipedia.org/wiki/SOLID
- **React Patterns:** https://react.dev/learn/thinking-in-react
- **TypeScript Best Practices:** https://typescript-eslint.io/rules/
- **Python Best Practices:** https://peps.python.org/pep-0008/

### Security

- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
- **Command Injection:** https://owasp.org/www-community/attacks/Command_Injection
- **Path Traversal:** https://owasp.org/www-community/attacks/Path_Traversal

---

## Troubleshooting

### Common Issues

**Issue: TypeScript compilation fails after refactoring**

Solution:
```bash
# Clean and rebuild
pnpm clean
rm -rf node_modules
pnpm install
pnpm build
```

**Issue: Tests fail with module not found**

Solution:
```bash
# Update jest config
# Add moduleNameMapper in jest.config.js
moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1'
}
```

**Issue: Widget doesn't render after refactoring**

Solution:
```typescript
// Check React imports
import * as React from '@theia/core/shared/react';

// Check component export
export const MyComponent: React.FC<Props> = (props) => {
    return <div>...</div>;
};
```

**Issue: Python build still fails**

Solution:
```bash
# Check directory structure
ls -la python/src/

# Should have agent_runtime_cockpit directory

# Verify pyproject.toml
cat python/pyproject.toml | grep packages
```

**Issue: Dev build still too large**

Solution:
```bash
# Analyze bundle
ANALYZE=true pnpm build
open packages/arc-browser-app/lib/bundle-report.html

# Look for:
# - Duplicate dependencies
# - Large unminified files
# - Unnecessary source maps
```

---

## Success Criteria

### P0 Tasks Complete When:

1. ✅ Python package builds without errors
2. ✅ No backup files in repository
3. ✅ Backend service split into 5 modules, each < 500 lines
4. ✅ Widget split into 6 components, each < 250 lines
5. ✅ TypeScript strict mode enabled globally
6. ✅ All 159 tests passing
7. ✅ Application starts and runs without errors

### P1 Tasks Complete When:

1. ✅ ESLint runs without errors
2. ✅ Prettier formats all files consistently
3. ✅ Test coverage >= 70% (statements, functions, lines)
4. ✅ Dev build < 300MB (40% reduction)
5. ✅ Build time < 2 minutes with caching

### P2 Tasks Complete When:

1. ✅ Documentation index created
2. ✅ Phase documents archived
3. ✅ All docs have "Last Updated" dates
4. ✅ No duplicate content in docs
5. ✅ (Optional) Missing features implemented

### Overall Success:

- ✅ All P0 tasks completed
- ✅ At least 80% of P1 tasks completed
- ✅ Application is production-ready
- ✅ Code quality improved
- ✅ Technical debt reduced
- ✅ Team can maintain codebase easily

---

## Timeline Summary

| Week | Focus | Tasks | Status |
|------|-------|-------|--------|
| 1 | Critical Fixes | P0: Tasks 1-4 | Required |
| 2 | Type Safety & Quality | P0-P1: Tasks 5-7 | Required |
| 3 | Optimization | P1: Tasks 8-9 | Recommended |
| 4+ | Features | P2: Task 10 | Optional |

**Minimum Viable:** Complete Week 1-2 (P0 tasks)  
**Recommended:** Complete Week 1-3 (P0 + P1 tasks)  
**Full Implementation:** Complete all weeks (P0 + P1 + P2 tasks)

---

## Contact and Support

**For Questions:**
- Review `CRITICAL_REVIEW_GENSPARK.md` for detailed analysis
- Check `GENSPARK_HANDOVER.md` for original handover
- Refer to `docs/` for architecture and API documentation

**For Issues:**
- Check `docs/TROUBLESHOOTING.md`
- Review `docs/BUILD_ISSUES.md`
- Check GitHub Issues (if applicable)

**Implementation Notes:**
- This plan is designed for Kimi 2.6 AI implementation
- Each task includes complete code examples
- All references are to official documentation
- Security considerations are included throughout
- Verification steps ensure quality

---

**Document Version:** 1.0  
**Created:** 2026-05-13  
**For:** Kimi 2.6 AI Implementation  
**Based On:** CRITICAL_REVIEW_GENSPARK.md

**END OF IMPLEMENTATION PLAN**
