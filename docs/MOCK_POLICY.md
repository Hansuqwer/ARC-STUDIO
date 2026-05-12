# Mock Policy

Mocks are allowed only for tests and explicit demos.

## Allowed

- Test fixtures under `packages/arc-test-fixtures`.
- Python test helpers and fixture workflows/schemas.
- Demo-only methods with names that include `demo`.

## Not Allowed

- Silent mock fallback in normal UI/backend paths.
- Fake successful run records when no real adapter can execute a workflow.
- Runtime capabilities claiming support because a fixture exists.

## Required Metadata

Every remaining mock must document:

- Owner.
- Reason.
- Real implementation path.
- Removal condition.

## Normal Product Behavior

If the daemon, CLI, external service, or runtime is unavailable, the product must return an explicit error envelope and render an error state.

The normal SwarmGraph run path invokes the real local `swarmgraph swarm --json` CLI. Its default backend is `stub`, which is local and non-paid. Provider-backed execution requires explicit approval before changing `ARC_SWARMGRAPH_RUN_BACKEND` to a live backend.

Run traces are stored under `<workspace>/.arc/traces`. `arc runs prune --workspace <path> --keep N` is dry-run by default and deletes only with `--yes`.
