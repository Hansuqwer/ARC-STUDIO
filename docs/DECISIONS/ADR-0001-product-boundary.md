# ADR-0001: Product Boundary — ARC Studio vs ARC Core

**Status:** Accepted  
**Date:** 2025  
**Deciders:** Lead Orchestrator, Architecture Reviewer

## Context

ARC Studio is a customized IDE shell. ARC Core is the Python daemon/backend layer.
These must remain cleanly separated so the IDE shell can be updated independently
of the backend protocol.

## Decision

```
ARC Studio = Theia IDE shell + ARC Theia native extensions
ARC Core   = Python CLI/daemon + adapters + context retrieval + traces
```

The Theia frontend **never imports Python code**.  
All communication crosses a JSON boundary (HTTP/process stdio).  
SwarmGraph is the first runtime adapter — not the product boundary.

## Consequences

- Extensions must communicate with ARC Core through JSON API contracts only.
- New runtimes are added as adapters, not as hardcoded IDE features.
- The IDE shell can theoretically run against any conformant ARC Core.
- Browser and Electron share the same extension codebase.
