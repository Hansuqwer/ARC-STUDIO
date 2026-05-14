/**
 * Backend Services Unit Tests
 *
 * Tests for the specialized backend service modules.
 */

import { WorkflowExecutor } from '../services/workflow-executor';
import { TraceParser } from '../services/trace-parser';
import { FileManager } from '../services/file-manager';
import { WorkflowDetector } from '../services/workflow-detector';
import { ArcError, ArcErrorCode } from '../../common/arc-protocol';
import * as fs from 'fs-extra';
import * as path from 'path';
import * as os from 'os';
// Mock child_process spawn
jest.mock('child_process', () => ({
    spawn: jest.fn()
}));

const mockSpawn = jest.requireMock('child_process').spawn;

describe('WorkflowExecutor', () => {
    let executor: WorkflowExecutor;

    beforeEach(() => {
        executor = new WorkflowExecutor();
        jest.clearAllMocks();
    });

    describe('executeWorkflow validation', () => {
        it('should throw ArcError for empty prompt', async () => {
            await expect(executor.executeWorkflow('')).rejects.toThrow(ArcError);
            await expect(executor.executeWorkflow('')).rejects.toMatchObject({
                code: ArcErrorCode.INVALID_INPUT
            });
        });

        it('should throw ArcError for whitespace-only prompt', async () => {
            await expect(executor.executeWorkflow('   ')).rejects.toThrow(ArcError);
            await expect(executor.executeWorkflow('   ')).rejects.toMatchObject({
                code: ArcErrorCode.INVALID_INPUT
            });
        });

        it('should throw ArcError for overly long prompt', async () => {
            const longPrompt = 'a'.repeat(10001);
            await expect(executor.executeWorkflow(longPrompt)).rejects.toThrow(ArcError);
            await expect(executor.executeWorkflow(longPrompt)).rejects.toMatchObject({
                code: ArcErrorCode.INVALID_INPUT
            });
        });

        it('should throw ArcError for non-string prompt', async () => {
            await expect(executor.executeWorkflow(null as unknown as string)).rejects.toThrow(ArcError);
        });

        it('should return failed result when swarmgraph CLI is not found', async () => {
            // Mock 'which' command to return empty (CLI not found)
            mockSpawn.mockImplementation(() => {
                const mockChild = {
                    stdout: { on: jest.fn() },
                    stderr: { on: jest.fn() },
                    on: jest.fn((event, handler) => {
                        if (event === 'close') {
                            setTimeout(() => handler(1), 0);
                        }
                    }),
                    kill: jest.fn()
                };
                return mockChild;
            });

            const result = await executor.executeWorkflow('test prompt');
            expect(result.status).toBe('failed');
            expect(result.error).toContain('swarmgraph');
        });
    });

    describe('executeWorkflow with ARC_SWARMGRAPH_CLI', () => {
        let tempDir: string;
        let mockCliPath: string;

        beforeEach(async () => {
            tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-exec-test-'));
            mockCliPath = path.join(tempDir, 'mock-swarmgraph');
            await fs.writeFile(mockCliPath, '#!/bin/bash\necho "mock"');
            process.env.ARC_SWARMGRAPH_CLI = mockCliPath;
        });

        afterEach(async () => {
            delete process.env.ARC_SWARMGRAPH_CLI;
            await fs.remove(tempDir);
        });

        it('should use ARC_SWARMGRAPH_CLI when set', async () => {
            mockSpawn.mockImplementation((cmd: string, args: string[]) => {
                const mockChild = {
                    stdout: { on: jest.fn((event, handler) => {
                        if (event === 'data') {
                            setTimeout(() => handler(Buffer.from(JSON.stringify({ id: 'run-123', status: 'completed' }))), 0);
                        }
                    }) },
                    stderr: { on: jest.fn() },
                    on: jest.fn((event, handler) => {
                        if (event === 'close') {
                            setTimeout(() => handler(0), 0);
                        }
                    }),
                    kill: jest.fn()
                };
                return mockChild;
            });

            const result = await executor.executeWorkflow('test prompt', { workspaceRoot: tempDir });
            expect(result.status).toBe('completed');
            expect(mockSpawn).toHaveBeenCalledWith(
                mockCliPath,
                expect.arrayContaining(['swarm', '--json']),
                expect.any(Object)
            );
        });
    });

    describe('executeWorkflow with workspace-local CLI', () => {
        let tempDir: string;
        let localCliPath: string;

        beforeEach(async () => {
            tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-local-test-'));
            localCliPath = path.join(tempDir, 'swarmgraph');
            await fs.writeFile(localCliPath, '#!/bin/bash\necho "local"');
            process.env.ARC_TRUST_WORKSPACE_LAUNCHER = '1';
        });

        afterEach(async () => {
            delete process.env.ARC_TRUST_WORKSPACE_LAUNCHER;
            await fs.remove(tempDir);
        });

        it('should use workspace-local CLI under ARC_TRUST_WORKSPACE_LAUNCHER=1', async () => {
            // Mock 'which' to fail (no system CLI)
            let callCount = 0;
            mockSpawn.mockImplementation((cmd: string, args: string[]) => {
                callCount++;
                if (cmd === 'which' && callCount === 1) {
                    // First call: 'which swarmgraph' fails
                    const mockChild = {
                        stdout: { on: jest.fn() },
                        stderr: { on: jest.fn() },
                        on: jest.fn((event, handler) => {
                            if (event === 'close') {
                                setTimeout(() => handler(1), 0);
                            }
                        }),
                        kill: jest.fn()
                    };
                    return mockChild;
                } else {
                    // Second call: actual execution with local CLI
                    const mockChild = {
                        stdout: { on: jest.fn((event, handler) => {
                            if (event === 'data') {
                                setTimeout(() => handler(Buffer.from(JSON.stringify({ id: 'run-local', status: 'completed' }))), 0);
                            }
                        }) },
                        stderr: { on: jest.fn() },
                        on: jest.fn((event, handler) => {
                            if (event === 'close') {
                                setTimeout(() => handler(0), 0);
                            }
                        }),
                        kill: jest.fn()
                    };
                    return mockChild;
                }
            });

            const result = await executor.executeWorkflow('test prompt', { workspaceRoot: tempDir });
            expect(result.status).toBe('completed');
            expect(mockSpawn).toHaveBeenCalledWith(
                localCliPath,
                expect.arrayContaining(['swarm', '--json']),
                expect.any(Object)
            );
        });
    });

    describe('executeWorkflow timeout', () => {
        let tempDir: string;
        let mockCliPath: string;

        beforeEach(async () => {
            tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-timeout-test-'));
            mockCliPath = path.join(tempDir, 'mock-swarmgraph');
            await fs.writeFile(mockCliPath, '#!/bin/bash\necho "mock"');
            process.env.ARC_SWARMGRAPH_CLI = mockCliPath;
        });

        afterEach(async () => {
            delete process.env.ARC_SWARMGRAPH_CLI;
            await fs.remove(tempDir);
        });

        it('should timeout after specified duration', async () => {
            mockSpawn.mockImplementation(() => {
                const mockChild = {
                    stdout: { on: jest.fn() },
                    stderr: { on: jest.fn() },
                    on: jest.fn((event, handler) => {
                        // Never close to simulate long-running process
                    }),
                    kill: jest.fn()
                };
                return mockChild;
            });

            const result = await executor.executeWorkflow('test prompt', { timeout: 100 });
            expect(result.status).toBe('failed');
            expect(result.error).toContain('timed out');
        });
    });

    describe('executeWorkflow output parsing', () => {
        let tempDir: string;
        let mockCliPath: string;

        beforeEach(async () => {
            tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-parse-test-'));
            mockCliPath = path.join(tempDir, 'mock-swarmgraph');
            await fs.writeFile(mockCliPath, '#!/bin/bash\necho "mock"');
            process.env.ARC_SWARMGRAPH_CLI = mockCliPath;
        });

        afterEach(async () => {
            delete process.env.ARC_SWARMGRAPH_CLI;
            await fs.remove(tempDir);
        });

        it('should parse successful execution output', async () => {
            mockSpawn.mockImplementation(() => {
                const mockChild = {
                    stdout: { on: jest.fn((event, handler) => {
                        if (event === 'data') {
                            setTimeout(() => handler(Buffer.from(JSON.stringify({ 
                                id: 'run-success', 
                                status: 'completed',
                                output: 'Task completed successfully'
                            }))), 0);
                        }
                    }) },
                    stderr: { on: jest.fn() },
                    on: jest.fn((event, handler) => {
                        if (event === 'close') {
                            setTimeout(() => handler(0), 0);
                        }
                    }),
                    kill: jest.fn()
                };
                return mockChild;
            });

            const result = await executor.executeWorkflow('test prompt');
            expect(result.status).toBe('completed');
            expect(result.runId).toBe('run-success');
            expect(result.output).toContain('Task completed successfully');
        });

        it('should parse failed execution output', async () => {
            mockSpawn.mockImplementation(() => {
                const mockChild = {
                    stdout: { on: jest.fn((event, handler) => {
                        if (event === 'data') {
                            setTimeout(() => handler(Buffer.from(JSON.stringify({ 
                                id: 'run-fail', 
                                status: 'failed',
                                error: 'Execution failed'
                            }))), 0);
                        }
                    }) },
                    stderr: { on: jest.fn() },
                    on: jest.fn((event, handler) => {
                        if (event === 'close') {
                            setTimeout(() => handler(1), 0);
                        }
                    }),
                    kill: jest.fn()
                };
                return mockChild;
            });

            const result = await executor.executeWorkflow('test prompt');
            expect(result.status).toBe('failed');
            expect(result.error).toContain('Execution failed');
        });
    });

    describe('cancelWorkflow', () => {
        it('should return failure for unknown run ID', async () => {
            const result = await executor.cancelWorkflow('nonexistent-run-id');
            expect(result.success).toBe(false);
            expect(result.message).toContain('No running process');
        });

        it('should cancel running workflow', async () => {
            const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-cancel-test-'));
            const mockCliPath = path.join(tempDir, 'mock-swarmgraph');
            await fs.writeFile(mockCliPath, '#!/bin/bash\necho "mock"');
            process.env.ARC_SWARMGRAPH_CLI = mockCliPath;

            const mockKill = jest.fn();
            mockSpawn.mockImplementation(() => {
                const mockChild = {
                    stdout: { on: jest.fn() },
                    stderr: { on: jest.fn() },
                    on: jest.fn((event, handler) => {
                        // Never close - simulates long-running process
                    }),
                    kill: mockKill
                };
                return mockChild;
            });

            // Start execution (don't await - it will hang)
            const execPromise = executor.executeWorkflow('long running task', { timeout: 60000 });

            // Wait for process to register
            await new Promise(resolve => setTimeout(resolve, 100));

            // Access the internal runningProcesses map to get the run ID
            const processes = (executor as any).runningProcesses as Map<string, any>;
            const keys = Array.from(processes.keys());
            expect(keys.length).toBeGreaterThan(0);
            const runId = keys[0];

            // Cancel it
            const cancelResult = await executor.cancelWorkflow(runId);
            expect(cancelResult.success).toBe(true);
            expect(mockKill).toHaveBeenCalledWith('SIGTERM');

            // Verify process was removed
            expect(processes.has(runId)).toBe(false);

            // Clean up
            delete process.env.ARC_SWARMGRAPH_CLI;
            await fs.remove(tempDir);
        });
    });
});

describe('TraceParser', () => {
    let parser: TraceParser;
    let tempDir: string;

    beforeEach(async () => {
        parser = new TraceParser();
        tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-parse-test-'));
    });

    afterEach(async () => {
        await fs.remove(tempDir);
    });

    describe('parseJsonlContent', () => {
        it('should return null for empty content', () => {
            const result = parser.parseJsonlContent('');
            expect(result).toBeNull();
        });

        it('should return null for whitespace-only content', () => {
            const result = parser.parseJsonlContent('   \n  \n  ');
            expect(result).toBeNull();
        });

        it('should parse single JSON object', () => {
            const content = JSON.stringify({
                id: 'test-run',
                status: 'completed',
                events: [{ type: 'MESSAGE', timestamp: new Date().toISOString(), runId: 'test-run', sequence: 0, data: {} }]
            });
            const result = parser.parseJsonlContent(content);
            expect(result).not.toBeNull();
            expect(result!.id).toBe('test-run');
            expect(result!.status).toBe('completed');
        });

        it('should parse LangGraph-style JSONL (multi-line)', () => {
            const content = [
                JSON.stringify({ type: 'RUN_STARTED', timestamp: new Date().toISOString(), run_id: 'lg-run' }),
                JSON.stringify({ type: 'RUN_COMPLETED', timestamp: new Date().toISOString() }),
            ].join('\n');
            const result = parser.parseJsonlContent(content);
            expect(result).not.toBeNull();
            expect(result!.id).toBe('lg-run');
            expect(result!.events).toHaveLength(2);
            expect(result!.status).toBe('completed');
        });

        it('should handle malformed lines gracefully', () => {
            const content = [
                JSON.stringify({ type: 'EVENT', timestamp: new Date().toISOString() }),
                'not valid json',
                JSON.stringify({ type: 'RUN_COMPLETED', timestamp: new Date().toISOString() }),
            ].join('\n');
            const result = parser.parseJsonlContent(content);
            expect(result).not.toBeNull();
            expect(result!.events).toHaveLength(2);
        });

        it('should use fallbackId when no ID found', () => {
            const content = JSON.stringify({ status: 'completed' });
            const result = parser.parseJsonlContent(content, 'fallback-id');
            expect(result).not.toBeNull();
            expect(result!.id).toContain('fallback-id');
        });
    });

    describe('parseTrace', () => {
        it('should throw ArcError for missing file', async () => {
            await expect(parser.parseTrace(path.join(tempDir, 'nonexistent.jsonl')))
                .rejects.toThrow(ArcError);
        });
    });

    describe('normalizeStatus', () => {
        it('should normalize success variants', () => {
            expect(parser.normalizeStatus('completed')).toBe('completed');
            expect(parser.normalizeStatus('success')).toBe('completed');
            expect(parser.normalizeStatus('ok')).toBe('completed');
        });

        it('should normalize failure variants', () => {
            expect(parser.normalizeStatus('failed')).toBe('failed');
            expect(parser.normalizeStatus('error')).toBe('failed');
            expect(parser.normalizeStatus('failure')).toBe('failed');
        });

        it('should return unknown for unknown status', () => {
            expect(parser.normalizeStatus('running')).toBe('unknown');
            expect(parser.normalizeStatus('')).toBe('unknown');
            expect(parser.normalizeStatus(undefined as unknown as string)).toBe('unknown');
        });
    });

    describe('isValidEvent', () => {
        it('should validate proper event structure', () => {
            expect(parser.isValidEvent({ type: 'MESSAGE', timestamp: new Date().toISOString() })).toBe(true);
        });

        it('should reject invalid events', () => {
            expect(parser.isValidEvent(undefined)).toBeFalsy();
            expect(parser.isValidEvent({})).toBeFalsy();
            expect(parser.isValidEvent({ type: 'MESSAGE' })).toBeFalsy();
        });

        it('should treat null as falsy', () => {
            expect(parser.isValidEvent(null)).toBeFalsy();
        });
    });
});

describe('FileManager', () => {
    let fileManager: FileManager;
    let tempDir: string;

    beforeEach(async () => {
        fileManager = new FileManager();
        tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-fm-test-'));
    });

    afterEach(async () => {
        await fs.remove(tempDir);
    });

    describe('getTraceFiles', () => {
        it('should return empty array when traces directory does not exist', async () => {
            const result = await fileManager.getTraceFiles(tempDir);
            expect(result).toEqual([]);
        });

        it('should list trace files in .arc/traces', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);
            await fs.writeFile(
                path.join(tracesDir, 'run-1.jsonl'),
                JSON.stringify({ id: 'run-1', status: 'completed' })
            );
            const result = await fileManager.getTraceFiles(tempDir);
            expect(result).toHaveLength(1);
            expect(result[0].id).toBe('run-1');
        });

        it('should only include .jsonl files', async () => {
            const tracesDir = path.join(tempDir, '.arc', 'traces');
            await fs.ensureDir(tracesDir);
            await fs.writeFile(path.join(tracesDir, 'run-1.jsonl'), JSON.stringify({ id: 'run-1' }));
            await fs.writeFile(path.join(tracesDir, 'readme.txt'), 'not a trace');
            const result = await fileManager.getTraceFiles(tempDir);
            expect(result).toHaveLength(1);
        });
    });

    describe('getTracePath', () => {
        it('should return correct path for trace ID', () => {
            const result = fileManager.getTracePath(tempDir, 'run-sg-abc123');
            expect(result).toContain('.arc/traces/run-sg-abc123.jsonl');
        });

        it('should throw on invalid trace ID', () => {
            expect(() => fileManager.getTracePath(tempDir, '../evil')).toThrow();
        });
    });

    describe('ensureTracesDir', () => {
        it('should create traces directory', async () => {
            await fileManager.ensureTracesDir(tempDir);
            const exists = await fs.pathExists(path.join(tempDir, '.arc', 'traces'));
            expect(exists).toBe(true);
        });
    });
});

describe('WorkflowDetector', () => {
    let detector: WorkflowDetector;
    let tempDir: string;

    beforeEach(async () => {
        detector = new WorkflowDetector();
        tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'arc-wd-test-'));
        // Mock spawn for WorkflowDetector's whichExecutable calls
        // The 'which' command returns exit code 1 (not found) for 'swarmgraph'
        mockSpawn.mockImplementation((cmd: string, args: string[]) => {
            if (cmd === 'which') {
                const mockChild: any = {
                    stdout: { on: jest.fn() },
                    stderr: { on: jest.fn() },
                    on: jest.fn((event: string, handler: Function) => {
                        if (event === 'close') {
                            setTimeout(() => handler(1), 0); // exit code 1 = not found
                        }
                    }),
                    kill: jest.fn(),
                };
                return mockChild;
            }
            return { stdout: { on: jest.fn() }, stderr: { on: jest.fn() }, on: jest.fn(), kill: jest.fn() };
        });
    });

    afterEach(async () => {
        await fs.remove(tempDir);
    });

    describe('detectWorkflows', () => {
        it('should return empty array for empty workspace', async () => {
            const result = await detector.detectWorkflows(tempDir);
            expect(Array.isArray(result)).toBe(true);
        });

        it('should detect local swarmgraph executable', async () => {
            const swarmgraphPath = path.join(tempDir, 'swarmgraph');
            await fs.writeFile(swarmgraphPath, '#!/bin/bash\necho "swarmgraph"');
            await fs.chmod(swarmgraphPath, 0o755);
            const result = await detector.detectWorkflows(tempDir);
            expect(result.length).toBeGreaterThanOrEqual(1);
            expect(result.some(w => w.type === 'swarmgraph')).toBe(true);
        });

        it('should detect LangGraph Python files', async () => {
            const pyDir = path.join(tempDir, 'workflows');
            await fs.ensureDir(pyDir);
            await fs.writeFile(
                path.join(pyDir, 'agent.py'),
                'from langgraph.graph import StateGraph\n' +
                'graph = StateGraph(state_schema)\n' +
                'graph.compile()\n'
            );
            const result = await detector.detectWorkflows(tempDir);
            expect(result.length).toBeGreaterThanOrEqual(1);
            expect(result.some(w => w.type === 'langgraph')).toBe(true);
        });

        it('should skip Python files without langgraph', async () => {
            await fs.writeFile(path.join(tempDir, 'hello.py'), 'print("hello")');
            const result = await detector.detectWorkflows(tempDir);
            expect(result.every(w => w.type !== 'langgraph')).toBe(true);
        });
    });
});
