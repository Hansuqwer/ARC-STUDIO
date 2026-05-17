# ADR-0003: Theia Extension Layering

**Status:** Accepted  
**Date:** 2025

## Extension Stack

```
arc-product     — branding, welcome, about, icons, product name
arc-core        — service contracts, workspace detection, JSON calls, common UI
arc-workflows   — workflow tree, graph topology, node/edge detail
arc-schemas     — schema list, JSON viewer, model detail
arc-runs        — run launcher, event stream, timeline, trace viewer
arc-audit       — audit chain viewer, tamper warnings
arc-context     — context pack viewer, source evidence
arc-adapters    — runtime adapter status, capabilities display
arc-settings    — ARC preferences, daemon path, env config
```

## Key Theia APIs Used (verified against Theia 1.71)

- `CommandContribution` / `CommandRegistry` — command palette
- `MenuContribution` / `MenuModelRegistry` — menus
- `AbstractViewContribution` — panel views
- `ReactWidget` — React-based widget base
- `FrontendApplicationContribution` — app lifecycle hooks
- `PreferenceContribution` — user preferences
- `BackendApplicationContribution` — backend service startup
- `WebSocketConnectionProvider` — frontend ↔ backend IPC
- `ApplicationShell` — layout management

## Source

- https://theia-ide.org/docs/widgets/
- https://theia-ide.org/docs/extensions/
- https://github.com/eclipse-theia/theia-ide
