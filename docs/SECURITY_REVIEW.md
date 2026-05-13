# Security Review Checklist

**Last Updated:** 2026-05-13

## Required Before Production

- [ ] Rotate any exposed provider keys before further live provider testing.
- [ ] Verify secrets are never logged by CLI, daemon, Theia backend, or CI.
- [x] Review local daemon CORS and host binding — CORS restricted to `localhost:3000`
- [x] Review workspace path validation and symlink handling — implemented in `security-utils.ts` and `security_utils.py`
- [ ] Review Electron permissions, plugin loading, and bundled extension provenance.
- [ ] Run dependency/license audit and preserve third-party notices.
- [ ] Run external security review before signed public installers.

## Completed

- [x] Command injection prevention — `shell: false` with argument arrays
- [x] Path traversal protection — strict trace ID validation
- [x] Workspace boundary enforcement — all paths validated
- [x] Input sanitization — shell metacharacter rejection
- [x] Error message sanitization — no internal details exposed
- [x] Subprocess environment allow-list — prevents credential leakage
- [x] Security test suite — 12 tests passing

## External Validation

- [ ] Manual user validation of SwarmGraph stub and provider-backed runs.
- [ ] Manual user validation of daemon SSE timeline replay.
- [ ] Cross-platform smoke: macOS, Windows, Linux.
- [ ] Signed installer install/uninstall/update smoke per platform.
