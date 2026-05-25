# DSPy Adapter Research — R31 (Adapter Phase 30)

**Compiled:** 2026-05-25
**Status:** Research complete; implementation baseline delivered.
**Sources:** dspy.ai official docs, GitHub stanfordnlp/dspy, PyPI, ARC adapter patterns.

---

## 1. DSPy Framework Summary

DSPy (Declarative Self-improving Python) is a declarative framework for building
modular AI software. Instead of hand-crafting prompts, developers define **signatures**
(declarative input/output specs) and compose them with **modules** (Predict,
ChainOfThought, ReAct, etc.) that the framework compiles into effective prompts.

### Key Concepts

| Concept | Description | ARC Mapping |
|---|---|---|
| `dspy.Signature` | Declarative I/O spec with `InputField()`/`OutputField()` | Workflow step definition |
| `dspy.Predict` | Basic prediction module | Simple node |
| `dspy.ChainOfThought` | Chain-of-thought reasoning | Reasoning node |
| `dspy.ReAct` | Reasoning + Acting with tools | Agent node with tool edges |
| `dspy.ProgramOfThought` | Code generation module | Code-gen node |
| `dspy.Module` | Base class for custom modules | Composite workflow |
| `dspy.LM` | Language model configuration | Provider binding |
| `dspy.configure()` | Global LM configuration | Runtime config |
| Optimizers | `BootstrapFewShot`, `MIPROv2`, `GEPA`, etc. | Compilation lifecycle |
| `dspy.Prediction` | Output from module execution | Run result |
| `dspy.Example` | Training/example data | Training data |
| `dspy.Tool` | Tool wrapper for ReAct | Tool node |

### Package Identity

- **PyPI:** `dspy` (current), `dspy-ai` (legacy, pre-2.5)
- **Import:** `import dspy` or `from dspy import ...`
- **Version:** 2.x series (active development, frequent releases)

---

## 2. Research Notes

### Source: dspy.ai Official Documentation
- **Link:** https://dspy.ai
- **What was learned:**
  - DSPy modules: Predict, ChainOfThought, ReAct, ProgramOfThought, Module, MultiChainComparison, Parallel, BestOfN, Refine, CodeAct, RLM
  - Signatures use `InputField()` and `OutputField()` with optional `desc` parameter
  - Custom modules inherit from `dspy.Module` and implement `forward()`
  - Optimizers: BootstrapFewShot, BootstrapRS, MIPROv2, GEPA, COPRO, BootstrapFinetune, Ensemble, BetterTogether, SIMBA
  - LM configuration via `dspy.LM("provider/model")` + `dspy.configure(lm=lm)`
  - Tools are plain Python functions wrapped with `dspy.Tool`
- **Implementation consequence:** Detection targets `dspy.Signature` subclasses, `dspy.Module` subclasses, and module instantiations (Predict, ChainOfThought, ReAct). Export maps signatures to workflow steps and module composition to edges.
- **Confidence:** High
- **Unresolved questions:** None for T1/T2. T3 requires live LM calls — gated scaffold only.

### Source: GitHub stanfordnlp/dspy
- **Link:** https://github.com/stanfordnlp/dspy
- **What was learned:**
  - Package name on PyPI is `dspy` (previously `dspy-ai`)
  - Active development with frequent releases
  - Uses LiteLLM under the hood for provider routing
  - `dspy.inspect_history()` for debugging/trace inspection
  - `dspy.streamify()` for streaming support
  - `dspy.asyncify()` for async support
- **Implementation consequence:** Detection checks both `dspy` and `dspy-ai` in requirements. Runner scaffold references `inspect_history` for future trace extraction.
- **Confidence:** High
- **Unresolved questions:** Streaming API (`streamify`) may be useful for T3 in future.

### Source: ARC Existing Adapter Patterns
- **Link:** `python/src/agent_runtime_cockpit/adapters/pydantic_ai/`, `langchain/`
- **What was learned:**
  - 3-tier pattern: detect.py (AST + import probe), export.py (AST visitor), runner.py (event handler)
  - DetectionResult NamedTuple with detected, confidence, evidence, version
  - AST visitors for class/assignment detection
  - Workspace scanning skips `.venv`, `venv`, `node_modules`
  - CapabilityReport must be honest about T1/T2/T3 status
  - Conformance tests validate detect(), capabilities(), export_workflow()
- **Implementation consequence:** DSPy adapter follows identical structure. Detection uses AST + import probe. Export uses AST visitor for Signature/Module classes. Runner is gated scaffold.
- **Confidence:** High
- **Unresolved questions:** None.

---

## 3. Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| Detection strategy | AST scan + import probe + requirements check | Runtime import only | Matches LangChain/Pydantic AI pattern; no code execution | `adapters/dspy/detect.py` | High |
| Signature extraction | AST ClassDef visitor for `dspy.Signature` subclasses | Regex scanning | AST is more reliable; matches existing export patterns | `adapters/dspy/export.py` | High |
| Module composition | AST detection of Predict/ChainOfThought/ReAct instantiations | Runtime introspection | Static analysis only; no code execution for T2 | `adapters/dspy/export.py` | High |
| Runner approach | Gated scaffold (env var `ARC_DSPY_RUNNER_ENABLED=1`) | Full execution | Requires live LM calls; gated matches truth constraints | `adapters/dspy/runner.py` | High |
| T3 event model | DSPY_PREDICT_START/END, DSPY_COMPILE_START/END, DSPY_MODULE_* | Generic events | DSPy-specific lifecycle is the adoption value | `adapters/dspy/runner.py` | High |
| Package detection | Both `dspy` and `dspy-ai` | Only `dspy` | Legacy package name still in use | `adapters/dspy/detect.py` | High |

---

## 4. Detection Targets (AST)

### Import Patterns
- `import dspy`
- `from dspy import ...`
- `from dspy.predict import ...`
- `from dspy.primitives import ...`

### Signature Classes
```python
class MySignature(dspy.Signature):
    """Docstring."""
    input_field: str = dspy.InputField()
    output_field: str = dspy.OutputField()
```

### Module Instantiations
- `dspy.Predict(signature)`
- `dspy.ChainOfThought(signature)`
- `dspy.ReAct(signature, tools=[...])`
- `dspy.ProgramOfThought(signature)`
- `dspy.MultiChainComparison(signature)`

### Custom Module Classes
```python
class MyModule(dspy.Module):
    def __init__(self):
        self.predict = dspy.Predict(MySignature)
    def forward(self, **inputs):
        return self.predict(**inputs)
```

### Requirements
- `dspy` or `dspy-ai` in `requirements.txt`, `pyproject.toml`

---

## 5. Truth Constraints

- No live provider/network calls in tests
- No DSPy compilation/optimization execution unless gated behind env var
- No broad DSPy adoption claims
- Detection must be AST-based (no code execution for detect/export)
- T3 runner is gated scaffold — requires `ARC_DSPY_RUNNER_ENABLED=1`
- Capability report must be honest: T1/T2 available, T3 gated
