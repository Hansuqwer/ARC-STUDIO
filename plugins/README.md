# ARC Studio — VS Code Plugins Directory

This directory holds downloaded VS Code extensions (.vsix) from Open VSX.

Plugins are downloaded via:
```bash
pnpm download:plugins
```

Configured in root `package.json` under `theiaPlugins`.

## Adding VS Code Extensions

1. Find extension on https://open-vsx.org/
2. Add to root `package.json`:
```json
{
  "theiaPlugins": {
    "vscode-icons": "https://open-vsx.org/api/vscode-icons-team/vscode-icons/12.0.1/file/vscode-icons-team.vscode-icons-12.0.1.vsix"
  }
}
```
3. Run `pnpm download:plugins`

## Current Extensions

None bundled in alpha. The `theiaPluginsDir` points here.

## License Note

All bundled VS Code extensions must be license-compatible with Apache 2.0.
Review each extension's license before bundling.
