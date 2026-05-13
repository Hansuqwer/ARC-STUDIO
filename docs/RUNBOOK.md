# ARC Studio Runbook

**Version:** 0.6.0-alpha  
**Last Updated:** 2026-05-13

---

## Common Operations

### Restart Application
```bash
# Stop current instance (Ctrl+C or kill process)
pkill -f "theia start"

# Start fresh
pnpm start:browser

# Or production
NODE_ENV=production pnpm start:prod
```

### Clear Build Cache
```bash
pnpm clean
rm -rf node_modules
rm -rf packages/*/lib
rm -rf packages/*/node_modules
pnpm install
pnpm build
```

### Update Dependencies
```bash
pnpm update
pnpm install
pnpm build
```

### Check Health
```bash
curl http://localhost:3000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "timestamp": "2026-05-13T...",
  "version": "0.6.0-alpha",
  "uptime": 123.456,
  "checks": {
    "filesystem": { "status": "ok" },
    "swarmgraph": { "status": "ok" },
    "traces": { "status": "ok" }
  }
}
```

### View Metrics
```bash
curl http://localhost:3000/api/metrics
```

Expected response:
```json
{
  "uptime": 123,
  "requests": 45,
  "executions": 12,
  "errors": 0,
  "memory": {
    "rss": 123456789,
    "heapTotal": 98765432,
    "heapUsed": 87654321,
    "external": 1234567
  }
}
```

### View Logs
```bash
# Theia logs to stdout by default
# If running with systemd:
journalctl -u arc-studio -f

# If running with Docker:
docker logs -f arc-studio
```

---

## Incident Response

### Application Won't Start

**Symptoms:** Process exits immediately, port not listening

**Diagnosis:**
```bash
# Check Node.js version
node --version  # Must be >= 18

# Check disk space
df -h

# Check port availability
lsof -i :3000

# Try manual start with verbose logging
pnpm start:browser 2>&1 | head -50
```

**Resolution:**
1. If Node.js < 18: Upgrade Node.js
2. If port in use: Kill existing process or change port
3. If dependencies missing: `pnpm install`
4. If build corrupted: `pnpm clean && pnpm build`
5. If disk full: Free up space

### High Memory Usage

**Symptoms:** Application slow, OOM errors, system sluggish

**Diagnosis:**
```bash
# Check metrics
curl http://localhost:3000/api/metrics

# Check process memory
ps aux | grep theia

# Check for memory leaks in DevTools
# Open http://localhost:3000 → DevTools → Memory → Take heap snapshot
```

**Resolution:**
1. Restart application: `pkill -f "theia start" && pnpm start:browser`
2. If persistent: Check recent changes, consider rolling back
3. If production: Increase container memory limit

### SwarmGraph Execution Fails

**Symptoms:** Workflow execution returns error, no trace file created

**Diagnosis:**
```bash
# Check health endpoint
curl http://localhost:3000/api/health | jq .checks.swarmgraph

# Verify CLI installed
which swarmgraph
swarmgraph --version

# Check env var
echo $ARC_SWARMGRAPH_CLI

# Test CLI directly
swarmgraph swarm --json "test prompt"
```

**Resolution:**
1. If CLI not found: Install SwarmGraph or set `ARC_SWARMGRAPH_CLI`
2. If permission denied: `chmod +x swarmgraph`
3. If workspace not trusted: Set `ARC_TRUST_WORKSPACE_LAUNCHER=1`
4. If timeout: Increase timeout in execution options

### Trace Files Not Loading

**Symptoms:** "Load Traces" returns empty or errors

**Diagnosis:**
```bash
# Check traces directory
ls -la .arc/traces/

# Check file permissions
stat .arc/traces/*.jsonl

# Verify JSONL format
head -1 .arc/traces/run-sg-*.jsonl | python3 -m json.tool

# Check disk space
df -h .arc/traces/
```

**Resolution:**
1. If directory missing: `mkdir -p .arc/traces`
2. If permission denied: `chmod 755 .arc/traces`
3. If malformed JSON: Remove or fix corrupted files
4. If disk full: Archive old traces, free space

### Keyboard Shortcuts Not Working

**Symptoms:** Cmd+E/L/S/H don't trigger actions

**Diagnosis:**
- Check if widget has focus (shortcuts work globally after Phase 6 fix)
- Check browser console for errors
- Verify keybinding contribution is registered

**Resolution:**
1. Refresh page
2. Check browser console for errors
3. Verify `arc-keybinding-contribution.ts` is compiled and loaded
4. Rebuild: `cd packages/arc-extension && pnpm build`

### Build Fails with Webpack Errors

**Symptoms:** `pnpm build` exits with webpack errors

**Diagnosis:**
```bash
# Check Node.js version
node --version

# Check pnpm version
pnpm --version

# Verify dependencies
pnpm install

# Check for stale generated files
rm -rf packages/arc-browser-app/src-gen
rm -rf packages/arc-browser-app/gen-webpack*.js
```

**Resolution:**
1. Clean and rebuild: `pnpm clean && pnpm install && pnpm build`
2. If Monaco errors: Verify `@theia/monaco-editor-core` is installed
3. If ripgrep errors: Check pnpm overrides in root package.json

---

## Backup Procedures

### Trace Files
```bash
# Backup all traces
tar -czf traces-backup-$(date +%Y%m%d).tar.gz .arc/traces/

# Restore
tar -xzf traces-backup-*.tar.gz
```

### Configuration
```bash
# Backup environment
env | grep ARC_ > arc-env-backup-$(date +%Y%m%d).txt

# Backup workspace settings
cp .vscode/settings.json settings-backup.json 2>/dev/null || true
```

### Full Backup
```bash
# Backup entire project (excluding node_modules)
tar -czf arc-studio-backup-$(date +%Y%m%d).tar.gz \
  --exclude=node_modules \
  --exclude=.git \
  --exclude=lib \
  .
```

---

## Monitoring Checklist

### Daily
- [ ] Health check responding: `curl localhost:3000/api/health`
- [ ] Error rate < 5%: Check `/api/metrics`
- [ ] Disk space > 20%: `df -h`

### Weekly
- [ ] Memory usage stable: Compare metrics over time
- [ ] Trace directory size reasonable: `du -sh .arc/traces/`
- [ ] No stale processes: `ps aux | grep theia`

### Monthly
- [ ] Dependencies up to date: `pnpm outdated`
- [ ] Security patches applied: Check GitHub advisories
- [ ] Backup verified: Test restore from backup

---

## Escalation Procedures

### Level 1: Self-Service
- Check this runbook
- Check `docs/TROUBLESHOOTING.md`
- Restart application

### Level 2: Developer
- Check application logs
- Review recent changes
- Check GitHub issues
- Contact: Project maintainers

### Level 3: Infrastructure
- Server issues
- Network problems
- Contact: System administrator

---

## Emergency Contacts

| Role | Contact |
|------|---------|
| Project Lead | GitHub: @Hansuqwer |
| Repository | https://github.com/Hansuqwer/arc-theia-studio |
| Issues | https://github.com/Hansuqwer/arc-theia-studio/issues |

---

**Last Reviewed:** 2026-05-13  
**Next Review:** 2026-06-13
