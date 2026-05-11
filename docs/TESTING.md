# ARC Studio — Testing Guide

## Python Tests

```bash
cd python
uv sync --all-extras --dev
.venv/bin/python -m pytest              # all tests
.venv/bin/python -m pytest -v           # verbose
.venv/bin/python -m pytest -k adapter   # filter by keyword
.venv/bin/python -m pytest --cov        # with coverage
```

### Test files

| File | Tests | Coverage |
|------|-------|---------|
| `test_protocol.py` | 13 | Envelope, error codes, domain models |
| `test_adapters.py` | 26+ | SwarmGraph, LangGraph, registry, conformance, scan ignores |
| `test_agui_bridge.py` | 7 | AG-UI event mapping, roundtrip |
| `test_context.py` | 16 | All 5 providers, cache, ranker, engine, pack |
| `test_security.py` | 12 | Redaction, path validation |
| `test_storage.py` | 5 | JSONL save/load/list |

## Node.js Unit Tests

```bash
node tests/unit/arc-protocol.test.js   # 8 tests
node packages/arc-test-fixtures/src/index.js  # fixtures self-test
```

## E2E Tests (Playwright)

```bash
# Prerequisites:
pnpm start:browser  # in terminal 1
cd tests/e2e && pnpm install:browsers  # first time only

# Run:
pnpm test:e2e      # from root
```

### E2E test file: `tests/e2e/arc-smoke.spec.ts`

| Test | What it checks |
|------|----------------|
| `browser app loads` | No crash, no ERR_ in title |
| `page title contains ARC Studio` | Branding configured |
| `Theia workbench exists` | Shell rendered |
| `ARC activity bar visible` | Extension loaded |
| `command palette opens` | F1 works |
| `ARC: Inspect Workspace in palette` | Command registered |
| `arc inspect returns valid JSON` | Python CLI integration |
| `conformance swarmgraph passes` | Adapter conformance |

## Conformance Tests

```bash
uv run arc adapter test swarmgraph  # 8/8 pass
uv run arc adapter test langgraph   # 9/9 pass
```

### What conformance tests verify

1. `detect()` never returns `True` with zero evidence (no false positives)
2. `detect()` returns correct types `(bool, float, list[str])`
3. `capabilities()` returns a `RuntimeCapabilities` instance
4. `export_workflow()` returns `list[WorkflowInfo]` (if `can_export_workflow=True`)
5. Workflow has nodes and entry points
6. `export_schemas()` returns `list[SchemaInfo]` (if `can_export_schema=True`)
7. Unsupported methods raise `NotImplementedError`
8. Evidence list is non-empty when detection is positive

## Check Script

```bash
bash scripts/check.sh   # runs all Python + Node.js checks
```
