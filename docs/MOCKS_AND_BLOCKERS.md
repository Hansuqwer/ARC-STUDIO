# ARC Studio — Mocks and Blockers Register

## Active Mocks

### Python Backend

| Mock | File | Reason | Fix Command |
|------|------|--------|-------------|
| Context7 provider | `context/providers/context7.py` | `ARC_CONTEXT7_API_KEY` not set | `export ARC_CONTEXT7_API_KEY=<key>` |
| Vercel Grep provider | `context/providers/vercel_grep.py` | No official API | Implement when API available |
| GitHub search | `context/providers/github_code_search.py` | `GITHUB_TOKEN` not set | `export GITHUB_TOKEN=<token>` |
| Web search | `context/providers/web_search.py` | `ARC_SEARCH_API_KEY` not set | `export ARC_SEARCH_API_KEY=<key>` |
| SwarmGraph live exec | `adapters/swarmgraph.py` | Library not installed | `pip install git+https://github.com/Hansuqwer/SwarmGraph` |
| LangGraph live exec | `adapters/langgraph.py` | Library not installed | `pip install langgraph` |
| A2UI validator | `extensions/a2ui.py` | Spec experimental | Await A2UI v1.0 |

### TypeScript/Theia Frontend

| Mock | File | Reason | Fix |
|------|------|--------|-----|
| ARC service fallback | `arc-core/src/node/arc-service-impl.ts` | Python daemon may not be running | `uv run arc serve` |
| Fixture workflow data | `arc-service-impl.ts:MOCK_DATA` | No live workspace | Open real project + start daemon |
| Replay viewer | `arc-runs` | Not implemented | Implement after trace schema stable |
| Flutter extension | `theia-extensions/arc-adapters` | Disabled by default | Enable `arc.extensions.enableFlutter` |
| A2UI extension UI | `arc-adapters` | Experimental | Enable `arc.extensions.enableA2UI` |

### Packaging

| Mock | File | Reason | Fix |
|------|------|--------|-----|
| Electron code signing | `applications/electron/electron-builder.release.yml` | No certs in CI | Set `CSC_LINK`, `CSC_KEY_PASSWORD`, `APPLE_ID` |
| VS Code plugin download | `plugins/README.md` | No plugins configured | Add to `theiaPlugins` in root `package.json` |

## Hard Blockers

Normal product paths must not return mock success. Current hard blockers before beta:

- Prove Theia build with pnpm.
- Implement real SwarmGraph execution or keep `can_run=False`.
- Implement LangGraph dynamic graph loading or narrow capability claims further.
- Verify E2E against a running browser app.

## Soft Blockers (require credentials)

| Blocker | Missing Credential | Smallest Repro |
|---------|-------------------|----------------|
| Context7 live docs | `ARC_CONTEXT7_API_KEY` | `export ARC_CONTEXT7_API_KEY=<key> && uv run arc context pack --task test` |
| GitHub code search | `GITHUB_TOKEN` | `export GITHUB_TOKEN=<token> && uv run arc context pack --task test` |
| Web search | `ARC_SEARCH_API_KEY` | `export ARC_SEARCH_API_KEY=<key> ARC_SEARCH_PROVIDER=brave && uv run arc context pack --task test` |
| Mac signing | `CSC_LINK` + `APPLE_ID` | `pnpm package:electron:mac` |
| Win signing | `CSC_LINK` + `CSC_KEY_PASSWORD` | `pnpm package:electron:win` |
