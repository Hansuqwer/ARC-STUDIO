# ARC Studio Monitoring Guide

## Overview

ARC Studio provides built-in health check and metrics endpoints for monitoring the status and performance of the extension.

## Endpoints

### Health Check

**Endpoint:** `GET /api/health`

Returns the current health status of ARC Studio components.

**Response (200 OK):**
```json
{
  "status": "ok",
  "timestamp": "2026-05-13T12:00:00.000Z",
  "version": "0.6.0-alpha",
  "uptime": 3600.5,
  "checks": {
    "filesystem": { "status": "ok" },
    "swarmgraph": { "status": "ok" },
    "traces": { "status": "ok" }
  }
}
```

**Response (503 Service Unavailable):**
Returned when one or more checks have status `error`.

**Health Checks:**

| Check        | Description                              | Statuses              |
|-------------|------------------------------------------|-----------------------|
| filesystem  | Workspace root accessibility             | ok, error             |
| swarmgraph  | SwarmGraph CLI availability              | ok, degraded, error   |
| traces      | Traces directory existence               | ok, error             |

**Environment Variables:**

- `ARC_SWARMGRAPH_CLI` - Override the SwarmGraph CLI command path (default: `swarmgraph`)

### Metrics

**Endpoint:** `GET /api/metrics`

Returns runtime metrics for ARC Studio.

**Response:**
```json
{
  "uptime": 3600,
  "requests": 150,
  "executions": 42,
  "errors": 3,
  "memory": {
    "rss": 123456789,
    "heapTotal": 98765432,
    "heapUsed": 87654321,
    "external": 1234567,
    "arrayBuffers": 123456
  }
}
```

**Metrics:**

| Metric       | Description                          |
|-------------|--------------------------------------|
| uptime      | Seconds since process start          |
| requests    | Total API requests received          |
| executions  | Total SwarmGraph executions          |
| errors      | Total errors encountered             |
| memory      | Node.js memory usage (bytes)         |

## Logging Configuration

ARC Studio uses Theia's built-in logging system. Configure log levels via:

1. **Command Palette:** `Preferences: Open Settings` → Search for `log.level`
2. **Environment variable:** `THEIA_LOG_LEVEL=debug|info|warn|error`

Log files are written to the workspace `.arc/logs/` directory.

## Alerting Recommendations

### Critical Alerts

- Health endpoint returns `503` for more than 2 consecutive checks
- Memory usage exceeds 80% of available heap
- Error rate exceeds 10% of total requests

### Warning Alerts

- SwarmGraph CLI check returns `degraded`
- Uptime resets unexpectedly (process restart)
- Response latency exceeds 5 seconds

### Suggested Alert Rules (Prometheus/Alertmanager)

```yaml
groups:
  - name: arc-studio
    rules:
      - alert: ArcStudioDown
        expr: up{job="arc-studio"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "ARC Studio is unreachable"

      - alert: ArcStudioHighMemory
        expr: process_memory_rss_bytes / process_memory_limit > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "ARC Studio memory usage above 80%"

      - alert: ArcStudioHighErrorRate
        expr: rate(arc_errors_total[5m]) / rate(arc_requests_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "ARC Studio error rate above 10%"
```

## Recommended Monitoring Tools

### Metrics Collection

- **Prometheus** - Scrape `/api/metrics` endpoint (requires a metrics exporter adapter for custom format)
- **Datadog** - Use HTTP check for health endpoint, custom agent check for metrics
- **Grafana Cloud** - Prometheus-compatible storage with dashboards

### Uptime Monitoring

- **UptimeRobot** - Monitor `/api/health` endpoint
- **Pingdom** - HTTP health check monitoring
- **Better Uptime** - Health check with incident management

### Log Aggregation

- **ELK Stack** (Elasticsearch, Logstash, Kibana) - Centralized log management
- **Loki + Grafana** - Lightweight log aggregation
- **Datadog Logs** - Cloud-based log management

### Dashboard Templates

Create dashboards tracking:
1. Health check status over time
2. Request/execution/error rates
3. Memory usage trends
4. SwarmGraph execution latency

## Integration Examples

### Docker Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1
```

### Kubernetes Liveness/Readiness Probes

```yaml
livenessProbe:
  httpGet:
    path: /api/health
    port: 3000
  initialDelaySeconds: 15
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /api/health
    port: 3000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Shell Script Monitoring

```bash
#!/bin/bash
HEALTH_URL="http://localhost:3000/api/health"
response=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")

if [ "$response" != "200" ]; then
    echo "ALERT: ARC Studio health check failed (HTTP $response)"
    # Trigger alert notification
fi
```
