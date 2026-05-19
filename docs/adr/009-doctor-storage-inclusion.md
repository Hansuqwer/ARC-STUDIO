# ADR-009: Doctor Storage Inclusion in `arc doctor all`

**Status:** Accepted  
**Date:** 2026-05-19  
**Author:** Release engineering automation  
**Supersedes:** N/A  

## Context

Phase 11 (Discipline Audits) identified that `arc doctor storage` exists as a standalone subcommand but is not included in `arc doctor all`. Phase 14 requires a decision on whether storage checks should be part of the comprehensive doctor command, documented in an ADR before implementation.

### Current State

- `arc doctor all` (lines 739-882 in `cli.py`) runs 6 subchecks: python version, CLI version, runtime detection, daemon connectivity, SwarmGraph CLI availability, and provider env-presence diagnostics.
- `arc doctor storage` (lines 970-1010 in `cli.py`) runs 4 subchecks: traces_dir existence/count, SQLite index existence/size, indexed_runs count, and evals_dir existence.
- The `evals_dir` check is explicitly non-gating (marked as informational only).

### Risks

Storage checks involve filesystem access (directory listing, file stat, SQLite query). The Phase 11 audit noted: "storage scans may be slower than normal doctor checks." The specific concerns are:

1. **`traces_dir`**: `traces_dir.glob("*.jsonl")` — counts JSONL files in `.arc/traces/`. Fast even with thousands of files (glob is O(n) in directory entries).
2. **`sqlite_index`**: `db_path.stat().st_size` — single file stat. O(1), negligible.
3. **`indexed_runs`**: `store.count_runs()` — opens SQLite and runs `SELECT COUNT(*)`. Fast (sub-millisecond for typical datasets; <100ms even for millions of rows with proper indexing).
4. **`evals_dir`**: `evals_dir.exists()` — single stat call. O(1), negligible.

**Conclusion:** The performance risk is negligible. None of the storage checks involve expensive scans, large file reads, or network I/O.

## Decision

Include storage checks in `arc doctor all` as subcheck #7, preserving the following semantics:

1. All four storage checks from `arc doctor storage` are included.
2. The `evals_dir` check remains non-gating (informational only), matching existing behavior.
3. `arc doctor storage` remains as a standalone subcommand for detailed storage-only diagnostics.
4. The storage section in `doctor all` is labeled with `"scope": "workspace_storage"` to distinguish from other check categories.

This avoids:
- Adding new failure modes to `doctor all` beyond what `doctor storage` already reports (the checks are the same).
- Performance regressions (checks are all O(1) or O(n) with negligible n).
- Duplicating maintenance burden (both `doctor all` and `doctor storage` share the same logic via inlined equivalent checks).

## Consequences

1. `arc doctor all` output format changes: a new `workspace_storage` check category appears.
2. Users running `arc doctor all` will see workspace storage diagnostics without needing a separate command.
3. `arc doctor storage` is preserved for focused storage debugging.
4. Test coverage must be updated to reflect the new storage subcheck in `doctor all`.
5. Release docs must be updated to state that storage is included in `doctor all`.

## References

- Phase 14 acceptance criterion 2: "`arc doctor all` storage behavior is ADR-backed, tested, and documented."
- PHASE_IMPLEMENTATION_PLAN.md Phase 14 section.
- LOCKED_REMAINING_ROADMAP.md Phase 11 Discipline Audit section.
