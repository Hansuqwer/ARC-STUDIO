/**
 * ARC Studio Backend Module
 *
 * This module provides the backend services for ARC Studio,
 * including SwarmGraph execution and trace file management.
 */

import { ContainerModule } from '@theia/core/shared/inversify';
import { ConnectionHandler, JsonRpcConnectionHandler } from '@theia/core';
import { ArcBackendService } from './arc-backend-service';
import { WorkflowExecutor } from './services/workflow-executor';
import { TraceParser } from './services/trace-parser';
import { WorkflowDetector } from './services/workflow-detector';
import { FileManager } from './services/file-manager';
import { ConfigService } from './services/config-service';
import { RunLifecycleService } from './services/run-lifecycle-service';
import { AuditBridgeService } from './services/audit-bridge-service';
import { ArcServicePath } from '../common/arc-protocol';

export default new ContainerModule(bind => {
    // Bind workspace root for service injection
    bind('WorkspaceRoot').toDynamicValue(() => {
        return process.cwd();
    }).inSingletonScope();

    // Bind specialized services
    bind(WorkflowExecutor).toSelf().inSingletonScope();
    bind(TraceParser).toSelf().inSingletonScope();
    bind(WorkflowDetector).toSelf().inSingletonScope();
    bind(FileManager).toSelf().inSingletonScope();

    // Bind new domain services (P2 refactoring)
    bind(ConfigService).toSelf().inSingletonScope();
    bind(RunLifecycleService).toSelf().inSingletonScope();
    bind(AuditBridgeService).toSelf().inSingletonScope();

    // Bind the backend service with explicit service dependencies.
    bind(ArcBackendService).toDynamicValue(ctx => new ArcBackendService(
        ctx.container.get(WorkflowExecutor),
        ctx.container.get(TraceParser),
        ctx.container.get(WorkflowDetector),
        ctx.container.get(FileManager),
        ctx.container.get(ConfigService),
        ctx.container.get(RunLifecycleService),
        ctx.container.get(AuditBridgeService)
    )).inSingletonScope();

    // Bind the RPC connection handler
    bind(ConnectionHandler).toDynamicValue(ctx =>
        new JsonRpcConnectionHandler(ArcServicePath, () => {
            return ctx.container.get(ArcBackendService);
        })
    ).inSingletonScope();
});
