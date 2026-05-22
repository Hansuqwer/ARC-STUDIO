# arc-backend-service split plan

## Domains observed (from method analysis)

| Method (current)            | Domain          | New home                     |
|-----------------------------|-----------------|------------------------------|
| getProviderStatus           | config          | ConfigService                |
| getProviderCatalog          | config          | ConfigService                |
| getProviderDiagnostics      | config          | ConfigService                |
| getProviderQuota            | config          | ConfigService                |
| resetProviderQuota          | config          | ConfigService                |
| runGatedProviderAction      | config          | ConfigService                |
| setProviderKeyRef           | config          | ConfigService                |
| unsetProviderKeyRef         | config          | ConfigService                |
| getWorkspaceStatus          | config          | ConfigService                |
| getConfigStatus             | config          | ConfigService                |
| saveConfig                  | config          | ConfigService                |
| listProfiles                | config          | ConfigService                |
| getIsolationStatus          | config          | ConfigService                |
| listIsolationProviders      | config          | ConfigService                |
| executeWorkflow             | run lifecycle   | RunLifecycleService          |
| cancelWorkflow              | run lifecycle   | RunLifecycleService          |
| startRun                    | run lifecycle   | RunLifecycleService          |
| preflightRun                | run lifecycle   | RunLifecycleService          |
| getTraces                   | run lifecycle   | RunLifecycleService          |
| readTrace                   | run lifecycle   | RunLifecycleService          |
| streamTrace                 | run lifecycle   | RunLifecycleService          |
| streamActiveTrace           | run lifecycle   | RunLifecycleService          |
| readActiveTraceStream       | run lifecycle   | RunLifecycleService          |
| cancelActiveTraceStream     | run lifecycle   | RunLifecycleService          |
| validateTrace               | run lifecycle   | RunLifecycleService          |
| detectWorkflows             | run lifecycle   | RunLifecycleService          |
| listRuntimeCapabilities     | run lifecycle   | RunLifecycleService          |
| getRunLinks                 | audit           | AuditBridgeService           |
| getRunReceipt               | audit           | AuditBridgeService           |
| getRunAutopsy               | audit           | AuditBridgeService           |

## Strategy

Composition over inheritance. Keep `ArcBackendService` as a delegating facade
for one minor + one patch cycle (per ADR-022) so existing Inversify bindings
remain stable. New code imports services directly.

## Implementation steps

1. Create service skeletons in `packages/arc-extension/src/node/services/`
2. Move methods verbatim from ArcBackendService to new services
3. Update ArcBackendService to delegate to new services
4. Update DI bindings in arc-backend-module.ts
5. Run golden-output regression guard (test count must stay identical)
6. Mark ArcBackendService as @deprecated with removal target v0.3.0
