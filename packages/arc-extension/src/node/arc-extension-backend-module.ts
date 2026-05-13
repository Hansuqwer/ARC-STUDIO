/**
 * ARC Studio Backend Module
 * 
 * This module provides the backend services for ARC Studio,
 * including SwarmGraph execution and trace file management.
 */

import { ContainerModule } from '@theia/core/shared/inversify';
import { ConnectionHandler, JsonRpcConnectionHandler } from '@theia/core';
import { ArcBackendService } from './arc-backend-service';
import { ArcServicePath } from '../common/arc-protocol';

export default new ContainerModule(bind => {
    // Bind the backend service
    bind(ArcBackendService).toSelf().inSingletonScope();

    // Bind the RPC connection handler
    bind(ConnectionHandler).toDynamicValue(ctx =>
        new JsonRpcConnectionHandler(ArcServicePath, () => {
            return ctx.container.get(ArcBackendService);
        })
    ).inSingletonScope();
});
