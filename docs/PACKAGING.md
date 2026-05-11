# ARC Studio — Packaging Guide

## Local Development Package (unsigned)

```bash
pnpm package:electron
# Output: applications/electron/dist/
```

## Code Signing (REQUIRED for distribution)

### macOS
```bash
# Set these before packaging:
export CSC_LINK=/path/to/Developer-ID-Application.p12
export CSC_KEY_PASSWORD=your_cert_password
export APPLE_ID=your@apple.id
export APPLE_APP_SPECIFIC_PASSWORD=xxxx-xxxx-xxxx-xxxx

pnpm package:electron
```

### Windows
```bash
export CSC_LINK=/path/to/code-signing.pfx
export CSC_KEY_PASSWORD=your_cert_password
pnpm package:electron
```

### Linux
Linux packages (AppImage, deb) do not require signing for local distribution.

## Mock: Signing Not Configured

```
MOCK_REASON: No signing certificates in CI environment
REAL_IMPLEMENTATION_PATH: scripts/sign-electron.sh
LOCAL_FIX_STEPS: Set CSC_LINK, CSC_KEY_PASSWORD, APPLE_ID env vars
REMOVE_BEFORE: Production release
```

## Electron Builder Config

See `applications/electron/electron-builder.yml` for full configuration.

## Python Bundling

The Python daemon is bundled into the Electron app via `extraResources` in electron-builder.yml.

The Electron main process launches the daemon automatically:

```
applications/electron/resources/arc-python/ ← bundled Python
```

For development, run the daemon separately: `uv run arc serve`

## Auto-Update

Auto-update is planned for beta. Use `electron-updater` with an S3/GitHub releases endpoint.
Set `updaterCacheDirName` and publish targets in `electron-builder.yml`.
