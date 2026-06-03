# ARC Mobile Runtime

ARC Mobile Runtime is the device-native edge runtime for ARC Studio — a privacy-first,
local-first, simulator-first foundation for mobile AI agents.

## MVP Status

All capabilities are **mock/simulator-only**. No real native bridges exist.

| Platform | Status |
|---|---|
| Flutter | Stub (types only) |
| Expo | Stub (types only) |
| React Native | Stub (types only) |
| iOS (native) | Planned |
| Android (native) | Planned |

## What is NOT in MVP

- No real camera/microphone/location/contacts/photos/calendar access
- No background execution
- No network by default
- No real OS permission prompts
- No app-store submission

## Quick start

```bash
arc mobile doctor --json
arc mobile capabilities --json
arc mobile init-runtime-pack ./my-mobile-pack --json
arc runtime-pack validate ./my-mobile-pack --json
```
