# Packaging

## Unsigned Smoke

```bash
pnpm build
pnpm package:electron:dir
```

This produces an unpacked Electron app only. It does not sign, notarize, upload, or publish artifacts.

## Signing Blockers

- macOS signing requires `CSC_LINK`, `CSC_KEY_PASSWORD`, Apple ID credentials, and notarization setup.
- Windows signing requires a code-signing certificate and timestamp server configuration.
- Linux repository publishing requires package signing keys and repository hosting.

Do not enable signing or auto-update publishing without explicit release approval.

## PyPI Trusted Publisher

Configure each PyPI project in the PyPI UI before publishing:

- Owner: `Hansuqwer`
- Repository: `arc-theia-studio`
- Workflow: release workflow name once added
- Environment: `pypi`

Publishing remains blocked until PyPI Trusted Publisher entries exist.

## Auto-Update

Auto-update needs a signed artifact pipeline and update feed. Add only after signing is configured and tested.
