# arc-arena (excluded from build)

This extension is currently excluded from the workspace build via
`pnpm-workspace.yaml`. It has 5 TypeScript errors (TS2305, TS2353,
TS17016) caused by Theia API drift. See the 2026-05-14 audit, finding F-2.

To revive: fix the TS errors against the current Theia version, re-add
the package to `pnpm-workspace.yaml`, and re-add the dependency to
`applications/electron/package.json` if needed.
