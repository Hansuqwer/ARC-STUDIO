"""
ARC Studio API Routes

Defines the REST API endpoints for ARC Studio backend.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import subprocess
import json
import os
from security_utils import (
    sanitize_prompt,
    validate_trace_id,
    validate_file_path,
    validate_backend,
    sanitize_error_message,
    validate_workspace_root,
    SecurityError
)

app = FastAPI(title="ARC Studio API", version="0.1.0")

# Initialize workspace root
try:
    WORKSPACE_ROOT = validate_workspace_root(os.getcwd())
except SecurityError as e:
    raise RuntimeError(f"Failed to initialize workspace: {e}")

# Allow-list of environment variables passed to child processes
_ALLOWED_ENV = {
    "PATH", "HOME", "USER", "LANG", "LC_ALL", "TZ", "TMPDIR",
    "ARC_SWARMGRAPH_CLI",
    "ARC_SWARMGRAPH_RUN_BACKEND", "ARC_SWARMGRAPH_ALLOW_COSTS",
    "ARC_SWARMGRAPH_GATEWAY_URL", "ARC_SWARMGRAPH_GATEWAY_TOKEN",
}

def _allowed_subprocess_env() -> dict[str, str]:
    """Build a filtered environment dict containing only allow-listed vars."""
    return {k: v for k, v in os.environ.items() if k in _ALLOWED_ENV}


class ExecutionRequest(BaseModel):
    prompt: str
    backend: str = "gateway"
    cost_allowed: bool = True


class ExecutionResponse(BaseModel):
    run_id: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    trace_path: str


class TraceInfo(BaseModel):
    id: str
    path: str
    timestamp: str
    status: str


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "ARC Studio Backend"}


@app.post("/api/execute", response_model=ExecutionResponse)
async def execute_workflow(request: ExecutionRequest):
    """Execute a SwarmGraph workflow"""
    try:
        # Validate and sanitize inputs
        sanitized_prompt = sanitize_prompt(request.prompt)
        validated_backend = validate_backend(request.backend)
        
        # Build command with validated backend and cost flags
        cmd = [
            "swarmgraph", "swarm",
            "--json",
            "--backend", validated_backend,
            "--prompt", sanitized_prompt,
        ]
        if not request.cost_allowed:
            cmd.append("--no-cost")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=str(WORKSPACE_ROOT),  # Execute in workspace root
            shell=False,  # Critical: disable shell to prevent command injection
            env=_allowed_subprocess_env()  # P1: env allow-list
        )
        
        # Parse run ID from output
        run_id = "unknown"
        if "run-sg-" in result.stdout:
            import re
            match = re.search(r'run-sg-([a-f0-9]+)', result.stdout)
            if match:
                run_id = f"run-sg-{match.group(1)}"
        
        return ExecutionResponse(
            run_id=run_id,
            status="completed" if result.returncode == 0 else "failed",
            output=result.stdout if result.returncode == 0 else None,
            error="Workflow execution failed" if result.returncode != 0 else None,
            trace_path=f".arc/traces/{run_id}.jsonl"
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Execution timeout")
    except SecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_error_message(e))


@app.get("/api/traces", response_model=List[TraceInfo])
async def get_traces():
    """Get list of trace files"""
    try:
        traces_dir = WORKSPACE_ROOT / ".arc" / "traces"
        
        # Validate traces directory is within workspace
        validated_traces_dir = validate_file_path(".arc/traces", str(WORKSPACE_ROOT))
        
        if not validated_traces_dir.exists():
            return []
        
        traces = []
        for trace_file in validated_traces_dir.glob("*.jsonl"):
            try:
                # Additional validation: ensure file is still within traces directory
                if not str(trace_file.resolve()).startswith(str(validated_traces_dir.resolve())):
                    continue
                
                with open(trace_file, 'r') as f:
                    try:
                        data = json.load(f)
                        traces.append(TraceInfo(
                            id=data.get("id", trace_file.stem),
                            path=str(trace_file),
                            timestamp=data.get("started_at", ""),
                            status=data.get("status", "unknown")
                        ))
                    except json.JSONDecodeError:
                        # Skip malformed JSON files
                        continue
            except Exception:
                # Skip files that can't be read
                continue
        
        return sorted(traces, key=lambda x: x.timestamp, reverse=True)
    except Exception:
        # Return empty array on error rather than exposing error details
        return []


@app.get("/api/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get a specific trace file"""
    try:
        # Validate trace ID to prevent path traversal
        validated_trace_id = validate_trace_id(trace_id)
        
        # Construct path within workspace
        trace_path = WORKSPACE_ROOT / ".arc" / "traces" / f"{validated_trace_id}.jsonl"
        
        # Validate the full path is within workspace
        validated_path = validate_file_path(str(trace_path), str(WORKSPACE_ROOT))
        
        if not validated_path.exists():
            raise HTTPException(status_code=404, detail="Trace not found")
        
        with open(validated_path, 'r') as f:
            return json.load(f)
    except HTTPException:
        raise
    except SecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=sanitize_error_message(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
