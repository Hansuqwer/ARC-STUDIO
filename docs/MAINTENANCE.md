# Maintenance Guide

**Project:** ARC Studio  
**Version:** 0.6.0-alpha  
**Last Updated:** 2026-05-13

---

## Regular Maintenance Tasks

### Weekly
- [ ] Review error logs: Check `/api/metrics` for error rate
- [ ] Clean old traces: Archive traces older than 30 days
- [ ] Check disk usage: `du -sh .arc/traces/`

### Monthly
- [ ] Update dependencies: `pnpm outdated` → `pnpm update`
- [ ] Review security advisories: Check GitHub and npm audit
- [ ] Test production build: `NODE_ENV=production pnpm build:prod`
- [ ] Verify backups: Test restore from latest backup

### Quarterly
- [ ] Review and update documentation
- [ ] Review Architecture Decision Records
- [ ] Assess technical debt items
- [ ] Plan next release

---

## Dependency Update Procedure

### 1. Check for Updates
```bash
pnpm outdated
```

### 2. Review Changes
- Check changelogs for breaking changes
- Review security advisories
- Check Theia migration guide if updating Theia packages

### 3. Update Dependencies
```bash
# Update all non-breaking dependencies
pnpm update

# For specific packages
pnpm update @theia/core @theia/monaco
```

### 4. Verify Build
```bash
pnpm clean
pnpm install
pnpm build
```

### 5. Run Tests
```bash
cd packages/arc-extension && pnpm test
cd python && uv run pytest -q
```

### 6. Manual Testing
```bash
pnpm start:browser
# Test: workflow execution, trace loading, workspace scanning
```

### 7. Commit
```bash
git add pnpm-lock.yaml package.json packages/*/package.json
git commit -m "chore(deps): update dependencies"
```

---

## Security Patch Procedure

### 1. Identify Vulnerability
```bash
pnpm audit
```

### 2. Assess Impact
- Check CVE details
- Determine if vulnerability affects ARC Studio
- Prioritize based on severity (Critical > High > Medium > Low)

### 3. Apply Patch
```bash
# Auto-fix if possible
pnpm audit --fix

# Or manual update
pnpm update vulnerable-package@latest
```

### 4. Verify
```bash
pnpm audit  # Should show 0 vulnerabilities
pnpm build
pnpm test
```

### 5. Deploy
- Merge to main
- Tag patch release (e.g., v0.6.1-alpha)
- Deploy to production

### 6. Document
- Update CHANGELOG.md
- Update SECURITY_AUDIT_REPORT.md if needed

---

## Release Procedure

### 1. Prepare Release
```bash
git checkout build/no-mockups-handoff
git pull origin build/no-mockups-handoff
```

### 2. Update Version
```bash
# Update package.json files
# Update CHANGELOG.md
```

### 3. Create Tag
```bash
git add package.json packages/*/package.json CHANGELOG.md
git commit -m "chore(release): v0.X.Y"
git tag -a v0.X.Y -m "ARC Studio v0.X.Y"
git push origin v0.X.Y
```

### 4. Create GitHub Release
```bash
gh release create v0.X.Y \
  --title "ARC Studio v0.X.Y" \
  --notes "Release notes here" \
  --prerelease  # Remove for stable releases
```

### 5. Merge to Main
```bash
gh pr create --base main --head build/no-mockups-handoff
gh pr merge <PR_NUMBER> --merge
```

### 6. Deploy
```bash
git checkout main
git pull origin main
bash scripts/deploy.sh
```

---

## Backup Schedule

### Automated (Recommended)
```bash
# Add to crontab
0 2 * * * cd /path/to/arc-studio && tar -czf /backups/traces-$(date +\%Y\%m\%d).tar.gz .arc/traces/
0 3 * * 0 cd /path/to/arc-studio && tar -czf /backups/full-$(date +\%Y\%m\%d).tar.gz --exclude=node_modules --exclude=.git .
```

### Manual
```bash
# Trace backup
tar -czf traces-backup-$(date +%Y%m%d).tar.gz .arc/traces/

# Full backup
tar -czf arc-studio-backup-$(date +%Y%m%d).tar.gz \
  --exclude=node_modules \
  --exclude=.git \
  --exclude=lib \
  .
```

### Retention
- Daily trace backups: Keep 7 days
- Weekly full backups: Keep 4 weeks
- Monthly archives: Keep 6 months

---

## Log Rotation

### Theia Logs
Theia logs to stdout by default. Use systemd or Docker for log rotation.

**systemd example** (`/etc/logrotate.d/arc-studio`):
```
/var/log/arc-studio/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 arc-studio arc-studio
}
```

**Docker**: Logs are managed by Docker daemon. Configure in `/etc/docker/daemon.json`:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

---

## Performance Monitoring

### Key Metrics
- **Uptime**: Should be stable, no unexpected restarts
- **Memory**: RSS should not grow unbounded (check for leaks)
- **Requests**: Track request rate and error rate
- **Executions**: Track workflow execution success rate

### Monitoring Endpoints
- Health: `GET /api/health`
- Metrics: `GET /api/metrics`

### Recommended Tools
| Tool | Purpose |
|------|---------|
| Prometheus | Metrics collection |
| Grafana | Dashboards |
| UptimeRobot | Uptime monitoring |
| ELK Stack | Log aggregation |
| New Relic | APM |

### Alerting Thresholds
| Metric | Warning | Critical |
|--------|---------|----------|
| Error rate | > 5% | > 10% |
| Memory usage | > 70% | > 85% |
| Disk usage | > 80% | > 90% |
| Response time | > 2s | > 5s |
| Uptime | < 99% | < 95% |

---

## Known Maintenance Issues

### @theia/file-search Unavailable
- **Cause**: ripgrep/Node.js v25 incompatibility
- **Impact**: File search feature not available
- **Workaround**: Accept limitation or downgrade Node.js
- **Status**: Accepted, waiting for upstream fix

### Monaco Bundle Size
- **Cause**: Monaco editor is large by nature (~50% of bundle)
- **Impact**: Large initial download
- **Workaround**: Code splitting (future work)
- **Status**: Accepted, inherent to Theia

### Test Coverage Gap
- **Cause**: Widget tests need jsdom harness (complex setup)
- **Impact**: Coverage at 63.86% vs 70% target
- **Workaround**: Source-code analysis for widget tests
- **Status**: Accepted for alpha, target for beta

---

**Last Reviewed:** 2026-05-13  
**Next Review:** 2026-06-13
