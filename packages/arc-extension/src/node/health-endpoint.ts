import { injectable } from '@theia/core/shared/inversify';
import { BackendApplicationContribution } from '@theia/core/lib/node';
import { Application } from 'express';
import * as fs from 'fs-extra';
import * as path from 'path';
import { execFile } from 'child_process';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

@injectable()
export class ArcHealthEndpoint implements BackendApplicationContribution {
    configure(app: Application): void {
        app.get('/api/health', async (req, res) => {
            try {
                const checks = {
                    status: 'ok',
                    timestamp: new Date().toISOString(),
                    version: '0.6.0-alpha',
                    uptime: process.uptime(),
                    checks: {
                        filesystem: await this.checkFilesystem(),
                        swarmgraph: await this.checkSwarmGraph(),
                        traces: await this.checkTraces(),
                    }
                };

                const allOk = Object.values(checks.checks).every(
                    (c: any) => c.status === 'ok' || c.status === 'degraded'
                );
                res.status(allOk ? 200 : 503).json(checks);
            } catch (error) {
                res.status(500).json({
                    status: 'error',
                    timestamp: new Date().toISOString(),
                    error: 'Health check failed'
                });
            }
        });
    }

    private async checkFilesystem(): Promise<{ status: string; details?: string }> {
        try {
            const workspaceRoot = process.cwd();
            const accessible = await fs.pathExists(workspaceRoot);
            return accessible 
                ? { status: 'ok' }
                : { status: 'error', details: 'Workspace not accessible' };
        } catch (error) {
            return { status: 'error', details: 'Filesystem check failed' };
        }
    }

    private async checkSwarmGraph(): Promise<{ status: string; details?: string }> {
        try {
            const cli = process.env.ARC_SWARMGRAPH_CLI || 'swarmgraph';
            await execFileAsync(cli, ['--version'], { timeout: 5000 });
            return { status: 'ok' };
        } catch (error) {
            return { status: 'degraded', details: 'SwarmGraph CLI not available' };
        }
    }

    private async checkTraces(): Promise<{ status: string; details?: string }> {
        try {
            const tracesDir = path.join(process.cwd(), '.arc', 'traces');
            const exists = await fs.pathExists(tracesDir);
            return exists 
                ? { status: 'ok' }
                : { status: 'ok', details: 'Traces directory not yet created' };
        } catch (error) {
            return { status: 'error', details: 'Traces check failed' };
        }
    }
}
