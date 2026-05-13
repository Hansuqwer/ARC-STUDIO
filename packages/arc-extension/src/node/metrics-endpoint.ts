import { injectable } from '@theia/core/shared/inversify';
import { BackendApplicationContribution } from '@theia/core/lib/node';
import { Application } from 'express';

@injectable()
export class ArcMetricsEndpoint implements BackendApplicationContribution {
    private metrics = {
        requests: 0,
        executions: 0,
        errors: 0,
        startTime: Date.now(),
    };

    configure(app: Application): void {
        app.get('/api/metrics', (req, res) => {
            res.json({
                uptime: Math.floor((Date.now() - this.metrics.startTime) / 1000),
                requests: this.metrics.requests,
                executions: this.metrics.executions,
                errors: this.metrics.errors,
                memory: process.memoryUsage(),
            });
        });
    }

    incrementRequests() { this.metrics.requests++; }
    incrementExecutions() { this.metrics.executions++; }
    incrementErrors() { this.metrics.errors++; }
}
