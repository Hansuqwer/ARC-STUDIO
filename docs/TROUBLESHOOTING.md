# ARC Studio — Troubleshooting

## Build Fails with Webpack Errors

**Symptom:** `pnpm build` fails with webpack compilation errors.

**Fixes:**
1. Clean and rebuild:
   ```bash
   pnpm clean && pnpm install && pnpm build
   ```
2. Check Node.js version (must be >= 18.0.0):
   ```bash
   node --version
   ```
3. Check pnpm version (must be >= 8.0.0):
   ```bash
   pnpm --version
   ```
4. Clear pnpm cache and reinstall:
   ```bash
   pnpm store prune
   rm -rf node_modules
   pnpm install
   pnpm build
   ```
5. Check for TypeScript errors specifically:
   ```bash
   cd packages/arc-extension && npx tsc --noEmit
   ```
6. Verify all dependencies are installed:
   ```bash
   pnpm install --frozen-lockfile
   ```

---

## Application Won't Start

**Symptom:** `pnpm start:browser` fails or browser shows blank page.

**Fixes:**
1. Ensure `pnpm build` ran successfully first:
   ```bash
   pnpm build
   echo $?  # Should output 0
   ```
2. Check Node.js version: `node --version` (must be 18+)
3. Clear build artifacts and rebuild:
   ```bash
   pnpm clean && pnpm install && pnpm build
   ```
4. Check port 3000 is free:
   ```bash
   lsof -i :3000
   kill -9 <PID>  # If a process is using it
   ```
5. Try starting with explicit port:
   ```bash
   PORT=3001 pnpm start:browser
   ```
6. Check browser console for JavaScript errors (F12 → Console tab)
7. Verify the browser app package is built:
   ```bash
   ls packages/arc-browser-app/lib/
   ```

---

## Widget Not Visible

**Symptom:** ARC Studio widget doesn't appear in the sidebar.

**Fixes:**
1. Check the left activity bar for the ARC Studio icon (project-diagram / network graph icon)
2. If the icon is missing, the extension may not be loaded:
   ```bash
   # Rebuild the extension
   cd packages/arc-extension && pnpm build
   cd ../.. && pnpm start:browser
   ```
3. Try opening via command palette:
   - Press `Ctrl+Shift+P` (`⌘+Shift+P` on Mac)
   - Type "ARC Studio"
   - Select the command to open the widget
4. Check browser console for errors:
   - Press F12 to open DevTools
   - Go to Console tab
   - Look for errors related to `arc-extension` or `arc-widget`
5. Verify the extension is in the browser app's dependencies:
   ```bash
   cat packages/arc-browser-app/package.json | grep arc-extension
   ```
6. Hard refresh the browser: `Ctrl+Shift+R` (`⌘+Shift+R` on Mac)

---

## Workflow Execution Fails

**Symptom:** Clicking "Execute Workflow" results in an error.

**Fixes:**
1. **Empty prompt:** Ensure you've entered text in the prompt input field
2. **SwarmGraph CLI not found:**
   ```bash
   which swarmgraph
   # If not found, install from: https://github.com/Hansuqwer/SwarmGraph
   ```
3. **SwarmGraph not in PATH:**
   ```bash
   # Add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
   export PATH="$PATH:/path/to/swarmgraph"
   ```
4. **Execution timeout:** Default timeout is 5 minutes. Complex workflows may need more time.
5. **Check error details:** The error banner shows specific failure information
6. **Try stub backend for testing:**
   - Use the stub backend to test without API calls
   - This avoids LLM provider authentication issues
7. **Verify trace directory exists:**
   ```bash
   mkdir -p .arc/traces
   ```
8. **Check permissions:**
   ```bash
   ls -la .arc/traces/
   chmod 755 .arc/traces/
   ```

---

## Traces Not Loading

**Symptom:** "Load Traces" returns no results or fails.

**Fixes:**
1. **No traces exist yet:** Execute a workflow first to generate traces
2. **Trace directory missing:**
   ```bash
   mkdir -p .arc/traces
   ```
3. **Check for trace files:**
   ```bash
   ls -la .arc/traces/
   # Should show .jsonl files
   ```
4. **Trace files are empty or corrupted:**
   ```bash
   # Check a trace file
   cat .arc/traces/run-sg-*.jsonl | head -5
   # Each line should be valid JSON
   cat .arc/traces/run-sg-*.jsonl | jq . 2>&1 | head -20
   ```
5. **File permissions:**
   ```bash
   chmod 644 .arc/traces/*.jsonl
   ```
6. **Filter is too restrictive:** Clear the filter input (click ×) and try again
7. **Check browser console for parse errors:**
   - Press F12 → Console tab
   - Look for JSON parse errors

---

## Keyboard Shortcuts Not Working

**Symptom:** Pressing `Ctrl+E`, `Ctrl+L`, `Ctrl+S`, or `Ctrl+H` does nothing.

**Fixes:**
1. **Widget must have focus:** Click anywhere inside the ARC Studio panel first, then try the shortcut
2. **Browser shortcuts conflict:** Some shortcuts may conflict with browser defaults:
   - `Ctrl+S` conflicts with browser save — the widget overrides this when focused
   - `Ctrl+H` conflicts with browser history on some browsers — try `Ctrl+?` as alternative
3. **Check if modifier key works:**
   - On Mac, use `⌘` (Command) instead of `Ctrl`
   - On Windows/Linux, use `Ctrl`
4. **Prompt input shortcut:** `Ctrl+Enter` only works when the prompt input field is focused
5. **Verify keyboard handler is registered:**
   - Open browser console (F12)
   - Look for widget initialization logs
6. **Try clicking the buttons directly** to verify functionality works
7. **Refresh the page** and try again:
   ```
   Ctrl+Shift+R (hard refresh)
   ```

---

## High Memory Usage

**Symptom:** Application uses excessive memory, becomes slow or unresponsive.

**Fixes:**
1. **Large trace files:** Use streaming for large traces:
   ```bash
   # Check trace file sizes
   ls -lh .arc/traces/
   # Files > 100MB may cause memory issues
   ```
2. **Clean old traces:**
   ```bash
   # Remove traces older than 7 days
   find .arc/traces/ -name "*.jsonl" -mtime +7 -delete
   ```
3. **Reduce concurrent executions:** Avoid running multiple workflows simultaneously
4. **Restart the application:**
   ```bash
   # Stop the current process (Ctrl+C)
   pnpm start:browser
   ```
5. **Clear browser cache:**
   - Open DevTools (F12)
   - Right-click the refresh button → "Empty Cache and Hard Reload"
6. **Monitor memory usage:**
   - Chrome DevTools → Performance tab → Memory
   - Look for memory leaks in trace loading
7. **Use stub backend for testing** to avoid large trace generation:
   - Stub backend generates minimal trace data

---

## Browser App Won't Start

**Symptom:** `pnpm start:browser` fails or browser shows blank page.

**Fixes:**
1. Ensure `pnpm build` ran successfully first
2. Check Node.js version: `node --version` (must be 20+)
3. Clear build artifacts: `pnpm clean && pnpm install && pnpm build`
4. Check port 3000 is free: `lsof -i :3000`

---

## ARC Panel Shows Mock Data

**This is expected** when the Python daemon is not running.

**To connect real data:**
```bash
cd python
uv run arc serve
# ARC daemon running on http://localhost:7777
```

Then reload the browser (Theia will reconnect automatically).

---

## Python CLI Not Found

**Symptom:** `uv run arc --help` fails.

**Fix:**
```bash
cd python
uv sync --all-extras --dev
uv run arc --help
```

If `uv` is not installed:
```bash
pip install uv --user
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Context7 Returns Mock Data

**Symptom:** Context pack shows "[MOCK — Context7 API key not set]"

**Fix:**
```bash
export ARC_CONTEXT7_API_KEY=your_key
uv run arc context pack --task "theia extension"
```

Get a key at https://context7.com/

---

## GitHub Search Returns Mock Data

```bash
export GITHUB_TOKEN=ghp_your_token
```

---

## Conformance Tests Fail

```bash
uv run arc adapter test swarmgraph --debug
uv run arc adapter test langgraph --debug
```

---

## Theia Build Fails (Native Modules)

For Electron, native modules must be rebuilt:

```bash
cd applications/electron
pnpm rebuild
```

---

## E2E Tests Fail

1. Ensure browser app is running: `pnpm start:browser`
2. Install Playwright browsers: `cd tests/e2e && pnpm install:browsers`
3. Run E2E: `pnpm test:e2e`

---

## Port 7777 Already in Use

```bash
lsof -i :7777
kill -9 <PID>
# or use a different port:
uv run arc serve --port 7778
```

---

## ARC Daemon Not Detected by Theia

Theia checks `localhost:7777/health` on startup. Ensure:
1. Daemon is running: `uv run arc serve`
2. No firewall blocking localhost
3. Check ARC settings: `arc.daemon.port` (default: 7777)

---

## Port 3000 Already in Use

```
Error: listen EADDRINUSE: address already in use :::3000
```

**Solution:**
```bash
# Find process using port 3000
lsof -i :3000

# Kill the process
kill -9 <PID>

# Or use different port
PORT=3001 pnpm start:browser
```

---

## Changes Not Reflected in Browser

**Solution:**
1. Stop the application (Ctrl+C)
2. Rebuild: `pnpm build`
3. Restart: `pnpm start:browser`
4. Hard refresh browser (Cmd+Shift+R)

---

## Known Issues

- **Electron signing not configured** — Requires CSC_LINK, CSC_KEY_PASSWORD, and Apple ID
- **LangGraph runtime execution** — Only dynamic workflow export is implemented
- **No rate limiting** — Planned for Phase 7
- **No authentication** — Planned for Phase 7
- **CrewAI, OpenAI Agents SDK, AG2 adapters** — Not yet implemented

For more issues, see [GitHub Issues](https://github.com/Hansuqwer/arc-theia-studio/issues).
