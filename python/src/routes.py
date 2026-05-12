"""
ARC Studio API Routes

Defines the REST API endpoints for ARC Studio backend.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import subprocess
import json
from pathlib import Path

app = FastAPI(title="ARC Studio API", version="0.1.0")


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
        # Execute swarmgraph CLI
        cmd = ["swarmgraph", "swarm", "--json", request.prompt]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
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
            error=result.stderr if result.returncode != 0 else None,
            trace_path=f".arc/traces/{run_id}.jsonl"
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Execution timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/traces", response_model=List[TraceInfo])
async def get_traces():
    """Get list of trace files"""
    traces_dir = Path(".arc/traces")
    
    if not traces_dir.exists():
        return []
    
    traces = []
    for trace_file in traces_dir.glob("*.jsonl"):
        try:
            with open(trace_file, 'r') as f:
                data = json.load(f)
                traces.append(TraceInfo(
                    id=data.get("id", trace_file.stem),
                    path=str(trace_file),
                    timestamp=data.get("started_at", ""),
                    status=data.get("status", "unknown")
                ))
        except Exception:
            continue
    
    return sorted(traces, key=lambda x: x.timestamp, reverse=True)


@app.get("/api/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Get a specific trace file"""
    trace_path = Path(f".arc/traces/{trace_id}.jsonl")
    
    if not trace_path.exists():
        raise HTTPException(status_code=404, detail="Trace not found")
    
    try:
        with open(trace_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
