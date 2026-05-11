# Plugin And License Policy

- No VS Code/Open VSX extensions are bundled in alpha.
- Add plugins only through root `theiaPlugins` and `pnpm download:plugins`.
- Record each plugin name, version, source URL, and license before bundling.
- Only bundle licenses compatible with Apache-2.0 distribution.
- Keep generated plugin artifacts out of source control unless explicitly approved.
- Re-run `pnpm check:licenses` before release.
