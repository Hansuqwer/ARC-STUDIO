# Mypy Expansion Priority

Currently gated: `ag_ui/`, `gating.py`, `security/`, `protocol/`, `workspace.py` (12 files, 0 errors).

## Priority Order

### Round 2 — Hot-path adapters (high value, low/medium effort)
| Directory | Files | Est. effort | Why |
|-----------|-------|-------------|-----|
| `adapters/base.py` | 1 | low | Base classes — few deps, high leverage |
| `adapters/swarmgraph/` | 5 | low | Runner, mapping — already well-typed implicitly |
| `adapters/langgraph/` | 3 | medium | Complex runtime dispatch but contained |

### Round 3 — Supporting infrastructure (medium value, low effort)
| Directory | Files | Est. effort | Why |
|-----------|-------|-------------|-----|
| `telemetry/` | 2 | low | Isolated OTLP exporter |
| `context/` | 2 | low | Chunked context manager |
| `arena/` | 3 | low | Arena model/service — few deps |

### Round 4 — Storage, runner (medium effort)
| Directory | Files | Est. effort | Why |
|-----------|-------|-------------|-----|
| `storage/` | 2 | medium | SQLite adapter, may need typed DB models |
| `runner.py` | 1 | low | Runtime router — contained surface |
| `workspace/` | 3 | medium | Workspace mgmt, may need type stubs |

### Round 5 — Integration-heavy (high effort)
| Directory | Files | Est. effort | Why |
|-----------|-------|-------------|-----|
| `adapters/ag2/` | 5 | high | Heavy Pydantic/AI interop |
| `adapters/crewai/` | 3 | high | External lib types |
| `adapters/openai_agents/` | 3 | high | OpenAI SDK types |

### Excluded indefinitely (tests + CLI)
| Path | Reason |
|------|--------|
| `tests/` | Test code; type-checked implicitly by pytest |
| `cli/` | Click + Typer patterns; low value/effort ratio |
| `web/` | FastAPI + Pydantic; well-typed at runtime |

## Expansion workflow

1. Pick a directory from the next unstarted round.
2. Add its path to the `mypy_paths` list in both `python.yml` and `arc-roadmap-gate.yml`.
3. Fix all errors in that directory (type annotations, not `# type: ignore`).
4. Run `uv run mypy <paths> --strict-equality` to confirm clean.
5. Commit, push, verify CI passes on all 5 workflows.
