/**
 * ARC Studio Backend Module
 * 
 * This module provides the backend services for ARC Studio,
 * including SwarmGraph execution and trace file management.
 */

import { ContainerModule } from '@theia/core/shared/inversify';
import { ConnectionHandler, JsonRpcConnectionHandler } from '@theia/core';
import { BackendApplicationContribution } from '@theia/core/lib/node';
import { ArcBackendService } from './arc-backend-service';
import { ArcServicePath } from '../common/arc-protocol';
import { ArcHealthEndpoint } from './health-endpoint';
import { ArcMetricsEndpoint } from './metrics-endpoint';

export default new ContainerModule(bind => {
    // Bind the backend service
    bind(ArcBackendService).toSelf().inSingletonScope();

    // Bind the RPC connection handler
    bind(ConnectionHandler).toDynamicValue(ctx =>
        new JsonRpcConnectionHandler(ArcServicePath, () => {
            return ctx.container.get(ArcBackendService);
        })
    ).inSingletonScope();

    // Bind health endpoint
    bind(ArcHealthEndpoint).toSelf().inSingletonScope();
    bind(BackendApplicationContribution).toService(ArcHealthEndpoint);

    // Bind metrics endpoint
    bind(ArcMetricsEndpoint).toSelf().inSingletonScope();
    bind(BackendApplicationContribution).toService(ArcMetricsEndpoint);
});
