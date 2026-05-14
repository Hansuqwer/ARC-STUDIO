# U-1 / U-2 Decisions — Pre-Merge Gates

> Context: Before `feature/security-and-mapper-fixes` merges to `main`, two residual security items need a decision. Both are documented in `docs/SECURITY_AUDIT_REPORT.md`. This doc provides the research and trade-offs.

---

## U-1: History Scrub on `.env` with `G4F_API_KEY`

### Facts

- A `G4F_API_KEY` (free GPT4Free service key) was committed in commit `e5d1414`.
- The key was later **rotated** (G4F provider switched to no-key endpoint), **removed from tracking**, and `.env.example` was added.
- The key value remains retrievable from **pre-`f08ef52` history** (any commit before the cleanup).
- The repo is now **private**, single-collaborator (`Hansuqwer`).
- No forks, no other clones in the wild.

### Options

#### Option A: Accept the risk (defer scrub)

- **Cost**: Zero effort. Nothing to do.
- **Risk**: The key was for a free service that no longer requires keys. Even if retrieved, the attacker gains access to... GPT4Free, which is a free proxy service. The key has been rotated. The repo is private.
- **Downside**: If the repo ever goes public (unlikely), the key is in history. Technically non-compliant with a strict secret-zero policy.
- **Verdict**: Pragmatic for alpha. The key is low-value, rotated, and the repo is private.

#### Option B: Scrub with `git filter-repo` (recommended tool)

```
git clone --mirror git@github.com:Hansuqwer/arc-theia-studio.git temp-clone
cd temp-clone
git filter-repo --path .env --invert-paths
git log --all --name-status -- .env              # verify gone
git push --force --mirror origin
cd .. && rm -rf temp-clone
```

- **Effect**: Rewrites **all SHAs** from `e5d1414` onward. Every commit changes hash.
- **Impact on PRs #17/#18**: Both are already merged. The merge commits reference pre-scrub SHAs in their parents. After scrub, those SHAs no longer exist → merge commits become orphaned. You'd need to recreate the merge commits or rebase.
- **Cost**: ~15 minutes of work, but **rewrites history for the entire repo**. All open PRs would need recreation. All local clones would need `git pull --force`.
- **Tool used**: `git filter-repo` (not BFG). BFG is 10-720x faster for large repos but requires Java (available: OpenJDK 17). However, `git filter-repo` is the Git project's recommended replacement for `filter-branch`, has better path-based filtering, and is already available if you have `git` installed on many systems. For a repo this size, speed is irrelevant — both finish in seconds.

#### Option C: Scrub with BFG Repo-Cleaner

```
git clone --mirror git@github.com:Hansuqwer/arc-theia-studio.git temp-clone
cd temp-clone
java -jar bfg.jar --delete-files .env
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push --force --mirror origin
```

- **Same effect** as filter-repo: all SHAs rewritten.
- Requires Java (available: OpenJDK 17) and downloading BFG JAR.
- Slightly simpler syntax for file deletion, but less control.
- **Recommendation**: Use `git filter-repo` over BFG — no external dependency, better maintained, more precise path control.

### Recommendation for U-1

**Accept the risk (Option A)**. The key was for a free service, has been rotated, the repo is private, and the history rewrite would orphan the merge commits from PRs #17/#18. The security benefit is negligible (free-tier API key, already rotated). Do the scrub before ever making the repo public, but for alpha, defer it.

---

## U-2: Daemon Authentication Default

### Facts

- The daemon binds to `127.0.0.1:7777` (loopback only).
- Current behavior (from `python/src/agent_runtime_cockpit/web/server.py`):
  - When `ARC_DAEMON_TOKEN` env var is **unset** → no auth (pass-through)
  - When `ARC_DAEMON_TOKEN` is **set** → `Authorization: Bearer <token>` required on all endpoints except `/health`
  - Token comparison uses `hmac.compare_digest` (constant-time)
  - `/health` is always open for liveness probes
- This is the **single-user, loopback-only** default (standard for local dev tools)
- 5 tests cover all auth states (`test_daemon_auth.py`: 88 lines)

### Options

#### Option A: Keep opt-in (current behavior)

- **`ARC_DAEMON_TOKEN` unset by default** → no auth
- **Effort**: Nothing to change. Works today.
- **Risk**: Any process on the same host can reach the daemon. On a single-user workstation this is acceptable (processes run as you). On a shared dev container or CI runner, it's a real exposure.
- **Precedent**: Docker daemon, Redis, Postgres — all default to no-auth on localhost for local development.

#### Option B: Require token by default

- Change the default: generate a random token at startup if none is set, or fail to start without it.
- **Effort**: Small code change (add a default-token fallback or startup check).
- **Impact**: Breaks backward compatibility for anyone running without the env var. The TypeScript client already sends the token automatically when the env var is present, but would need updating if the daemon generates a random token.
- **Benefit**: Safer out of the box. No silent exposure if someone deploys to a shared host without reading the docs.

#### Option C: Generate a random token when unset (middle ground)

```python
import secrets
TOKEN = os.environ.get("ARC_DAEMON_TOKEN") or secrets.token_hex(32)
```

- **Effort**: One line of code.
- **Impact**: Zero-config security. Every daemon instance gets a unique token. The TypeScript client would need to be told what token to use (can't rely on env var anymore).
- **Downside**: Harder to debug (token is ephemeral). The TypeScript client needs to discover the token somehow (via a startup file, stdout, or a one-time setup endpoint).

### Recommendation for U-2

**Keep opt-in (Option A) for now**, but document the trade-off clearly in `README.md` (already done at line 186). The single-user, loopback-only design is standard for local developer tools. The optional token scheme exists for users who want it. Revisit if:
- You add multi-tenant support
- You deploy to a shared dev container
- Someone opens a security issue about it

If you want a quick win without breaking changes, **Option C** (generate a random token when unset) is low-effort but creates a token-discovery problem for the TypeScript client. Worth deferring until the client integration is tighter.

---

## Summary & Action

| Item | Decision | Effort | Blocking merge? |
|------|----------|--------|-----------------|
| **U-1** | ✅ **Accept risk** (defer BFG/filter-repo scrub) | 0 | **No** — proceed |
| **U-2** | ✅ **Keep opt-in** (current behavior) | 0 | **No** — proceed |

**Neither U-1 nor U-2 blocks the merge to `main`.** Both are accepted/mitigated risks for alpha. The feature branch can merge to main immediately, and the first tag can be cut.

After the merge and tag, document both decisions in `CHANGELOG.md` with a note about when to revisit.
