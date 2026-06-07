# Workspace Intelligence Audit — 2026-06-07

> **Scope:** Code search, workspace inventory, symbols, file graph, test detection, repository awareness, IDE search integration  
> **Agent count:** 12 parallel sub-agents

---

## 1. Architecture Map

```
IDE (Theia)            TUI (/cmd)          CLI (arc *)
CommandCentre panel    /workspace          arc workspace inventory
 files/git/MCP/sym      trust-status only  arc workspace search
TestBenchTab           (/search exists)    arc testbench detect/run
 detect-only, no Run   /testbench: ABSENT  arc context pack
arc-context-drawer                         arc agents-md discover
 (widget stub only)
NO search panel
NO symbol browser
NO navigator integration
```

### Inventory payload (5 sections)

```json
{
  "workspace": "/abs/path",
  "files":   { "count": N, "total_size": N, "entries": [{ "path", "size", "suffix", "provenance": "workspace_file" }] },
  "git":     { "present": true, "branch", "commit", "commit_count", "dirty", "git_dir" },
  "traces":  { "count": N, "entries": [{ "name", "size", "provenance": "trace_store" }] },
  "mcp_resources": [{ "name", "provenance": "mcp_resource" }],
  "symbols": { "symbols": [...], "errors": [...], "total_symbols": N, "truncated": bool }
}
```

### Hard caps (all hardcoded, none CLI-exposed)

| Cap | Value |
|---|---|
| Max files (file walker) | 1000 |
| Max total bytes | 10 MB |
| Max files (symbol extractor input) | 500 |
| Max symbols total | 5000 |
| Max file size (symbol scan) | 512 KB |

### Ignored directories (hardcoded)

`.cache`, `.git`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.venv`, `.venv2`, `__pycache__`, `dist`, `lib`, `node_modules`, `src-gen`

---

## 2. CLI and IDE Feature Inventory

### CLI commands

| Command | JSON safe | Notes |
|---|---|---|
| `arc workspace inventory` | ✅ | files+git+traces+MCP+symbols |
| `arc workspace search <q>` | ✅ | ripgrep+pathlib, **no result cap**, no regex flag |
| `arc workspace init` | ✅ | isolation chooser |
| `arc workspace info` | ✅ | name, trust level |
| `arc workspace trust/untrust/trust-status` | ✅ | trust DB operations |
| `arc testbench detect` | ✅ | 17 config scanners, structured output |
| `arc testbench run -- <cmd>` | ✅ | sandbox-gated, JSONL streaming mode |
| `arc context pack --task` | ✅ | ContextEngine fan-out |

### TUI slash commands

| Command | Status |
|---|---|
| `/search <regex>` | ✅ (50-match cap, `--include`, `--path`) |
| `/workspace trust-status` | ✅ (stub — only trust-status, nothing else) |
| `/context pack <task>` | ✅ |
| `/testbench` | ❌ absent |
| `/workspace inventory` | ❌ absent |

### IDE panels

| Panel | Status |
|---|---|
| CommandCentreTab workspace section | ✅ minimal (counts + trust level) |
| TestBenchTab | ✅ detect-only, **no Run button** |
| CiGuardrailsTab | ✅ read-only |
| arc-context-drawer | ⚠️ ID+LABEL stub only |
| Search panel | ❌ absent |
| Symbol browser | ❌ count only (one integer) |
| Theia navigator integration | ❌ absent |
| File-graph / dependency graph | ❌ absent |

---

## 3. Code Search Gap Analysis

```
Current state:
  arc workspace search   → lexical substring (ripgrep literal)
  LocalRepoProvider      → keyword frequency scoring (coarse)
  GitHub provider        → hardcoded to eclipse-theia/theia repo

Critical gaps:
  No result cap in CLI     → OOM / terminal flood on broad queries
  No regex mode            → users must know exact text
  No file-type filter CLI  → searches all file types
  No case-insensitive flag
  No shared search library → CLI and provider diverge completely
  No semantic/embedding    → intent-based queries fail
  GitHub provider hardcoded → useless for own repos
  No chat injection bridge → results invisible to agent
  No line_number on entry  → no IDE navigation
  pathlib fallback has no timeout → hangs on large repos
```

### Symbol accuracy

| Language | Method | Accuracy |
|---|---|---|
| Python | AST (`ast.parse`) | HIGH ✅ |
| TypeScript/TSX | Regex + brace scanner | LOW-MEDIUM ⚠️ |
| JavaScript/JSX | Regex + brace scanner | LOW-MEDIUM ⚠️ |

Known TS/JS issues: arrow functions captured as `variable`, class expressions missed, brace scanner desyncs on template literals, `text[:start].count("\n")` is O(position) per match.

---

## 4. Performance and Safety Risks

### Performance

| Risk | Severity |
|---|---|
| No result cap on `arc workspace search` | High — OOM/flood risk |
| `_is_nested_function` O(n²) in Python symbol extractor | Medium |
| TS line-number O(position) per match | Medium |
| `LocalRepoProvider` no file-size guard | High — 100MB JSON file → OOM |
| 4× sequential git subprocesses (max 20s blocking) | Medium |
| `ContextCache` exists but is never used | Medium — dead code |
| `rglob` traversal is O(N_total) even with file cap | Medium |
| Double `iter_workspace_files` call in `/inspect` route | Low |

### Security

| Risk | Severity |
|---|---|
| `.env`/`*.key` not excluded from inventory/search | **High** |
| `workspace inventory` has no trust gate | **High** |
| `workspace search` has no trust gate | **High** |
| `workspace_search` confinement uses `relative_to()` not `realpath()` | Medium |
| `_SECRET_READ_DENY` list never consulted by scanner | **High** |
| `resolve_python_entrypoint()` no trust check | **High** |
| No gitignore integration | Medium |

### Test quality issues

| Issue | File |
|---|---|
| Weak or-chain assertion | `test_workspace_search_path_confined` |
| `test_no_duplicates` soft fallback — passes vacuously | `test_context.py` |
| `os.chdir(tmp_path)` fragile under parallel execution | `test_phase59_memory_graph.py` |

---

## 5. Test Requirements (prioritized)

| Priority | Test |
|---|---|
| P0 | `test_workspace_search_result_cap` — assert ≤200 results and `truncated: True` |
| P0 | `test_workspace_search_no_env_file_in_results` |
| P0 | `test_workspace_inventory_no_key_file_in_results` |
| P1 | `test_workspace_search_path_confined_uses_realpath` — specific exit code, not or-chain |
| P1 | `test_symbol_extraction_is_nested_function_benchmark` — performance regression guard |
| P1 | `test_workspace_search_pathlib_timeout` |
| P1 | `test_testbench_linters_separate_from_runners` |
| P2 | `test_workspace_search_gitignore_respected` |
| P2 | `test_context_pack_no_env_file_content` |
| P3 | `test_git_metadata_dirty_true` |

---

## 6. Next-Slice Implementation Prompt

**Target:** Safe workspace search + sensitive file exclusion + provenance line numbers

### 1. Sensitive file exclusion in `iter_workspace_files()`

```python
_SENSITIVE_FILENAMES = frozenset({
    ".env", ".env.local", ".env.production", ".env.staging", ".env.test",
    "id_rsa", "id_ed25519", "id_dsa", "id_ecdsa",
    ".netrc", ".npmrc", ".pypirc", ".git-credentials",
})
_SENSITIVE_SUFFIXES = frozenset({".key", ".pem", ".p12", ".pfx", ".cer", ".crt"})
_SENSITIVE_PATTERNS = frozenset({"credentials", "secrets"})
```

Skip files matching any pattern in `iter_workspace_files()` and `LocalRepoProvider.retrieve()`.

### 2. Search result cap + pathlib timeout

In `workspace_search()`:
- Add `MAX_SEARCH_RESULTS = 200`
- Add `"truncated": bool, "count": int` to JSON envelope
- Pathlib fallback: add `time.monotonic()` deadline check (30s)
- Fix confinement: `candidate.resolve().relative_to(ws.resolve())` (add `.resolve()`)

### 3. `line_number` field on `ContextPackEntry`

```python
line_number: Optional[int] = None  # 1-indexed start line of snippet
end_line: Optional[int] = None
```

Update `LocalRepoProvider._extract_snippet()` to capture start line.
Update `source` format to `"path/to/file.py:12"` (matching `/search` output).

### 4. Add `/workspace inventory` and `/testbench` to TUI

Minimal dispatch to existing CLI functions via existing adapter bridge.

### 5. Add README entries

`arc workspace search <query>`, `arc testbench detect --json`, `arc testbench run --policy local-safe -- pytest`

### Do NOT do

- Semantic/embedding search
- @symbol mention parsing (Reserved v0.2)
- TypeScript AST replacement
- IDE search panel

---

## Key Findings Summary

**Three biggest problems:**

1. **Sensitive files are not excluded.** `.env`, `*.key`, `credentials.*` appear in inventory and `LocalRepoProvider` context packs. The sandbox `_SECRET_READ_DENY` list exists but is never consulted during file scanning.

2. **`arc workspace search` has no result cap.** An empty query or broad pattern on a large repo produces unbounded output. Pathlib fallback has no timeout.

3. **Context provenance is line-number-blind.** `ContextPackEntry` has no `line_number` field, breaking IDE navigation and citation. `EvidenceRef` system has full file:line range but is disconnected from context retrieval.
