# Release Procedure

This document defines how to tag, publish, and roll back ARC Studio releases.

## Authority

Only repository maintainers may create or delete release tags.

Before tagging, verify `docs/RELEASE_CHECKLIST.md` and record any explicit
exceptions in the release notes.

## Preconditions

1. `main` is the source branch.
2. Working tree is clean: `git status --short` returns no output.
3. All 5 workflows are green on `main`.
4. `docs/RELEASE_CHECKLIST.md` required items are checked or have documented exceptions.

## Tag A Release

Run from a clean checkout on `main`:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git status --short
git tag -a v0.6.0-alpha -m "ARC Studio v0.6.0-alpha"
git push origin v0.6.0-alpha
```

After pushing the tag:

1. Verify GitHub Actions runs for the tag.
2. Verify release artifacts, if any, are attached to the GitHub release.
3. Publish release notes with known exceptions from `docs/RELEASE_CHECKLIST.md`.

## Roll Back A Tag Before Public Announcement

Use this path if the tag is wrong but has not been announced externally.

```bash
git push --delete origin v0.6.0-alpha
git tag -d v0.6.0-alpha
```

Then fix `main`, create a new tag, and document the replacement tag in the
release notes.

## Roll Back After Public Announcement

Use this path if users may already have consumed the tag.

1. Do not silently delete the tag.
2. Publish a GitHub release note marking the tag as withdrawn.
3. Create a patch release from the last known-good SHA.
4. Link the withdrawn tag, replacement tag, and root-cause issue.

If deletion is unavoidable for security reasons, announce it before deletion
and include remediation steps for users who already pulled the tag.

## Revert A Bad Release Commit

If the release points at a bad commit on `main`:

```bash
git revert <bad-sha>
git push origin main
```

Never use `git reset --hard` or force-push `main` for release rollback unless
all maintainers explicitly approve an emergency history rewrite.
