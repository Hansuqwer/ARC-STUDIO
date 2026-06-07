# arc_mobile_runtime — Flutter Simulator Preview

Current status: **mock-only simulator preview**.

This package does **not** provide a production Flutter plugin yet. It currently declares a Flutter package shell for ARC Mobile Runtime simulator-preview workflows.

## What exists today

- Flutter package metadata
- Preview/stub status

## What does not exist today

- No Dart platform interface implementation
- No MethodChannel or EventChannel bridge
- No native iOS/Android implementation
- No real camera, microphone, contacts, calendar, photos, files, health, location, or notification access
- No background execution
- No production MCP gateway
- No app-store-ready privacy artifact generation from this package

Use this package only for ARC Mobile Runtime simulator-preview integration until the production gates in `docs/mobile/PRODUCTION_READINESS.md` are satisfied.
