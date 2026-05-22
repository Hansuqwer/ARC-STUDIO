# ARC Studio Architecture

**Type:** Explanation (Diátaxis)  
**Audience:** Developers, contributors, architects  
**Purpose:** Understand WHY ARC Studio is architected as a three-layer system

---

## Introduction

ARC Studio is an Agent Runtime Cockpit IDE for developing, executing, and monitoring AI agent workflows. Its architecture is deliberately split into three distinct layers, each with specific responsibilities and technologies. This document explains why this architecture exists, what problems it solves, and how the layers work together.

---

## The Three-Layer Architecture

ARC Studio consists of three layers:

1. **Python Backend** — Agent runtime orchestration, storage, security, and adapter integration
2. **TypeScript Extension** — Theia extension providing IDE services and UI components
3. **Theia Application** — Eclipse Theia-based IDE shell providing the development environment

```
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Theia Application (Browser)                   │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Eclipse Theia IDE Shell                          │  │
│  │  - Monaco Editor                                   │  │
│  │  - File Explorer                                   │  │
│  │  - Terminal                                        │  │
│  │  - Extension Host                                  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↕ Extension API
┌─────────────────────────────────────────────────────────┐
│  Layer 2: TypeScript Extension (arc-extension)          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Backend Services (Node.js)                       │  │
│  │  - Workflow Executor                              │  │
│  │  - Trace Parser                                   │  │
│  │  - File Manager                                   │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Frontend Widgets (React)                         │  │
│  │  - ARC Studio Widget                              │  │
│  │  - Run Timeline                                   │  │
│  │  - Event Stream                                   │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↕ JSON-RPC / HTTP
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Python Backend (agent_runtime_cockpit)        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Orchestration                                     │  │
│  │  - Event Broker (SSE streaming)                   │  │
│  │  - Job Supervisor (lifecycle)                     │  │
│  │  - Runtime Router (adapter selection)             │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Adapters                                          │  │
│  │  - SwarmGraph, LangGraph, CrewAI                  │  │
│  │  - Provider-backed execution                      │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Storage & Security                                │  │
│  │  - JSONL traces + SQLite index                    │  │
│  │  - Workspace trust, profiles, isolation           │  │
│  │  - Audit chain (HMAC-SHA256)                      │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Why Three Layers?

### Separation of Concerns

Each layer has a distinct responsibility:

- **Python Backend:** Agent runtime logic, where the complexity of orchestrating multiple agent frameworks lives. Python is the lingua franca of AI/ML tooling, making it the natural choice for adapter integration.

- **TypeScript Extension:** IDE integration logic, bridging the Python backend with the Theia UI. TypeScript provides type safety and seamless integration with Theia's extension API.

- **Theia Application:** Development environment shell, providing the editor, file system, terminal, and extension host. Theia gives us a production-ready IDE foundation without building one from scratch.

### Technology Fit

Each layer uses the technology best suited to its domain:

- **Python** for agent orchestration: Most agent frameworks (LangChain, CrewAI, AutoGen) are Python-first. Using Python for the backend means we can integrate with these frameworks directly, without FFI or subprocess overhead.

- **TypeScript** for IDE services: Theia is TypeScript-based. Writing the extension in TypeScript means we get full type safety, IDE autocomplete, and seamless integration with Theia's APIs.

- **Theia** for the IDE shell: Building a full IDE from scratch would take years. Theia provides Monaco editor, file explorer, terminal, debugger, and extension host out of the box. We focus on agent-specific features, not reinventing IDE basics.

### Independent Evolution

The three-layer architecture allows each layer to evolve independently:

- The Python backend can add new adapters (e.g., OpenAI Agents, LlamaIndex) without touching the TypeScript extension.
- The TypeScript extension can add new UI widgets without changing the Python backend.
- The Theia application can upgrade to newer Theia versions without rewriting the Python backend.

This independence is critical for long-term maintainability.

---

## Layer 1: Python Backend

### Purpose

The Python backend is the **agent runtime orchestration layer**. It:
- Executes agent workflows via adapters (SwarmGraph, LangGraph, CrewAI)
- Manages run lifecycle (start, cancel, orphan recovery)
- Streams events to the IDE via Server-Sent Events (SSE)
- Stores traces (JSONL) and run metadata (SQLite)
- Enforces security (workspace trust, profiles, isolation)
- Maintains audit chains (HMAC-SHA256 for EU AI Act compliance)

### Why Python?

**Agent framework ecosystem:** Python is the dominant language for AI agent frameworks. LangChain, CrewAI, AutoGen, LlamaIndex, and most LLM SDKs are Python-first. Using Python for the backend means:
- Direct integration with agent frameworks (no subprocess overhead)
- Access to the full Python AI/ML ecosystem (transformers, numpy, pandas)
- Easier contribution from the AI/ML community (most AI engineers know Python)

**Async/await for concurrency:** Python's `asyncio` provides lightweight concurrency for streaming events, managing multiple runs, and handling SSE connections without thread overhead.

**Rich standard library:** Python's standard library includes everything needed for file I/O, JSON parsing, subprocess management, and HTTP servers. Less dependency bloat.

### Key Design Decisions

**Event-driven architecture:** The `EventBroker` uses a bounded queue pub/sub model. Runs publish events, the IDE subscribes via SSE. This decouples run execution from UI rendering—runs can complete even if the IDE disconnects.

**Adapter pattern:** Each agent framework (SwarmGraph, LangGraph, CrewAI) has an adapter that translates framework-specific events into a unified AG-UI event schema. This allows the IDE to render any framework's execution without framework-specific UI code.

**Dual storage (JSONL + SQLite):** Traces are stored as append-only JSONL (canonical, immutable, auditable). Run metadata is indexed in SQLite for fast queries. This gives us both auditability and performance.

**Workspace trust model:** Workspaces are untrusted by default. Users must explicitly trust a workspace before ARC will execute code from it. This prevents malicious workflows from running automatically.

### What It Doesn't Do

The Python backend does **not**:
- Render UI (that's the TypeScript extension's job)
- Manage editor state (that's Theia's job)
- Handle user input directly (the IDE sends commands via HTTP/JSON-RPC)

This keeps the backend focused on agent orchestration, not UI concerns.

---

## Layer 2: TypeScript Extension

### Purpose

The TypeScript extension is the **IDE integration layer**. It:
- Provides UI widgets (ARC Studio panel, run timeline, event stream)
- Executes workflows by calling the Python backend
- Parses and displays traces
- Manages file operations (list traces, delete runs)
- Integrates with Theia's extension API (commands, menus, views)

### Why TypeScript?

**Theia is TypeScript-based:** Theia's extension API is TypeScript. Using TypeScript for the extension means:
- Full type safety when calling Theia APIs
- IDE autocomplete for Theia types
- Compile-time errors instead of runtime crashes
- Seamless integration with Theia's dependency injection (Inversify)

**Type-safe protocol:** The extension defines a JSON-RPC protocol for communicating with the Python backend. TypeScript's type system ensures the frontend and backend agree on message shapes.

**React for UI:** The extension uses React for UI components. React's component model makes it easy to build complex, stateful UIs (run timelines, event streams, trace viewers) without manual DOM manipulation.

### Key Design Decisions

**Backend services in Node.js:** The extension's backend services (workflow executor, trace parser, file manager) run in Node.js, not the browser. This allows them to:
- Spawn Python subprocesses
- Read/write files directly
- Make HTTP requests to the Python backend without CORS issues

**Frontend widgets in React:** The extension's frontend widgets run in the browser. They communicate with backend services via JSON-RPC. This separation keeps the UI responsive—long-running operations (like workflow execution) don't block the UI thread.

**Dependency injection:** The extension uses Inversify DI (Theia's DI framework) to wire up services. This makes services testable (you can inject mocks) and loosely coupled (services depend on interfaces, not concrete classes).

**JSON-RPC protocol:** The extension communicates with backend services via JSON-RPC over Theia's connection infrastructure. This is the same protocol Theia uses internally, so we get connection management, error handling, and message routing for free.

### What It Doesn't Do

The TypeScript extension does **not**:
- Execute agent workflows directly (that's the Python backend's job)
- Implement agent framework logic (that's the Python backend's job)
- Provide the IDE shell (that's Theia's job)

This keeps the extension focused on IDE integration, not agent orchestration.

---

## Layer 3: Theia Application

### Purpose

The Theia application is the **IDE shell**. It provides:
- Monaco editor (the same editor as VS Code)
- File explorer
- Terminal
- Extension host (loads and runs extensions like arc-extension)
- Command palette, menus, keybindings
- Workspace management

### Why Theia?

**Production-ready IDE foundation:** Building a full IDE from scratch would take years. Theia provides:
- A mature editor (Monaco, used by VS Code)
- A robust extension API (similar to VS Code's)
- A plugin system for adding features
- A workspace model for managing projects
- A terminal, debugger, and file explorer

Using Theia means we can focus on agent-specific features (run timelines, trace viewers, audit chains) instead of reinventing IDE basics (syntax highlighting, file navigation, terminal emulation).

**VS Code compatibility:** Theia's extension API is similar to VS Code's. Many VS Code extensions work in Theia with minimal changes. This gives us access to a large ecosystem of existing extensions (language servers, debuggers, themes).

**Customizable:** Theia is designed to be customized. We can:
- Add custom views (ARC Studio panel)
- Add custom commands (run workflow, inspect trace)
- Add custom menus and keybindings
- Customize the layout and branding

**Open source:** Theia is open source (EPL-2.0 and Apache-2.0). We can fork it, modify it, and contribute back. No vendor lock-in.

### Key Design Decisions

**Browser-based:** The Theia application runs in the browser. This means:
- No installation required (just open a URL)
- Cross-platform (works on Windows, macOS, Linux)
- Easy deployment (just serve static files)
- Sandboxed (browser security model protects the host system)

**Extension host:** Theia's extension host loads and runs extensions (like arc-extension). Extensions can:
- Add UI widgets
- Add commands and menus
- Communicate with backend services
- Access the file system (via Theia's file service)

**Workspace model:** Theia's workspace model manages projects. A workspace is a directory containing:
- Source code
- Configuration files (`.arc/config.yaml`)
- Traces (`.arc/traces/`)
- Audit chains (`.arc/audit/`)

The workspace model gives us a natural place to store ARC-specific data.

### What It Doesn't Do

The Theia application does **not**:
- Execute agent workflows (that's the Python backend's job)
- Implement agent-specific UI (that's the TypeScript extension's job)

Theia provides the IDE shell; we provide the agent-specific features.

---

## Inter-Layer Communication

### TypeScript Extension ↔ Python Backend

**Protocol:** HTTP + JSON-RPC  
**Direction:** Bidirectional (extension calls backend, backend streams events to extension)

**Why HTTP?** The Python backend exposes an HTTP API (`/api/runs`, `/api/runtimes`, etc.). The TypeScript extension makes HTTP requests to this API. HTTP is simple, well-understood, and works across languages.

**Why JSON-RPC?** For bidirectional communication (e.g., streaming events), the extension uses JSON-RPC over HTTP. JSON-RPC provides:
- Request/response semantics (like HTTP)
- Notification semantics (one-way messages)
- Error handling (structured error responses)

**Why Server-Sent Events (SSE)?** For streaming run events, the Python backend uses SSE. SSE is a simple, one-way streaming protocol built on HTTP. The extension subscribes to `/api/runs/{id}/events` and receives events as they happen.

### Theia Application ↔ TypeScript Extension

**Protocol:** JSON-RPC over Theia's connection infrastructure  
**Direction:** Bidirectional (frontend widgets call backend services, backend services notify frontend)

**Why JSON-RPC?** Theia uses JSON-RPC internally for frontend-backend communication. Using the same protocol means we get:
- Connection management (reconnect on disconnect)
- Error handling (structured error responses)
- Message routing (messages go to the right service)

**Why Theia's connection infrastructure?** Theia provides a `ConnectionProvider` that manages WebSocket connections between the frontend and backend. Using this infrastructure means we don't have to implement our own connection management.

---

## Design Philosophy

### Principle 1: Separation of Concerns

Each layer has a single, well-defined responsibility. The Python backend orchestrates agents. The TypeScript extension integrates with the IDE. The Theia application provides the IDE shell. This separation makes the system easier to understand, test, and maintain.

### Principle 2: Technology Fit

Each layer uses the technology best suited to its domain. Python for agent orchestration (because agent frameworks are Python-first). TypeScript for IDE integration (because Theia is TypeScript-based). Theia for the IDE shell (because building an IDE from scratch is a multi-year project).

### Principle 3: Independent Evolution

Each layer can evolve independently. The Python backend can add new adapters without touching the TypeScript extension. The TypeScript extension can add new UI widgets without changing the Python backend. The Theia application can upgrade to newer Theia versions without rewriting the Python backend.

### Principle 4: Auditability

Every run produces an immutable, append-only trace (JSONL). Every trace can be verified (HMAC-SHA256 audit chain). This makes ARC Studio suitable for regulated environments (EU AI Act, SOC 2, ISO 27001).

### Principle 5: Security by Default

Workspaces are untrusted by default. Users must explicitly trust a workspace before ARC will execute code from it. Runs are isolated (subprocess isolation, env filtering). Secrets are redacted from traces. This makes ARC Studio safe to use with untrusted code.

---

## Alternatives Considered

### Why Not a Monolith?

**Alternative:** Build ARC Studio as a single Python application with a web UI (Flask/FastAPI + React).

**Why not?**
- **No IDE integration:** We'd have to build our own editor, file explorer, terminal, etc. This is a multi-year project.
- **No extension ecosystem:** We'd have no access to VS Code/Theia extensions (language servers, debuggers, themes).
- **Harder to customize:** Users couldn't add their own extensions or customize the UI without forking the entire application.

### Why Not VS Code Extension?

**Alternative:** Build ARC Studio as a VS Code extension instead of a Theia application.

**Why not?**
- **Limited customization:** VS Code extensions can't customize the core UI (e.g., replace the file explorer, change the layout). Theia allows deeper customization.
- **No backend control:** VS Code extensions run in a sandboxed environment. We need full control over the backend (to spawn Python subprocesses, manage file I/O, etc.).
- **Deployment complexity:** VS Code extensions require users to install VS Code. Theia can be deployed as a web application (no installation required).

### Why Not Electron?

**Alternative:** Build ARC Studio as an Electron application (like VS Code).

**Why not?**
- **Deployment complexity:** Electron applications require installation. Theia can be deployed as a web application (just open a URL).
- **Cross-platform testing:** Electron applications need to be tested on Windows, macOS, and Linux. Theia runs in the browser (one platform to test).
- **Security:** Electron applications have full access to the host system. Theia runs in the browser (sandboxed by the browser's security model).

### Why Not Jupyter?

**Alternative:** Build ARC Studio as a Jupyter extension (like JupyterLab).

**Why not?**
- **Notebook-centric:** Jupyter is designed for notebooks (cells, kernels, outputs). ARC Studio is designed for workflows (files, runs, traces).
- **Limited IDE features:** Jupyter has basic editor features but lacks a full IDE (no debugger, no refactoring tools, no language servers).
- **Python-only:** Jupyter is Python-centric. ARC Studio needs to support multiple languages (Python for the backend, TypeScript for the extension).

---

## Future Evolution

### Potential Changes

**Multi-language backend:** The Python backend could be extended to support other languages (e.g., a Rust backend for performance-critical adapters). The three-layer architecture makes this possible—the TypeScript extension doesn't care what language the backend is written in, as long as it speaks HTTP/JSON-RPC.

**Cloud deployment:** The Theia application could be deployed to the cloud (e.g., AWS, GCP, Azure). Users would access ARC Studio via a web browser, with no installation required. The three-layer architecture makes this straightforward—the Python backend and TypeScript extension already communicate over HTTP.

**Desktop application:** The Theia application could be packaged as an Electron app for users who prefer a desktop application. The three-layer architecture makes this possible—the Python backend and TypeScript extension don't care whether Theia runs in a browser or Electron.

**Plugin ecosystem:** The TypeScript extension could expose a plugin API, allowing third-party developers to add custom adapters, UI widgets, and commands. The three-layer architecture makes this feasible—plugins would interact with the extension layer, not the Python backend directly.

### What Won't Change

**The three-layer architecture:** The separation between Python backend, TypeScript extension, and Theia application is fundamental. This separation provides the flexibility, maintainability, and technology fit that make ARC Studio possible.

**The protocol:** HTTP/JSON-RPC for backend communication, JSON-RPC for frontend-backend communication. These protocols are simple, well-understood, and language-agnostic. Changing them would require rewriting large parts of the system.

**The storage model:** JSONL for traces, SQLite for metadata, HMAC-SHA256 for audit chains. This storage model provides auditability, performance, and compliance. Changing it would break existing traces and audit chains.

---

## Summary

ARC Studio's three-layer architecture is a deliberate design choice that:
- **Separates concerns:** Each layer has a single, well-defined responsibility.
- **Fits technology to domain:** Python for agent orchestration, TypeScript for IDE integration, Theia for the IDE shell.
- **Enables independent evolution:** Each layer can evolve without affecting the others.
- **Provides auditability:** Every run produces an immutable, verifiable trace.
- **Ensures security:** Workspaces are untrusted by default, runs are isolated, secrets are redacted.

This architecture makes ARC Studio maintainable, extensible, and suitable for production use in regulated environments.

---

## Related Documentation

- **[Getting Started](../tutorials/getting-started.md)** — Install and run your first workflow
- **[ADR-013: SwarmGraph Architecture](../adr/ADR-013-swarmgraph-architecture.md)** — SwarmGraph adapter design
- **[ADR-014: Security Architecture](../adr/ADR-014-security-architecture.md)** — Workspace trust and isolation
- **[ADR-021: Audit Chain Architecture](../adr/021-audit-chain-architecture.md)** — HMAC-SHA256 audit chains for EU AI Act compliance
- **[AGENTS.md](../AGENTS.md)** — Agent onboarding and context (technical reference)
