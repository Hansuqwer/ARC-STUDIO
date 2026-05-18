# .env History Scrub Plan

This is a gated release task. Do not run it during normal development.

**Current status (2026-05-18):** Preparation only. Target release date is 2026-06-01 and latest observed required-ish GitHub `main` workflows are green on `6fed466`, but no `.env` scrub, history rewrite, force-push, secret rotation, branch deletion, tag, publish, or release action is approved.

## Trigger

Run only after ARC Studio is working as intended, a v0.1.0-alpha release date is re-set, and the scrub is at least 7 days before the tag.

## Why

The repository history may contain a deleted `.env`. Public release branches must not expose historic secrets or misleading local credentials.

## Preconditions

- Release owner announces the scrub window.
- All active branches are paused or rebased after the scrub.
- A fresh clone is used for the rewrite.
- Current private remotes/backups are confirmed.
- Any real secrets that ever appeared in `.env` are rotated before the rewrite.

## Non-Destructive Preparation Checklist

These checks may be refreshed before the scrub window because they do not rewrite history or publish anything:

- Confirm release date is set and scrub date is at least 7 days before the planned tag.
- Confirm required GitHub `main` workflows are green; current baseline reference remains last all-green `073238d` until superseded by a newer all-green set.
- Confirm release owner and maintainer approver names.
- Confirm backup/private remote strategy and rollback branch name.
- Confirm all active PR/branch owners know a future rewrite may require rebase or reclone.
- Confirm any real secrets that ever appeared in `.env` are identified for rotation outside this repo.
- Confirm `git-filter-repo` availability in a disposable clone outside the working repository.
- Record the exact approval strings that will be required later, separately, for any history rewrite and force-push.

Do not run `git filter-repo`, rotate secrets, delete refs, tag, publish, release, or force-push during preparation.

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
