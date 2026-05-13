# Phase 2 Continuation: PR9 & PR10

## Current Status (2026-05-12 17:04 UTC)

**Phase 1:** ✅ 100% Complete (PR1-PR7 merged)  
**Phase 2:** 33% Complete (PR8 merged)  
**Remaining:** PR9 (OTel Export) + PR10 (Health Monitor)  
**Tests:** 196/196 passing ✅  
**Branch:** `main` (all PRs merged)  

---

## Mission: Complete Phase 2

Implement the remaining 2 PRs to finish Phase 2: Telemetry & Health.

### Objectives

1. **PR9: OTel Trace Export** - OTLP exporter with user opt-in
2. **PR10: Health Monitor** - Daemon health view with restart capability

**Estimated Time:** 1-1.5 hours

---

## PR9: OTel Trace Export

### Goal
Export run traces to OpenTelemetry collector (user opt-in, local only by default).

### Tasks
- [ ] Update docs/TELEMETRY_SEMCONV.md with OTel GenAI semconv version
- [ ] Create Python trace exporter service in `python/src/agent_runtime_cockpit/telemetry/`
- [ ] Implement RunRecord → OTLP span conversion
- [ ] Add PreferenceContribution for OTLP endpoint (default: none)
- [ ] Add CommandContribution: "ARC: Export Trace to OTLP"
- [ ] Add endpoint validation (warn for non-localhost)
- [ ] Implement span attribute mapping (gen_ai.agent.*, gen_ai.tool.*)
- [ ] Add Python tests for exporter

### Implementation Guide

**1. Update TELEMETRY_SEMCONV.md**
```markdown
## OTel GenAI Semantic Conventions

**Version:** v1.28.0 (Development status)
**Spec:** https://opentelemetry.io/docs/specs/semconv/gen-ai/

### Span Attributes
- gen_ai.agent.name
- gen_ai.agent.id
- gen_ai.tool.name
- gen_ai.request.model
- gen_ai.response.finish_reason
```

**2. Create Exporter Service**
```python
# python/src/agent_runtime_cockpit/telemetry/otlp_exporter.py

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def export_run_to_otlp(run: RunRecord, endpoint: str) -> bool:
    """Export run trace to OTLP endpoint. Returns True on success."""
    # Validate endpoint
    if not endpoint:
        raise ValueError("OTLP endpoint not configured")
    
    # Warn for non-local endpoints
    if not endpoint.startswith(('http://localhost', 'http://127.0.0.1')):
        # Log warning
        pass
    
    # Convert RunRecord to OTLP spans
    # Map AG-UI events to gen_ai.* attributes
    # Export to endpoint
    pass
```

**3. Add Preference**
```typescript
// theia-extensions/arc-core/src/browser/arc-preferences.ts
export const ARC_OTLP_ENDPOINT = 'arc.telemetry.otlpEndpoint';

export const arcPreferenceSchema: PreferenceSchema = {
  properties: {
    [ARC_OTLP_ENDPOINT]: {
      type: 'string',
      default: '',
      description: 'OTLP endpoint for trace export (e.g., http://localhost:4317). Leave empty to disable.'
    }
  }
};
```

**4. Add Command**
```typescript
// theia-extensions/arc-runs/src/browser/arc-runs-contribution.ts
@inject(PreferenceService)
protected readonly preferences: PreferenceService;

async exportTraceToOTLP(): Promise<void> {
  const endpoint = this.preferences.get(ARC_OTLP_ENDPOINT);
  if (!endpoint) {
    this.messageService.warn('OTLP endpoint not configured. Set in Preferences.');
    return;
  }
  
  const run = this.getSelectedRun();
  if (!run) return;
  
  // Call Python service to export
  const result = await this.arcService.exportTraceToOTLP(run.id, endpoint);
  if (result.ok) {
    this.messageService.info(`Trace exported to ${endpoint}`);
  } else {
    this.messageService.error(`Export failed: ${result.error}`);
  }
}
```

### Acceptance Criteria
- [ ] OTel semconv version documented
- [ ] Exporter converts RunRecord → OTLP spans
- [ ] Preference for OTLP endpoint (default empty)
- [ ] Command exports selected run
- [ ] Warning for non-localhost endpoints
- [ ] No export without endpoint configured
- [ ] No secrets in span attributes
- [ ] Python tests pass (exporter + validation)

### Tests
```python
# python/tests/telemetry/test_otlp_exporter.py

def test_export_requires_endpoint():
    with pytest.raises(ValueError):
        export_run_to_otlp(run, "")

def test_export_validates_endpoint():
    # Test localhost allowed
    # Test non-localhost warns

def test_export_converts_run_to_spans():
    # Test RunRecord → OTLP conversion
    # Verify gen_ai.* attributes

def test_export_redacts_secrets():
    # Verify no secrets in span attributes
```

### Security
- [ ] User opt-in required (no default endpoint)
- [ ] Endpoint validation (warn on non-local)
- [ ] No secrets in span attributes
- [ ] No automatic export

---

## PR10: Python Daemon Health Monitor

### Goal
Create health monitoring view showing Python daemon status.

### Tasks
- [ ] Verify Python daemon health endpoint exists (`/health`)
- [ ] Create health client service in Theia
- [ ] Implement health view widget (AbstractViewContribution)
- [ ] Add CommandContribution: "ARC: Show Health Monitor"
- [ ] Add CommandContribution: "ARC: Restart Daemon" (with confirmation)
- [ ] Poll health endpoint (loopback only, 5s interval)
- [ ] Display: daemon status, active runs, version, uptime
- [ ] Show degraded state if health check fails

### Implementation Guide

**1. Verify Health Endpoint**
```python
# python/src/agent_runtime_cockpit/web/routes.py

async def health(request: web.Request) -> web.Response:
    return _json(ok({
        "status": "healthy",
        "version": "0.1.0-alpha",
        "uptime_seconds": time.time() - START_TIME,
        "active_runs": len(get_active_runs()),
    }).model_dump())
```

**2. Create Health Client**
```typescript
// theia-extensions/arc-core/src/browser/arc-health-client.ts

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unreachable';
  version?: string;
  uptimeSeconds?: number;
  activeRuns?: number;
}

@injectable()
export class ArcHealthClient {
  async getHealth(): Promise<HealthStatus> {
    try {
      const response = await fetch('http://127.0.0.1:8765/health');
      const data = await response.json();
      return {
        status: 'healthy',
        version: data.data.version,
        uptimeSeconds: data.data.uptime_seconds,
        activeRuns: data.data.active_runs,
      };
    } catch (error) {
      return { status: 'unreachable' };
    }
  }
}
```

**3. Create Health View Widget**
```typescript
// theia-extensions/arc-health/src/browser/arc-health-widget.tsx

export class ArcHealthWidget extends ReactWidget {
  protected state = {
    health: null as HealthStatus | null,
    loading: true,
  };
  
  protected pollInterval: NodeJS.Timeout | null = null;
  
  @postConstruct()
  protected init(): void {
    this.startPolling();
  }
  
  protected startPolling(): void {
    this.pollInterval = setInterval(() => {
      this.updateHealth();
    }, 5000);
    this.updateHealth();
  }
  
  protected async updateHealth(): Promise<void> {
    const health = await this.healthClient.getHealth();
    this.state.health = health;
    this.state.loading = false;
    this.update();
  }
  
  protected render(): React.ReactNode {
    const { health } = this.state;
    return (
      <div>
        <h3>Daemon Health</h3>
        <div>Status: {health?.status}</div>
        <div>Version: {health?.version}</div>
        <div>Uptime: {formatUptime(health?.uptimeSeconds)}</div>
        <div>Active Runs: {health?.activeRuns}</div>
        <button onClick={() => this.restartDaemon()}>Restart Daemon</button>
      </div>
    );
  }
  
  protected async restartDaemon(): Promise<void> {
    const confirmed = await this.messageService.confirm('Restart Python daemon? Active runs will be interrupted.');
    if (confirmed) {
      // Call restart endpoint
    }
  }
}
```

### Acceptance Criteria
- [ ] Health view shows daemon status (healthy/degraded/unreachable)
- [ ] Displays active run count
- [ ] Shows daemon version
- [ ] Shows uptime
- [ ] Restart command works with confirmation dialog
- [ ] Health polling only on loopback (127.0.0.1)
- [ ] No environment variable dump
- [ ] TypeScript compilation passes

### Tests
- [ ] Health client unit tests (mocked HTTP)
- [ ] Health view renders correctly
- [ ] Restart confirmation shown
- [ ] Polling interval correct (5s)

### Security
- [ ] Loopback only (127.0.0.1:8765)
- [ ] Restart requires confirmation
- [ ] No env var exposure
- [ ] No sensitive data in health response

---

## Execution Steps

### 1. Start PR9
```bash
git checkout main
git pull
git checkout -b roadmap/pr9-otel-export

# Implement PR9 tasks
# Run tests
# Commit and push
# Create PR
# Merge
```

### 2. Start PR10
```bash
git checkout main
git pull
git checkout -b roadmap/pr10-health-monitor

# Implement PR10 tasks
# Run tests
# Commit and push
# Create PR
# Merge
```

### 3. Verify Phase 2 Complete
```bash
# All tests passing
npm test
cd python && source .venv/bin/activate && pytest tests/

# All PRs merged
gh pr list --state merged

# Documentation updated
cat docs/PR_ACCEPTANCE.md
```

---

## Success Criteria

### Phase 2 Complete When:
- [x] PR8 merged: Event filtering ✅
- [ ] PR9 merged: OTLP export functional
- [ ] PR10 merged: Health monitor operational
- [ ] All tests passing (200+ tests)
- [ ] Documentation updated
- [ ] No security issues
- [ ] No regressions

---

## Quick Start Command

```
Execute Phase 2 completion: PR9 (OTel Export) and PR10 (Health Monitor)

Current status: PR1-PR8 complete and merged
Remaining: 2 PRs (estimated 1-1.5 hours)

Start with PR9:
1. Update docs/TELEMETRY_SEMCONV.md
2. Create Python OTLP exporter
3. Add Theia preference and command
4. Test and merge

Then PR10:
1. Verify /health endpoint
2. Create health client service
3. Implement health view widget
4. Add restart command with confirmation
5. Test and merge

Follow test-green discipline and security-first principles.
All details in PHASE2_CONTINUE.md.
```

---

**Status:** Ready for PR9 & PR10 execution  
**Date:** 2026-05-12 17:04 UTC  
**Next Action:** Start PR9 (OTel Export)
