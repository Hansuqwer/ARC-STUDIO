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
