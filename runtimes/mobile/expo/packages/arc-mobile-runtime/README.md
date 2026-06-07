# arc-mobile-runtime — Expo Simulator Preview

Current status: **mock-only simulator preview**.

This package does **not** provide a production Expo Module yet. It currently exposes a TypeScript mock-mode API for simulator-preview workflows.

## What exists today

- `ARC_MOBILE_SDK_VERSION`
- `ARC_MOBILE_MOCK_MODE = true`
- `simulateAction(...)` returning a mock result

## What does not exist today

- No real native Expo Module bridge
- No Swift/Kotlin native implementation
- No real camera, microphone, contacts, calendar, photos, files, health, location, or notification access
- No background execution
- No production MCP gateway
- No app-store-ready privacy artifact generation from this package

Use this package only for ARC Mobile Runtime simulator-preview integration until the production gates in `docs/mobile/PRODUCTION_READINESS.md` are satisfied.
