# .env History Scrub Plan

This is a gated release task. Do not run it during normal development.

## Trigger

Run only after a v0.1.0-alpha release date is set and at least 7 days before the tag.

## Why

The repository history may contain a deleted `.env`. Public release branches must not expose historic secrets or misleading local credentials.

## Preconditions

- Release owner announces the scrub window.
- All active branches are paused or rebased after the scrub.
- A fresh clone is used for the rewrite.
- Current private remotes/backups are confirmed.
- Any real secrets that ever appeared in `.env` are rotated before the rewrite.

## Procedure

```bash
git clone git@github.com:Hansuqwer/arc-theia-studio.git arc-theia-studio-scrub
cd arc-theia-studio-scrub
git checkout main
git pull --ff-only

# Requires git-filter-repo. Install outside this repo if needed.
git filter-repo --path .env --invert-paths

# Verify `.env` is absent from rewritten history.
git log --all --full-history --diff-filter=D -- .env
git rev-list --objects --all | grep -F '.env' && exit 1 || true
```

## Publish Plan

```bash
git remote add scrubbed git@github.com:Hansuqwer/arc-theia-studio.git
git push scrubbed main:scrubbed-main
```

After review, replace `main` only with explicit maintainer approval:

```bash
git push --force-with-lease scrubbed main
```

## Risks

- History rewrite invalidates old commit SHAs.
- Open PRs and local clones must rebase or reclone.
- Force-push requires coordination and should never happen during active work.

## Rollback

Rollback is the preserved pre-scrub remote branch or backup clone. Do not delete it until the release tag is published and verified.
