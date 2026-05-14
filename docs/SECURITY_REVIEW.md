# Security Review Checklist

## Required Before Production

- Rotate any exposed provider keys before further live provider testing.
- Verify secrets are never logged by CLI, daemon, Theia backend, or CI.
- Review local daemon CORS and host binding before exposing non-local access.
- Review workspace path validation and symlink handling.
- Review Electron permissions, plugin loading, and bundled extension provenance.
- Run dependency/license audit and preserve third-party notices.
- Run external security review before signed public installers.

## External Validation

- Manual user validation of SwarmGraph stub and provider-backed runs.
- Manual user validation of daemon SSE timeline replay.
- Cross-platform smoke: macOS, Windows, Linux.
- Signed installer install/uninstall/update smoke per platform.
