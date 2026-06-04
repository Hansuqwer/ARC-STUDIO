# Follow-up: scripts/check-pr.sh false-positives on env-var references

## Problem
`pnpm check:pr` fails on `vendor/copilot-arena-server/docker-compose.yml`
because the secret scan matches `${OPENAI_API_KEY}`, which is an env-var
reference, not a leaked secret.

## Verification
This failure exists on `main` before `feat/post-merge-and-ux-p0`.

## Fix
Exclude `\${[A-Z_]+}` patterns from the secret-scan regex in
`scripts/check-pr.sh`. ~5 LOC.

## Priority
Low — single false positive, doesn't block CI on the vendored
sub-repo path. Fix in a standalone PR.
