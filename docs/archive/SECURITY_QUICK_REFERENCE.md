# Security Quick Reference Guide

## For Developers Working on ARC Studio

This guide provides quick reference for secure coding practices in the ARC Studio project.

---

## ⚠️ Critical Security Rules

### 1. NEVER Interpolate User Input into Shell Commands

```typescript
// ❌ WRONG - Vulnerable to command injection
const command = `swarmgraph swarm --json "${userInput}"`;
exec(command);

// ✅ CORRECT - Safe from command injection
import { sanitizePrompt } from './security-utils';
const sanitized = sanitizePrompt(userInput);
spawn('swarmgraph', ['swarm', '--json', sanitized], { shell: false });
```

### 2. ALWAYS Validate File Paths

```typescript
// ❌ WRONG - Vulnerable to path traversal
const filePath = path.join(baseDir, userProvidedPath);
fs.readFile(filePath);

// ✅ CORRECT - Protected against path traversal
import { validateFilePath } from './security-utils';
const safePath = validateFilePath(userProvidedPath, workspaceRoot);
fs.readFile(safePath);
```

### 3. ALWAYS Sanitize User Inputs

```typescript
// ❌ WRONG - No validation
async function executeWorkflow(prompt: string) {
    // Direct use of prompt
}

// ✅ CORRECT - Validated and sanitized
import { sanitizePrompt } from './security-utils';
async function executeWorkflow(prompt: string) {
    const sanitized = sanitizePrompt(prompt); // Throws on invalid input
    // Use sanitized
}
```

### 4. ALWAYS Sanitize Error Messages

```typescript
// ❌ WRONG - Exposes internal details
catch (error: any) {
    return { error: error.message }; // May leak file paths, stack traces
}

// ✅ CORRECT - Safe error messages
import { sanitizeErrorMessage } from './security-utils';
catch (error: any) {
    return { error: sanitizeErrorMessage(error) };
}
```

---

## Security Utilities Reference

### TypeScript (`packages/arc-extension/src/node/security-utils.ts`)

#### `sanitizePrompt(prompt: string): string`
Validates and sanitizes user prompts.
- **Throws**: `Error` if prompt contains dangerous characters
- **Use**: Before executing any command with user input

```typescript
const safe = sanitizePrompt(userPrompt);
```

#### `validateTraceId(traceId: string): string`
Validates trace ID format.
- **Throws**: `Error` if trace ID is invalid or contains path traversal
- **Use**: Before accessing trace files

```typescript
const safeId = validateTraceId(userTraceId);
```

#### `validateFilePath(filePath: string, workspaceRoot: string): string`
Validates file path is within workspace.
- **Throws**: `Error` if path escapes workspace
- **Use**: Before any file system operation

```typescript
const safePath = validateFilePath(userPath, this.workspaceRoot);
```

#### `validateBackend(backend: string): string`
Validates backend option.
- **Throws**: `Error` if backend is not whitelisted
- **Use**: Before using backend parameter

```typescript
const safeBackend = validateBackend(userBackend);
```

#### `sanitizeErrorMessage(error: any): string`
Sanitizes error messages.
- **Returns**: Safe, generic error message
- **Use**: In all catch blocks before returning to client

```typescript
catch (error) {
    const safeMsg = sanitizeErrorMessage(error);
}
```

#### `validateWorkspaceRoot(workspaceRoot: string): string`
Validates workspace root directory.
- **Throws**: `Error` if workspace root is invalid
- **Use**: During service initialization

```typescript
this.workspaceRoot = validateWorkspaceRoot(process.cwd());
```

---

### Python (`python/src/security_utils.py`)

#### `sanitize_prompt(prompt: str) -> str`
Validates and sanitizes user prompts.
- **Raises**: `SecurityError` if prompt contains dangerous characters
- **Use**: Before executing any command with user input

```python
from security_utils import sanitize_prompt
safe = sanitize_prompt(user_prompt)
```

#### `validate_trace_id(trace_id: str) -> str`
Validates trace ID format.
- **Raises**: `SecurityError` if trace ID is invalid
- **Use**: Before accessing trace files

```python
from security_utils import validate_trace_id
safe_id = validate_trace_id(user_trace_id)
```

#### `validate_file_path(file_path: str, workspace_root: str) -> Path`
Validates file path is within workspace.
- **Raises**: `SecurityError` if path escapes workspace
- **Use**: Before any file system operation

```python
from security_utils import validate_file_path
safe_path = validate_file_path(user_path, WORKSPACE_ROOT)
```

#### `validate_backend(backend: str) -> str`
Validates backend option.
- **Raises**: `SecurityError` if backend is not whitelisted
- **Use**: Before using backend parameter

```python
from security_utils import validate_backend
safe_backend = validate_backend(user_backend)
```

#### `sanitize_error_message(error: Exception) -> str`
Sanitizes error messages.
- **Returns**: Safe, generic error message
- **Use**: In all except blocks before returning to client

```python
from security_utils import sanitize_error_message
except Exception as e:
    safe_msg = sanitize_error_message(e)
```

---

## Common Patterns

### Executing Commands Safely

```typescript
// TypeScript
import { spawn } from 'child_process';
import { sanitizePrompt } from './security-utils';

async function executeCommand(userPrompt: string) {
    const sanitized = sanitizePrompt(userPrompt);
    
    return new Promise((resolve, reject) => {
        const child = spawn('swarmgraph', ['swarm', '--json', sanitized], {
            cwd: this.workspaceRoot,
            shell: false, // CRITICAL: Must be false
            timeout: 300000
        });
        
        // Handle output...
    });
}
```

```python
# Python
import subprocess
from security_utils import sanitize_prompt

def execute_command(user_prompt: str):
    sanitized = sanitize_prompt(user_prompt)
    
    result = subprocess.run(
        ["swarmgraph", "swarm", "--json", sanitized],
        capture_output=True,
        shell=False,  # CRITICAL: Must be False
        timeout=300,
        cwd=str(WORKSPACE_ROOT)
    )
    
    return result
```

### Reading Files Safely

```typescript
// TypeScript
import { validateFilePath } from './security-utils';
import * as fs from 'fs-extra';

async function readFile(userPath: string) {
    const safePath = validateFilePath(userPath, this.workspaceRoot);
    return await fs.readFile(safePath, 'utf-8');
}
```

```python
# Python
from security_utils import validate_file_path
from pathlib import Path

def read_file(user_path: str):
    safe_path = validate_file_path(user_path, WORKSPACE_ROOT)
    return safe_path.read_text()
```

### Handling Errors Safely

```typescript
// TypeScript
import { sanitizeErrorMessage } from './security-utils';

try {
    // Operation
} catch (error) {
    return {
        status: 'failed',
        error: sanitizeErrorMessage(error)
    };
}
```

```python
# Python
from security_utils import sanitize_error_message, SecurityError
from fastapi import HTTPException

try:
    # Operation
except SecurityError as e:
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    raise HTTPException(status_code=500, detail=sanitize_error_message(e))
```

---

## Security Checklist for Code Reviews

When reviewing code, check for:

- [ ] User input is validated before use
- [ ] Commands use `spawn()`/`subprocess.run()` with `shell: false`
- [ ] File paths are validated with `validateFilePath()`
- [ ] Trace IDs are validated with `validateTraceId()`
- [ ] Error messages are sanitized before returning to client
- [ ] No user input is interpolated into strings used as commands
- [ ] All file operations are scoped to workspace
- [ ] Timeouts are set for long-running operations
- [ ] No sensitive information in logs or error messages

---

## Dangerous Patterns to Avoid

### ❌ String Interpolation in Commands

```typescript
// NEVER DO THIS
const cmd = `command ${userInput}`;
exec(cmd);
```

### ❌ Unsanitized File Paths

```typescript
// NEVER DO THIS
const path = `.arc/traces/${userInput}.jsonl`;
fs.readFile(path);
```

### ❌ Raw Error Messages

```typescript
// NEVER DO THIS
catch (error) {
    res.json({ error: error.message });
}
```

### ❌ Shell Execution

```typescript
// NEVER DO THIS
exec(command, { shell: true });
subprocess.run(command, shell=True);
```

---

## Testing Your Code

Always test security-critical code with malicious inputs:

```typescript
// Test cases to try
const maliciousInputs = [
    "test; rm -rf /",
    "test | cat /etc/passwd",
    "test `whoami`",
    "test $(whoami)",
    "../../../etc/passwd",
    "test\x00injection",
    "a".repeat(100000) // DoS attempt
];

for (const input of maliciousInputs) {
    try {
        sanitizePrompt(input);
        console.error(`SECURITY ISSUE: Input not blocked: ${input}`);
    } catch (error) {
        console.log(`✓ Blocked: ${input}`);
    }
}
```

---

## Getting Help

- **Security Documentation**: See `docs/SECURITY.md`
- **Security Audit Report**: See `SECURITY_AUDIT_REPORT.md`
- **Test Examples**: See `python/src/test_security.py`

For security questions or to report vulnerabilities:
- Create a security advisory on GitHub
- Do not disclose publicly until patched

---

## Quick Command Reference

```bash
# Run security tests (Python)
cd python && python -m pytest src/test_security.py -v

# Check TypeScript compilation
cd packages/arc-extension && npx tsc --noEmit

# Scan for potential security issues (if tools installed)
npm audit
pip-audit
```

---

**Remember**: Security is everyone's responsibility. When in doubt, validate!
