# Haystack Adapter Research — R32 (Adapter Phase 31)

**Compiled:** 2026-05-25
**Status:** Research complete; implementation baseline delivered.
**Sources:** docs.haystack.deepset.ai, GitHub deepset-ai/haystack, PyPI, ARC adapter patterns.

---

## 1. Haystack Framework Summary

Haystack is an open-source AI orchestration framework by deepset for building
production-ready LLM applications. It uses a **Pipeline DAG** architecture where
**Components** are connected via typed input/output sockets.

### Key Concepts

| Concept | Description | ARC Mapping |
|---|---|---|
| `Pipeline` | Directed multigraph of components | WorkflowInfo (DAG) |
| `@component` | Decorator for custom components | Workflow node |
| `pipeline.add_component(name, comp)` | Register component | Node registration |
| `pipeline.connect(src, dst)` | Connect output→input | WorkflowEdge |
| `pipeline.run(inputs)` | Execute pipeline | Run execution |
| `pipeline.to_dict()` | Serialize to dict/YAML | Export format |
| `@component.output_types()` | Declare outputs | Output socket types |
| `warm_up()` | Load heavy resources | Init lifecycle |
| `AsyncPipeline` | Parallel execution | Concurrent run |

### Package Identity

- **PyPI:** `haystack-ai` (current 2.x), `farm-haystack` (legacy 1.x)
- **Import:** `import haystack`, `from haystack import Pipeline, component`
- **Version:** 2.x series (active development, current 2.29)

### Pipeline DAG Structure

```python
from haystack import Pipeline
from haystack.components.retrievers import InMemoryBM25Retriever
from haystack.components.generators import OpenAIGenerator

pipe = Pipeline()
pipe.add_component("retriever", InMemoryBM25Retriever(document_store=store))
pipe.add_component("generator", OpenAIGenerator(model="gpt-4o-mini"))
pipe.connect("retriever.documents", "generator.prompt")
result = pipe.run({"retriever": {"query": "What is Haystack?"}})
```

### Component Definition

```python
from haystack import component

@component
class MyComponent:
    @component.output_types(result=str)
    def run(self, input_text: str) -> dict:
        return {"result": input_text.upper()}
```

---

## 2. Research Notes

### Source: docs.haystack.deepset.ai
- **Link:** https://docs.haystack.deepset.ai/docs/pipelines
- **What was learned:**
  - Pipelines are directed multigraphs (loops, branches, parallel paths supported)
  - `Pipeline()` creates pipeline; `add_component(name, comp)` registers; `connect(src, dst)` wires
  - Components have `run()` method with typed inputs/outputs
  - `@component.output_types(name=Type)` decorator declares output types
  - Serialization via `to_dict()`/`from_dict()` (YAML format)
  - `AsyncPipeline` for parallel execution
  - Smart pipeline connections for implicit type adaptation
- **Implementation consequence:** Detection targets `Pipeline()` calls, `add_component()`, `connect()`, and `@component` decorators. Export maps the DAG to WorkflowInfo nodes/edges.
- **Confidence:** High
- **Unresolved questions:** None for T1/T2.

### Source: GitHub deepset-ai/haystack
- **Link:** https://github.com/deepset-ai/haystack
- **What was learned:**
  - Package name on PyPI is `haystack-ai` (2.x), `farm-haystack` (legacy 1.x)
  - Active development with frequent releases
  - Components are decorated with `@component`
  - Pipeline serialization to YAML is the standard format
  - `haystack.components` package has built-in components (retrievers, generators, embedders, etc.)
- **Implementation consequence:** Detection checks both `haystack-ai` and `farm-haystack` in requirements. Export can parse both Python code and YAML pipeline definitions.
- **Confidence:** High
- **Unresolved questions:** None.

### Source: ARC Existing Adapter Patterns
- **Link:** `python/src/agent_runtime_cockpit/adapters/dspy/`
- **What was learned:**
  - 3-tier pattern: detect.py (AST + import probe), export.py (AST visitor), runner.py (event handler)
  - DetectionResult NamedTuple with detected, confidence, evidence, version
  - AST visitors for class/assignment detection
  - Workspace scanning skips `.venv`, `venv`, `node_modules`
  - CapabilityReport must be honest about T1/T2/T3 status
- **Implementation consequence:** Haystack adapter follows identical structure.
- **Confidence:** High
- **Unresolved questions:** None.

---

## 3. Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| Detection strategy | AST scan + import probe + requirements check | Runtime import only | Matches DSPy/LangChain pattern; no code execution | `adapters/haystack/detect.py` | High |
| Pipeline extraction | AST detection of `Pipeline()`, `add_component()`, `connect()` | YAML parsing only | Python code is primary; YAML is secondary | `adapters/haystack/export.py` | High |
| Component extraction | AST detection of `@component` decorator | Regex scanning | AST is more reliable | `adapters/haystack/export.py` | High |
| Runner approach | Gated scaffold (`ARC_HAYSTACK_RUNNER_ENABLED=1`) | Full execution | Requires live LM calls; gated matches truth constraints | `adapters/haystack/runner.py` | High |
| Package detection | Both `haystack-ai` and `farm-haystack` | Only `haystack-ai` | Legacy package name still in use | `adapters/haystack/detect.py` | High |

---

## 4. Detection Targets (AST)

### Import Patterns
- `import haystack`
- `from haystack import Pipeline`
- `from haystack import component`
- `from haystack.components import ...`
- `from haystack.components.generators import ...`
- `from haystack.components.retrievers import ...`

### Pipeline Construction
```python
pipe = Pipeline()
pipe.add_component("retriever", InMemoryBM25Retriever())
pipe.connect("retriever.documents", "generator.prompt")
```

### Component Definitions
```python
@component
class MyComponent:
    @component.output_types(result=str)
    def run(self, input_text: str) -> dict:
        ...
```

### Requirements
- `haystack-ai` or `farm-haystack` in `requirements.txt`, `pyproject.toml`

---

## 5. Truth Constraints

- No live provider/network calls in tests
- No Haystack pipeline execution unless gated behind env var
- No broad Haystack adoption claims
- Detection must be AST-based (no code execution for detect/export)
- T3 runner is gated scaffold — requires `ARC_HAYSTACK_RUNNER_ENABLED=1`
- Capability report must be honest: T1/T2 available, T3 gated
